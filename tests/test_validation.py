"""Tests for CSV validation functionality."""

import tempfile
from pathlib import Path

import pytest

from anki_voiced.validation import (
    ValidationResult,
    validate_csv_file,
    validate_furigana_text,
)


class TestValidateFuriganaText:
    """Tests for furigana validation."""

    def test_valid_furigana(self):
        result = ValidationResult()
        assert validate_furigana_text("機能【きのう】は完了【かんりょう】", 1, result) is True
        assert not result.errors

    def test_unmatched_open_bracket(self):
        result = ValidationResult()
        assert validate_furigana_text("機能【きのう", 1, result) is False
        assert len(result.errors) == 1
        assert "Unmatched brackets" in result.errors[0]

    def test_unmatched_close_bracket(self):
        result = ValidationResult()
        assert validate_furigana_text("機能きのう】", 1, result) is False
        assert len(result.errors) == 1

    def test_invalid_reading(self):
        result = ValidationResult()
        # Reading contains invalid characters (Chinese characters inside brackets)
        assert validate_furigana_text("機能【漢字】", 1, result) is False
        assert "Invalid reading" in result.errors[0]

    def test_valid_katakana_reading(self):
        result = ValidationResult()
        assert validate_furigana_text("API【エーピーアイ】", 1, result) is True
        assert not result.errors

    def test_no_furigana(self):
        result = ValidationResult()
        assert validate_furigana_text("普通のテキスト", 1, result) is True
        assert not result.errors


class TestValidateCsvFile:
    """Tests for CSV file validation."""

    def test_missing_file(self):
        result = validate_csv_file(Path("/nonexistent/file.csv"))
        assert result.has_errors
        assert "not found" in result.errors[0]

    def test_valid_csv(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("sentence,translation,pronunciation\n")
            f.write("こんにちは,Hello,こんにちは\n")
            f.write("ありがとう,Thank you,ありがとう\n")
            f.flush()

            result = validate_csv_file(Path(f.name))
            assert result.is_valid
            assert result.row_count == 2
            Path(f.name).unlink()

    def test_empty_required_field(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("sentence,translation\n")
            f.write(",Hello\n")  # Empty sentence
            f.flush()

            result = validate_csv_file(Path(f.name))
            assert result.has_errors
            assert "Empty required field" in result.errors[0]
            Path(f.name).unlink()

    def test_furigana_validation(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("sentence,translation,pronunciation\n")
            f.write("テスト,Test,機能【きのう】\n")
            f.write("テスト2,Test2,機能【きのう\n")  # Unmatched bracket
            f.flush()

            result = validate_csv_file(Path(f.name), check_furigana=True)
            assert result.has_errors
            assert result.furigana_total == 2
            assert result.furigana_valid == 1
            Path(f.name).unlink()


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_empty_result(self):
        result = ValidationResult()
        assert result.is_valid
        assert not result.has_errors

    def test_add_error(self):
        result = ValidationResult()
        result.add_error("Test error")
        assert result.has_errors
        assert not result.is_valid
        assert "Test error" in result.errors

    def test_add_warning(self):
        result = ValidationResult()
        result.add_warning("Test warning")
        assert not result.has_errors
        assert result.is_valid
        assert "Test warning" in result.warnings
