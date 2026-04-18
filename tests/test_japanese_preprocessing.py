"""Tests for Japanese text preprocessing (Edge TTS pipeline)."""

from anki_voiced.preprocessing.acronyms import TTS_KANJI_OVERRIDES
from anki_voiced.preprocessing.japanese import (
    add_adverb_commas,
    add_ga_commas,
    convert_english_terms,
    extract_furigana,
    insert_particle_pauses,
    preprocess_for_tts,
    replace_particle_ha,
    to_ruby_html,
)


class TestExtractFurigana:
    """extract_furigana keeps kanji (Edge TTS reads them correctly)."""

    def test_keeps_kanji_when_annotated(self):
        assert extract_furigana("昼食【ちゅうしょく】") == "昼食"

    def test_keeps_multiple_kanji(self):
        assert extract_furigana("昼食【ちゅうしょく】前【まえ】に") == "昼食前に"

    def test_preserves_digits(self):
        assert extract_furigana("2日【にち】") == "2日"

    def test_mixed_with_plain_text(self):
        assert extract_furigana("今日【きょう】は良い天気【てんき】です") == "今日は良い天気です"

    def test_no_brackets(self):
        assert extract_furigana("これはテストです") == "これはテストです"

    def test_hiragana_only(self):
        assert extract_furigana("ありがとう") == "ありがとう"

    def test_kanji_override_uses_reading(self):
        # 型 is in TTS_KANJI_OVERRIDES -> reading is substituted
        assert "型" in TTS_KANJI_OVERRIDES
        assert extract_furigana("型【かた】を") == "かたを"

    def test_per_kanji_okurigana(self):
        # 食【た】べる should keep 食べる (not replace with たべる)
        assert extract_furigana("食【た】べる") == "食べる"


class TestToRubyHtml:
    def test_simple_ruby(self):
        assert to_ruby_html("会議【かいぎ】") == "<ruby>会議<rt>かいぎ</rt></ruby>"

    def test_multiple_ruby(self):
        result = to_ruby_html("会議【かいぎ】は10時【じ】に")
        assert "<ruby>会議<rt>かいぎ</rt></ruby>" in result
        assert "<ruby>時<rt>じ</rt></ruby>" in result

    def test_per_kanji_okurigana_wraps_only_kanji(self):
        # Per-kanji format 食【た】べる wraps just 食, not the okurigana
        assert to_ruby_html("食【た】べる") == "<ruby>食<rt>た</rt></ruby>べる"

    def test_plain_text_passes_through(self):
        assert to_ruby_html("ありがとう") == "ありがとう"


class TestReplaceParticleHa:
    def test_replaces_particle_ha(self):
        assert replace_particle_ha("会議【かいぎ】は") == "会議【かいぎ】わ"

    def test_keeps_ha_inside_brackets(self):
        # 話【はな】 - は inside brackets is a word reading, not a particle
        assert "は" in replace_particle_ha("話【はな】せますか")

    def test_no_ha_no_change(self):
        assert replace_particle_ha("ありがとう") == "ありがとう"


class TestConvertEnglishTerms:
    def test_known_acronym(self):
        result = convert_english_terms("APIを使う")
        assert "エーピーアイ" in result

    def test_aws_pattern(self):
        # EC2 -> イーシーツー
        assert "イーシー" in convert_english_terms("EC2")

    def test_unknown_acronym_spelled_out(self):
        # ZZZ (not in map) -> ゼットゼットゼット
        result = convert_english_terms("ZZZ")
        assert "ゼット" in result

    def test_single_letter_passthrough(self):
        # Single letter isn't matched by 2-5 rule
        assert convert_english_terms("A is fine") != ""


class TestParticlePauses:
    def test_inserts_comma_after_wo(self):
        assert "を、" in insert_particle_pauses("データを保存します")

    def test_no_comma_before_punctuation(self):
        result = insert_particle_pauses("これを。")
        assert "を。" in result
        assert "を、" not in result


class TestGaCommas:
    def test_adds_comma_for_subject_ga(self):
        # 私が食べる -> 私が、食べる
        result = add_ga_commas("私が食べる")
        assert "が、食べる" in result

    def test_skips_arigatou(self):
        assert "ありがとうございます" in add_ga_commas("ありがとうございます")
        assert "が、" not in add_ga_commas("ありがとうございます")

    def test_skips_nagara(self):
        result = add_ga_commas("歩きながら")
        assert "が、" not in result


class TestAdverbCommas:
    def test_adds_comma_after_initial_adverb(self):
        result = add_adverb_commas("まずテストします")
        assert result.startswith("まず、")

    def test_handles_annotated_adverb(self):
        result = add_adverb_commas("実【じつ】はそうです")
        assert "実【じつ】は、" in result

    def test_after_period(self):
        result = add_adverb_commas("はい。次に何をしますか")
        assert "次に、" in result


class TestPreprocessForTts:
    def test_full_pipeline(self):
        out = preprocess_for_tts("会議【かいぎ】は10時【じ】です。")
        # は -> わ, furigana stripped but kanji kept
        assert "会議" in out
        assert "10時" in out
        assert "かいぎ" not in out  # brackets stripped
        assert "わ" in out  # particle ha replaced

    def test_ends_with_punctuation(self):
        assert preprocess_for_tts("これ").endswith("。")

    def test_acronym_converted(self):
        out = preprocess_for_tts("APIを使います")
        assert "エーピーアイ" in out
        assert "を、" in out  # particle を gets comma

    def test_percent_substituted(self):
        out = preprocess_for_tts("50%です")
        assert "パーセント" in out
