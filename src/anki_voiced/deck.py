"""Anki deck generation using genanki."""

import random
from pathlib import Path

import genanki

from .models import DeckConfig, VocabEntry


# Stable model ID (generated once)
MODEL_ID = 1607392319


def create_two_card_model() -> genanki.Model:
    """Create the 2-card Anki model.

    Card A (Comprehension): Audio + Front → Back + Pronunciation
    Card B (Production): Back → Front + Audio + Pronunciation
    """
    return genanki.Model(
        MODEL_ID,
        "anki-voiced Two-Card",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
            {"name": "Pronunciation"},
            {"name": "Tags"},
            {"name": "Audio"},
            {"name": "Hint"},
        ],
        templates=[
            # Card A: Comprehension (Listening + Reading)
            {
                "name": "Comprehension",
                "qfmt": """
<div class="card-type">Comprehension</div>
<div class="audio">{{Audio}}</div>
<div class="front">{{Front}}</div>
<div class="tags">{{Tags}}</div>
""",
                "afmt": """
<div class="card-type">Comprehension</div>
<div class="audio">{{Audio}}</div>
<div class="front">{{Front}}</div>
<div class="tags">{{Tags}}</div>
<hr id="answer">
<div class="back">{{Back}}</div>
<div class="pronunciation">{{Pronunciation}}</div>
""",
            },
            # Card B: Production
            {
                "name": "Production",
                "qfmt": """
<div class="card-type">Production</div>
<div class="back">{{Back}}</div>
<div class="prompt">How do you say this?</div>
<div class="hint">Hint: {{Hint}}</div>
""",
                "afmt": """
<div class="card-type">Production</div>
<div class="back">{{Back}}</div>
<hr id="answer">
<div class="front">{{Front}}</div>
<div class="audio">{{Audio}}</div>
<div class="pronunciation">{{Pronunciation}}</div>
""",
            },
        ],
        css="""
.card {
    font-family: "Hiragino Kaku Gothic Pro", "Noto Sans", sans-serif;
    font-size: 20px;
    text-align: center;
    color: #333;
    background-color: #fafafa;
    padding: 20px;
}

.card-type {
    font-size: 12px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 15px;
}

.front {
    font-size: 28px;
    font-weight: bold;
    margin: 20px 0;
    line-height: 1.5;
}

.back {
    font-size: 22px;
    color: #444;
    margin: 15px 0;
}

.pronunciation {
    font-size: 18px;
    color: #666;
    margin: 15px 0;
    line-height: 1.8;
}

.tags {
    display: inline-block;
    background: #e0e0e0;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    color: #555;
    margin-top: 10px;
}

.prompt {
    font-size: 16px;
    color: #888;
    font-style: italic;
    margin: 15px 0;
}

.hint {
    font-size: 18px;
    color: #666;
    margin: 10px 0;
}

.audio {
    margin: 10px 0;
}

hr#answer {
    border: none;
    border-top: 1px solid #ddd;
    margin: 20px 0;
}
""",
    )


def create_basic_model() -> genanki.Model:
    """Create a basic single-card model."""
    return genanki.Model(
        MODEL_ID + 1,
        "anki-voiced Basic",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
            {"name": "Audio"},
        ],
        templates=[
            {
                "name": "Card",
                "qfmt": """
<div class="audio">{{Audio}}</div>
<div class="front">{{Front}}</div>
""",
                "afmt": """
<div class="audio">{{Audio}}</div>
<div class="front">{{Front}}</div>
<hr id="answer">
<div class="back">{{Back}}</div>
""",
            },
        ],
        css="""
.card {
    font-family: "Noto Sans", sans-serif;
    font-size: 20px;
    text-align: center;
    padding: 20px;
}
.front { font-size: 28px; font-weight: bold; margin: 20px 0; }
.back { font-size: 22px; color: #444; margin: 15px 0; }
hr#answer { border: none; border-top: 1px solid #ddd; margin: 20px 0; }
""",
    )


class DeckBuilder:
    """Build Anki decks from vocabulary entries."""

    def __init__(self, config: DeckConfig):
        self.config = config
        self.deck_id = random.randint(1000000000, 9999999999)

    def build(self, entries: list[VocabEntry], audio_dir: Path | None = None) -> Path:
        """Build an Anki deck from vocabulary entries.

        Args:
            entries: List of vocabulary entries
            audio_dir: Directory containing audio files

        Returns:
            Path to the generated .apkg file
        """
        deck = genanki.Deck(self.deck_id, self.config.name)

        if self.config.card_template == "two-card":
            model = create_two_card_model()
        else:
            model = create_basic_model()

        media_files = []

        for entry in entries:
            # Prepare audio reference
            if entry.audio_file and audio_dir:
                audio_ref = f"[sound:{entry.audio_file}]"
                audio_path = audio_dir / entry.audio_file
                if audio_path.exists():
                    media_files.append(str(audio_path))
            else:
                audio_ref = ""

            # Create hint (first 2 characters)
            hint = entry.front[:2] + "..." if len(entry.front) > 2 else entry.front

            # Create note based on template
            if self.config.card_template == "two-card":
                note = genanki.Note(
                    model=model,
                    fields=[
                        entry.front,
                        entry.back,
                        entry.pronunciation,
                        ", ".join(entry.tags),
                        audio_ref,
                        hint,
                    ],
                    tags=entry.tags,
                )
            else:
                note = genanki.Note(
                    model=model,
                    fields=[
                        entry.front,
                        entry.back,
                        audio_ref,
                    ],
                    tags=entry.tags,
                )

            deck.add_note(note)

        # Write package
        output_path = self.config.output_dir / f"{self.config.name.replace(' ', '-').lower()}.apkg"
        package = genanki.Package(deck)
        package.media_files = media_files
        package.write_to_file(str(output_path))

        return output_path
