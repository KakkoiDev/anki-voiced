"""CSV helpers for the fixed 9-column Japanese schema.

Columns (canonical, case-sensitive):
  Sentence, Translation, Cloze, Pronunciation, Note, Register,
  KeyMeaning, PitchAccent, Audio

Use the helpers in deck.py (load_tier_entries, write_tier_entries) for
the full pipeline. This module provides lightweight inspection utilities.
"""

import csv
from pathlib import Path

from .models import CSV_COLUMNS, REQUIRED_CSV_COLUMNS


def read_headers(csv_path: Path) -> list[str]:
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        return next(reader, [])


def missing_required_columns(csv_path: Path) -> set[str]:
    headers = set(read_headers(csv_path))
    return REQUIRED_CSV_COLUMNS - headers


def count_rows(csv_path: Path) -> int:
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)


def create_sample_csv(csv_path: Path) -> None:
    """Create a minimal starter CSV with the full column set."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        writer.writerow([
            "会議【かいぎ】は10時【じ】です。",
            "The meeting is at 10.",
            "会議",
            "会議【かいぎ】は10時【じ】です。",
            "Business - Meetings",
            "polite",
            "meeting",
            "",
            "",
        ])
