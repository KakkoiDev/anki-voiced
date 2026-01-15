# anki-voiced

> Your vocabulary, voiced.

Turn any vocabulary list into a professional Anki deck with native-quality audio in minutes.

## The Problem

Creating high-quality Anki decks with audio is painful:
- Recording audio yourself is tedious (1000 cards = hours of work)
- Buying pre-made decks lacks customization
- Manual TTS copy-paste is slow and inconsistent
- Existing tools generate single-sided cards (passive recognition only)

## The Solution

```bash
anki-voiced generate vocabulary.csv --lang ja --name "My Japanese Deck"
# → Professional deck with native audio, zero manual work
```

## Features

| Feature | Benefit |
|---------|---------|
| **2-card design** | Learn both comprehension AND production |
| **AI-generated audio** | Native-quality TTS via Kokoro |
| **CSV → Deck pipeline** | Your content, professional output |
| **Batch processing** | 1000 cards as easily as 10 |
| **Multi-language** | Japanese, English, Chinese, Korean, French, Spanish |

## Installation

```bash
# Using pip
pip install anki-voiced

# Using uv (recommended)
uv tool install anki-voiced
```

### System Requirements

- Python 3.10+
- `espeak-ng` for phonemization:
  ```bash
  # Ubuntu/Debian
  sudo apt install espeak-ng

  # macOS
  brew install espeak-ng
  ```

## Quick Start

### 1. Create a vocabulary CSV

```csv
front,back,pronunciation,tags
こんにちは,Hello,こんにちは,greeting
ありがとう,Thank you,ありがとう,greeting
```

Or generate a sample:
```bash
anki-voiced init --lang ja
```

### 2. Generate your deck

```bash
anki-voiced generate vocabulary.csv --name "Japanese Basics" --lang ja
```

### 3. Import into Anki

Open Anki → File → Import → Select the `.apkg` file

## Commands

### `generate` - Create a deck

```bash
anki-voiced generate vocabulary.csv [OPTIONS]

Options:
  -n, --name TEXT      Deck name (default: "My Vocabulary")
  -l, --lang TEXT      Target language: ja, en, zh, ko, fr, es (default: ja)
  --voice TEXT         Voice gender: male/female (default: male)
  -o, --output PATH    Output directory (default: current)
  -t, --template TEXT  Card template: two-card/basic (default: two-card)
  --no-audio           Skip audio generation
```

### `init` - Create sample CSV

```bash
anki-voiced init [OPTIONS]

Options:
  -o, --output PATH    Output directory
  -l, --lang TEXT      Sample language (default: ja)
```

### `preview` - Preview CSV contents

```bash
anki-voiced preview vocabulary.csv [OPTIONS]

Options:
  -n, --count INT      Number of entries to preview (default: 5)
```

### `voices` - List available voices

```bash
anki-voiced voices
```

## CSV Format

### Required Columns
- `front` - Target language text (what you're learning)
- `back` - Translation/meaning

### Optional Columns
- `pronunciation` - Reading guide (furigana, IPA, etc.)
- `tags` - Categories (comma or space separated)

### Flexible Column Names

The tool recognizes common variations:

| Field | Accepted Names |
|-------|---------------|
| front | front, sentence, word, term, question, target |
| back | back, translation, meaning, definition, answer |
| pronunciation | pronunciation, reading, furigana, phonetic, ipa |
| tags | tags, tag, category, note |

## Card Templates

### Two-Card (Default)

Creates 2 cards per vocabulary entry:

**Card A (Comprehension)**
- Front: Audio + Target text
- Back: Translation + Pronunciation

**Card B (Production)**
- Front: Translation + Hint
- Back: Target text + Audio

### Basic

Creates 1 card per entry:
- Front: Audio + Target text
- Back: Translation

## Supported Languages

| Language | Code | Male Voice | Female Voice |
|----------|------|------------|--------------|
| Japanese | ja | jm_kumo | jf_alpha |
| English | en | am_adam | af_sarah |
| Chinese | zh | zm_yunxi | zf_xiaobei |
| Korean | ko | km_chul | kf_yuna |
| French | fr | fm_pierre | ff_chloe |
| Spanish | es | em_carlos | ef_maria |

## Performance

- Audio generation: ~8 seconds per entry
- 100 cards: ~13 minutes
- 1000 cards: ~2.2 hours

## Development

```bash
# Clone the repo
git clone https://github.com/kakkoidev/anki-voiced
cd anki-voiced

# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run locally
uv run anki-voiced --help
```

## License

MIT

## Credits

- [Kokoro TTS](https://github.com/hexgrad/kokoro) - High-quality text-to-speech
- [genanki](https://github.com/kerrickstaley/genanki) - Anki deck generation
- [Typer](https://typer.tiangolo.com/) - CLI framework
