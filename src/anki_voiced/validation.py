"""Validate tier CSVs and audio before deck generation.

Checks:
  - CSV structure: required columns, row count vs tier size
  - Furigana: matched brackets, hiragana/katakana readings only
  - KeyMeaning: not empty, reasonable length
  - Register: valid enum value if present
  - Audio: files exist and are non-empty (with --check-audio)
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from .models import DeckConfig, REQUIRED_CSV_COLUMNS, Register

HIRAGANA_KATAKANA_PATTERN = re.compile(r"^[\u3040-\u309F\u30A0-\u30FFー・]+$")
FURIGANA_PATTERN = re.compile(r"【([^】]*)】")

MIN_AUDIO_BYTES = 1024


@dataclass
class ValidationResult:
    tier: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    csv_valid: bool = False
    furigana_valid: int = 0
    furigana_total: int = 0
    key_meaning_valid: int = 0
    key_meaning_total: int = 0
    audio_valid: int = 0
    audio_total: int = 0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def is_valid(self) -> bool:
        return not self.has_errors


def _validate_furigana_text(text: str, row_num: int, result: ValidationResult) -> bool:
    if text.count("【") != text.count("】"):
        result.add_error(f"Row {row_num}: unmatched brackets in '{text[:50]}...'")
        return False

    for reading in FURIGANA_PATTERN.findall(text):
        if not reading:
            continue
        if HIRAGANA_KATAKANA_PATTERN.match(reading):
            continue
        # Tolerate edge cases with digits/letters
        if re.match(r"^[\u3040-\u309F\u30A0-\u30FF0-9A-Za-zー・]+$", reading):
            continue
        result.add_error(f"Row {row_num}: invalid reading '{reading}' (not hiragana/katakana)")
        return False
    return True


def _validate_row_fields(
    row: dict, row_num: int, result: ValidationResult, registers_allowed: bool = True
) -> None:
    for field_name in ("Sentence", "Translation", "Cloze", "KeyMeaning"):
        if not (row.get(field_name, "") or "").strip():
            result.add_error(f"Row {row_num}: empty required field '{field_name}'")

    # KeyMeaning sanity
    cloze = row.get("Cloze", "")
    km = row.get("KeyMeaning", "").strip()
    if km:
        if km == cloze and not re.match(r"^[A-Za-z0-9\s\-\./]+$", cloze):
            result.add_warning(
                f"Row {row_num}: KeyMeaning equals Cloze ('{km}') - likely untranslated"
            )
        else:
            if len(km) > 50:
                result.add_warning(f"Row {row_num}: KeyMeaning too long ({len(km)} chars)")
            result.key_meaning_valid += 1
    result.key_meaning_total += 1

    # Register enum
    if registers_allowed:
        reg = (row.get("Register", "") or "").strip()
        if reg and reg not in {r.value for r in Register}:
            result.add_warning(
                f"Row {row_num}: unknown register '{reg}' "
                f"(expected one of: {', '.join(r.value for r in Register)})"
            )

    # Furigana in Pronunciation
    pron = row.get("Pronunciation", "")
    if pron and "【" in pron:
        result.furigana_total += 1
        if _validate_furigana_text(pron, row_num, result):
            result.furigana_valid += 1


def validate_csv(
    csv_path: Path,
    result: ValidationResult,
    expected_size: int = 0,
) -> list[dict]:
    if not csv_path.exists():
        result.add_error(f"CSV not found: {csv_path}")
        return []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_CSV_COLUMNS - columns
        if missing:
            result.add_error(f"Missing columns: {', '.join(sorted(missing))}")
            return []

        rows = list(reader)
        result.row_count = len(rows)
        result.csv_valid = True

    if expected_size and result.row_count != expected_size:
        result.add_warning(
            f"Row count {result.row_count} differs from tier size {expected_size}"
        )

    for idx, row in enumerate(rows, start=1):
        _validate_row_fields(row, idx, result)

    return rows


def validate_audio(
    audio_dir: Path,
    row_count: int,
    tier: int,
    result: ValidationResult,
) -> None:
    result.audio_total = row_count
    if not audio_dir.exists():
        result.add_warning(f"Audio directory not found: {audio_dir}")
        return

    for idx in range(1, row_count + 1):
        audio_file = audio_dir / f"tier{tier}_{idx:03d}.mp3"
        if not audio_file.exists():
            result.add_error(f"Missing audio: {audio_file.name}")
            continue
        size = audio_file.stat().st_size
        if size < MIN_AUDIO_BYTES:
            result.add_error(f"Audio too small ({size}B): {audio_file.name}")
            continue
        result.audio_valid += 1


def validate_tier(
    config: DeckConfig,
    tier: int,
    decks_root: Path,
    check_audio: bool = False,
    female: bool = False,
) -> ValidationResult:
    result = ValidationResult(tier=tier)
    tier_conf = config.tier(tier)
    csv_path = config.csv_path(decks_root, tier)
    rows = validate_csv(csv_path, result, expected_size=tier_conf.size)
    if check_audio and rows:
        audio_dir = config.audio_dir(decks_root, tier, female=female)
        validate_audio(audio_dir, len(rows), tier, result)
    return result
