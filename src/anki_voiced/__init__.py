"""anki-voiced: Generate Anki flashcard decks with AI-voiced audio."""

__version__ = "0.1.0"
__author__ = "kakkoidev"

from .models import DeckConfig, VocabEntry
from .deck import DeckBuilder
from .audio import AudioGenerator

__all__ = [
    "__version__",
    "DeckConfig",
    "VocabEntry",
    "DeckBuilder",
    "AudioGenerator",
]
