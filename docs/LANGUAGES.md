# Language Support

anki-voiced supports multiple languages through the Kokoro TTS engine.

## Supported Languages

| Language | Code | Full Name | Default Voice |
|----------|------|-----------|---------------|
| English | `en` | `english` | `af_heart` (female) |
| Japanese | `ja` | `japanese` | `jm_kumo` (male) |
| French | `fr` | `french` | `ff_siwis` (female) |
| Portuguese | `pt` | `portuguese` | `pf_camila` (female) |

## Using Language Codes

You can use either the short code or full name:

```bash
anki-voiced create vocab.csv --lang japanese
anki-voiced create vocab.csv --lang ja
```

## Available Voices

### English
- Female: `af_heart`, `af_bella`, `af_nicole`, `af_sarah`, `af_sky`
- Male: `am_adam`, `am_michael`

### Japanese
- Female: `jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`
- Male: `jm_kumo`

### French
- Female: `ff_siwis`

### Portuguese
- Female: `pf_camila`

## Specifying Voice

Use `--voice` with either gender or specific voice name:

```bash
# Use default female voice for the language
anki-voiced create vocab.csv --lang japanese --voice female

# Use specific voice
anki-voiced create vocab.csv --lang japanese --voice jf_alpha
```

List available voices:

```bash
anki-voiced voices
anki-voiced voices --lang japanese
```

---

## Japanese-Specific Features

Japanese has special preprocessing for accurate TTS output.

### Furigana Support

Use furigana annotations for accurate readings:

```csv
sentence,translation,pronunciation,tags
会議【かいぎ】は10時【じ】に始【はじ】まります。,The meeting starts at 10.,かいぎはじゅうじにはじまります,business
```

The `pronunciation` field is preprocessed:
- Furigana extracted: `会議【かいぎ】` → `かいぎ`
- Numbers with furigana: `2日【ふつか】` → `ふつか`

### IT Terminology

Common IT terms are automatically converted to their Japanese pronunciation:

| English | Japanese |
|---------|----------|
| API | エーピーアイ |
| JSON | ジェイソン |
| GitHub | ギットハブ |
| Docker | ドッカー |
| React | リアクト |
| AWS | エーダブリューエス |

And many more. See the full list in the source code.

### Acronym Handling

Unknown acronyms (2-5 uppercase letters) are spelled out:
- `XYZ` → `エックスワイゼット`

AWS-style service names are handled:
- `EC2` → `イーシーツー`
- `S3` → `エススリー`

---

## Best Practices

### Japanese

1. **Use furigana in the sentence field** for kanji readings:
   ```csv
   会議【かいぎ】は明日【あした】です。
   ```

2. **Provide kana-only pronunciation** for TTS:
   ```csv
   sentence,translation,pronunciation
   会議【かいぎ】は明日です。,The meeting is tomorrow.,かいぎはあしたです
   ```

3. **IT terms**: Leave them in English/romaji; they'll be converted automatically.

### French & Portuguese

The TTS handles these languages natively. Just provide the text:

```csv
sentence,translation,pronunciation,tags
La réunion commence à 10 heures.,The meeting starts at 10.,La réunion commence à 10 heures.,business
```

### English

For learning English, the default female voice `af_heart` provides natural pronunciation:

```csv
sentence,translation,pronunciation,tags
The meeting starts at 10 AM.,会議は10時に始まります。,The meeting starts at 10 AM.,business
```
