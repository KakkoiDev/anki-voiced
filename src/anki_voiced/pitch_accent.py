"""Generate pitch accent HTML for the Cloze word.

Uses UniDic (via fugashi) to look up the accent type (aType) and produces
colored ruby HTML:
  - <span class="pitch-h">mora</span>  (green, high)
  - <span class="pitch-l">mora</span>  (red, low)

Coverage strategy (100% via fallback):
  1. Single-token Cloze with UniDic aType -> pitch-colored ruby HTML
  2. Anything else -> plain furigana fallback (ruby tags, no pitch colors)

Reading extraction for the fallback cascades:
  a. Exact match: cloze appears with 【reading】 annotation
  b. Contiguous: cloze spans multiple annotations in sequence
  c. Segment: cloze is in dictionary form, pronunciation is inflected
     (e.g. 協力する vs 協力【きょうりょく】して)
  d. Decompose: kanji block spans multiple annotations separated by
     particles (重複排除 annotated as 重複【じゅうふく】を排除【はいじょ】)

Note: UniDic (~500MB) must be downloaded once:
    python -m unidic download
"""

import re
from functools import lru_cache

# Small kana that combine with the preceding char to form one mora
# Note: っ/ッ is its OWN mora, not a combiner.
_SMALL_KANA = set("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")

_KANJI_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\u3005]")
_KANJI_RUN_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\u3005]+")
_KATAKANA_RE = re.compile(r"[\u30A0-\u30FF]")
_ANNOTATED_RE = re.compile(r"([\u4e00-\u9fff\u3400-\u4dbf\u3005]+)【([^】]+)】")


@lru_cache(maxsize=1)
def _get_tagger():
    """Lazy-load fugashi.Tagger. UniDic must be installed."""
    import fugashi
    return fugashi.Tagger()


def _kata_to_hira(text: str) -> str:
    out = []
    for c in text:
        if "ァ" <= c <= "ン":
            out.append(chr(ord(c) - 0x60))
        else:
            out.append(c)
    return "".join(out)


def _split_moras(kana: str) -> list[str]:
    moras = []
    i = 0
    while i < len(kana):
        if i + 1 < len(kana) and kana[i + 1] in _SMALL_KANA:
            moras.append(kana[i: i + 2])
            i += 2
        else:
            moras.append(kana[i])
            i += 1
    return moras


def _accent_pattern(num_moras: int, atype: int) -> list[str]:
    """H/L pattern for each mora per Tokyo-dialect rules.

    Type 0 (heiban):    L H H H ...
    Type 1 (atamadaka): H L L L ...
    Type N (N>=2):      L H H ... H L L ... (drops after mora N)
    """
    if num_moras == 0:
        return []
    if atype == 0:
        return ["L"] + ["H"] * (num_moras - 1)
    if atype == 1:
        return ["H"] + ["L"] * (num_moras - 1)
    result = []
    for i in range(1, num_moras + 1):
        if i == 1:
            result.append("L")
        elif i <= atype:
            result.append("H")
        else:
            result.append("L")
    return result


def _parse_pronunciation(text: str) -> list[tuple[str, str]]:
    """Split annotated text into (surface, reading) pairs."""
    parts = []
    pos = 0
    while pos < len(text):
        m = _ANNOTATED_RE.match(text, pos)
        if m:
            parts.append((m.group(1), m.group(2)))
            pos = m.end()
        else:
            parts.append((text[pos], text[pos]))
            pos += 1
    return parts


def _decompose_kanji(kanji_seg: str, pronunciation: str) -> str | None:
    """Find readings for a kanji segment spanning multiple annotations."""
    readings = []
    remaining = kanji_seg
    while remaining:
        found = False
        for length in range(len(remaining), 0, -1):
            prefix = remaining[:length]
            m = re.search(re.escape(prefix) + r"【([^】]+)】", pronunciation)
            if m:
                readings.append(m.group(1))
                remaining = remaining[length:]
                found = True
                break
        if not found:
            return None
    return "".join(readings)


