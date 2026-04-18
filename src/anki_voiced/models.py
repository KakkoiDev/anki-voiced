"""Data models for anki-voiced (Japanese-only)."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


# Edge TTS Japanese voices
VOICES = {
    "male": "ja-JP-KeitaNeural",
    "female": "ja-JP-NanamiNeural",
}

DEFAULT_VOICE_GENDER = "male"


class Register(str, Enum):
    """Japanese speech register."""

    CASUAL = "casual"
    POLITE = "polite"
    FORMAL = "formal"
    KEIGO = "keigo"


def resolve_voice(voice: str) -> str:
    """Resolve 'male'/'female' or a voice ID into an Edge TTS voice name."""
    if voice in VOICES:
        return VOICES[voice]
    return voice


class VocabEntry(BaseModel):
    """A single vocabulary entry.

    Mirrors the CSV schema ported from nihongo-it-anki. The Pronunciation
    field is dual-purpose: card display (via to_ruby_html) AND TTS input
    (via preprocess_for_tts). Never replace kanji with kana in the CSV to
    fix TTS issues - add to TTS_KANJI_OVERRIDES instead.
    """

    model_config = ConfigDict(protected_namespaces=())

    sentence: str = Field(..., description="Japanese sentence (display form)")
    translation: str = Field(..., description="English translation")
    cloze: str = Field(default="", description="Key vocabulary word to test")
    pronunciation: str = Field(
        default="",
        description="Japanese with furigana brackets, e.g. 会議【かいぎ】",
    )
    note: str = Field(default="", description="Category/context for tagging")
    register: str = Field(default="", description="casual|polite|formal|keigo")
    key_meaning: str = Field(default="", description="English gloss of Cloze")
    pitch_accent: str = Field(
        default="",
        description="Auto-generated colored ruby HTML for Cloze word",
    )
    audio_file: str | None = Field(
        default=None, description="Generated audio filename"
    )


class TierConfig(BaseModel):
    """Configuration for a single tier in a deck."""

    number: int = Field(..., ge=1, description="Tier number (1-based)")
    name: str = Field(..., description="Tier display name")
    size: int = Field(..., ge=0, description="Expected row count")


class DeckConfig(BaseModel):
    """Per-deck configuration, loaded from decks/<slug>/deck.toml."""

    slug: str = Field(..., description="Deck directory name")
    name: str = Field(..., description="Human-readable deck name")
    model_id: int = Field(..., description="Stable Anki model ID")
    deck_base_id: int = Field(..., description="Base deck ID; tier ID = base + tier")
    tiers: list[TierConfig] = Field(..., description="Tier definitions")

    # Runtime options
    voice: str = Field(default=DEFAULT_VOICE_GENDER)
    force: bool = Field(default=False)
    dry_run: bool = Field(default=False)

    @property
    def resolved_voice(self) -> str:
        return resolve_voice(self.voice)

    @property
    def tier_count(self) -> int:
        return len(self.tiers)

    def tier(self, number: int) -> TierConfig:
        for t in self.tiers:
            if t.number == number:
                return t
        raise KeyError(f"No tier {number} in deck {self.slug}")

    def tier_range(self) -> range:
        return range(1, self.tier_count + 1)

    def get_deck_id(self, tier: int) -> int:
        return self.deck_base_id + tier

    def data_dir(self, decks_root: Path) -> Path:
        return decks_root / self.slug

    def csv_path(self, decks_root: Path, tier: int) -> Path:
        return self.data_dir(decks_root) / f"tier{tier}-vocabulary.csv"

    def audio_dir(self, decks_root: Path, tier: int, female: bool = False) -> Path:
        suffix = "-female" if female else ""
        return self.data_dir(decks_root) / f"tier{tier}-audio{suffix}"


class GenerationResult(BaseModel):
    """Result of deck generation."""

    output_path: Path
    card_count: int
    note_count: int
    audio_count: int
    voice: str
    generated_audio: int = 0
    cached_audio: int = 0


# CSV column names (canonical, case-insensitive)
CSV_COLUMNS = [
    "Sentence",
    "Translation",
    "Cloze",
    "Pronunciation",
    "Note",
    "Register",
    "KeyMeaning",
    "PitchAccent",
    "Audio",
]

REQUIRED_CSV_COLUMNS = {"Sentence", "Translation", "Cloze", "Pronunciation", "KeyMeaning"}
