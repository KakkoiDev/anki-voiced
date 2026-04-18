"""Command-line interface for anki-voiced (Japanese only).

Commands:
  anki-voiced init <slug>                     # scaffold a new deck
  anki-voiced create --deck <slug>            # build .apkg for a deck
  anki-voiced create <csv> -o <out.apkg>      # one-shot build from a CSV
  anki-voiced audio --deck <slug> [--tier N]  # generate Edge TTS audio
  anki-voiced pitch --deck <slug> [--tier N]  # generate PitchAccent HTML
  anki-voiced validate --deck <slug> [...]    # check CSVs (and audio)
  anki-voiced voices                          # list Edge TTS voices
  anki-voiced join <apkg>... -o ... -n ...    # combine built decks
"""

import csv
import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .audio import AudioGenerationInterrupted, AudioGenerator
from .config import get_decks_root, should_use_color
from .csv_utils import count_rows, missing_required_columns
from .deck import (
    build_combined_package,
    build_single_tier_package,
    join_decks as _join_decks,
    load_tier_entries,
    write_tier_entries,
)
from .deck_config import list_decks, load_deck_config, scaffold_deck
from .models import VOICES, VocabEntry
from .pitch_accent import get_pitch_html
from .validation import validate_tier

app = typer.Typer(
    name="anki-voiced",
    help="Generate Japanese Anki decks with AI-voiced audio, furigana, and pitch accent.",
    add_completion=False,
    no_args_is_help=True,
)

console = Console(force_terminal=should_use_color())


def _print_error(message: str) -> None:
    console.print(f"[red]error:[/red] {message}")


def _print_success(message: str) -> None:
    console.print(f"[green]{message}[/green]")


def _output_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


