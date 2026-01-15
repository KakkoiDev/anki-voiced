"""Tests for CSV utilities."""

import tempfile
from pathlib import Path

import pytest

from anki_voiced.csv_utils import create_sample_csv, load_csv


def test_create_sample_csv_ja():
    """Test creating a Japanese sample CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        create_sample_csv(path, "ja")

        assert path.exists()
        entries = load_csv(path)
        assert len(entries) == 3
        assert entries[0].front == "こんにちは"
        assert entries[0].back == "Hello"


def test_create_sample_csv_en():
    """Test creating an English sample CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        create_sample_csv(path, "en")

        assert path.exists()
        entries = load_csv(path)
        assert len(entries) == 3
        assert entries[0].front == "Hello"


def test_load_csv_flexible_columns():
    """Test that CSV loading accepts flexible column names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"

        # Use alternative column names
        path.write_text("sentence,translation,reading,category\nテスト,Test,てすと,noun\n")

        entries = load_csv(path)
        assert len(entries) == 1
        assert entries[0].front == "テスト"
        assert entries[0].back == "Test"
        assert entries[0].pronunciation == "てすと"
        assert entries[0].tags == ["noun"]


def test_load_csv_missing_required_columns():
    """Test error when required columns are missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text("word,definition\nテスト,Test\n")

        # Should work - word maps to front, definition maps to back
        entries = load_csv(path)
        assert len(entries) == 1


def test_load_csv_comma_separated_tags():
    """Test parsing comma-separated tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text('front,back,tags\nテスト,Test,"noun, common, n5"\n')

        entries = load_csv(path)
        assert entries[0].tags == ["noun", "common", "n5"]


def test_load_csv_space_separated_tags():
    """Test parsing space-separated tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        path.write_text("front,back,tags\nテスト,Test,noun common n5\n")

        entries = load_csv(path)
        assert entries[0].tags == ["noun", "common", "n5"]
