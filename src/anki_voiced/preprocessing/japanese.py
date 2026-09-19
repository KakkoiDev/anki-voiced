"""Japanese text preprocessing for TTS and card display.

Pipeline for preprocess_for_tts():
  1. Symbol substitutions (%, version strings)
  2. Insert adverb commas (まず -> まず、) - before furigana extraction
  3. Replace particle は -> わ (so TTS reads "wa" not "ha")
  4. Extract furigana, keeping kanji (unless in TTS_KANJI_OVERRIDES)
  5. Convert English acronyms/terms to katakana
  6. Insert particle pauses (を -> を、)
  7. Insert が subject-marker pauses (context-aware)
  8. Cleanup

CRITICAL: The Pronunciation field serves DUAL purpose:
  1. Card display: to_ruby_html() renders furigana as <ruby> tags.
  2. TTS input: preprocess_for_tts() cleans it for Edge TTS.

  NEVER replace kanji with kana directly in the CSV Pronunciation field
  to fix TTS issues. That destroys the kanji+furigana display on cards.
  Instead, add the kanji to TTS_KANJI_OVERRIDES (see acronyms.py).
"""

import re

from jp_core import furigana

from .acronyms import ACRONYM_MAP, LETTER_MAP, NUMBER_MAP, TTS_KANJI_OVERRIDES

# Character ranges
_KANJI = r"\u4e00-\u9fff\u3400-\u4dbf\u3005"  # CJK + ideographic iter mark 々
_HIRAGANA = r"\u3040-\u309f"
_KATAKANA = r"\u30a0-\u30ff"
_KANA = _HIRAGANA + _KATAKANA

# Introductory adverbs that get a comma after them for natural TTS rhythm
ADVERBS = [
    # Attention-getters
    "すみません", "すいません", "ごめんなさい", "ごめん", "あのう", "あの",
    # Sequence
    "まず", "次に", "最初に", "最後に", "その前に", "その後",
    "そして", "それから",
    # Addition
    "また", "さらに", "しかも",
    # Contrast
    "しかし", "ただし", "ただ",
    # Examples
    "例えば", "特に", "具体的には", "基本的には",
    # Actuality
    "実は", "実際には", "本当は",
    # Conditions
    "もし", "仮に",
    # Emphasis
    "確かに", "当然", "もちろん",
    # Time
    "今すぐ", "後で", "先に",
]


# ---------- Furigana / ruby HTML ----------

def extract_furigana(text: str) -> str:
    """Strip furigana brackets, keeping kanji (for TTS input).

    Converts: 昼食【ちゅうしょく】前【まえ】に -> 昼食前に
    Converts: 食【た】べる -> 食べる (per-kanji okurigana preserved)
    Converts: 2日【ふつか】 -> 2日 (digits preserved)

    Exception: kanji in TTS_KANJI_OVERRIDES get replaced with their
    reading instead of being kept, because Edge TTS misreads them.
    E.g. 型【かた】 -> かた (since TTS reads 型 as がた).
    """
    return furigana.keep_base(text, overrides=TTS_KANJI_OVERRIDES)


def to_ruby_html(text: str) -> str:
    """Convert 漢字【かんじ】 to <ruby>漢字<rt>かんじ</rt></ruby>.

    Per-kanji annotations are the source of truth:
      食【た】べる -> <ruby>食<rt>た</rt></ruby>べる
    Furigana appears over kanji only, never over trailing okurigana.
    """
    return furigana.to_ruby(text)


# ---------- English acronym conversion ----------

def _convert_acronym(match: re.Match) -> str:
    word = match.group(0)
    if word in ACRONYM_MAP:
        return ACRONYM_MAP[word]
    if word.upper() in ACRONYM_MAP:
        return ACRONYM_MAP[word.upper()]

    # EC2, S3 pattern
    ec2_match = re.match(r"^([A-Z]+)(\d+)$", word)
    if ec2_match:
        letters, numbers = ec2_match.groups()
        letter_part = "".join(LETTER_MAP.get(c, c) for c in letters)
        number_part = "".join(NUMBER_MAP.get(c, c) for c in numbers)
        return letter_part + number_part

    # Unknown 2-5 uppercase acronym -> letter-by-letter
    if re.match(r"^[A-Z]{2,5}$", word):
        return "".join(LETTER_MAP.get(c, c) for c in word)

    # Otherwise pass through
    return word