def _version_callback(value: bool) -> None:
    if value:
        print(f"anki-voiced {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """anki-voiced: Japanese Anki deck builder."""


# ---------- init ----------

@app.command("init")
def init_cmd(
    slug: Annotated[str, typer.Argument(help="Deck slug (directory name under decks/)")],
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Human-readable deck name"),
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q")] = False,
) -> None:
    """Scaffold decks/<slug>/ with deck.toml and tier1-vocabulary.csv."""
    deck_dir = scaffold_deck(slug, name=name)
    if not quiet:
        console.print(f"Scaffolded [cyan]{deck_dir}[/cyan]")
        console.print("  deck.toml")
        console.print("  tier1-vocabulary.csv")
        console.print()
        console.print("Next steps:")
        console.print(f"  1. Edit [cyan]{deck_dir}/tier1-vocabulary.csv[/cyan]")
        console.print(f"  2. [cyan]anki-voiced validate --deck {slug}[/cyan]")
        console.print(f"  3. [cyan]anki-voiced pitch --deck {slug}[/cyan]")
        console.print(f"  4. [cyan]anki-voiced audio --deck {slug}[/cyan]")
        console.print(f"  5. [cyan]anki-voiced create --deck {slug}[/cyan]")
    else:
        print(deck_dir)


# ---------- pitch ----------

@app.command("pitch")
def pitch_cmd(
    deck: Annotated[Optional[str], typer.Option("--deck", "-d", help="Deck slug")] = None,
    tier: Annotated[Optional[int], typer.Option("--tier", "-t")] = None,
    csv_file: Annotated[
        Optional[Path],
        typer.Option("--csv", help="One-off: process a single CSV file"),
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q")] = False,
) -> None:
    """Generate/refresh the PitchAccent column for a deck tier (or a CSV)."""
    targets: list[Path] = []

    if csv_file:
        targets = [csv_file]
    elif deck:
        config = load_deck_config(deck)
        decks_root = get_decks_root()
        tiers = [tier] if tier else list(config.tier_range())
        for t in tiers:
            targets.append(config.csv_path(decks_root, t))
    else:
        _print_error("Provide --deck <slug> or --csv <path>")
        raise typer.Exit(1)

    for path in targets:
        if not path.exists():
            _print_error(f"CSV not found: {path}")
            raise typer.Exit(1)
        _apply_pitch(path, quiet)


def _apply_pitch(csv_path: Path, quiet: bool) -> None:
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if "PitchAccent" not in fieldnames:
        fieldnames.append("PitchAccent")
    if "Audio" not in fieldnames:
        fieldnames.append("Audio")

    filled = 0
    for row in rows:
        cloze = row.get("Cloze", "") or ""
        pron = row.get("Pronunciation", "") or ""
        html = get_pitch_html(cloze, pron) if cloze else ""
        row["PitchAccent"] = html
        if html:
            filled += 1

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    if not quiet:
        console.print(f"  {csv_path.name}: {len(rows)} rows, {filled} with pitch accent")


# ---------- audio ----------

@app.command("audio")
def audio_cmd(
    deck: Annotated[Optional[str], typer.Option("--deck", "-d")] = None,
    tier: Annotated[Optional[int], typer.Option("--tier", "-t")] = None,
    voice: Annotated[str, typer.Option("--voice", "-v", help="male|female|<edge-tts voice id>")] = "male",
    force: Annotated[bool, typer.Option("--force", help="Regenerate even if cached")] = False,
    female: Annotated[bool, typer.Option("--female", help="Shortcut for --voice female")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q")] = False,
) -> None:
    """Generate Edge TTS audio for a deck tier."""
    if female:
        voice = "female"

    if not deck:
        _print_error("--deck is required")
        raise typer.Exit(1)

    config = load_deck_config(deck)
    decks_root = get_decks_root()
    tiers = [tier] if tier else list(config.tier_range())

    generator = AudioGenerator(voice=voice, force=force, quiet=quiet)

    for t in tiers:
        csv_path = config.csv_path(decks_root, t)
        if not csv_path.exists():
            _print_error(f"Missing CSV: {csv_path}")
            raise typer.Exit(1)
        entries = load_tier_entries(csv_path)
        audio_dir = config.audio_dir(decks_root, t, female=(voice == "female"))
        audio_dir.mkdir(parents=True, exist_ok=True)

        if not quiet:
            console.print(
                f"\nTier {t}: {len(entries)} entries  "
                f"voice=[cyan]{generator.resolved_voice}[/cyan]  "
                f"out=[cyan]{audio_dir}[/cyan]"
            )

        def filename_fn(idx: int, _t=t) -> str:
            return f"tier{_t}_{idx:03d}.mp3"

        try:
            entries, generated, cached = generator.generate_batch(
                entries, audio_dir, filename_fn=filename_fn
            )
        except AudioGenerationInterrupted:
            console.print("\n[yellow]Interrupted[/yellow] (partial cache preserved)")
            raise typer.Exit(130)

        if not quiet:
            console.print(f"  generated={generated} cached={cached}")

        # Write Audio column back to CSV for downstream steps
        write_tier_entries(csv_path, entries)


# ---------- validate ----------

@app.command("validate")
def validate_cmd(
    deck: Annotated[Optional[str], typer.Option("--deck", "-d")] = None,
    tier: Annotated[Optional[int], typer.Option("--tier", "-t")] = None,
    csv_file: Annotated[
        Optional[Path],
        typer.Argument(help="One-off: validate a single CSV file"),
    ] = None,
    check_audio: Annotated[bool, typer.Option("--check-audio", "-a")] = False,
    female: Annotated[bool, typer.Option("--female")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-V")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Validate tier CSV(s) and (optionally) audio files."""
    if csv_file:
        _validate_one_csv(csv_file, json_output, verbose)
        return

    if not deck:
        _print_error("Provide --deck <slug> or a CSV file path")
        raise typer.Exit(1)

    config = load_deck_config(deck)
    decks_root = get_decks_root()
    tiers = [tier] if tier else list(config.tier_range())

    results = []
    for t in tiers:
        res = validate_tier(config, t, decks_root, check_audio=check_audio, female=female)
        results.append(res)

    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)

    if json_output:
        _output_json({
            "deck": deck,
            "tiers": [
                {
                    "tier": r.tier,
                    "rows": r.row_count,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "furigana": {"valid": r.furigana_valid, "total": r.furigana_total},
                    "key_meaning": {"valid": r.key_meaning_valid, "total": r.key_meaning_total},
                    "audio": {"valid": r.audio_valid, "total": r.audio_total},
                }
                for r in results
            ],
            "valid": total_errors == 0,
        })
        raise typer.Exit(0 if total_errors == 0 else 1)

    for r in results:
        console.print(f"\nTier {r.tier}: {r.row_count} rows")
        if r.csv_valid:
            console.print("  CSV: [green]OK[/green]")
        else:
            console.print("  CSV: [red]FAIL[/red]")
        if r.furigana_total:
            ok = r.furigana_valid == r.furigana_total
            console.print(f"  Furigana: {r.furigana_valid}/{r.furigana_total} {'[green]OK[/green]' if ok else '[red]FAIL[/red]'}")
        if r.key_meaning_total:
            ok = r.key_meaning_valid == r.key_meaning_total
            console.print(
                f"  KeyMeaning: {r.key_meaning_valid}/{r.key_meaning_total} "
                f"{'[green]OK[/green]' if ok else '[yellow]WARN[/yellow]'}"
            )
        if r.audio_total:
            ok = r.audio_valid == r.audio_total
            console.print(f"  Audio: {r.audio_valid}/{r.audio_total} {'[green]OK[/green]' if ok else '[red]FAIL[/red]'}")
        if verbose:
            for e in r.errors[:10]:
                console.print(f"    [red]error:[/red] {e}")
            for w in r.warnings[:10]:
                console.print(f"    [yellow]warn:[/yellow] {w}")

    console.print()
    if total_errors == 0:
        _print_success(f"Validation passed ({total_warnings} warnings)")
    else:
        _print_error(f"Validation failed: {total_errors} errors, {total_warnings} warnings")
        raise typer.Exit(1)


