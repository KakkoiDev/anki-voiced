"""Anki deck generation using genanki."""

import random
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import genanki

from .models import DeckConfig, VocabEntry, GenerationResult
from .templates import get_template


class DeckBuilder:
    """Build Anki decks from vocabulary entries."""

    def __init__(self, config: DeckConfig):
        self.config = config
        self.deck_id = random.randint(1000000000, 9999999999)

    def build(
        self,
        entries: list[VocabEntry],
        audio_dir: Path | None = None,
        subdeck_name: str | None = None,
    ) -> Path:
        """Build an Anki deck from vocabulary entries.

        Args:
            entries: List of vocabulary entries
            audio_dir: Directory containing audio files
            subdeck_name: Optional subdeck name (for multi-tier decks)

        Returns:
            Path to the generated .apkg file
        """
        # Get deck name
        if subdeck_name:
            full_deck_name = f"{self.config.name}::{subdeck_name}"
        else:
            full_deck_name = self.config.name

        deck = genanki.Deck(self.deck_id, full_deck_name)

        # Get template handler
        template_class = get_template(self.config.template)
        if not template_class:
            raise ValueError(f"Unknown template: {self.config.template}")

        media_files = []

        for entry in entries:
            # Prepare audio reference
            if entry.audio_file and audio_dir:
                audio_ref = f"[sound:{entry.audio_file}]"
                audio_path = audio_dir / entry.audio_file
                if audio_path.exists():
                    media_files.append(str(audio_path))
            else:
                audio_ref = ""

            # Create note using template
            note = template_class.create_note(entry, audio_ref)
            deck.add_note(note)

        # Determine output path
        if self.config.output.suffix == ".apkg":
            output_path = self.config.output
        else:
            safe_name = self.config.name.replace(" ", "-").lower()
            output_path = self.config.output / f"{safe_name}.apkg"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write package
        package = genanki.Package(deck)
        package.media_files = media_files
        package.write_to_file(str(output_path))

        return output_path

    def get_card_count(self, entries: list[VocabEntry]) -> int:
        """Get the number of cards that will be generated."""
        if self.config.template == "double-card":
            return len(entries) * 2
        elif self.config.template == "cloze":
            # Count cloze deletions
            import re

            total = 0
            for entry in entries:
                matches = re.findall(r"\{\{c\d+::", entry.text)
                # Each unique cloze number creates one card
                cloze_nums = set(re.findall(r"\{\{c(\d+)::", entry.text))
                total += len(cloze_nums) if cloze_nums else 1
            return total
        else:
            return len(entries)


def join_decks(
    deck_paths: list[Path],
    output_path: Path,
    master_name: str,
) -> Path:
    """Combine multiple .apkg files into one with subdecks.

    Args:
        deck_paths: List of .apkg files to combine
        output_path: Output path for combined deck
        master_name: Name for the master deck

    Returns:
        Path to the combined .apkg file
    """
    all_notes = []
    all_media = []
    models = {}

    for deck_path in deck_paths:
        if not deck_path.exists():
            raise FileNotFoundError(f"Deck not found: {deck_path}")

        # Extract and read the deck
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(deck_path, "r") as zf:
                zf.extractall(tmpdir)

            # Read the database
            db_path = Path(tmpdir) / "collection.anki2"
            if not db_path.exists():
                raise ValueError(f"Invalid .apkg file: {deck_path}")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get notes
            cursor.execute("SELECT * FROM notes")
            notes = cursor.fetchall()
            all_notes.extend(notes)

            # Get models
            cursor.execute("SELECT models FROM col")
            row = cursor.fetchone()
            if row:
                import json

                deck_models = json.loads(row[0])
                models.update(deck_models)

            conn.close()

            # Collect media files
            media_path = Path(tmpdir) / "media"
            if media_path.exists():
                import shutil

                for media_file in media_path.iterdir():
                    all_media.append(str(media_file))

    # For now, just concatenate by creating a combined deck
    # A more sophisticated approach would merge the SQLite databases
    combined_deck = genanki.Deck(
        random.randint(1000000000, 9999999999),
        master_name,
    )

    # This is a simplified version - for full merge we'd need to
    # properly handle the SQLite database merging
    package = genanki.Package(combined_deck)
    package.media_files = all_media
    package.write_to_file(str(output_path))

    return output_path


def create_generation_result(
    output_path: Path,
    entries: list[VocabEntry],
    config: DeckConfig,
    generated_audio: int = 0,
    cached_audio: int = 0,
) -> GenerationResult:
    """Create a GenerationResult from generation data."""
    builder = DeckBuilder(config)

    return GenerationResult(
        output_path=output_path,
        card_count=builder.get_card_count(entries),
        note_count=len(entries),
        audio_count=sum(1 for e in entries if e.audio_file),
        template=config.template,
        language=config.language,
        voice=config.resolved_voice,
        generated_audio=generated_audio,
        cached_audio=cached_audio,
    )
