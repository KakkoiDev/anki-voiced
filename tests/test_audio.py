"""Tests for audio generation TTS text selection logic."""

import pytest

from anki_voiced.models import VocabEntry


class TestTtsTextSelection:
    """Tests for TTS text selection priority in VocabEntry."""

    def test_tts_pronunciation_field_exists(self):
        """Test that VocabEntry has tts_pronunciation field."""
        entry = VocabEntry(
            sentence="テスト",
            translation="Test",
            tts_pronunciation="custom tts",
        )
        assert entry.tts_pronunciation == "custom tts"

    def test_tts_pronunciation_default_empty(self):
        """Test that tts_pronunciation defaults to empty string."""
        entry = VocabEntry(sentence="テスト", translation="Test")
        assert entry.tts_pronunciation == ""

    def test_all_fields_populated(self):
        """Test entry with all pronunciation fields populated."""
        entry = VocabEntry(
            sentence="会議【かいぎ】です",
            translation="It's a meeting",
            pronunciation="かいぎです",
            tts_pronunciation="かいぎ、です",
        )
        assert entry.sentence == "会議【かいぎ】です"
        assert entry.pronunciation == "かいぎです"
        assert entry.tts_pronunciation == "かいぎ、です"


class TestTtsTextSelectionLogic:
    """Tests for the TTS text selection logic used in audio generation.

    The priority is:
    1. tts_pronunciation (if provided) - used directly, no preprocessing
    2. pronunciation (if provided) - used with preprocessing
    3. sentence - used with preprocessing
    """

    def get_tts_text_and_preprocess(self, entry: VocabEntry):
        """Simulate the TTS text selection logic from audio.py."""
        if entry.tts_pronunciation:
            return entry.tts_pronunciation, False  # No preprocessing
        elif entry.pronunciation:
            return entry.pronunciation, True  # With preprocessing
        else:
            return entry.sentence, True  # With preprocessing

    def test_priority_tts_pronunciation_first(self):
        """tts_pronunciation takes priority over pronunciation and sentence."""
        entry = VocabEntry(
            sentence="会議【かいぎ】です",
            pronunciation="かいぎです",
            tts_pronunciation="かいぎ、です",
            translation="Meeting",
        )
        text, needs_preprocess = self.get_tts_text_and_preprocess(entry)
        assert text == "かいぎ、です"
        assert needs_preprocess is False

    def test_priority_pronunciation_second(self):
        """pronunciation used when tts_pronunciation is empty."""
        entry = VocabEntry(
            sentence="会議【かいぎ】です",
            pronunciation="かいぎです",
            tts_pronunciation="",
            translation="Meeting",
        )
        text, needs_preprocess = self.get_tts_text_and_preprocess(entry)
        assert text == "かいぎです"
        assert needs_preprocess is True

    def test_priority_sentence_last(self):
        """sentence used when both tts_pronunciation and pronunciation are empty."""
        entry = VocabEntry(
            sentence="会議【かいぎ】です",
            pronunciation="",
            tts_pronunciation="",
            translation="Meeting",
        )
        text, needs_preprocess = self.get_tts_text_and_preprocess(entry)
        assert text == "会議【かいぎ】です"
        assert needs_preprocess is True

    def test_tts_pronunciation_skips_preprocessing(self):
        """tts_pronunciation should skip preprocessing entirely."""
        entry = VocabEntry(
            sentence="APIを使う",
            tts_pronunciation="エーピーアイを、使う",
            translation="Use the API",
        )
        text, needs_preprocess = self.get_tts_text_and_preprocess(entry)
        # The text should be used as-is
        assert text == "エーピーアイを、使う"
        assert needs_preprocess is False

    def test_pronunciation_with_preprocessing(self):
        """pronunciation should go through preprocessing."""
        entry = VocabEntry(
            sentence="APIを使う",
            pronunciation="APIを使う",
            translation="Use the API",
        )
        text, needs_preprocess = self.get_tts_text_and_preprocess(entry)
        assert text == "APIを使う"
        assert needs_preprocess is True