def _validate_one_csv(csv_file: Path, json_output: bool, verbose: bool) -> None:
    if not csv_file.exists():
        _print_error(f"CSV not found: {csv_file}")
        raise typer.Exit(1)
    missing = missing_required_columns(csv_file)
    rows = count_rows(csv_file)
    if json_output:
        _output_json({"csv": str(csv_file), "rows": rows, "missing_columns": sorted(missing)})
        raise typer.Exit(0 if not missing else 1)
    console.print(f"\n[cyan]{csv_file}[/cyan]: {rows} rows")
    if missing:
        _print_error(f"Missing columns: {', '.join(sorted(missing))}")
        raise typer.Exit(1)
    _print_success("OK")


# ---------- create ----------

@app.command("create")
def create_cmd(
    data_file: Annotated[Optional[Path], typer.Argument(help="CSV file (one-shot mode)")] = None,
    deck: Annotated[Optional[str], typer.Option("--deck", "-d", help="Deck slug")] = None,
    tier: Annotated[Optional[int], typer.Option("--tier", "-t")] = None,
    output: Annotated[Optional[Path], typer.Option("--output", "-o")] = None,
    combined: Annotated[bool, typer.Option("--combined", help="Combined .apkg with tier subdecks")] = True,
    quiet: Annotated[bool, typer.Option("--quiet", "-q")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Build .apkg for a deck (default) or from a single CSV (one-shot)."""
    if data_file and deck:
        _print_error("Pass either a CSV file or --deck, not both")
        raise typer.Exit(1)

    if data_file:
        _create_from_csv(data_file, output, quiet, json_output)
        return
    if not deck:
        _print_error("Provide --deck <slug> or a CSV file path")
        raise typer.Exit(1)

    config = load_deck_config(deck)
    decks_root = get_decks_root()

    if tier:
        entries = load_tier_entries(config.csv_path(decks_root, tier))
        audio_dir = config.audio_dir(decks_root, tier)
        out_path = output or Path(f"{deck}-tier{tier}.apkg")
        result = build_single_tier_package(config, tier, entries, audio_dir, out_path)
    else:
        tiers_data = []
        for t in config.tier_range():
            entries = load_tier_entries(config.csv_path(decks_root, t))
            audio_dir = config.audio_dir(decks_root, t)
            tiers_data.append((t, entries, audio_dir))
        out_path = output or Path(f"{deck}-complete.apkg" if combined else f"{deck}.apkg")
        result = build_combined_package(config, tiers_data, out_path)

    if json_output:
        _output_json({
            "output": str(result.output_path),
            "notes": result.note_count,
            "cards": result.card_count,
            "audio": result.audio_count,
        })
    elif not quiet:
        size_mb = result.output_path.stat().st_size / (1024 * 1024)
        console.print(
            f"\n[green]Created {result.output_path}[/green] "
            f"({size_mb:.1f} MB, {result.note_count} notes, {result.card_count} cards, "
            f"{result.audio_count} audio files)"
        )


def _create_from_csv(csv_path: Path, output: Path | None, quiet: bool, json_output: bool) -> None:
    """One-shot build: expects the 9-column schema; uses one synthetic tier."""
    from .models import DeckConfig as _DC, TierConfig as _TC
    import hashlib
    import tempfile

    if not csv_path.exists():
        _print_error(f"CSV not found: {csv_path}")
        raise typer.Exit(1)

    entries = load_tier_entries(csv_path)
    name = csv_path.stem.replace("-", " ").replace("_", " ").title()
    h = int(hashlib.sha256(name.encode()).hexdigest(), 16)
    config = _DC(
        slug=csv_path.stem,
        name=name,
        model_id=1_000_000_000 + (h % 1_000_000_000),
        deck_base_id=2_000_000_000 + ((h >> 32) % 1_000_000_000),
        tiers=[_TC(number=1, name="Tier 1", size=len(entries))],
    )

    out_path = output or csv_path.with_suffix(".apkg")

    with tempfile.TemporaryDirectory() as tmp:
        audio_dir = Path(tmp) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Look for pre-generated audio in <csv_stem>-audio/ beside the CSV
        preset = csv_path.parent / f"{csv_path.stem}-audio"
        if preset.exists():
            audio_dir = preset

        result = build_single_tier_package(config, 1, entries, audio_dir, out_path)

    if json_output:
        _output_json({
            "output": str(result.output_path),
            "notes": result.note_count,
            "cards": result.card_count,
            "audio": result.audio_count,
        })
    elif not quiet:
        size_mb = result.output_path.stat().st_size / (1024 * 1024)
        console.print(
            f"\n[green]Created {result.output_path}[/green] "
            f"({size_mb:.1f} MB, {result.note_count} notes, {result.card_count} cards)"
        )


# ---------- join ----------

@app.command("join")
def join_cmd(
    deck_files: Annotated[list[Path], typer.Argument(help="Two or more .apkg files")],
    output: Annotated[Path, typer.Option("--output", "-o")],
    name: Annotated[str, typer.Option("--name", "-n")],
    quiet: Annotated[bool, typer.Option("--quiet", "-q")] = False,
) -> None:
    """Combine multiple .apkg files into one master deck."""
    if len(deck_files) < 2:
        _print_error("At least two deck files are required")
        raise typer.Exit(1)
    for p in deck_files:
        if not p.exists():
            _print_error(f"Deck not found: {p}")
            raise typer.Exit(1)

    _join_decks(deck_files, output, name)
    if not quiet:
        _print_success(f"Created {output}")
    else:
        print(output)


# ---------- voices ----------

@app.command("voices")
def voices_cmd(
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List available Edge TTS Japanese voices."""
    if json_output:
        _output_json({"voices": VOICES})
        return

    table = Table(title="Edge TTS Japanese voices")
    table.add_column("Gender", style="cyan")
    table.add_column("Voice ID", style="magenta")

    for gender, voice_id in VOICES.items():
        table.add_row(gender, voice_id)

    console.print(table)


# ---------- decks ----------

@app.command("decks")
def decks_cmd(
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List all configured decks in decks/."""
    slugs = list_decks()
    if json_output:
        data = []
        for slug in slugs:
            try:
                cfg = load_deck_config(slug)
                data.append({
                    "slug": slug,
                    "name": cfg.name,
                    "tiers": cfg.tier_count,
                    "total_size": sum(t.size for t in cfg.tiers),
                })
            except Exception as e:  # noqa: BLE001
                data.append({"slug": slug, "error": str(e)})
        _output_json({"decks": data})
        return

    if not slugs:
        console.print("[yellow]No decks found[/yellow]")
        console.print(f"Create one with: [cyan]anki-voiced init <slug>[/cyan]")
        return

    table = Table(title="Configured decks")
    table.add_column("Slug", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Tiers", justify="right", style="magenta")
    table.add_column("Entries", justify="right", style="green")

    for slug in slugs:
        try:
            cfg = load_deck_config(slug)
            table.add_row(slug, cfg.name, str(cfg.tier_count), str(sum(t.size for t in cfg.tiers)))
        except Exception as e:  # noqa: BLE001
            table.add_row(slug, f"[red]error: {e}[/red]", "-", "-")

    console.print(table)


if __name__ == "__main__":
    app()
