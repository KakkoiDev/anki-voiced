"""User config, XDG paths, and SHA256 audio cache."""

import hashlib
import os
from pathlib import Path

APP_NAME = "anki-voiced"


def _get_xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _get_xdg_cache_home() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))


CONFIG_DIR = _get_xdg_config_home() / APP_NAME
CACHE_DIR = _get_xdg_cache_home() / APP_NAME
USER_CONFIG_FILE = CONFIG_DIR / "config.toml"
DECK_CONFIG_FILE = "deck.toml"

# Default decks root (overridable with ANKI_VOICED_DECKS_DIR)
DEFAULT_DECKS_DIR = Path("decks")


def get_decks_root() -> Path:
    """Directory where deck slugs live (usually ./decks/)."""
    env = os.environ.get("ANKI_VOICED_DECKS_DIR")
    if env:
        return Path(env).resolve()
    return Path.cwd() / DEFAULT_DECKS_DIR


def should_use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CI"):
        return False
    return True


def get_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def get_audio_cache_path(text: str, voice: str) -> Path:
    """SHA256-keyed path under ~/.cache/anki-voiced/."""
    key = f"{text}|{voice}"
    hash_str = hashlib.sha256(key.encode()).hexdigest()[:16]
    return get_cache_dir() / f"{hash_str}.mp3"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
