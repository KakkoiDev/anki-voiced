"""Load per-deck configuration from decks/<slug>/deck.toml."""

from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from .config import DECK_CONFIG_FILE, get_decks_root
from .models import DeckConfig, TierConfig


def load_deck_config(slug: str, decks_root: Path | None = None) -> DeckConfig:
    """Load a deck configuration from <decks_root>/<slug>/deck.toml."""
    root = decks_root or get_decks_root()
    config_path = root / slug / DECK_CONFIG_FILE
    if not config_path.exists():
        raise FileNotFoundError(f"No deck config at {config_path}")

    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    deck = raw["deck"]
    tiers_raw = raw["tiers"]

    names = {int(k): v for k, v in tiers_raw.get("names", {}).items()}
    sizes = {int(k): v for k, v in tiers_raw.get("sizes", {}).items()}
    count = int(tiers_raw.get("count", len(names) or len(sizes)))

    tiers = [
        TierConfig(
            number=n,
            name=names.get(n, f"Tier {n}"),
            size=sizes.get(n, 0),
        )
        for n in range(1, count + 1)
    ]

    return DeckConfig(
        slug=deck["slug"],
        name=deck["name"],
        model_id=int(deck["model_id"]),
        deck_base_id=int(deck["deck_base_id"]),
        tiers=tiers,
    )


def list_decks(decks_root: Path | None = None) -> list[str]:
    """Return slugs of all configured decks."""
    root = decks_root or get_decks_root()
    if not root.exists():
        return []
    return sorted(
        d.name
        for d in root.iterdir()
        if d.is_dir() and (d / DECK_CONFIG_FILE).exists()
    )


def scaffold_deck(
    slug: str,
    name: str | None = None,
    decks_root: Path | None = None,
) -> Path:
    """Create decks/<slug>/ with deck.toml and an empty tier1-vocabulary.csv."""
    root = decks_root or get_decks_root()
    deck_dir = root / slug
    deck_dir.mkdir(parents=True, exist_ok=True)

    display_name = name or slug.replace("-", " ").replace("_", " ").title()

    # Generate stable IDs from slug (deterministic, non-colliding)
    import hashlib

    h = int(hashlib.sha256(slug.encode()).hexdigest(), 16)
    model_id = 1_000_000_000 + (h % 1_000_000_000)
    deck_base_id = 2_000_000_000 + ((h >> 32) % 1_000_000_000)

    config_path = deck_dir / DECK_CONFIG_FILE
    if not config_path.exists():
        config_path.write_text(
            f'''[deck]
slug = "{slug}"
name = "{display_name}"
model_id = {model_id}
deck_base_id = {deck_base_id}

[tiers]
count = 1

[tiers.names]
1 = "Tier 1"

[tiers.sizes]
1 = 0
''',
            encoding="utf-8",
        )

    csv_path = deck_dir / "tier1-vocabulary.csv"
    if not csv_path.exists():
        csv_path.write_text(
            "Sentence,Translation,Cloze,Pronunciation,Note,Register,KeyMeaning,PitchAccent,Audio\n"
            '会議【かいぎ】は10時【じ】です。,The meeting is at 10.,会議,会議【かいぎ】は10時【じ】です。,'
            "Business - Meetings,polite,meeting,,\n",
            encoding="utf-8",
        )

    return deck_dir
