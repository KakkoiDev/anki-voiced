"""Three-card model: Listening / Reading / Vocabulary (cloze).

Pedagogy (ported from nihongo-it-anki):
  Card 1 - Listening:  Audio-only front, no text (beats reading-along habit)
  Card 2 - Reading:    Plain sentence front, no audio (pure reading skill)
  Card 3 - Vocabulary: Front blanks the Cloze word (tests single vocab item)

CSS is loaded from templates/assets/card.css. Dark mode via .night_mode.
"""

from pathlib import Path

import genanki

from ..models import DeckConfig, VocabEntry
from ..preprocessing.japanese import to_ruby_html

_ASSET_DIR = Path(__file__).parent / "assets"


def _load_css() -> str:
    return (_ASSET_DIR / "card.css").read_text(encoding="utf-8")


def create_three_card_model(deck_config: DeckConfig) -> genanki.Model:
    """Return the genanki Model for the 3-card design."""
    return genanki.Model(
        deck_config.model_id,
        f"{deck_config.name} (3-Card)",
        fields=[
            {"name": "Sentence"},
            {"name": "Translation"},
            {"name": "Cloze"},
            {"name": "Pronunciation"},   # ruby HTML
            {"name": "Category"},
            {"name": "Audio"},
            {"name": "Register"},
            {"name": "KeyMeaning"},
            {"name": "PitchAccent"},
        ],
        templates=[
            {
                "name": "Listening",
                "qfmt": (
                    '<div class="card-type">Listening</div>\n'
                    '<div class="audio listening-front">{{Audio}}</div>\n'
                ),
                "afmt": (
                    '<div class="card-type">Listening</div>\n'
                    '<div class="audio">{{Audio}}</div>\n'
                    '<div class="sentence">{{Pronunciation}}</div>\n'
                    '<div class="translation">{{Translation}}</div>\n'
                    '<hr id="answer">\n'
                    '<div class="category">{{Category}}</div>'
                    '{{#Register}}<span class="register register-{{Register}}">{{Register}}</span>{{/Register}}\n'
                    '<div class="key-vocab">Key: '
                    '{{#PitchAccent}}{{PitchAccent}}{{/PitchAccent}}'
                    '{{^PitchAccent}}<span class="vocab">{{Cloze}}</span>{{/PitchAccent}} '
                    '({{KeyMeaning}})</div>\n'
                ),
            },
            {
                "name": "Reading",
                "qfmt": (
                    '<div class="card-type">Reading</div>\n'
                    '<div class="sentence">{{Sentence}}</div>\n'
                    '<div class="category">{{Category}}</div>'
                    '{{#Register}}<span class="register register-{{Register}}">{{Register}}</span>{{/Register}}\n'
                ),
                "afmt": (
                    '<div class="card-type">Reading</div>\n'
                    '<div class="audio">{{Audio}}</div>\n'
                    '<div class="sentence">{{Pronunciation}}</div>\n'
                    '<hr id="answer">\n'
                    '<div class="translation">{{Translation}}</div>\n'
                    '<div class="key-vocab">Key: '
                    '{{#PitchAccent}}{{PitchAccent}}{{/PitchAccent}}'
                    '{{^PitchAccent}}<span class="vocab">{{Cloze}}</span>{{/PitchAccent}} '
                    '({{KeyMeaning}})</div>\n'
                ),
            },
            {
                "name": "Vocabulary",
                "qfmt": (
                    '<div class="card-type">Vocabulary</div>\n'
                    '<div id="sentence" class="sentence">{{Sentence}}</div>\n'
                    '<div class="translation">{{Translation}}</div>\n'
                    '<div class="category">{{Category}}</div>\n'
                    '<script>\n'
                    "(function() {\n"
                    "    var el = document.getElementById('sentence');\n"
                    "    var cloze = '{{Cloze}}';\n"
                    "    if (el && cloze) {\n"
                    "        el.innerHTML = el.textContent.split(cloze).join('<span class=\"blank\">\\uff3f\\uff3f\\uff3f</span>');\n"
                    "    }\n"
                    "})();\n"
                    '</script>\n'
                ),
                "afmt": (
                    '<div class="card-type">Vocabulary</div>\n'
                    '<div id="sentence" class="sentence">{{Sentence}}</div>\n'
                    '<div class="audio">{{Audio}}</div>\n'
                    '<div class="translation">{{Translation}}</div>\n'
                    '<hr id="answer">\n'
                    '<div class="pronunciation">{{Pronunciation}}</div>\n'
                    '<script>\n'
                    "(function() {\n"
                    "    var el = document.getElementById('sentence');\n"
                    "    var cloze = '{{Cloze}}';\n"
                    "    if (el && cloze) {\n"
                    "        el.innerHTML = el.textContent.split(cloze).join('<span class=\"cloze-answer\">' + cloze + '</span>');\n"
                    "    }\n"
                    "})();\n"
                    '</script>\n'
                ),
            },
        ],
        css=_load_css(),
    )


def create_note(entry: VocabEntry, model: genanki.Model, audio_ref: str) -> genanki.Note:
    """Create one genanki Note for a 3-card entry."""
    pronunciation_html = to_ruby_html(entry.pronunciation) if entry.pronunciation else entry.sentence

    return genanki.Note(
        model=model,
        fields=[
            entry.sentence,
            entry.translation,
            entry.cloze,
            pronunciation_html,
            entry.note,
            audio_ref,
            entry.register,
            entry.key_meaning,
            entry.pitch_accent,
        ],
        guid=genanki.guid_for(entry.sentence),
        tags=[entry.note.replace(" ", "_").replace("-", "_")] if entry.note else [],
    )


CARDS_PER_NOTE = 3
