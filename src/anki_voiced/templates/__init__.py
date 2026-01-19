"""Built-in card templates for Anki decks."""

from .basic import create_basic_model, BasicTemplate
from .double_card import create_double_card_model, DoubleCardTemplate
from .cloze import create_cloze_model, ClozeTemplate

__all__ = [
    "create_basic_model",
    "create_double_card_model",
    "create_cloze_model",
    "BasicTemplate",
    "DoubleCardTemplate",
    "ClozeTemplate",
    "get_template",
    "TEMPLATE_INFO",
]

# Template information for help text
TEMPLATE_INFO = {
    "basic": {
        "name": "Basic",
        "description": "Simple front/back cards",
        "fields": ["front", "back"],
        "cards": 1,
        "required_columns": ["front", "back"],
    },
    "double-card": {
        "name": "Double Card",
        "description": "Comprehension + Production cards for language learning",
        "fields": ["sentence", "translation", "pronunciation", "hint", "tags"],
        "cards": 2,
        "required_columns": ["sentence", "translation"],
    },
    "cloze": {
        "name": "Cloze",
        "description": "Fill-in-the-blank cards with {{c1::cloze}} markers",
        "fields": ["text", "extra"],
        "cards": "variable",
        "required_columns": ["text"],
    },
}


def get_template(name: str):
    """Get a template class by name."""
    templates = {
        "basic": BasicTemplate,
        "double-card": DoubleCardTemplate,
        "cloze": ClozeTemplate,
    }
    return templates.get(name)
