"""Command-line interface for anki-voiced."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .audio import AudioGenerator
from .csv_utils import create_sample_csv, load_csv
from .deck import DeckBuilder
from .models import DeckConfig, VOICES, LANG_CODES

app = typer.Typer(
    name="anki-voiced",
    help="Turn any vocabulary list into a professional Anki deck with native-quality audio.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"anki-voiced {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """anki-voiced: Your vocabulary, voiced."""
    pass


@app.command()
def generate(
    csv_file: Annotated[Path, typer.Argument(help="Path to vocabulary CSV file")],
    name: Annotated[str, typer.Option("--name", "-n", help="Deck name")] = "My Vocabulary",
    language: Annotated[
        str, typer.Option("--lang", "-l", help="Target language code (ja, en, zh, ko, fr, es)")
    ] = "ja",
    voice: Annotated[
        str, typer.Option("--voice", help="Voice gender (male/female)")
    ] = "male",
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory")
    ] = Path("."),
    no_audio: Annotated[
        bool, typer.Option("--no-audio", help="Skip audio generation")
    ] = False,
    template: Annotated[
        str, typer.Option("--template", "-t", help="Card template (two-card/basic)")
    ] = "two-card",
) -> None:
    """Generate an Anki deck from a CSV file with TTS audio."""
    # Validate inputs
    if not csv_file.exists():
        console.print(f"[red]Error:[/red] CSV file not found: {csv_file}")
        raise typer.Exit(1)

    if language not in LANG_CODES:
        console.print(f"[red]Error:[/red] Unsupported language: {language}")
        console.print(f"Supported: {', '.join(LANG_CODES.keys())}")
        raise typer.Exit(1)

    # Create config
    config = DeckConfig(
        name=name,
        input_csv=csv_file,
        output_dir=output,
        language=language,
        voice_gender=voice,  # type: ignore
        include_audio=not no_audio,
        card_template=template,  # type: ignore
    )

    # Load vocabulary
    console.print(f"\n[bold]Loading vocabulary from:[/bold] {csv_file}")
    entries = load_csv(csv_file)
    console.print(f"[green]Found {len(entries)} entries[/green]\n")

    # Generate audio
    audio_dir = None
    if config.include_audio:
        audio_dir = output / "audio"
        console.print(f"[bold]Generating audio with voice:[/bold] {config.voice}")
        console.print(f"[dim]This may take a while (~8 sec per entry)...[/dim]\n")

        generator = AudioGenerator(config)
        entries = generator.generate_batch(entries, audio_dir, prefix="card")

        audio_count = sum(1 for e in entries if e.audio_file)
        console.print(f"\n[green]Generated {audio_count} audio files[/green]\n")

    # Build deck
    console.print(f"[bold]Building Anki deck:[/bold] {name}")
    builder = DeckBuilder(config)
    output_path = builder.build(entries, audio_dir)

    # Summary
    cards_per_note = 2 if template == "two-card" else 1
    console.print(
        Panel(
            f"[green bold]Deck created successfully![/green bold]\n\n"
            f"[bold]Output:[/bold] {output_path}\n"
            f"[bold]Notes:[/bold] {len(entries)}\n"
            f"[bold]Cards:[/bold] {len(entries) * cards_per_note}\n"
            f"[bold]Audio:[/bold] {'Yes' if config.include_audio else 'No'}",
            title="Complete",
            border_style="green",
        )
    )


@app.command()
def init(
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory")
    ] = Path("."),
    language: Annotated[
        str, typer.Option("--lang", "-l", help="Sample language")
    ] = "ja",
) -> None:
    """Create a sample CSV file to get started."""
    sample_path = output / "vocabulary.csv"

    if sample_path.exists():
        overwrite = typer.confirm(f"{sample_path} already exists. Overwrite?")
        if not overwrite:
            raise typer.Exit()

    output.mkdir(parents=True, exist_ok=True)
    create_sample_csv(sample_path, language)

    console.print(
        Panel(
            f"[green]Created sample CSV:[/green] {sample_path}\n\n"
            f"Edit this file with your vocabulary, then run:\n"
            f"[cyan]anki-voiced generate {sample_path}[/cyan]",
            title="Ready to start",
            border_style="blue",
        )
    )


@app.command()
def voices() -> None:
    """List available TTS voices."""
    table = Table(title="Available Voices")
    table.add_column("Language", style="cyan")
    table.add_column("Code", style="green")
    table.add_column("Male Voice", style="blue")
    table.add_column("Female Voice", style="magenta")

    lang_names = {
        "ja": "Japanese",
        "en": "English",
        "zh": "Chinese",
        "ko": "Korean",
        "fr": "French",
        "es": "Spanish",
    }

    for code, voices in VOICES.items():
        table.add_row(
            lang_names.get(code, code),
            code,
            voices["male"],
            voices["female"],
        )

    console.print(table)


@app.command()
def preview(
    csv_file: Annotated[Path, typer.Argument(help="Path to vocabulary CSV file")],
    count: Annotated[int, typer.Option("--count", "-n", help="Number of entries to preview")] = 5,
) -> None:
    """Preview entries from a CSV file without generating anything."""
    if not csv_file.exists():
        console.print(f"[red]Error:[/red] CSV file not found: {csv_file}")
        raise typer.Exit(1)

    entries = load_csv(csv_file)

    table = Table(title=f"Preview: {csv_file.name} ({len(entries)} total entries)")
    table.add_column("#", style="dim")
    table.add_column("Front", style="cyan")
    table.add_column("Back", style="green")
    table.add_column("Pronunciation", style="yellow")
    table.add_column("Tags", style="magenta")

    for i, entry in enumerate(entries[:count], 1):
        table.add_row(
            str(i),
            entry.front[:40] + ("..." if len(entry.front) > 40 else ""),
            entry.back[:40] + ("..." if len(entry.back) > 40 else ""),
            entry.pronunciation[:20] + ("..." if len(entry.pronunciation) > 20 else ""),
            ", ".join(entry.tags[:3]),
        )

    console.print(table)

    if len(entries) > count:
        console.print(f"\n[dim]Showing {count} of {len(entries)} entries[/dim]")


if __name__ == "__main__":
    app()
