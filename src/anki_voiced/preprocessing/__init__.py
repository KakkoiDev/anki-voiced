"""Language-specific preprocessing modules."""

from .japanese import preprocess_for_tts as japanese_preprocess

__all__ = ["japanese_preprocess"]
