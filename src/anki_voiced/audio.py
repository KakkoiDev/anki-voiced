"""Audio generation using Kokoro TTS with MP3 encoding and caching."""

import signal
import sys
from pathlib import Path
from typing import Callable

import lameenc
import numpy as np
from kokoro import KPipeline
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from .config import get_audio_cache_path
from .models import DeckConfig, VocabEntry


class AudioGenerationInterrupted(Exception):
    """Raised when audio generation is interrupted by the user."""

    pass


class AudioGenerator:
    """Generate audio files using Kokoro TTS with MP3 encoding and caching."""

    def __init__(self, config: DeckConfig, quiet: bool = False):
        self.config = config
        self.quiet = quiet
        self.pipeline: KPipeline | None = None
        self._interrupted = False

    def _init_pipeline(self) -> None:
        """Initialize the Kokoro TTS pipeline (lazy loading)."""
        if self.pipeline is None:
            self.pipeline = KPipeline(lang_code=self.config.lang_code)

    def _encode_mp3(self, audio_data: np.ndarray) -> bytes:
        """Encode audio data to MP3 format.

        Args:
            audio_data: Float32 audio data at 24kHz

        Returns:
            MP3 encoded bytes
        """
        # Convert float32 audio to int16 for MP3 encoding
        audio_int16 = (audio_data * 32767).astype(np.int16)

        # Encode to MP3 using lameenc
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(128)
        encoder.set_in_sample_rate(24000)
        encoder.set_channels(1)
        encoder.set_quality(2)  # 2 = high quality, 7 = fast

        return encoder.encode(audio_int16.tobytes()) + encoder.flush()

    def generate_audio(
        self,
        text: str,
        output_path: Path,
        preprocess: Callable[[str], str] | None = None,
    ) -> bool:
        """Generate audio for a single text.

        Args:
            text: Text to synthesize
            output_path: Path to save the MP3 file
            preprocess: Optional function to preprocess text before TTS

        Returns:
            True if successful, False otherwise
        """
        self._init_pipeline()

        # Check cache first
        cache_path = get_audio_cache_path(text, self.config.resolved_voice, self.config.language)
        if cache_path.exists() and not self.config.force:
            # Copy from cache
            import shutil

            shutil.copy(cache_path, output_path)
            return True

        try:
            # Preprocess text if function provided
            tts_input = preprocess(text) if preprocess else text

            audio_chunks = []
            for _, _, audio in self.pipeline(tts_input, voice=self.config.resolved_voice):
                # Convert PyTorch tensor to numpy if needed
                if hasattr(audio, "numpy"):
                    audio_chunks.append(audio.numpy())
                else:
                    audio_chunks.append(audio)

            if audio_chunks:
                # Concatenate audio chunks
                if len(audio_chunks) == 1:
                    audio_data = audio_chunks[0]
                else:
                    audio_data = np.concatenate(audio_chunks)

                # Encode to MP3
                mp3_data = self._encode_mp3(audio_data)

                # Write to output path
                with open(output_path, "wb") as f:
                    f.write(mp3_data)

                # Also save to cache
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, "wb") as f:
                    f.write(mp3_data)

                return True
            return False
        except Exception as e:
            if not self.quiet:
                print(f"Error generating audio for '{text[:30]}...': {e}", file=sys.stderr)
            return False

    def _setup_signal_handler(self) -> None:
        """Set up signal handler for graceful interruption."""

        def handler(signum, frame):
            self._interrupted = True

        signal.signal(signal.SIGINT, handler)

    def generate_batch(
        self,
        entries: list[VocabEntry],
        output_dir: Path,
        prefix: str = "card",
        preprocess: Callable[[str], str] | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> tuple[list[VocabEntry], int, int]:
        """Generate audio for a batch of vocabulary entries.

        Args:
            entries: List of vocabulary entries
            output_dir: Directory to save audio files
            prefix: Prefix for audio filenames
            preprocess: Optional function to preprocess text before TTS
            progress_callback: Optional callback(current, total, item_text)

        Returns:
            Tuple of (updated entries, generated_count, cached_count)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        self._init_pipeline()
        self._setup_signal_handler()
        self._interrupted = False

        generated = 0
        cached = 0

        if self.quiet:
            # Quiet mode - no progress bar
            for idx, entry in enumerate(entries):
                if self._interrupted:
                    raise AudioGenerationInterrupted()

                num = idx + 1
                audio_file = f"{prefix}_{num:04d}.mp3"
                audio_path = output_dir / audio_file

                # Get text to speak (use pronunciation if available, else sentence)
                tts_text = entry.pronunciation if entry.pronunciation else entry.sentence

                # Check if cached
                cache_path = get_audio_cache_path(
                    tts_text, self.config.resolved_voice, self.config.language
                )
                was_cached = cache_path.exists() and not self.config.force

                if self.generate_audio(tts_text, audio_path, preprocess):
                    entry.audio_file = audio_file
                    if was_cached:
                        cached += 1
                    else:
                        generated += 1

                if progress_callback:
                    progress_callback(num, len(entries), entry.sentence[:30])
        else:
            # Interactive mode with progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                TextColumn("[cyan]{task.fields[current]}"),
            ) as progress:
                task = progress.add_task(
                    "Generating audio...", total=len(entries), current=""
                )

                for idx, entry in enumerate(entries):
                    if self._interrupted:
                        progress.stop()
                        raise AudioGenerationInterrupted()

                    num = idx + 1
                    audio_file = f"{prefix}_{num:04d}.mp3"
                    audio_path = output_dir / audio_file

                    # Get text to speak
                    tts_text = entry.pronunciation if entry.pronunciation else entry.sentence

                    progress.update(task, current=entry.sentence[:30])

                    # Check if cached
                    cache_path = get_audio_cache_path(
                        tts_text, self.config.resolved_voice, self.config.language
                    )
                    was_cached = cache_path.exists() and not self.config.force

                    if self.generate_audio(tts_text, audio_path, preprocess):
                        entry.audio_file = audio_file
                        if was_cached:
                            cached += 1
                        else:
                            generated += 1

                    progress.advance(task)

        return entries, generated, cached


def get_preprocessor(language: str):
    """Get the appropriate text preprocessor for a language.

    Returns a function that preprocesses text for TTS, or None if no
    preprocessing is needed.
    """
    lang = language.lower()
    if lang in ("japanese", "ja", "jp"):
        from .preprocessing.japanese import preprocess_for_tts

        return preprocess_for_tts
    return None
