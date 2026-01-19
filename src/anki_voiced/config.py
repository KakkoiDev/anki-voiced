"""Configuration system with XDG paths, environment variables, and TOML support.

Configuration precedence (highest to lowest):
1. Command-line flags
2. Environment variables
3. Project config file (deck.toml in current directory)
4. User config file (~/.config/anki-voiced/config.toml)
5. Built-in defaults
"""

import os
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


# XDG Base Directory defaults
def _get_xdg_config_home() -> Path:
    """Get XDG config directory."""
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _get_xdg_cache_home() -> Path:
    """Get XDG cache directory."""
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))


# Application directories
APP_NAME = "anki-voiced"
CONFIG_DIR = _get_xdg_config_home() / APP_NAME
CACHE_DIR = _get_xdg_cache_home() / APP_NAME
USER_CONFIG_FILE = CONFIG_DIR / "config.toml"
PROJECT_CONFIG_FILE = "deck.toml"

# Environment variable prefix
ENV_PREFIX = "ANKI_VOICED_"

# Default values
DEFAULTS = {
    "language": "english",
    "voice": "female",
    "template": "double-card",
}


def load_toml_file(path: Path) -> dict[str, Any]:
    """Load a TOML file, returning empty dict if not found."""
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def get_env_config() -> dict[str, Any]:
    """Get configuration from environment variables."""
    config: dict[str, Any] = {}

    env_mappings = {
        f"{ENV_PREFIX}LANG": "language",
        f"{ENV_PREFIX}VOICE": "voice",
        f"{ENV_PREFIX}TEMPLATE": "template",
    }

    for env_var, config_key in env_mappings.items():
        value = os.environ.get(env_var)
        if value:
            config[config_key] = value

    return config


def should_use_color() -> bool:
    """Check if colored output should be used."""
    # NO_COLOR is a standard (https://no-color.org/)
    if os.environ.get("NO_COLOR"):
        return False
    # Also check for common CI environments
    if os.environ.get("CI"):
        return False
    return True


def is_quiet_mode() -> bool:
    """Check if quiet mode is enabled via environment."""
    return bool(os.environ.get(f"{ENV_PREFIX}QUIET"))


class Config:
    """Configuration container with precedence handling."""

    def __init__(self):
        self._user_config = load_toml_file(USER_CONFIG_FILE)
        self._project_config = load_toml_file(Path.cwd() / PROJECT_CONFIG_FILE)
        self._env_config = get_env_config()

    def get(self, key: str, default: Any = None, cli_value: Any = None) -> Any:
        """Get a config value with proper precedence.

        Args:
            key: Configuration key
            default: Default value if not found anywhere
            cli_value: Value from command line (highest priority)
        """
        # CLI value takes precedence
        if cli_value is not None:
            return cli_value

        # Then environment
        if key in self._env_config:
            return self._env_config[key]

        # Then project config
        if key in self._project_config:
            return self._project_config[key]

        # Then user config
        if key in self._user_config:
            return self._user_config[key]

        # Then defaults
        return DEFAULTS.get(key, default)

    @property
    def project_config(self) -> dict[str, Any]:
        """Get the full project configuration."""
        return self._project_config

    def has_project_config(self) -> bool:
        """Check if a project config file exists."""
        return bool(self._project_config)


def get_cache_dir() -> Path:
    """Get the audio cache directory, creating it if needed."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def get_audio_cache_path(text: str, voice: str, lang: str) -> Path:
    """Get the cache path for a specific audio file.

    Uses a hash of the text + voice + language to create unique filenames.
    """
    import hashlib

    key = f"{text}|{voice}|{lang}"
    hash_str = hashlib.sha256(key.encode()).hexdigest()[:16]
    return get_cache_dir() / f"{hash_str}.mp3"


def ensure_config_dir() -> None:
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