def convert_english_terms(text: str) -> str:
    """Convert English acronyms/tech terms to katakana."""
    # Note: \b doesn't work at Japanese/ASCII boundaries. Match
    # ASCII alphanumeric sequences starting with a letter.
    return re.sub(r"[A-Za-z][A-Za-z0-9]*", _convert_acronym, text)


# ---------- Particle handling ----------

def replace_particle_ha(text: str) -> str:
    """Replace particle は with わ so Edge TTS reads it as 'wa'.

    Must run BEFORE furigana extraction so brackets still disambiguate
    word-internal は (inside 【】) from particle は (outside).
    """
    parts = re.split(r"(【[^】]*】)", text)
    for i, part in enumerate(parts):
        if not part.startswith("【"):
            parts[i] = part.replace("は", "わ")
    return "".join(parts)


def insert_particle_pauses(text: str) -> str:
    """Insert commas after を (object marker) for natural TTS rhythm."""
    return re.sub(r"を([^、。！？\s])", r"を、\1", text)


def _should_add_comma_after_ga(sentence: str, ga_pos: int) -> bool:
    before = sentence[:ga_pos]
    after = sentence[ga_pos + 1:]

    if after.startswith("、"):
        return False

    # ありがとう
    if "ありがとう" in sentence[max(0, ga_pos - 5): ga_pos + 5]:
        return False
    if before.endswith("ありがと"):
        return False

    # 方がいい / ほうがいい
    before_stripped = re.sub(r"【[^】]+】$", "", before)
    if before_stripped.endswith("方") or before_stripped.endswith("ほう"):
        return False

    # ながら (while doing)
    if before.endswith("な") and after.startswith("ら"):
        return False

    # Verb stems with が (上がる、下がる、広がる、ひろがる)
    verb_stem_chars = ["上", "下", "広", "拡", "あ", "さ", "ひろ"]
    if any(before.endswith(c) for c in verb_stem_chars):
        if after and after[0] in "りるっれろ":
            return False

    # End of sentence / immediate punctuation
    if not after or after[0] in "。、！？":
        return False

    # Followed by a verb-like pattern -> particle が
    if re.match(rf"^[{_KANA}\u4e00-\u9fff]", after):
        return True
    return False


def add_ga_commas(text: str) -> str:
    """Insert commas after subject-marker が (context-aware)."""
    out = []
    for i, ch in enumerate(text):
        out.append(ch)
        if ch == "が" and _should_add_comma_after_ga(text, i):
            out.append("、")
    return "".join(out)


# ---------- Adverb commas ----------

def _adverb_regex(adverb: str) -> str:
    """Build a regex that matches an adverb with optional furigana between chars.

    Example: 実は -> 実(?:【[^】]+】)?は
    Lets 実【じつ】は match the same rule as plain 実は.
    """
    return "".join(re.escape(c) + r"(?:【[^】]+】)?" for c in adverb)


def add_adverb_commas(text: str) -> str:
    result = text
    for adverb in ADVERBS:
        pat = _adverb_regex(adverb)

        # At sentence start
        result = re.sub(
            f"^({pat})([^、。！？])",
            r"\1、\2",
            result,
        )
        # After 。 (new sentence)
        result = re.sub(
            f"。({pat})([^、。！？])",
            r"。\1、\2",
            result,
        )
    return result


# ---------- Full pipeline ----------

def preprocess_for_tts(pronunciation_field: str) -> str:
    """Full TTS preprocessing pipeline."""
    text = pronunciation_field

    # 1. Symbols
    text = text.replace("%", "パーセント")
    text = re.sub(r"(?<![A-Za-z])v(\d)", r"バージョン\1", text)

    # 2. Adverb commas (before furigana extraction so annotated adverbs match)
    text = add_adverb_commas(text)

    # 3. は -> わ (before furigana extraction while brackets disambiguate)
    text = replace_particle_ha(text)

    # 4. Extract furigana (keep kanji, honor TTS_KANJI_OVERRIDES)
    text = extract_furigana(text)

    # 5. English terms -> katakana
    text = convert_english_terms(text)

    # 6. Particle pauses
    text = insert_particle_pauses(text)

    # 7. が subject-marker pauses
    text = add_ga_commas(text)

    # 8. Cleanup
    text = text.replace("「", "").replace("」", "")
    text = re.sub(r"【[^】]*】", "", text)
    text = " ".join(text.split())

    # Terminate with punctuation for clean TTS delivery
    if text and text[-1] not in "。！？、":
        text += "。"

    return text
