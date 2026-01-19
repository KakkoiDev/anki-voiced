# Card Templates

anki-voiced includes three built-in card templates designed for different learning scenarios.

## Basic Template

The simplest template for vocabulary and phrase learning.

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| front | Yes | Target language text (what you're learning) |
| back | Yes | Translation or definition |

### CSV Example

```csv
front,back
Hello,Bonjour
Thank you,Merci
```

### Card Layout

**Question side:**
- Audio playback button
- Front text (large)

**Answer side:**
- Audio playback button
- Front text
- Back text (translation)

### Use Cases

- Simple vocabulary lists
- Phrase memorization
- Quick flashcard creation

---

## Double-Card Template

The default template, optimized for language learning with both comprehension and production practice.

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| sentence | Yes | Target language sentence |
| translation | Yes | Translation |
| pronunciation | No | Reading guide (furigana, IPA, etc.) |
| hint | No | Hint for production card (auto-generated if empty) |
| tags | No | Categories for organization |

### CSV Example

```csv
sentence,translation,pronunciation,tags
会議【かいぎ】は10時に始まります。,The meeting starts at 10.,かいぎはじゅうじにはじまります,business
```

### Cards Generated

**Card 1: Comprehension**
- Question: Audio + Sentence + Tags
- Answer: Translation + Pronunciation

**Card 2: Production**
- Question: Translation + Hint
- Answer: Sentence + Audio + Pronunciation

### Hints

If no hint is provided, an automatic hint is generated from the first 2 characters of the sentence followed by "...".

### Use Cases

- Language learning with active recall
- Vocabulary in context
- Sentence pattern practice

---

## Cloze Template

Fill-in-the-blank cards using Anki's native cloze deletion feature.

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| text | Yes | Text with `{{c1::word}}` cloze markers |
| extra | No | Additional information shown on answer |

### CSV Example

```csv
text,extra
I {{c1::like}} apples.,verb: to enjoy
She {{c1::runs}} every {{c2::day}}.,verb: to run; noun: period of time
```

### Cloze Syntax

Use `{{c1::word}}` to mark deletions:
- `{{c1::word}}` - Basic cloze
- `{{c1::word::hint}}` - Cloze with hint
- `{{c2::word}}` - Second cloze (creates separate card)

### Cards Generated

One card per unique cloze number. In the example above:
- "I {{c1::like}} apples." creates 1 card
- "She {{c1::runs}} every {{c2::day}}." creates 2 cards

### Use Cases

- Grammar patterns
- Vocabulary in context
- Fill-in-the-blank exercises

---

## Column Name Flexibility

All templates accept common column name variations:

| Field | Accepted Names |
|-------|---------------|
| front | front, word, term, question, target, sentence |
| back | back, translation, meaning, definition, answer |
| sentence | sentence, front, word, term, target, text |
| translation | translation, back, meaning, definition, answer |
| pronunciation | pronunciation, reading, furigana, phonetic, ipa |
| hint | hint, clue |
| tags | tags, tag, category, categories, note, notes |
| text | text, sentence, front, cloze |
| extra | extra, hint, note, explanation |

This means you can use your existing CSV files without renaming columns.

---

## Choosing a Template

| Template | Cards/Entry | Best For |
|----------|-------------|----------|
| basic | 1 | Quick vocabulary lists, simple phrases |
| double-card | 2 | Active recall, language learning |
| cloze | Variable | Grammar patterns, fill-in-the-blank |

Use `--template` to specify:

```bash
anki-voiced create vocab.csv --template basic
anki-voiced create vocab.csv --template double-card
anki-voiced create vocab.csv --template cloze
```
