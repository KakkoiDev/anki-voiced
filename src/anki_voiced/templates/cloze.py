"""Cloze (fill-in-the-blank) template."""

import genanki

from ..models import VocabEntry

# Stable model ID - must be different from other templates
MODEL_ID = 1607392321


def create_cloze_model() -> genanki.Model:
    """Create a cloze model.

    Fields: text (with {{c1::cloze}}), extra, audio
    Cards: Auto-generated from cloze markers
    Use case: Grammar patterns, vocabulary in context
    """
    return genanki.Model(
        MODEL_ID,
        "anki-voiced Cloze",
        model_type=genanki.Model.CLOZE,
        fields=[
            {"name": "Text"},
            {"name": "Extra"},
            {"name": "Audio"},
        ],
        templates=[
            {
                "name": "Cloze",
                "qfmt": """
<div class="audio">{{Audio}}</div>
<div class="text">{{cloze:Text}}</div>
""",
                "afmt": """
<div class="audio">{{Audio}}</div>
<div class="text">{{cloze:Text}}</div>
{{#Extra}}<hr id="answer"><div class="extra">{{Extra}}</div>{{/Extra}}
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

.text {
    font-size: 24px;
    margin: 20px 0;
    line-height: 1.6;
}

.cloze {
    font-weight: bold;
    color: #0066cc;
}

.extra {
    font-size: 16px;
    color: #666;
    margin: 15px 0;
    font-style: italic;
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


class ClozeTemplate:
    """Handler for cloze template."""

    name = "cloze"
    model = None

    @classmethod
    def get_model(cls) -> genanki.Model:
        if cls.model is None:
            cls.model = create_cloze_model()
        return cls.model

    @classmethod
    def create_note(cls, entry: VocabEntry, audio_ref: str = "") -> genanki.Note:
        """Create a note for the cloze template."""
        return genanki.Note(
            model=cls.get_model(),
            fields=[
                entry.text,
                entry.extra,
                audio_ref,
            ],
            tags=entry.tags,
        )

    @classmethod
    def get_required_columns(cls) -> list[str]:
        return ["text"]

    @classmethod
    def get_audio_text(cls, entry: VocabEntry) -> str:
        """Get the text to generate audio for (without cloze markers)."""
        import re

        # Remove cloze markers to get plain text for TTS
        # {{c1::word}} → word
        # {{c1::word::hint}} → word
        text = entry.text
        text = re.sub(r"\{\{c\d+::([^}:]+)(?:::[^}]*)?\}\}", r"\1", text)
        return text
