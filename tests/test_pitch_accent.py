"""Tests for pitch accent logic (fallback paths don't require UniDic)."""

from anki_voiced.pitch_accent import get_kana_reading


class TestGetKanaReading:
    def test_exact_annotation_match(self):
        assert get_kana_reading("会議", "会議【かいぎ】は10時【じ】です。") == "かいぎ"

    def test_hiragana_cloze_returns_itself(self):
        assert get_kana_reading("あります", "機能【きのう】があります。") == "あります"

    def test_katakana_cloze_returns_hiragana(self):
        # Katakana cloze -> hiragana reading
        assert get_kana_reading("ブロック", "APIチームにブロックされています。") == "ぶろっく"

    def test_contiguous_segments(self):
        # 実は in 実【じつ】はもっと -> じつは
        assert get_kana_reading("実は", "実【じつ】はもっとあります。") == "じつは"

    def test_segment_with_inflection(self):
        # 協力する vs 協力【きょうりょく】して -> きょうりょくする
        result = get_kana_reading("協力する", "協力【きょうりょく】してください。")
        assert result == "きょうりょくする"

    def test_no_match_returns_none(self):
        assert get_kana_reading("存在しない", "全然関係ない文【ぶん】。") is None
