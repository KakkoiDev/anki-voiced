"""Audio generation via Microsoft Edge TTS, with SHA256 caching."""

import asyncio
import shutil
import signal
import sys
from pathlib import Path
from typing import Callable

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from .config import get_audio_cache_path
from .models import VOICES, VocabEntry, resolve_voice
from .preprocessing.japanese import preprocess_for_tts

# Rate limiting for Edge TTS
DELAY_BETWEEN_REQUESTS = 0.3
MAX_RETRIES = 3


class AudioGenerationInterrupted(Exception):
    """Raised when audio generation is interrupted by the user."""


async def _edge_tts_save(text: str, voice: str, output_path: Path, retries: int = MAX_RETRIES) -> None:
    """Call edge-tts and save to output_path, with exponential backoff."""
    import edge_tts  # lazy import

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries - 1:
                await asyncio.sleep(2 ** (attempt + 1))
            else:
                raise
    if last_err:
        raise last_err


class AudioGenerator:
    """Generate MP3 audio via Edge TTS, caching by SHA256(text|voice)."""

    def __init__(self, voice: str = "male", force: bool = False, quiet: bool = False):
        self.voice_name = voice
        self.resolved_voice = resolve_voice(voice)
        self.force = force
        self.quiet = quiet
        self._interrupted = False

    # Sync wrappers around async Edge TTS

    def generate_audio(
        self,
        text: str,
        output_path: Path,
        preprocess: Callable[[str], str] | None = None,
    ) -> bool:
        """Generate one MP3 file. Returns True on success."""
        tts_input = preprocess(text) if preprocess else text

        cache_path = get_audio_cache_path(tts_input, self.resolved_voice)
        if cache_path.exists() and not self.force:
            shutil.copy(cache_path, output_path)
            return True

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            asyncio.run(_edge_tts_save(tts_input, self.resolved_voice, output_path))
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(output_path, cache_path)
            return True
        except Exception as e:  # noqa: BLE001
            if not self.quiet:
                print(f"Error generating audio for '{text[:30]}...': {e}", file=sys.stderr)
            return False

    def _setup_signal_handler(self) -> None:
        def handler(signum, frame):  # noqa: ARG001
            self._interrupted = True

        signal.signal(signal.SIGINT, handler)

    def generate_batch(
        self,
        entries: list[VocabEntry],
        output_dir: Path,
        filename_fn: Callable[[int], str] | None = None,
        preprocess: Callable[[str], str] | None = preprocess_for_tts,
    ) -> tuple[list[VocabEntry], int, int]:
        """Generate MP3s for a batch of entries.

        Returns (entries, generated_count, cached_count).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        self._setup_signal_handler()
        self._interrupted = False

        generated = 0
        cached = 0
        total = len(entries)

        filename = filename_fn or (lambda i: f"card_{i:04d}.mp3")

        def _audio_text(entry: VocabEntry) -> str:
            # Pronunciation field is dual-purpose (display + TTS). Fall back
            # to sentence if pronunciation is empty.
            return entry.pronunciation or entry.sentence

        iterator: object

        if self.quiet:
            iterator = enumerate(entries, start=1)
        else:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                TextColumn("[cyan]{task.fields[current]}"),
            )
            progress.start()
            task_id = progress.add_task("Generating audio", total=total, current="")

            def wrap(_iter):
                try:
                    for pair in _iter:
                        idx, entry = pair
                        progress.update(task_id, current=entry.sentence[:30])
                        yield pair
                        progress.advance(task_id)
                finally:
                    progress.stop()

            iterator = wrap(enumerate(entries, start=1))

        for idx, entry in iterator:
            if self._interrupted:
                raise AudioGenerationInterrupted()

            text = _audio_text(entry)
            tts_input = preprocess(text) if preprocess else text

            cache_path = get_audio_cache_path(tts_input, self.resolved_voice)
            was_cached = cache_path.exists() and not self.force

            audio_file = filename(idx)
            audio_path = output_dir / audio_file

            if self.generate_audio(text, audio_path, preprocess):
                entry.audio_file = audio_file
                if was_cached:
                    cached += 1
                else:
                    generated += 1

        return entries, generated, cached


def list_voices() -> dict[str, str]:
    """Return the built-in Edge TTS Japanese voices."""
    return dict(VOICES)
