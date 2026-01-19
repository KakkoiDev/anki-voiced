"""Double-card template for comprehension and production."""

import genanki

from ..models import VocabEntry
from ..preprocessing.japanese import to_ruby_html

# Stable model ID
MODEL_ID = 1607392319


def create_double_card_model() -> genanki.Model:
    """Create the 2-card Anki model.

    Fields: sentence, translation, pronunciation, hint, tags, audio
    Cards:
      - Comprehension: Audio + Sentence → Translation
      - Production: Translation + Hint → Sentence + Audio
    Use case: Language learning with active recall
    """
    return genanki.Model(
        MODEL_ID,
        "anki-voiced Double-Card",
        fields=[
            {"name": "Sentence"},
            {"name": "Translation"},
            {"name": "Pronunciation"},
            {"name": "Hint"},
            {"name": "Tags"},
            {"name": "Audio"},
        ],
        templates=[
            # Card A: Comprehension (Listening + Reading)
            {
                "name": "Comprehension",
                "qfmt": """
<div class="card-type">Comprehension</div>
<div class="audio">{{Audio}}</div>
<div class="sentence">{{Sentence}}</div>
<div class="tags">{{Tags}}</div>
""",
                "afmt": """
<div class="card-type">Comprehension</div>
<div class="audio">{{Audio}}</div>
<div class="sentence">{{Sentence}}</div>
<div class="tags">{{Tags}}</div>
<hr id="answer">
<div class="translation">{{Translation}}</div>
""",
            },
            # Card B: Production
            {
                "name": "Production",
                "qfmt": """
<div class="card-type">Production</div>
<div class="translation">{{Translation}}</div>
<div class="prompt">How do you say this?</div>
{{#Hint}}<div class="hint">Hint: {{Hint}}</div>{{/Hint}}
""",
                "afmt": """
<div class="card-type">Production</div>
<div class="translation">{{Translation}}</div>
<hr id="answer">
<div class="sentence">{{Sentence}}</div>
<div class="audio">{{Audio}}</div>
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

.sentence {
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

.translation {
    font-size: 22px;
    color: #444;
    margin: 15px 0;
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


class DoubleCardTemplate:
    """Handler for double-card template."""

    name = "double-card"
    model = None

    @classmethod
    def get_model(cls) -> genanki.Model:
        if cls.model is None:
            cls.model = create_double_card_model()
        return cls.model

    @classmethod
    def create_note(cls, entry: VocabEntry, audio_ref: str = "") -> genanki.Note:
        """Create a note for the double-card template."""
        # Auto-generate hint if not provided
        hint = entry.hint
        if not hint and entry.sentence:
            hint = entry.sentence[:2] + "..." if len(entry.sentence) > 2 else entry.sentence

        # Convert bracket furigana to ruby HTML for display
        sentence_html = to_ruby_html(entry.sentence)

        return genanki.Note(
            model=cls.get_model(),
            fields=[
                sentence_html,
                entry.translation,
                entry.pronunciation,
                hint,
                ", ".join(entry.tags),
                audio_ref,
            ],
            tags=entry.tags,
        )

    @classmethod
    def get_required_columns(cls) -> list[str]:
        return ["sentence", "translation"]

    @classmethod
    def get_audio_text(cls, entry: VocabEntry) -> str:
        """Get the text to generate audio for."""
        # Use pronunciation if available, otherwise sentence
        return entry.pronunciation if entry.pronunciation else entry.sentence
