"""anki-voiced: Generate Japanese Anki decks with AI-voiced audio."""

import warnings

# Pydantic warns about VocabEntry.register shadowing BaseModel.register.
# This is expected; the field name matches the CSV column "Register".
warnings.filterwarnings(
    "ignore",
    message='Field name "register" in "VocabEntry" shadows an attribute in parent "BaseModel"',
    category=UserWarning,
)

__version__ = "0.2.0"
__author__ = "kakkoidev"

from .audio import AudioGenerator
from .deck import build_combined_package, build_single_tier_package
from .deck_config import load_deck_config
from .models import DeckConfig, Register, VocabEntry
from .pitch_accent import get_pitch_html
from .preprocessing.japanese import preprocess_for_tts, to_ruby_html

__all__ = [
    "__version__",
    "DeckConfig",
    "VocabEntry",
    "Register",
    "AudioGenerator",
    "build_combined_package",
    "build_single_tier_package",
    "get_pitch_html",
    "load_deck_config",
    "preprocess_for_tts",
    "to_ruby_html",
]
