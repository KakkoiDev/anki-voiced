"""CSV and audio validation for Anki deck generation.

Catches common issues before deck generation:
- Missing or incorrectly named CSV columns
- Empty required fields
- Invalid furigana format (unclosed brackets, invalid readings)
- Missing or empty audio files
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

# Hiragana and katakana ranges for validating furigana readings
HIRAGANA_KATAKANA_PATTERN = re.compile(r"^[\u3040-\u309F\u30A0-\u30FFー・]+$")

# Furigana bracket pattern
FURIGANA_PATTERN = re.compile(r"【([^】]*)】")


@dataclass
class ValidationResult:
    """Tracks validation results."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    csv_valid: bool = False
    furigana_valid: int = 0
    furigana_total: int = 0
    audio_valid: int = 0
    audio_total: int = 0

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def is_valid(self) -> bool:
        return not self.has_errors


def validate_furigana_text(text: str, row_num: int, result: ValidationResult) -> bool:
    """Validate furigana format in a text field.

    Checks:
    - Matched brackets 【】
    - Valid readings (hiragana/katakana only inside brackets)

    Returns True if valid.
    """
    # Check bracket matching
    open_count = text.count("【")
    close_count = text.count("】")

    if open_count != close_count:
        result.add_error(f"Row {row_num}: Unmatched brackets in '{text[:50]}...'")
        return False

    # Check each furigana reading
    readings = FURIGANA_PATTERN.findall(text)

    for reading in readings:
        if reading and not HIRAGANA_KATAKANA_PATTERN.match(reading):
            # Allow mixed readings with numbers/letters for edge cases
            if not re.match(r"^[\u3040-\u309F\u30A0-\u30FF0-9A-Za-zー・]+$", reading):
                result.add_error(
                    f"Row {row_num}: Invalid reading '{reading}' (not hiragana/katakana)"
                )
                return False

    return True


def validate_csv_rows(
    rows: list[dict],
    required_fields: list[str],
    result: ValidationResult,
    check_furigana: bool = True,
) -> None:
    """Validate CSV rows for common issues.

    Args:
        rows: List of row dictionaries from CSV
        required_fields: Fields that must not be empty
        result: ValidationResult to update
        check_furigana: Whether to validate furigana format in pronunciation field
    """
    result.row_count = len(rows)
    result.csv_valid = True

    # Fields that might contain furigana
    furigana_fields = ["pronunciation", "tts_pronunciation"]

    for idx, row in enumerate(rows, 1):
        # Check required fields are not empty
        for field_name in required_fields:
            value = row.get(field_name, "")
            if not value or not value.strip():
                result.add_error(f"Row {idx}: Empty required field '{field_name}'")

        # Check furigana format
        if check_furigana:
            for field_name in furigana_fields:
                value = row.get(field_name, "")
                if value and "【" in value:
                    result.furigana_total += 1
                    if validate_furigana_text(value, idx, result):
                        result.furigana_valid += 1


def validate_audio_files(
    audio_dir: Path,
    expected_count: int,
    result: ValidationResult,
    file_pattern: str = "*.mp3",
    min_size: int = 1024,
) -> None:
    """Validate audio files exist and are not empty.

    Args:
        audio_dir: Directory containing audio files
        expected_count: Expected number of audio files
        result: ValidationResult to update
        file_pattern: Glob pattern for audio files
        min_size: Minimum file size in bytes (default 1KB)
    """
    result.audio_total = expected_count

    if not audio_dir.exists():
        result.add_warning(f"Audio directory not found: {audio_dir}")
        return

    audio_files = sorted(audio_dir.glob(file_pattern))

    if len(audio_files) != expected_count:
        result.add_warning(
            f"Audio file count mismatch: found {len(audio_files)}, expected {expected_count}"
        )

    for audio_file in audio_files:
        size = audio_file.stat().st_size
        if size < min_size:
            result.add_error(f"Audio too small ({size} bytes): {audio_file.name}")
        else:
            result.audio_valid += 1


def validate_csv_file(
    csv_path: Path,
    required_columns: set[str] | None = None,
    check_furigana: bool = True,
) -> ValidationResult:
    """Validate a CSV file.

    Args:
        csv_path: Path to CSV file
        required_columns: Set of required column names
        check_furigana: Whether to validate furigana format

    Returns:
        ValidationResult with errors and warnings
    """
    import csv

    result = ValidationResult()

    if not csv_path.exists():
        result.add_error(f"CSV file not found: {csv_path}")
        return result

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])

        # Check required columns
        if required_columns:
            missing = required_columns - columns
            if missing:
                result.add_error(f"Missing columns: {', '.join(sorted(missing))}")
                return result

        rows = list(reader)

        # Determine required fields based on what's present
        required_fields = []
        if "sentence" in columns:
            required_fields.append("sentence")
        if "translation" in columns:
            required_fields.append("translation")
        if "front" in columns:
            required_fields.append("front")
        if "back" in columns:
            required_fields.append("back")

        validate_csv_rows(rows, required_fields, result, check_furigana)

    return result
