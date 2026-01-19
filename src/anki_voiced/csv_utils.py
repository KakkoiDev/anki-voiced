"""CSV parsing utilities with template-specific column handling."""

import csv
import sys
from pathlib import Path

from .models import VocabEntry


# Supported column name mappings per template
COLUMN_MAPPINGS = {
    # For basic template
    "front": ["front", "word", "term", "question", "target", "sentence"],
    "back": ["back", "translation", "meaning", "definition", "answer", "native"],
    # For double-card template
    "sentence": ["sentence", "front", "word", "term", "target", "text"],
    "translation": ["translation", "back", "meaning", "definition", "answer"],
    "pronunciation": ["pronunciation", "reading", "furigana", "phonetic", "ipa"],
    "hint": ["hint", "clue"],
    "tags": ["tags", "tag", "category", "categories", "note", "notes"],
    # For cloze template
    "text": ["text", "sentence", "front", "cloze"],
    "extra": ["extra", "hint", "note", "explanation"],
}


def _find_column(headers: list[str], candidates: list[str]) -> str | None:
    """Find the first matching column from candidates (case-insensitive)."""
    headers_lower = [h.lower().strip() for h in headers]
    for candidate in candidates:
        if candidate.lower() in headers_lower:
            idx = headers_lower.index(candidate.lower())
            return headers[idx]
    return None


def validate_csv_for_template(
    headers: list[str], template: str
) -> tuple[bool, list[str], str]:
    """Validate CSV headers for a specific template.

    Returns:
        (is_valid, missing_columns, suggestion_message)
    """
    required = {
        "basic": ["front", "back"],
        "double-card": ["sentence", "translation"],
        "cloze": ["text"],
    }

    missing = []
    for field in required.get(template, []):
        col = _find_column(headers, COLUMN_MAPPINGS[field])
        if not col:
            missing.append(field)

    if missing:
        # Generate helpful suggestion
        found_cols = ", ".join(headers)
        expected_cols = ", ".join(required.get(template, []))

        suggestion = f"Found columns: {found_cols}\n"
        suggestion += f"Expected for {template} template: {expected_cols}\n"

        # Check if another template might work
        for other_template, other_required in required.items():
            if other_template != template:
                all_found = all(
                    _find_column(headers, COLUMN_MAPPINGS[f]) for f in other_required
                )
                if all_found:
                    suggestion += f"\nHint: Use --template {other_template} if your file has "
                    suggestion += f"'{other_required[0]}' and '{other_required[1]}' columns"
                    break

        return False, missing, suggestion

    return True, [], ""


def load_csv(
    path: Path,
    template: str = "double-card",
) -> list[VocabEntry]:
    """Load vocabulary entries from a CSV file.

    Args:
        path: Path to the CSV file
        template: Template name for column validation

    Returns:
        List of VocabEntry objects

    Raises:
        ValueError: If required columns are not found
    """
    entries = []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Validate for template
        is_valid, missing, suggestion = validate_csv_for_template(headers, template)
        if not is_valid:
            raise ValueError(
                f"CSV is missing required column(s): {', '.join(missing)}\n\n{suggestion}"
            )

        # Find column mappings based on template
        if template == "basic":
            front_col = _find_column(headers, COLUMN_MAPPINGS["front"])
            back_col = _find_column(headers, COLUMN_MAPPINGS["back"])
        elif template == "cloze":
            text_col = _find_column(headers, COLUMN_MAPPINGS["text"])
            extra_col = _find_column(headers, COLUMN_MAPPINGS["extra"])
        else:  # double-card
            sentence_col = _find_column(headers, COLUMN_MAPPINGS["sentence"])
            translation_col = _find_column(headers, COLUMN_MAPPINGS["translation"])
            pron_col = _find_column(headers, COLUMN_MAPPINGS["pronunciation"])
            hint_col = _find_column(headers, COLUMN_MAPPINGS["hint"])

        tags_col = _find_column(headers, COLUMN_MAPPINGS["tags"])

        for row in reader:
            # Parse tags (comma or space separated)
            tags_str = row.get(tags_col, "") if tags_col else ""
            if "," in tags_str:
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            else:
                tags = [t.strip() for t in tags_str.split() if t.strip()]

            # Create entry based on template
            if template == "basic":
                entry = VocabEntry(
                    sentence=row[front_col],
                    translation=row[back_col],
                    tags=tags,
                )
            elif template == "cloze":
                entry = VocabEntry(
                    text=row[text_col],
                    extra=row.get(extra_col, "") if extra_col else "",
                    tags=tags,
                )
            else:  # double-card
                entry = VocabEntry(
                    sentence=row[sentence_col],
                    translation=row[translation_col],
                    pronunciation=row.get(pron_col, "") if pron_col else "",
                    hint=row.get(hint_col, "") if hint_col else "",
                    tags=tags,
                )

            entries.append(entry)

    return entries


