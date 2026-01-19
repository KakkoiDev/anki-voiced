# Japanese TTS Resources

Language-specific resources for generating accurate Japanese audio with TTS engines.

## Problem

TTS engines like Kokoro often mispronounce:
- **Kanji**: 今日中 → "konnichichuu" instead of "kyoujyuuni"
- **English acronyms**: API → "エーチーム" (dropping letters)
- **Counters**: 2日 → "nihi" instead of "futsuka"

## Solution

Use furigana annotations in your source data, then preprocess before TTS.

### Input Format

Annotate kanji with readings using 【】brackets:

```
今日中【きょうじゅう】にできますか？
2日【ふつか】かかります。
APIの応答【おうとう】が遅【おそ】い。
```

### Preprocessing

```python
from pronunciation import preprocess_for_tts

text = "APIの応答【おうとう】が遅【おそ】い"
tts_input = preprocess_for_tts(text)
# Result: "エーピーアイのおうとうがおそい"
```

## Features

### Furigana Extraction
Converts kanji with readings to pure hiragana:
- `昼食【ちゅうしょく】` → `ちゅうしょく`
- `2日【ふつか】` → `ふつか` (handles number+kanji)

### English Term Conversion
Converts English to katakana pronunciation:
- `API` → `エーピーアイ`
- `EC2` → `イーシーツー`
- `JSON` → `ジェイソン`

### 150+ IT Terms
Pre-mapped pronunciations for common tech vocabulary:
- Cloud: AWS, GCP, Lambda, Kubernetes, Docker
- DevOps: CI/CD, GitHub, Terraform, Jenkins
- Frontend: React, Vue, TypeScript, webpack
- Backend: REST, GraphQL, SQL, Redis, Kafka
- Security: JWT, OAuth, SSL, CORS, XSS

## Adding Custom Terms

```python
from pronunciation import add_acronym

add_acronym('MQTT', 'エムキューティーティー')
```

## Design Philosophy

1. **Furigana is authoritative** - Always use provided readings
2. **English needs conversion** - TTS models struggle with English in Japanese context
3. **Context-aware numbers**:
   - English context (EC2, S3): `ツー`, `スリー`
   - Japanese context: Use furigana (`2日【ふつか】` → `ふつか`)
