"""Data models for anki-voiced."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


# Supported Kokoro voices
VOICES = {
    "ja": {
        "male": "jm_kumo",
        "female": "jf_alpha",
    },
    "en": {
        "male": "am_adam",
        "female": "af_sarah",
    },
    "zh": {
        "male": "zm_yunxi",
        "female": "zf_xiaobei",
    },
    "ko": {
        "male": "km_chul",
        "female": "kf_yuna",
    },
    "fr": {
        "male": "fm_pierre",
        "female": "ff_chloe",
    },
    "es": {
        "male": "em_carlos",
        "female": "ef_maria",
    },
}

# Language code mapping for Kokoro
LANG_CODES = {
    "ja": "j",  # Japanese
    "en": "a",  # American English
    "zh": "z",  # Chinese
    "ko": "k",  # Korean
    "fr": "f",  # French
    "es": "e",  # Spanish
}


class VocabEntry(BaseModel):
    """A single vocabulary entry."""

    front: str = Field(..., description="Front of card (target language)")
    back: str = Field(..., description="Back of card (translation)")
    pronunciation: str = Field(default="", description="Reading/pronunciation guide")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    audio_file: str | None = Field(default=None, description="Path to audio file")


class DeckConfig(BaseModel):
    """Configuration for deck generation."""

    name: str = Field(..., description="Deck name")
    input_csv: Path = Field(..., description="Path to input CSV file")
    output_dir: Path = Field(default=Path("."), description="Output directory")
    language: str = Field(default="ja", description="Target language code")
    voice_gender: Literal["male", "female"] = Field(default="male", description="Voice gender")
    include_audio: bool = Field(default=True, description="Generate and include audio")
    card_template: Literal["two-card", "basic"] = Field(
        default="two-card", description="Card template to use"
    )

    @property
    def voice(self) -> str:
        """Get the Kokoro voice ID for this config."""
        return VOICES.get(self.language, VOICES["en"])[self.voice_gender]

    @property
    def lang_code(self) -> str:
        """Get the Kokoro language code."""
        return LANG_CODES.get(self.language, "a")


class GenerationProgress(BaseModel):
    """Track progress of audio/deck generation."""

    total: int = 0
    completed: int = 0
    failed: int = 0
    current_item: str = ""

    @property
    def percent(self) -> float:
        """Get completion percentage."""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100
