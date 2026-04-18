"""Tests for CSV/audio validation."""

from pathlib import Path

from anki_voiced.csv_utils import create_sample_csv
from anki_voiced.models import DeckConfig, TierConfig
from anki_voiced.validation import (
    ValidationResult,
    validate_audio,
    validate_csv,
    validate_tier,
)


def _sample_deck_config(slug: str = "test", size: int = 1) -> DeckConfig:
    return DeckConfig(
        slug=slug,
        name="Test Deck",
        model_id=1234567890,
        deck_base_id=9876543210,
        tiers=[TierConfig(number=1, name="Tier 1", size=size)],
    )


def test_validate_csv_ok(tmp_path: Path):
    csv_path = tmp_path / "t1.csv"
    create_sample_csv(csv_path)
    result = ValidationResult(tier=1)
    rows = validate_csv(csv_path, result, expected_size=1)
    assert len(rows) == 1
    assert result.csv_valid
    assert result.is_valid


def test_validate_csv_missing_columns(tmp_path: Path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("Sentence,Translation\nこんにちは,hello\n", encoding="utf-8")
    result = ValidationResult(tier=1)
    rows = validate_csv(csv_path, result)
    assert rows == []
    assert not result.is_valid
    assert any("Missing columns" in e for e in result.errors)


def test_validate_furigana_bracket_mismatch(tmp_path: Path):
    csv_path = tmp_path / "t1.csv"
    csv_path.write_text(
        "Sentence,Translation,Cloze,Pronunciation,Note,Register,KeyMeaning,PitchAccent,Audio\n"
        "テスト,test,テスト,テスト【,tag,polite,test,,\n",
        encoding="utf-8",
    )
    result = ValidationResult(tier=1)
    validate_csv(csv_path, result)
    assert any("unmatched brackets" in e.lower() for e in result.errors)


def test_validate_audio_reports_missing(tmp_path: Path):
    result = ValidationResult(tier=1)
    validate_audio(tmp_path / "absent", 2, tier=1, result=result)
    assert any("not found" in w for w in result.warnings)


def test_validate_audio_counts_files(tmp_path: Path):
    audio_dir = tmp_path / "tier1-audio"
    audio_dir.mkdir()
    (audio_dir / "tier1_001.mp3").write_bytes(b"X" * 2048)
    (audio_dir / "tier1_002.mp3").write_bytes(b"X" * 2048)

    result = ValidationResult(tier=1)
    validate_audio(audio_dir, 2, tier=1, result=result)
    assert result.audio_valid == 2
    assert result.is_valid


def test_validate_tier_integration(tmp_path: Path):
    config = _sample_deck_config()
    deck_dir = tmp_path / config.slug
    deck_dir.mkdir()
    csv_path = deck_dir / "tier1-vocabulary.csv"
    create_sample_csv(csv_path)

    result = validate_tier(config, 1, decks_root=tmp_path)
    assert result.csv_valid
    assert result.row_count == 1
    assert result.is_valid
