"""Basic single-card template."""

import genanki

from ..models import VocabEntry
from ..preprocessing.japanese import to_ruby_html

# Stable model ID
MODEL_ID = 1607392320


def create_basic_model() -> genanki.Model:
    """Create a basic single-card model.

    Fields: front, back, audio
    Cards: 1 card (Front + Audio → Back)
    Use case: Simple vocabulary, phrases
    """
    return genanki.Model(
        MODEL_ID,
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
    font-family: "Noto Sans", "Hiragino Kaku Gothic Pro", sans-serif;
    font-size: 20px;
    text-align: center;
    color: #333;
    background-color: #fafafa;
    padding: 20px;
}

.front {
    font-size: 28px;
    font-weight: bold;
    margin: 20px 0;
    line-height: 2;
}

ruby {
    ruby-align: center;
}

ruby rt {
    font-size: 12px;
    font-weight: normal;
    color: #666;
}

.back {
    font-size: 22px;
    color: #444;
    margin: 15px 0;
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


class BasicTemplate:
    """Handler for basic template."""

    name = "basic"
    model = None

    @classmethod
    def get_model(cls) -> genanki.Model:
        if cls.model is None:
            cls.model = create_basic_model()
        return cls.model

    @classmethod
    def create_note(cls, entry: VocabEntry, audio_ref: str = "") -> genanki.Note:
        """Create a note for the basic template."""
        # Convert bracket furigana to ruby HTML for display
        front_html = to_ruby_html(entry.front)

        return genanki.Note(
            model=cls.get_model(),
            fields=[
                front_html,
                entry.back,
                audio_ref,
            ],
            tags=entry.tags,
        )

    @classmethod
    def get_required_columns(cls) -> list[str]:
        return ["front", "back"]

    @classmethod
    def get_audio_text(cls, entry: VocabEntry) -> str:
        """Get the text to generate audio for."""
        return entry.front