def load_csv_from_stdin(template: str = "double-card") -> list[VocabEntry]:
    """Load vocabulary entries from stdin.

    Args:
        template: Template name for column validation

    Returns:
        List of VocabEntry objects
    """
    import io

    content = sys.stdin.read()
    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []

    # Same logic as load_csv but from stdin
    is_valid, missing, suggestion = validate_csv_for_template(headers, template)
    if not is_valid:
        raise ValueError(
            f"CSV is missing required column(s): {', '.join(missing)}\n\n{suggestion}"
        )

    entries = []

    if template == "basic":
        front_col = _find_column(headers, COLUMN_MAPPINGS["front"])
        back_col = _find_column(headers, COLUMN_MAPPINGS["back"])
    elif template == "cloze":
        text_col = _find_column(headers, COLUMN_MAPPINGS["text"])
        extra_col = _find_column(headers, COLUMN_MAPPINGS["extra"])
    else:
        sentence_col = _find_column(headers, COLUMN_MAPPINGS["sentence"])
        translation_col = _find_column(headers, COLUMN_MAPPINGS["translation"])
        pron_col = _find_column(headers, COLUMN_MAPPINGS["pronunciation"])
        hint_col = _find_column(headers, COLUMN_MAPPINGS["hint"])

    tags_col = _find_column(headers, COLUMN_MAPPINGS["tags"])

    for row in reader:
        tags_str = row.get(tags_col, "") if tags_col else ""
        if "," in tags_str:
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        else:
            tags = [t.strip() for t in tags_str.split() if t.strip()]

        if template == "basic":
            entry = VocabEntry(
                sentence=row[front_col],
                translation=row[back_col],
                tags=tags,
            )
        elif template == "cloze":
            entry = VocabEntry(
                text=row[text_col],
                extra=row.get(extra_col, "") if extra_col else "",
                tags=tags,
            )
        else:
            entry = VocabEntry(
                sentence=row[sentence_col],
                translation=row[translation_col],
                pronunciation=row.get(pron_col, "") if pron_col else "",
                hint=row.get(hint_col, "") if hint_col else "",
                tags=tags,
            )

        entries.append(entry)

    return entries


def create_sample_csv(path: Path, language: str = "english", template: str = "double-card") -> None:
    """Create a sample CSV file with example entries.

    Args:
        path: Path to create the sample CSV
        language: Language code for sample content
        template: Template to generate sample for
    """
    samples = {
        "english": {
            "double-card": [
                ("The meeting starts at 10 AM.", "La reunion commence a 10h.", "The meeting starts at 10 AM.", "business"),
                ("Could you review my pull request?", "Pouvez-vous reviser ma pull request?", "Could you review my pull request?", "development"),
                ("Let me share my screen.", "Laissez-moi partager mon ecran.", "Let me share my screen.", "meetings"),
            ],
            "basic": [
                ("Hello", "Bonjour"),
                ("Goodbye", "Au revoir"),
                ("Thank you", "Merci"),
            ],
            "cloze": [
                ("I {{c1::like}} apples.", "verb: to enjoy"),
                ("She {{c1::runs}} every day.", "verb: to run"),
                ("The {{c1::API}} returns JSON data.", "Application Programming Interface"),
            ],
        },
        "japanese": {
            "double-card": [
                ("これは何【なん】ですか?", "What is this?", "これはなんですか", "basics"),
                ("水【みず】をください。", "Water, please.", "みずをください", "restaurant"),
                ("駅【えき】はどこですか?", "Where is the station?", "えきはどこですか", "travel"),
            ],
            "basic": [
                ("こんにちは", "Hello"),
                ("さようなら", "Goodbye"),
                ("ありがとう", "Thank you"),
            ],
            "cloze": [
                ("私【わたし】は{{c1::りんご}}が好【す】きです。", "noun: apple"),
                ("今日【きょう】は{{c1::暑【あつ】い}}です。", "adjective: hot"),
                ("毎日【まいにち】{{c1::勉強【べんきょう】}}します。", "verb: to study"),
            ],
        },
        "french": {
            "double-card": [
                ("La reunion commence a 10 heures.", "The meeting starts at 10.", "La reunion commence a 10 heures.", "business"),
                ("Pouvez-vous reviser ma pull request?", "Could you review my pull request?", "Pouvez-vous reviser ma pull request?", "development"),
                ("Laissez-moi partager mon ecran.", "Let me share my screen.", "Laissez-moi partager mon ecran.", "meetings"),
            ],
            "basic": [
                ("Bonjour", "Hello"),
                ("Au revoir", "Goodbye"),
                ("Merci", "Thank you"),
            ],
            "cloze": [
                ("J'{{c1::aime}} les pommes.", "verb: aimer"),
                ("Elle {{c1::court}} tous les jours.", "verb: courir"),
                ("L'{{c1::API}} retourne des donnees JSON.", "Interface de Programmation"),
            ],
        },
        "portuguese": {
            "double-card": [
                ("A reuniao comeca as 10 horas.", "The meeting starts at 10.", "A reuniao comeca as 10 horas.", "business"),
                ("Voce pode revisar meu pull request?", "Could you review my pull request?", "Voce pode revisar meu pull request?", "development"),
                ("Deixe-me compartilhar minha tela.", "Let me share my screen.", "Deixe-me compartilhar minha tela.", "meetings"),
            ],
            "basic": [
                ("Ola", "Hello"),
                ("Adeus", "Goodbye"),
                ("Obrigado", "Thank you"),
            ],
            "cloze": [
                ("Eu {{c1::gosto}} de macas.", "verb: gostar"),
                ("Ela {{c1::corre}} todos os dias.", "verb: correr"),
                ("A {{c1::API}} retorna dados JSON.", "Interface de Programacao"),
            ],
        },
    }

    # Normalize language
    lang_map = {"en": "english", "ja": "japanese", "jp": "japanese", "fr": "french", "pt": "portuguese"}
    language = lang_map.get(language.lower(), language.lower())

    content = samples.get(language, samples["english"]).get(template, [])

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        if template == "basic":
            writer.writerow(["front", "back"])
            for row in content:
                writer.writerow(row)
        elif template == "cloze":
            writer.writerow(["text", "extra"])
            for row in content:
                writer.writerow(row)
        else:  # double-card
            writer.writerow(["sentence", "translation", "pronunciation", "tags"])
            for row in content:
                writer.writerow(row)
