"""Command-line interface for anki-voiced.

Follows clig.dev guidelines:
- Human-first design with machine-readable output via --json
- Progress indicators for operations >1s
- Clear error messages with suggestions
- Graceful Ctrl-C handling
"""

import json
import sys
import tempfile
from difflib import get_close_matches
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .audio import AudioGenerationInterrupted, AudioGenerator, get_preprocessor
from .config import (
    CACHE_DIR,
    Config,
    PROJECT_CONFIG_FILE,
    load_toml_file,
    should_use_color,
)
from .csv_utils import create_sample_csv, load_csv, load_csv_from_stdin
from .deck import DeckBuilder, create_generation_result, join_decks
from .models import (
    DeckConfig,
    LANGUAGES,
    LANGUAGE_ALIASES,
    TEMPLATES,
    TierConfig,
    VOICES,
    normalize_language,
)

app = typer.Typer(
    name="anki-voiced",
    help="Generate Anki flashcard decks with AI-voiced audio.",
    add_completion=False,
    no_args_is_help=True,
)

# Console for rich output
console = Console(force_terminal=should_use_color())

# Available language names for validation
AVAILABLE_LANGUAGES = list(LANGUAGES.keys()) + list(LANGUAGE_ALIASES.keys())


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"anki-voiced {__version__}")
        raise typer.Exit()


def suggest_language(input_lang: str) -> str | None:
    """Suggest a correct language name if input is close."""
    matches = get_close_matches(input_lang.lower(), AVAILABLE_LANGUAGES, n=1, cutoff=0.6)
    return matches[0] if matches else None


def print_error(message: str, suggestion: str | None = None) -> None:
    """Print an error message with optional suggestion."""
    console.print(f"[red]error:[/red] {message}")
    if suggestion:
        console.print(f"\n{suggestion}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]{message}[/green]")


