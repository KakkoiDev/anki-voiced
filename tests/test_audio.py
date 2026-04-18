"""Tests for audio generation (Edge TTS + cache)."""

from pathlib import Path
from unittest.mock import patch

from anki_voiced.audio import AudioGenerator
from anki_voiced.models import VocabEntry


class TestVoiceResolution:
    def test_resolves_male_to_keita(self):
        g = AudioGenerator(voice="male")
        assert g.resolved_voice == "ja-JP-KeitaNeural"

    def test_resolves_female_to_nanami(self):
        g = AudioGenerator(voice="female")
        assert g.resolved_voice == "ja-JP-NanamiNeural"

    def test_passes_through_voice_id(self):
        g = AudioGenerator(voice="ja-JP-KeitaNeural")
        assert g.resolved_voice == "ja-JP-KeitaNeural"


class TestCacheLookup:
    def test_uses_cache_when_present(self, tmp_path: Path):
        """If the cache file exists and force=False, we should copy from cache."""
        from anki_voiced.config import get_audio_cache_path
        from anki_voiced.preprocessing.japanese import preprocess_for_tts

        text = "テストです。"
        voice = "ja-JP-KeitaNeural"
        cache_path = get_audio_cache_path(preprocess_for_tts(text), voice)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(b"FAKEMP3DATA")

        g = AudioGenerator(voice="male", quiet=True)
        out = tmp_path / "out.mp3"

        with patch("anki_voiced.audio._edge_tts_save") as mocked:
            success = g.generate_audio(text, out, preprocess=preprocess_for_tts)
            assert success
            assert not mocked.called  # network call skipped
        assert out.read_bytes() == b"FAKEMP3DATA"

    def test_force_bypasses_cache(self, tmp_path: Path):
        from anki_voiced.config import get_audio_cache_path
        from anki_voiced.preprocessing.japanese import preprocess_for_tts

        text = "こんにちは。"
        voice = "ja-JP-KeitaNeural"
        cache_path = get_audio_cache_path(preprocess_for_tts(text), voice)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(b"OLDBYTES")

        g = AudioGenerator(voice="male", force=True, quiet=True)
        out = tmp_path / "out.mp3"

        async def fake_save(text, voice, path, retries=3):  # noqa: ARG001
            Path(path).write_bytes(b"NEWBYTES")

        with patch("anki_voiced.audio._edge_tts_save", side_effect=fake_save):
            g.generate_audio(text, out, preprocess=preprocess_for_tts)
        assert out.read_bytes() == b"NEWBYTES"


class TestBatch:
    def test_batch_updates_audio_filenames(self, tmp_path: Path):
        entries = [
            VocabEntry(sentence="一つ目。", translation="first", cloze="一つ", pronunciation="一【ひと】つ目【め】。", key_meaning="first"),
            VocabEntry(sentence="二つ目。", translation="second", cloze="二つ", pronunciation="二【ふた】つ目【め】。", key_meaning="second"),
        ]
        g = AudioGenerator(voice="male", quiet=True)

        async def fake_save(text, voice, path, retries=3):  # noqa: ARG001
            Path(path).write_bytes(b"FAKEFAKEFAKEFAKE" * 100)

        with patch("anki_voiced.audio._edge_tts_save", side_effect=fake_save):
            updated, gen, cached = g.generate_batch(
                entries,
                tmp_path,
                filename_fn=lambda i: f"t1_{i:03d}.mp3",
            )
        assert updated[0].audio_file == "t1_001.mp3"
        assert updated[1].audio_file == "t1_002.mp3"
        assert (tmp_path / "t1_001.mp3").exists()
