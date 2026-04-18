"""Tests for deck_config loader and scaffolder."""

from pathlib import Path

from anki_voiced.deck_config import list_decks, load_deck_config, scaffold_deck


def test_scaffold_creates_toml_and_csv(tmp_path: Path):
    deck_dir = scaffold_deck("demo", decks_root=tmp_path)
    assert (deck_dir / "deck.toml").exists()
    assert (deck_dir / "tier1-vocabulary.csv").exists()


def test_load_deck_config_from_scaffold(tmp_path: Path):
    scaffold_deck("demo", name="Demo Deck", decks_root=tmp_path)
    cfg = load_deck_config("demo", decks_root=tmp_path)
    assert cfg.slug == "demo"
    assert cfg.name == "Demo Deck"
    assert cfg.tier_count == 1
    assert cfg.tier(1).name == "Tier 1"


def test_list_decks(tmp_path: Path):
    scaffold_deck("alpha", decks_root=tmp_path)
    scaffold_deck("beta", decks_root=tmp_path)
    slugs = list_decks(decks_root=tmp_path)
    assert slugs == ["alpha", "beta"]
