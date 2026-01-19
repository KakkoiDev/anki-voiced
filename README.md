# anki-voiced

Generate Anki flashcard decks with AI-voiced audio.

## Quick Start

```bash
pip install anki-voiced       # Install the tool
anki-voiced init              # Create sample vocabulary.csv and deck.toml
anki-voiced create vocabulary.csv  # Generate deck with AI audio
```

## Installation

```bash
# Using uv (recommended)
uv tool install anki-voiced

# Using pip
pip install anki-voiced

# Using pipx
pipx install anki-voiced
```

To uninstall:

```bash
uv tool uninstall anki-voiced
# or
pip uninstall anki-voiced
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

### Japanese Language Support

For Japanese TTS, download the UniDic dictionary after installation:

```bash
python -m unidic download
```

This downloads ~500MB of dictionary data required for Japanese text processing.

## Usage

### Create a deck from CSV

```bash
# Quick single deck
anki-voiced create sentences.csv -o my-deck.apkg --lang japanese --voice male

# With config file for multi-tier decks
anki-voiced create --config deck.toml

# Read from stdin
cat data.csv | anki-voiced create - -o deck.apkg
```

### Initialize a new project

```bash
anki-voiced init --lang japanese
```

Creates:
- `vocabulary.csv` - Sample vocabulary file
- `deck.toml` - Configuration file for multi-tier decks

### List available voices

```bash
anki-voiced voices
anki-voiced voices --lang japanese
```

### Combine multiple decks

```bash
anki-voiced join tier1.apkg tier2.apkg -o combined.apkg -n "Master Deck"
```

## Commands

### `create`

Generate an Anki deck with AI-voiced audio from a CSV file.

```
Usage: anki-voiced create [OPTIONS] DATA_FILE

Options:
  -o, --output PATH       Output .apkg file [default: DATA_FILE.apkg]
  -n, --name TEXT         Deck name shown in Anki [default: filename]
  -l, --lang LANG         Language: english, japanese, french, portuguese
  -v, --voice VOICE       Voice: male, female, or specific voice name
  -t, --template NAME     Card template: basic, double-card, cloze
  -c, --config FILE       TOML config (overrides other options)
      --dry-run           Show what would be generated
      --force             Regenerate audio even if cached
  -q, --quiet             Minimal output (for scripts)
      --json              Machine-readable JSON output
```

### `init`

Create a new deck project with sample files.

```
Usage: anki-voiced init [OPTIONS]

Options:
  -l, --lang LANG    Language for sample content [default: english]
  -t, --template     Template to use [default: double-card]
```

### `voices`

List available voices for text-to-speech.

```
Usage: anki-voiced voices [OPTIONS]

Options:
  -l, --lang LANG    Filter by language
      --json         Machine-readable JSON output
```

### `join`

Combine multiple .apkg files into one master deck.

```
Usage: anki-voiced join [OPTIONS] DECK_FILES...

Options:
  -o, --output PATH    Output .apkg file (required)
  -n, --name TEXT      Master deck name (required)
```

## Templates

### `basic` - Simple Front/Back

- **Fields**: front, back
- **Cards**: 1 card (Front + Audio -> Back)
- **Use case**: Simple vocabulary, phrases

```csv
front,back
Hello,Bonjour
Goodbye,Au revoir
```

### `double-card` - Comprehension + Production

- **Fields**: sentence, translation, pronunciation, tags
- **Cards**: 2 cards per entry
  - Comprehension: Audio + Sentence -> Translation
  - Production: Translation + Hint -> Sentence + Audio
- **Use case**: Language learning with active recall

```csv
sentence,translation,pronunciation,tags
The meeting starts at 10 AM.,La réunion commence à 10h.,The meeting starts at 10 AM.,business
```

### `cloze` - Fill-in-the-blank

- **Fields**: text (with `{{c1::cloze}}`), extra
- **Cards**: Auto-generated from cloze markers
- **Use case**: Grammar patterns, vocabulary in context

```csv
text,extra
I {{c1::like}} apples.,verb: to enjoy
She {{c1::runs}} every day.,verb: to run
```

## Languages & Voices

| Language | Code | Default Voice | Available Voices |
|----------|------|---------------|------------------|
| English | `en` | `af_heart` | af_heart, af_bella, af_nicole, af_sarah, af_sky, am_adam, am_michael |
| Japanese | `ja` | `jm_kumo` | jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro, jm_kumo |
| French | `fr` | `ff_siwis` | ff_siwis |
| Portuguese | `pt` | `pf_camila` | pf_camila |

## Configuration

### Project Config (deck.toml)

```toml
name = "Japanese IT Vocabulary"
language = "japanese"
voice = "jm_kumo"
template = "double-card"
output = "japanese-it-complete.apkg"

[[tiers]]
name = "Tier 1 - Foundations"
data = "tier1.csv"

[[tiers]]
name = "Tier 2 - Development"
data = "tier2.csv"
```

### Environment Variables

```bash
ANKI_VOICED_LANG=japanese      # Default language
ANKI_VOICED_VOICE=female       # Default voice
ANKI_VOICED_TEMPLATE=basic     # Default template
NO_COLOR=1                     # Disable colors
```

### Configuration Precedence

1. Command-line flags (highest)
2. Environment variables
3. Project config (deck.toml in current directory)
4. User config (~/.config/anki-voiced/config.toml)
5. Built-in defaults (lowest)

## Caching

Audio files are cached in `~/.cache/anki-voiced/` for faster regeneration. To clear the cache:

```bash
rm -rf ~/.cache/anki-voiced
```

## Development

```bash
# Clone the repo
git clone https://github.com/kakkoidev/anki-voiced
cd anki-voiced

# Install with uv (recommended)
uv sync --all-extras

# Run tests
uv run pytest

# Run locally
uv run anki-voiced --help

# Or with pip
pip install -e ".[dev]"
pytest
python -m anki_voiced --help
```

## License

MIT

## Credits

- [Kokoro TTS](https://github.com/hexgrad/kokoro) - High-quality text-to-speech
- [genanki](https://github.com/kerrickstaley/genanki) - Anki deck generation
- [lameenc](https://github.com/chrisstaite/lern) - MP3 encoding
- [Typer](https://typer.tiangolo.com/) - CLI framework
