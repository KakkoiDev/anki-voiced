"""CSV parsing utilities."""

import csv
from pathlib import Path

from .models import VocabEntry


# Supported column name mappings
COLUMN_MAPPINGS = {
    "front": ["front", "sentence", "word", "term", "question", "target"],
    "back": ["back", "translation", "meaning", "definition", "answer", "native"],
    "pronunciation": ["pronunciation", "reading", "furigana", "phonetic", "ipa"],
    "tags": ["tags", "tag", "category", "categories", "note", "notes"],
}


def _find_column(headers: list[str], candidates: list[str]) -> str | None:
    """Find the first matching column from candidates."""
    headers_lower = [h.lower().strip() for h in headers]
    for candidate in candidates:
        if candidate in headers_lower:
            return headers[headers_lower.index(candidate)]
    return None


def load_csv(path: Path) -> list[VocabEntry]:
    """Load vocabulary entries from a CSV file.

    Supports flexible column names - will try to match common variations.

    Args:
        path: Path to the CSV file

    Returns:
        List of VocabEntry objects

    Raises:
        ValueError: If required columns (front, back) are not found
    """
    entries = []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Find column mappings
        front_col = _find_column(headers, COLUMN_MAPPINGS["front"])
        back_col = _find_column(headers, COLUMN_MAPPINGS["back"])
        pron_col = _find_column(headers, COLUMN_MAPPINGS["pronunciation"])
        tags_col = _find_column(headers, COLUMN_MAPPINGS["tags"])

        if not front_col or not back_col:
            raise ValueError(
                f"CSV must have 'front' and 'back' columns (or equivalents). "
                f"Found: {headers}"
            )

        for row in reader:
            # Parse tags (comma or space separated)
            tags_str = row.get(tags_col, "") if tags_col else ""
            if "," in tags_str:
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            else:
                tags = [t.strip() for t in tags_str.split() if t.strip()]

            entry = VocabEntry(
                front=row[front_col],
                back=row[back_col],
                pronunciation=row.get(pron_col, "") if pron_col else "",
                tags=tags,
            )
            entries.append(entry)

    return entries


def create_sample_csv(path: Path, language: str = "ja") -> None:
    """Create a sample CSV file with example entries.

    Args:
        path: Path to create the sample CSV
        language: Language code for sample content
    """
    samples = {
        "ja": [
            ("こんにちは", "Hello", "こんにちは", "greeting"),
            ("ありがとう", "Thank you", "ありがとう", "greeting"),
            ("お願いします", "Please", "おねがいします", "request"),
        ],
        "en": [
            ("Hello", "Hola", "", "greeting"),
            ("Thank you", "Gracias", "", "greeting"),
            ("Please", "Por favor", "", "request"),
        ],
    }

    content = samples.get(language, samples["en"])

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["front", "back", "pronunciation", "tags"])
        writer.writerows(content)
