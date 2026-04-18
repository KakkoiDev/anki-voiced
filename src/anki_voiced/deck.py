"""Build .apkg files from CSV + audio."""

import csv
from dataclasses import dataclass
from pathlib import Path

import genanki

from .models import DeckConfig, REQUIRED_CSV_COLUMNS, VocabEntry
from .templates import CARDS_PER_NOTE, create_note, create_three_card_model


@dataclass
class DeckBuildResult:
    output_path: Path
    note_count: int
    card_count: int
    audio_count: int


def load_tier_entries(csv_path: Path) -> list[VocabEntry]:
    """Read a tier CSV into VocabEntry objects (matched by column name)."""
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_CSV_COLUMNS - columns
        if missing:
            raise ValueError(
                f"{csv_path} missing required columns: {sorted(missing)}"
            )

        entries = []
        for row in reader:
            entries.append(
                VocabEntry(
                    sentence=row["Sentence"],
                    translation=row["Translation"],
                    cloze=row.get("Cloze", ""),
                    pronunciation=row.get("Pronunciation", ""),
                    note=row.get("Note", ""),
                    register=row.get("Register", ""),
                    key_meaning=row.get("KeyMeaning", ""),
                    pitch_accent=row.get("PitchAccent", ""),
                )
            )
        return entries


def write_tier_entries(csv_path: Path, entries: list[VocabEntry]) -> None:
    """Write entries back to a tier CSV (preserving column order)."""
    fieldnames = [
        "Sentence", "Translation", "Cloze", "Pronunciation",
        "Note", "Register", "KeyMeaning", "PitchAccent", "Audio",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "Sentence": entry.sentence,
                "Translation": entry.translation,
                "Cloze": entry.cloze,
                "Pronunciation": entry.pronunciation,
                "Note": entry.note,
                "Register": entry.register,
                "KeyMeaning": entry.key_meaning,
                "PitchAccent": entry.pitch_accent,
                "Audio": f"[sound:{entry.audio_file}]" if entry.audio_file else "",
            })


def build_tier_deck(
    config: DeckConfig,
    tier: int,
    entries: list[VocabEntry],
    audio_dir: Path,
    deck_name_override: str | None = None,
) -> tuple[genanki.Deck, list[str]]:
    """Build a single-tier genanki.Deck and list of media paths."""
    tier_conf = config.tier(tier)
    deck_name = deck_name_override or f"{config.name} - {tier_conf.name}"
    deck = genanki.Deck(config.get_deck_id(tier), deck_name)
    model = create_three_card_model(config)
    media: list[str] = []

    for idx, entry in enumerate(entries, start=1):
        audio_file = f"tier{tier}_{idx:03d}.mp3"
        audio_path = audio_dir / audio_file
        if audio_path.exists():
            audio_ref = f"[sound:{audio_file}]"
            media.append(str(audio_path))
            entry.audio_file = audio_file
        else:
            audio_ref = "[No audio]"
        deck.add_note(create_note(entry, model, audio_ref))

    return deck, media


def build_single_tier_package(
    config: DeckConfig,
    tier: int,
    entries: list[VocabEntry],
    audio_dir: Path,
    output_path: Path,
) -> DeckBuildResult:
    """Write a .apkg for one tier."""
    deck, media = build_tier_deck(config, tier, entries, audio_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    package = genanki.Package(deck)
    package.media_files = media
    package.write_to_file(str(output_path))
    return DeckBuildResult(
        output_path=output_path,
        note_count=len(entries),
        card_count=len(entries) * CARDS_PER_NOTE,
        audio_count=len(media),
    )


def build_combined_package(
    config: DeckConfig,
    tiers_data: list[tuple[int, list[VocabEntry], Path]],
    output_path: Path,
) -> DeckBuildResult:
    """Write a combined .apkg where each tier is a subdeck.

    tiers_data: list of (tier_number, entries, audio_dir).
    """
    all_decks: list[genanki.Deck] = []
    all_media: list[str] = []
    total_notes = 0

    for tier, entries, audio_dir in tiers_data:
        tier_conf = config.tier(tier)
        subdeck_name = f"{config.name}::{tier:02d} {tier_conf.name}"
        deck, media = build_tier_deck(
            config, tier, entries, audio_dir, deck_name_override=subdeck_name
        )
        all_decks.append(deck)
        all_media.extend(media)
        total_notes += len(entries)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    package = genanki.Package(all_decks)
    package.media_files = all_media
    package.write_to_file(str(output_path))

    return DeckBuildResult(
        output_path=output_path,
        note_count=total_notes,
        card_count=total_notes * CARDS_PER_NOTE,
        audio_count=len(all_media),
    )


def join_decks(
    deck_paths: list[Path],
    output_path: Path,
    master_name: str,
) -> Path:
    """Concatenate existing .apkg files into one master (simple shell).

    Creates a new empty master deck and bundles media from the source decks.
    For true note-level merge, rebuild from CSVs instead - this helper is
    for quickly packaging pre-built tier decks for distribution.
    """
    import random
    import shutil
    import tempfile
    import zipfile

    all_media: list[str] = []
    tmp_roots: list[Path] = []

    try:
        for p in deck_paths:
            if not p.exists():
                raise FileNotFoundError(p)
            tmp = Path(tempfile.mkdtemp())
            tmp_roots.append(tmp)
            with zipfile.ZipFile(p) as zf:
                zf.extractall(tmp)
            media_dir = tmp / "media"
            if media_dir.exists():
                for f in media_dir.iterdir():
                    all_media.append(str(f))

        deck = genanki.Deck(random.randint(1_000_000_000, 9_999_999_999), master_name)
        package = genanki.Package(deck)
        package.media_files = all_media
        package.write_to_file(str(output_path))
        return output_path
    finally:
        for r in tmp_roots:
            shutil.rmtree(r, ignore_errors=True)
