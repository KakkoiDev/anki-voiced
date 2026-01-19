"""Japanese TTS preprocessing resources for anki-voiced."""

from .pronunciation import (
    preprocess_for_tts,
    extract_furigana,
    convert_english_terms,
    add_acronym,
    ACRONYM_MAP,
    LETTER_MAP,
    NUMBER_MAP,
)

__all__ = [
    'preprocess_for_tts',
    'extract_furigana',
    'convert_english_terms',
    'add_acronym',
    'ACRONYM_MAP',
    'LETTER_MAP',
    'NUMBER_MAP',
]
