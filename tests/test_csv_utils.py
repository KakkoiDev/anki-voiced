"""Tests for CSV utilities."""

import tempfile
from pathlib import Path

import pytest

from anki_voiced.csv_utils import create_sample_csv, load_csv


def test_create_sample_csv_japanese():
    """Test creating a Japanese sample CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        create_sample_csv(path, "japanese", "double-card")

        assert path.exists()
        entries = load_csv(path, "double-card")
        assert len(entries) == 3
        # First entry is "これは何【なん】ですか?" / "What is this?"
        assert "これは" in entries[0].sentence
        assert "what" in entries[0].translation.lower()


def test_create_sample_csv_english():
    """Test creating an English sample CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        create_sample_csv(path, "english", "double-card")

        assert path.exists()
        entries = load_csv(path, "double-card")
        assert len(entries) == 3
        assert "meeting" in entries[0].sentence.lower()


def test_create_sample_csv_basic_template():
    """Test creating a basic template sample CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        create_sample_csv(path, "english", "basic")

        assert path.exists()
        entries = load_csv(path, "basic")
        assert len(entries) == 3
        assert entries[0].front == "Hello"


def test_create_sample_csv_cloze_template():
    """Test creating a cloze template sample CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        create_sample_csv(path, "english", "cloze")

        assert path.exists()
        entries = load_csv(path, "cloze")
        assert len(entries) == 3
        assert "{{c1::" in entries[0].text


def test_load_csv_flexible_columns():
    """Test that CSV loading accepts flexible column names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"

        # Use alternative column names
        path.write_text("sentence,translation,reading,category\nテスト,Test,てすと,noun\n")

        entries = load_csv(path, "double-card")
        assert len(entries) == 1
        assert entries[0].sentence == "テスト"
        assert entries[0].translation == "Test"
        assert entries[0].pronunciation == "てすと"
        assert entries[0].tags == ["noun"]


def test_load_csv_basic_template():
    """Test loading basic template CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text("front,back\nHello,Bonjour\n")

        entries = load_csv(path, "basic")
        assert len(entries) == 1
        assert entries[0].front == "Hello"
        assert entries[0].back == "Bonjour"


def test_load_csv_cloze_template():
    """Test loading cloze template CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text("text,extra\nI {{c1::like}} apples.,verb: to enjoy\n")

        entries = load_csv(path, "cloze")
        assert len(entries) == 1
        assert "{{c1::like}}" in entries[0].text
        assert entries[0].extra == "verb: to enjoy"


def test_load_csv_missing_required_columns():
    """Test error when required columns are missing for template."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text("foo,bar\nテスト,Test\n")

        with pytest.raises(ValueError) as exc_info:
            load_csv(path, "double-card")

        assert "missing required column" in str(exc_info.value).lower()


def test_load_csv_comma_separated_tags():
    """Test parsing comma-separated tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text('sentence,translation,tags\nテスト,Test,"noun, common, n5"\n')

        entries = load_csv(path, "double-card")
        assert entries[0].tags == ["noun", "common", "n5"]


def test_load_csv_space_separated_tags():
    """Test parsing space-separated tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text("sentence,translation,tags\nテスト,Test,noun common n5\n")

        entries = load_csv(path, "double-card")
        assert entries[0].tags == ["noun", "common", "n5"]


def test_load_csv_tts_pronunciation_column():
    """Test loading CSV with tts_pronunciation column."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text(
            "sentence,translation,pronunciation,tts_pronunciation,tags\n"
            "テスト,Test,てすと,てすと、です,noun\n"
        )

        entries = load_csv(path, "double-card")
        assert len(entries) == 1
        assert entries[0].pronunciation == "てすと"
        assert entries[0].tts_pronunciation == "てすと、です"


def test_load_csv_tts_pronunciation_empty():
    """Test that empty tts_pronunciation is handled correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text(
            "sentence,translation,pronunciation,tts_pronunciation,tags\n"
            "テスト,Test,てすと,,noun\n"
        )

        entries = load_csv(path, "double-card")
        assert entries[0].tts_pronunciation == ""


def test_load_csv_tts_column_alias():
    """Test that 'tts' column alias works for tts_pronunciation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text(
            "sentence,translation,pronunciation,tts,tags\n"
            "テスト,Test,てすと,custom tts text,noun\n"
        )

        entries = load_csv(path, "double-card")
        assert entries[0].tts_pronunciation == "custom tts text"


def test_load_csv_audio_text_column_alias():
    """Test that 'audio_text' column alias works for tts_pronunciation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text(
            "sentence,translation,pronunciation,audio_text,tags\n"
            "テスト,Test,てすと,audio text here,noun\n"
        )

        entries = load_csv(path, "double-card")
        assert entries[0].tts_pronunciation == "audio text here"


def test_create_sample_csv_includes_tts_pronunciation_header():
    """Test that sample CSV includes tts_pronunciation column."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        create_sample_csv(path, "japanese", "double-card")

        content = path.read_text()
        assert "tts_pronunciation" in content.split("\n")[0]
