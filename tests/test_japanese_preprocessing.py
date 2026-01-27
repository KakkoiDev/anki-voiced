"""Tests for Japanese text preprocessing."""

import pytest

from anki_voiced.preprocessing.japanese import (
    ADVERBS,
    add_adverb_commas,
    add_ga_commas,
    convert_english_terms,
    extract_furigana,
    insert_particle_pauses,
    preprocess_for_tts,
    should_add_comma_after_ga,
    to_ruby_html,
)


class TestExtractFurigana:
    """Tests for furigana extraction."""

    def test_simple_kanji_with_furigana(self):
        assert extract_furigana("昼食【ちゅうしょく】") == "ちゅうしょく"

    def test_multiple_kanji_with_furigana(self):
        assert extract_furigana("昼食【ちゅうしょく】前【まえ】に") == "ちゅうしょくまえに"

    def test_number_before_kanji(self):
        assert extract_furigana("2日【ふつか】") == "ふつか"

    def test_mixed_text(self):
        assert extract_furigana("今日【きょう】は良い天気【てんき】です") == "きょうは良いてんきです"

    def test_no_furigana(self):
        assert extract_furigana("これはテストです") == "これはテストです"

    def test_hiragana_only(self):
        assert extract_furigana("ありがとう") == "ありがとう"


class TestToRubyHtml:
    """Tests for HTML ruby tag conversion."""

    def test_simple_ruby(self):
        result = to_ruby_html("会議【かいぎ】")
        assert result == "<ruby>会議<rt>かいぎ</rt></ruby>"

    def test_multiple_ruby(self):
        result = to_ruby_html("会議【かいぎ】は10時【じ】に")
        assert "<ruby>会議<rt>かいぎ</rt></ruby>" in result
        assert "<ruby>時<rt>じ</rt></ruby>" in result
        assert "10" in result  # Number preserved

    def test_no_furigana(self):
        result = to_ruby_html("テスト")
        assert result == "テスト"


class TestConvertEnglishTerms:
    """Tests for English to katakana conversion."""

    def test_known_acronym(self):
        assert convert_english_terms("API") == "エーピーアイ"

    def test_known_term(self):
        assert convert_english_terms("React") == "リアクト"

    def test_unknown_uppercase_acronym(self):
        # Unknown acronyms get spelled out
        result = convert_english_terms("XYZ")
        assert "エックス" in result
        assert "ワイ" in result
        assert "ゼット" in result

    def test_aws_service_pattern(self):
        assert convert_english_terms("EC2") == "イーシーツー"
        assert convert_english_terms("S3") == "エススリー"

    def test_mixed_text(self):
        result = convert_english_terms("APIを使う")
        assert "エーピーアイ" in result
        assert "を使う" in result

    def test_multiple_terms(self):
        result = convert_english_terms("ReactとVue")
        assert "リアクト" in result
        assert "ビュー" in result


class TestInsertParticlePauses:
    """Tests for を particle pause insertion."""

    def test_wo_followed_by_text(self):
        assert "を、" in insert_particle_pauses("データを保存します")

    def test_wo_followed_by_punctuation(self):
        # Should not add comma before existing punctuation
        result = insert_particle_pauses("データを。")
        assert result == "データを。"

    def test_wo_followed_by_comma(self):
        result = insert_particle_pauses("データを、保存")
        assert result.count("を、") == 1  # No double comma

    def test_multiple_wo(self):
        result = insert_particle_pauses("データを保存してコードをレビュー")
        assert result.count("を、") == 2


class TestShouldAddCommaAfterGa:
    """Tests for が particle context detection."""

    def test_subject_marker_before_verb(self):
        assert should_add_comma_after_ga("バグが発生", 2) is True

    def test_already_has_comma(self):
        assert should_add_comma_after_ga("バグが、発生", 2) is False

    def test_arigatou_exclusion(self):
        assert should_add_comma_after_ga("ありがとう", 3) is False

    def test_hou_ga_ii_exclusion(self):
        assert should_add_comma_after_ga("方がいい", 1) is False
        assert should_add_comma_after_ga("ほうがいい", 2) is False

    def test_nagara_exclusion(self):
        assert should_add_comma_after_ga("ながら", 1) is False

    def test_verb_stem_agaru(self):
        assert should_add_comma_after_ga("上がる", 1) is False
        assert should_add_comma_after_ga("下がる", 1) is False

    def test_end_of_sentence(self):
        assert should_add_comma_after_ga("問題が。", 2) is False

    def test_before_kanji(self):
        assert should_add_comma_after_ga("問題が発生", 2) is True

    def test_before_katakana(self):
        assert should_add_comma_after_ga("エラーがアプリ", 3) is True


class TestAddGaCommas:
    """Tests for が comma insertion."""

    def test_adds_comma(self):
        assert "が、" in add_ga_commas("バグが発生しました")

    def test_preserves_exclusions(self):
        assert "が、" not in add_ga_commas("ありがとうございます")
        assert "が、" not in add_ga_commas("上がる")

    def test_multiple_ga(self):
        result = add_ga_commas("問題がありバグが発生")
        assert result.count("が、") == 2


class TestAddAdverbCommas:
    """Tests for introductory adverb comma insertion."""

    def test_mazu_at_start(self):
        assert add_adverb_commas("まずテスト").startswith("まず、")

    def test_shikashi_at_start(self):
        assert add_adverb_commas("しかし問題").startswith("しかし、")

    def test_tatoeba_at_start(self):
        assert add_adverb_commas("例えばこの場合").startswith("例えば、")

    def test_after_period(self):
        result = add_adverb_commas("終わり。まず確認")
        assert "。まず、" in result

    def test_already_has_comma(self):
        result = add_adverb_commas("まず、テスト")
        assert result.count("まず、") == 1

    def test_with_furigana(self):
        result = add_adverb_commas("実【じつ】は問題")
        assert "、" in result

    def test_adverbs_list_not_empty(self):
        assert len(ADVERBS) > 0
        assert "まず" in ADVERBS
        assert "しかし" in ADVERBS


class TestPreprocessForTts:
    """Integration tests for full preprocessing pipeline."""

    def test_combined_wo_particle(self):
        result = preprocess_for_tts("データを保存します")
        assert "を、" in result

    def test_combined_ga_particle(self):
        result = preprocess_for_tts("バグが発生しました")
        assert "が、" in result

    def test_combined_adverb(self):
        result = preprocess_for_tts("まずテストを書きます")
        assert "まず、" in result
        assert "を、" in result

    def test_combined_english_conversion(self):
        result = preprocess_for_tts("まずAPIを呼び出します")
        assert "まず、" in result
        assert "エーピーアイ" in result
        assert "を、" in result

    def test_furigana_extraction(self):
        result = preprocess_for_tts("会議【かいぎ】は10時【じ】です")
        assert "かいぎ" in result
        assert "じ" in result
        assert "【" not in result

    def test_furigana_with_adverb(self):
        result = preprocess_for_tts("実【じつ】は問題です")
        assert "じつは、" in result

    def test_exclusions_preserved(self):
        assert "が、" not in preprocess_for_tts("ありがとうございます")
        assert "が、" not in preprocess_for_tts("方がいい")
        assert "が、" not in preprocess_for_tts("上がる")

    def test_whitespace_normalization(self):
        result = preprocess_for_tts("テスト  です")
        assert "  " not in result

    def test_cleanup_remaining_brackets(self):
        result = preprocess_for_tts("テスト【てすと】")
        assert "【" not in result
        assert "】" not in result
