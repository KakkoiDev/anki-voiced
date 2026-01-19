"""Data models for anki-voiced."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


# Language configuration
# Maps user-facing language names to Kokoro lang codes
LANGUAGES = {
    "english": {"code": "a", "default_voice": "af_heart"},
    "japanese": {"code": "j", "default_voice": "jm_kumo"},
    "french": {"code": "f", "default_voice": "ff_siwis"},
    "portuguese": {"code": "p", "default_voice": "pf_camila"},
}

# Short aliases for languages
LANGUAGE_ALIASES = {
    "en": "english",
    "ja": "japanese",
    "jp": "japanese",
    "fr": "french",
    "pt": "portuguese",
}

# Available voices per language (Kokoro voices)
VOICES = {
    "english": {
        "male": ["am_adam", "am_michael"],
        "female": ["af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky"],
    },
    "japanese": {
        "male": ["jm_kumo"],
        "female": ["jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro"],
    },
    "french": {
        "male": [],
        "female": ["ff_siwis"],
    },
    "portuguese": {
        "male": [],
        "female": ["pf_camila"],
    },
}

# Templates available
TEMPLATES = ["basic", "double-card", "cloze"]


def normalize_language(lang: str) -> str:
    """Normalize language input to canonical form."""
    lang_lower = lang.lower().strip()
    return LANGUAGE_ALIASES.get(lang_lower, lang_lower)


def get_lang_code(language: str) -> str:
    """Get Kokoro language code for a language."""
    lang = normalize_language(language)
    if lang in LANGUAGES:
        return LANGUAGES[lang]["code"]
    return "a"  # Default to English


def get_default_voice(language: str, gender: str = "female") -> str:
    """Get the default voice for a language and gender."""
    lang = normalize_language(language)
    if lang not in VOICES:
        lang = "english"

    voices = VOICES[lang].get(gender, [])
    if voices:
        return voices[0]

    # Fall back to opposite gender
    other_gender = "female" if gender == "male" else "male"
    voices = VOICES[lang].get(other_gender, [])
    if voices:
        return voices[0]

    return LANGUAGES.get(lang, LANGUAGES["english"])["default_voice"]


def resolve_voice(voice: str, language: str) -> str:
    """Resolve a voice specification to an actual voice ID.

    Args:
        voice: Either 'male', 'female', or a specific voice ID
        language: The target language
    """
    if voice in ("male", "female"):
        return get_default_voice(language, voice)
    return voice


class VocabEntry(BaseModel):
    """A single vocabulary entry."""

    # For double-card template
    sentence: str = Field(default="", description="Target language sentence")
    translation: str = Field(default="", description="Translation")
    pronunciation: str = Field(default="", description="Reading/pronunciation guide")
    hint: str = Field(default="", description="Hint for production card")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    audio_file: str | None = Field(default=None, description="Path to audio file")

    # Aliases for basic template compatibility
    @property
    def front(self) -> str:
        return self.sentence

    @property
    def back(self) -> str:
        return self.translation

    # For cloze template
    text: str = Field(default="", description="Text with {{c1::cloze}} markers")
    extra: str = Field(default="", description="Extra information for cloze")


class TierConfig(BaseModel):
    """Configuration for a single tier in multi-tier decks."""

    name: str = Field(..., description="Subdeck name")
    data: str = Field(..., description="Path to CSV file")


class DeckConfig(BaseModel):
    """Configuration for deck generation."""

    name: str = Field(default="My Vocabulary", description="Deck name")
    input_csv: Path | None = Field(default=None, description="Path to input CSV file")
    output: Path = Field(default=Path("."), description="Output path for .apkg file")
    language: str = Field(default="english", description="Target language")
    voice: str = Field(default="female", description="Voice ID or gender")
    template: Literal["basic", "double-card", "cloze"] = Field(
        default="double-card", description="Card template to use"
    )

    # Multi-tier support
    tiers: list[TierConfig] = Field(default_factory=list, description="Tier configurations")

    # Processing options
    force: bool = Field(default=False, description="Force regenerate audio")
    dry_run: bool = Field(default=False, description="Show what would be generated")

    @property
    def resolved_voice(self) -> str:
        """Get the resolved Kokoro voice ID."""
        return resolve_voice(self.voice, self.language)

    @property
    def lang_code(self) -> str:
        """Get the Kokoro language code."""
        return get_lang_code(self.language)

    @property
    def is_multi_tier(self) -> bool:
        """Check if this is a multi-tier deck."""
        return len(self.tiers) > 0


class GenerationResult(BaseModel):
    """Result of deck generation."""

    output_path: Path
    card_count: int
    note_count: int
    audio_count: int
    template: str
    language: str
    voice: str
    cached_audio: int = 0
    generated_audio: int = 0