def get_kana_reading(cloze: str, pronunciation: str) -> str | None:
    """Extract hiragana reading of cloze from Pronunciation annotations."""
    # 1. Exact match
    m = re.search(re.escape(cloze) + r"【([^】]+)】", pronunciation)
    if m:
        return m.group(1)

    # Cloze has no kanji -> it IS the reading
    if not _KANJI_RE.search(cloze):
        return _kata_to_hira(cloze)

    # 2. Contiguous match
    parts = _parse_pronunciation(pronunciation)
    surface_str = "".join(s for s, _ in parts)
    idx = surface_str.find(cloze)
    if idx >= 0:
        reading = []
        surface_pos = 0
        ok = True
        for s, r in parts:
            part_end = surface_pos + len(s)
            if part_end <= idx:
                surface_pos = part_end
                continue
            if surface_pos >= idx + len(cloze):
                break
            if surface_pos >= idx and part_end <= idx + len(cloze):
                reading.append(r)
            else:
                ok = False
                break
            surface_pos = part_end
        if ok and reading:
            return "".join(reading)

    # 3. Segment match (dictionary form vs inflected)
    segments = re.findall(
        r"[\u4e00-\u9fff\u3400-\u4dbf\u3005]+|[^\u4e00-\u9fff\u3400-\u4dbf]+",
        cloze,
    )
    reading_parts = []
    for seg in segments:
        if _KANJI_RE.match(seg):
            m = re.search(re.escape(seg) + r"【([^】]+)】", pronunciation)
            if m:
                reading_parts.append(m.group(1))
            else:
                decomposed = _decompose_kanji(seg, pronunciation)
                if decomposed:
                    reading_parts.append(decomposed)
                else:
                    return None
        else:
            reading_parts.append(_kata_to_hira(seg))
    return "".join(reading_parts) if reading_parts else None


def _pitch_ruby(cloze: str, kana: str, atype: int) -> str:
    moras = _split_moras(kana)
    if not moras:
        return ""

    pattern = _accent_pattern(len(moras), atype)
    colored = "".join(
        f'<span class="pitch-{p.lower()}">{m}</span>'
        for m, p in zip(moras, pattern)
    )

    has_kanji = bool(_KANJI_RE.search(cloze))
    has_kata = bool(_KATAKANA_RE.search(cloze))
    if has_kanji or has_kata:
        return f'<ruby class="vocab">{cloze}<rt>{colored}</rt></ruby>'
    return f'<span class="vocab">{colored}</span>'


def _fallback_ruby(cloze: str, kana: str | None) -> str:
    has_kanji = bool(_KANJI_RE.search(cloze))
    if has_kanji and kana:
        return f'<ruby class="vocab">{cloze}<rt>{kana}</rt></ruby>'
    return f'<span class="vocab">{cloze}</span>'


def get_pitch_html(cloze: str, pronunciation: str) -> str:
    """Return colored ruby HTML for cloze, or plain fallback."""
    if not cloze:
        return ""

    kana_from_pron = get_kana_reading(cloze, pronunciation)

    try:
        tagger = _get_tagger()
    except Exception:
        return _fallback_ruby(cloze, kana_from_pron)

    tokens = list(tagger(cloze))
    if len(tokens) == 1:
        token = tokens[0]
        atype_raw = getattr(token.feature, "aType", "") or ""
        if atype_raw and atype_raw != "*":
            try:
                atype = int(atype_raw.split(",")[0])
            except (ValueError, AttributeError):
                atype = None
            else:
                kana = kana_from_pron
                if not kana:
                    raw_kana = getattr(token.feature, "kana", "") or ""
                    if raw_kana and raw_kana != "*":
                        kana = _kata_to_hira(raw_kana)
                if kana:
                    return _pitch_ruby(cloze, kana, atype)

    return _fallback_ruby(cloze, kana_from_pron)
