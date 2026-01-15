"""Audio generation using Kokoro TTS."""

from pathlib import Path

import soundfile as sf
from kokoro import KPipeline
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .models import DeckConfig, VocabEntry


class AudioGenerator:
    """Generate audio files using Kokoro TTS."""

    def __init__(self, config: DeckConfig):
        self.config = config
        self.pipeline: KPipeline | None = None

    def _init_pipeline(self) -> None:
        """Initialize the Kokoro TTS pipeline (lazy loading)."""
        if self.pipeline is None:
            self.pipeline = KPipeline(lang_code=self.config.lang_code)

    def generate_audio(self, text: str, output_path: Path) -> bool:
        """Generate audio for a single text.

        Args:
            text: Text to synthesize
            output_path: Path to save the WAV file

        Returns:
            True if successful, False otherwise
        """
        self._init_pipeline()

        try:
            audio_chunks = []
            for _, _, audio in self.pipeline(text, voice=self.config.voice):
                audio_chunks.append(audio)

            if audio_chunks:
                import numpy as np

                audio_data = np.concatenate(audio_chunks)
                sf.write(str(output_path), audio_data, 24000)
                return True
            return False
        except Exception as e:
            print(f"Error generating audio for '{text[:30]}...': {e}")
            return False

    def generate_batch(
        self, entries: list[VocabEntry], output_dir: Path, prefix: str = "card"
    ) -> list[VocabEntry]:
        """Generate audio for a batch of vocabulary entries.

        Args:
            entries: List of vocabulary entries
            output_dir: Directory to save audio files
            prefix: Prefix for audio filenames

        Returns:
            Updated entries with audio_file paths set
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        self._init_pipeline()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[cyan]{task.fields[current]}"),
        ) as progress:
            task = progress.add_task(
                "Generating audio...", total=len(entries), current=""
            )

            for idx, entry in enumerate(entries):
                num = idx + 1
                audio_file = f"{prefix}_{num:04d}.wav"
                audio_path = output_dir / audio_file

                progress.update(task, current=entry.front[:30])

                if self.generate_audio(entry.front, audio_path):
                    entry.audio_file = audio_file

                progress.advance(task)

        return entries