def output_json(data: dict) -> None:
    """Output data as JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """anki-voiced: Generate Anki decks with AI-voiced audio."""
    pass


@app.command()
def create(
    data_file: Annotated[
        Optional[Path],
        typer.Argument(
            help="CSV file with vocabulary data (or - for stdin)",
        ),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output",
            "-o",
            help="Output .apkg file [default: DATA_FILE.apkg]",
        ),
    ] = None,
    name: Annotated[
        Optional[str],
        typer.Option(
            "--name",
            "-n",
            help="Deck name shown in Anki [default: filename]",
        ),
    ] = None,
    lang: Annotated[
        Optional[str],
        typer.Option(
            "--lang",
            "-l",
            help="Language: english, japanese, french, portuguese",
        ),
    ] = None,
    voice: Annotated[
        Optional[str],
        typer.Option(
            "--voice",
            "-v",
            help="Voice: male, female, or specific voice name",
        ),
    ] = None,
    template: Annotated[
        Optional[str],
        typer.Option(
            "--template",
            "-t",
            help="Card template: basic, double-card, cloze",
        ),
    ] = None,
    config_file: Annotated[
        Optional[Path],
        typer.Option(
            "--config",
            "-c",
            help="TOML config file (overrides other options)",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would be generated without creating files",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Regenerate audio even if cached",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Minimal output (for scripts)",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Machine-readable JSON output",
        ),
    ] = False,
) -> None:
    """Generate an Anki deck with AI-voiced audio from a CSV file.

    Examples:
      anki-voiced create vocab.csv
      anki-voiced create vocab.csv -o japanese.apkg --lang japanese
      anki-voiced create --config deck.toml
      cat data.csv | anki-voiced create - -o deck.apkg
    """
    # Load config with precedence
    cfg = Config()

    # If config file specified, load and use it
    project_config = {}
    if config_file:
        if not config_file.exists():
            print_error(f"Config file not found: {config_file}")
            raise typer.Exit(1)
        project_config = load_toml_file(config_file)
    elif cfg.has_project_config() and data_file is None:
        # Use project config if no data file specified
        project_config = cfg.project_config

    # Handle multi-tier config
    if project_config.get("tiers"):
        _create_multi_tier(project_config, quiet, json_output, force, dry_run)
        return

    # Determine data source
    from_stdin = data_file is not None and str(data_file) == "-"

    if data_file is None and not project_config:
        print_error("No data file specified")
        console.print("\nUsage: anki-voiced create DATA_FILE [OPTIONS]")
        console.print("       anki-voiced create --config deck.toml")
        raise typer.Exit(1)

    # Get input file from config or argument
    if not from_stdin:
        csv_path = data_file or Path(project_config.get("data", "vocabulary.csv"))
        if not csv_path.exists():
            print_error(f"CSV file not found: {csv_path}")
            raise typer.Exit(1)

    # Resolve options with precedence
    resolved_lang = cfg.get("language", "english", lang or project_config.get("language"))
    resolved_voice = cfg.get("voice", "female", voice or project_config.get("voice"))
    resolved_template = cfg.get("template", "double-card", template or project_config.get("template"))

    # Normalize and validate language
    normalized_lang = normalize_language(resolved_lang)
    if normalized_lang not in LANGUAGES:
        suggestion = suggest_language(resolved_lang)
        msg = f"unknown language '{resolved_lang}'"
        if suggestion:
            msg += f"\n\n  Did you mean: {suggestion}?"
        msg += f"\n\n  Available languages: {', '.join(LANGUAGES.keys())}"
        msg += "\n  Run 'anki-voiced voices' to see all available voices"
        print_error(msg)
        raise typer.Exit(1)

    # Validate template
    if resolved_template not in TEMPLATES:
        print_error(
            f"unknown template '{resolved_template}'\n\n"
            f"  Available templates: {', '.join(TEMPLATES)}"
        )
        raise typer.Exit(1)

    # Determine deck name
    if name:
        deck_name = name
    elif project_config.get("name"):
        deck_name = project_config["name"]
    elif not from_stdin:
        deck_name = csv_path.stem.replace("-", " ").replace("_", " ").title()
    else:
        deck_name = "My Vocabulary"

    # Determine output path
    if output:
        output_path = output
    elif project_config.get("output"):
        output_path = Path(project_config["output"])
    elif not from_stdin:
        output_path = csv_path.with_suffix(".apkg")
    else:
        output_path = Path("deck.apkg")

    # Create deck config
    deck_config = DeckConfig(
        name=deck_name,
        input_csv=csv_path if not from_stdin else None,
        output=output_path,
        language=normalized_lang,
        voice=resolved_voice,
        template=resolved_template,
        force=force,
        dry_run=dry_run,
    )

    # Load vocabulary
    try:
        if from_stdin:
            entries = load_csv_from_stdin(resolved_template)
        else:
            entries = load_csv(csv_path, resolved_template)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)

    if not entries:
        print_error("CSV file is empty")
        raise typer.Exit(1)

    # Dry run - show what would be generated
    if dry_run:
        builder = DeckBuilder(deck_config)
        card_count = builder.get_card_count(entries)

        if json_output:
            output_json({
                "dry_run": True,
                "output": str(output_path),
                "cards": card_count,
                "notes": len(entries),
                "template": resolved_template,
                "language": normalized_lang,
                "voice": deck_config.resolved_voice,
            })
        else:
            console.print(f"Would create: [cyan]{output_path}[/cyan]")
            console.print(f"  {len(entries)} notes ({resolved_template} template)")
            console.print(f"  {card_count} cards")
            console.print(f"  Language: {normalized_lang}")
            console.print(f"  Voice: {deck_config.resolved_voice}")
        raise typer.Exit(0)

    # Generate audio
    audio_dir = None
    generated_audio = 0
    cached_audio = 0

    if not quiet:
        console.print(f"Loading {csv_path.name if not from_stdin else 'stdin'}... {len(entries)} sentences")

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_dir = Path(tmpdir) / "audio"

        try:
            generator = AudioGenerator(deck_config, quiet=quiet)
            preprocessor = get_preprocessor(normalized_lang)
            entries, generated_audio, cached_audio = generator.generate_batch(
                entries,
                audio_dir,
                prefix="card",
                preprocess=preprocessor,
            )
        except AudioGenerationInterrupted:
            console.print("\n[yellow]Interrupted.[/yellow] Partial audio cached in ~/.cache/anki-voiced/")
            console.print("Run again to resume from where you left off.")
            raise typer.Exit(130)  # Standard exit code for SIGINT

        # Build deck
        if not quiet:
            console.print("Building deck...")

        builder = DeckBuilder(deck_config)
        actual_output = builder.build(entries, audio_dir)

    # Output result
    result = create_generation_result(
        actual_output, entries, deck_config, generated_audio, cached_audio
    )

    if json_output:
        output_json({
            "success": True,
            "output": str(result.output_path),
            "cards": result.card_count,
            "notes": result.note_count,
            "audio_files": result.audio_count,
            "generated_audio": result.generated_audio,
            "cached_audio": result.cached_audio,
            "template": result.template,
            "language": result.language,
            "voice": result.voice,
        })
    elif quiet:
        print(actual_output)
    else:
        # Calculate file size
        size_mb = actual_output.stat().st_size / (1024 * 1024)

        console.print(f"[green]Created {actual_output}[/green] ({size_mb:.1f} MB, {result.card_count} cards)")
        if cached_audio > 0:
            console.print(f"  Audio: {generated_audio} generated, {cached_audio} from cache")


def _create_multi_tier(
    config: dict,
    quiet: bool,
    json_output: bool,
    force: bool,
    dry_run: bool,
) -> None:
    """Handle multi-tier deck creation from config."""
    deck_name = config.get("name", "Multi-Tier Deck")
    language = config.get("language", "english")
    voice = config.get("voice", "female")
    template = config.get("template", "double-card")
    output_path = Path(config.get("output", f"{deck_name.lower().replace(' ', '-')}.apkg"))
    tiers = config.get("tiers", [])

    if not tiers:
        print_error("No tiers defined in config")
        raise typer.Exit(1)

    normalized_lang = normalize_language(language)

    if dry_run:
        console.print(f"Would create: [cyan]{output_path}[/cyan]")
        console.print(f"  Master deck: {deck_name}")
        for tier in tiers:
            console.print(f"  - {tier.get('name')}: {tier.get('data')}")
        raise typer.Exit(0)

    if not quiet:
        console.print(f"Creating multi-tier deck: [bold]{deck_name}[/bold]")

    all_entries = []
    tier_decks = []

    for tier_data in tiers:
        tier_config = TierConfig(**tier_data)
        tier_path = Path(tier_config.data)

        if not tier_path.exists():
            print_error(f"Tier data file not found: {tier_path}")
            raise typer.Exit(1)

        entries = load_csv(tier_path, template)

        if not quiet:
            console.print(f"  {tier_config.name}: {len(entries)} sentences")

        all_entries.extend(entries)

    # Generate all audio
    deck_config = DeckConfig(
        name=deck_name,
        output=output_path,
        language=normalized_lang,
        voice=voice,
        template=template,
        force=force,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_dir = Path(tmpdir) / "audio"

        try:
            generator = AudioGenerator(deck_config, quiet=quiet)
            preprocessor = get_preprocessor(normalized_lang)
            all_entries, generated, cached = generator.generate_batch(
                all_entries,
                audio_dir,
                prefix="card",
                preprocess=preprocessor,
            )
        except AudioGenerationInterrupted:
            console.print("\n[yellow]Interrupted.[/yellow]")
            raise typer.Exit(130)

        # Build combined deck
        builder = DeckBuilder(deck_config)
        actual_output = builder.build(all_entries, audio_dir)

    if quiet:
        print(actual_output)
    else:
        size_mb = actual_output.stat().st_size / (1024 * 1024)
        console.print(f"[green]Created {actual_output}[/green] ({size_mb:.1f} MB)")


@app.command()
def join(
    deck_files: Annotated[
        list[Path],
        typer.Argument(help="Two or more .apkg files to combine"),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output .apkg file (required)",
        ),
    ],
    name: Annotated[
        str,
        typer.Option(
            "--name",
            "-n",
            help="Master deck name (required)",
        ),
    ],
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Minimal output",
        ),
    ] = False,
) -> None:
    """Combine multiple .apkg files into one master deck.

    Examples:
      anki-voiced join tier1.apkg tier2.apkg -o complete.apkg -n "Japanese IT"
    """
    if len(deck_files) < 2:
        print_error("At least two deck files are required")
        raise typer.Exit(1)

    # Validate all files exist
    for deck_file in deck_files:
        if not deck_file.exists():
            print_error(f"Deck file not found: {deck_file}")
            raise typer.Exit(1)

    if not quiet:
        console.print(f"Combining {len(deck_files)} decks into [bold]{name}[/bold]")

    try:
        result_path = join_decks(deck_files, output, name)
    except Exception as e:
        print_error(f"Failed to join decks: {e}")
        raise typer.Exit(1)

    if quiet:
        print(result_path)
    else:
        console.print(f"[green]Created {result_path}[/green]")


@app.command("init")
def init_project(
    lang: Annotated[
        str,
        typer.Option(
            "--lang",
            "-l",
            help="Language for sample content [default: english]",
        ),
    ] = "english",
    template: Annotated[
        str,
        typer.Option(
            "--template",
            "-t",
            help="Template to use [default: double-card]",
        ),
    ] = "double-card",
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Minimal output",
        ),
    ] = False,
) -> None:
    """Create a new deck project with sample files.

    Creates:
      vocabulary.csv     Sample vocabulary file
      deck.toml          Configuration file (for multi-tier decks)
    """
    normalized_lang = normalize_language(lang)

    vocab_path = Path("vocabulary.csv")
    config_path = Path(PROJECT_CONFIG_FILE)

    # Create sample CSV
    create_sample_csv(vocab_path, normalized_lang, template)

    # Create sample config
    config_content = f'''# anki-voiced deck configuration
name = "My Vocabulary Deck"
language = "{normalized_lang}"
voice = "female"
template = "{template}"
output = "my-vocabulary.apkg"

# Uncomment for multi-tier deck:
# [[tiers]]
# name = "Tier 1 - Basics"
# data = "tier1.csv"
#
# [[tiers]]
# name = "Tier 2 - Intermediate"
# data = "tier2.csv"
'''

    with open(config_path, "w") as f:
        f.write(config_content)

    if quiet:
        print(vocab_path)
        print(config_path)
    else:
        console.print("Created:")
        console.print(f"  [cyan]vocabulary.csv[/cyan]  (sample {normalized_lang} sentences)")
        console.print(f"  [cyan]deck.toml[/cyan]       (configuration file)")
        console.print()
        console.print("Next steps:")
        console.print("  1. Edit vocabulary.csv with your content")
        console.print("  2. Run: [cyan]anki-voiced create vocabulary.csv[/cyan]")
        console.print("  3. Import the .apkg file into Anki")


@app.command()
def voices(
    lang: Annotated[
        Optional[str],
        typer.Option(
            "--lang",
            "-l",
            help="Filter by language",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Machine-readable JSON output",
        ),
    ] = False,
) -> None:
    """List available voices for text-to-speech.

    Examples:
      anki-voiced voices
      anki-voiced voices --lang japanese
    """
    # Filter by language if specified
    if lang:
        normalized = normalize_language(lang)
        if normalized not in VOICES:
            suggestion = suggest_language(lang)
            msg = f"unknown language '{lang}'"
            if suggestion:
                msg += f"\n\n  Did you mean: {suggestion}?"
            msg += f"\n\n  Available languages: {', '.join(LANGUAGES.keys())}"
            print_error(msg)
            raise typer.Exit(1)

        languages_to_show = {normalized: VOICES[normalized]}
    else:
        languages_to_show = VOICES

    if json_output:
        output_json({"voices": languages_to_show})
        return

    table = Table(title="Available Voices")
    table.add_column("Language", style="cyan")
    table.add_column("Male Voices", style="blue")
    table.add_column("Female Voices", style="magenta")

    for language, voice_dict in languages_to_show.items():
        male_voices = ", ".join(voice_dict.get("male", [])) or "-"
        female_voices = ", ".join(voice_dict.get("female", [])) or "-"
        table.add_row(language.title(), male_voices, female_voices)

    console.print(table)

    if not lang:
        console.print()
        console.print("Use --lang to filter, e.g.: anki-voiced voices --lang japanese")


if __name__ == "__main__":
    app()
