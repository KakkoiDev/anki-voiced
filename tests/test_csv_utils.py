"""Tests for CSV utilities."""

from pathlib import Path

from anki_voiced.csv_utils import (
    count_rows,
    create_sample_csv,
    missing_required_columns,
)
from anki_voiced.deck import load_tier_entries, write_tier_entries
from anki_voiced.models import VocabEntry


def test_create_sample_csv(tmp_path: Path):
    path = tmp_path / "test.csv"
    create_sample_csv(path)
    assert path.exists()
    assert count_rows(path) == 1
    assert missing_required_columns(path) == set()


def test_load_and_write_tier_entries_round_trip(tmp_path: Path):
    path = tmp_path / "tier1-vocabulary.csv"
    create_sample_csv(path)

    entries = load_tier_entries(path)
    assert len(entries) == 1
    assert entries[0].sentence.startswith("会議")
    assert entries[0].cloze == "会議"
    assert entries[0].register == "polite"

    entries[0].audio_file = "tier1_001.mp3"
    write_tier_entries(path, entries)

    entries2 = load_tier_entries(path)
    assert entries2[0].sentence == entries[0].sentence
    assert entries2[0].cloze == "会議"


def test_missing_column_detected(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("Sentence,Translation\nこんにちは,hello\n", encoding="utf-8")
    missing = missing_required_columns(path)
    assert "Cloze" in missing
    assert "Pronunciation" in missing
    assert "KeyMeaning" in missing


def test_vocab_entry_accepts_new_fields():
    entry = VocabEntry(
        sentence="会議【かいぎ】は10時【じ】です。",
        translation="The meeting is at 10.",
        cloze="会議",
        pronunciation="会議【かいぎ】は10時【じ】です。",
        note="Business - Meetings",
        register="polite",
        key_meaning="meeting",
    )
    assert entry.register == "polite"
    assert entry.key_meaning == "meeting"
    assert entry.audio_file is None
