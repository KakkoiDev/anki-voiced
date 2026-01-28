"""Japanese text preprocessing for accurate TTS audio generation.

This module converts Japanese text (with optional furigana annotations)
into clean text that TTS engines can read correctly.

Handles:
1. Furigana extraction: 昼食【ちゅうしょく】 → ちゅうしょく
2. English acronyms: API → エーピーアイ
3. Common IT terms: React → リアクト
4. Particle pause insertion: を → を、 (for natural TTS rhythm)
5. Subject marker pauses: が → が、 (context-aware)
6. Introductory adverb pauses: まず → まず、
"""

import re

# English letter → Japanese katakana mapping
LETTER_MAP = {
    "A": "エー",
    "B": "ビー",
    "C": "シー",
    "D": "ディー",
    "E": "イー",
    "F": "エフ",
    "G": "ジー",
    "H": "エイチ",
    "I": "アイ",
    "J": "ジェー",
    "K": "ケー",
    "L": "エル",
    "M": "エム",
    "N": "エヌ",
    "O": "オー",
    "P": "ピー",
    "Q": "キュー",
    "R": "アール",
    "S": "エス",
    "T": "ティー",
    "U": "ユー",
    "V": "ブイ",
    "W": "ダブリュー",
    "X": "エックス",
    "Y": "ワイ",
    "Z": "ゼット",
}

# Common acronyms with special/preferred pronunciations
ACRONYM_MAP = {
    "JSON": "ジェイソン",
    "REST": "レスト",
    "SQL": "エスキューエル",
    "NULL": "ヌル",
    "CRUD": "クラッド",
    "GUI": "ジーユーアイ",
    "CLI": "シーエルアイ",
    "SSH": "エスエスエイチ",
    "SSL": "エスエスエル",
    "TLS": "ティーエルエス",
    "DNS": "ディーエヌエス",
    "TCP": "ティーシーピー",
    "UDP": "ユーディーピー",
    "VPN": "ブイピーエヌ",
    "VPC": "ブイピーシー",
    "IAM": "アイエーエム",
    "AWS": "エーダブリューエス",
    "GCP": "ジーシーピー",
    "ORM": "オーアールエム",
    "MVC": "エムブイシー",
    "DRY": "ドライ",
    "SOLID": "ソリッド",
    "CORS": "コース",
    "CSRF": "シーエスアールエフ",
    "XSS": "エックスエスエス",
    "JWT": "ジェーダブリューティー",
    "OAuth": "オーオース",
    "SAML": "サムル",
    "SSO": "エスエスオー",
    "MFA": "エムエフエー",
    "RBAC": "アールバック",
    "GDPR": "ジーディーピーアール",
    "PCI": "ピーシーアイ",
    "SOC": "ソック",
    "WAF": "ワフ",
    "DDoS": "ディードス",
    "CDN": "シーディーエヌ",
    "TTL": "ティーティーエル",
    "SSD": "エスエスディー",
    "IOPS": "アイオプス",
    "EBS": "イービーエス",
    "RDS": "アールディーエス",
    "SQS": "エスキューエス",
    "SNS": "エスエヌエス",
    "ECS": "イーシーエス",
    "EKS": "イーケーエス",
    "ALB": "エーエルビー",
    "NLB": "エヌエルビー",
    "AMI": "エーエムアイ",
    "KMS": "ケーエムエス",
    "ETL": "イーティーエル",
    "SSR": "エスエスアール",
    "CSR": "シーエスアール",
    "SEO": "エスイーオー",
    "DOM": "ドム",
    "CSS": "シーエスエス",
    "ARIA": "アリア",
    "API": "エーピーアイ",
    "URL": "ユーアールエル",
    "HTTP": "エイチティーティーピー",
    "HTTPS": "エイチティーティーピーエス",
    "HTML": "エイチティーエムエル",
    "PR": "ピーアール",
    "CI": "シーアイ",
    "CD": "シーディー",
    "npm": "エヌピーエム",
    "yarn": "ヤーン",
    "pip": "ピップ",
    "git": "ギット",
    "Slack": "スラック",
    "Jira": "ジラ",
    "cron": "クーロン",
    "grep": "グレップ",
    "sudo": "スードゥー",
    "bash": "バッシュ",
    "vim": "ビム",
    "nginx": "エンジンエックス",
    "Redis": "レディス",
    "Kafka": "カフカ",
    "React": "リアクト",
    "Vue": "ビュー",
    "Node": "ノード",
    "async": "エイシンク",
    "await": "アウェイト",
    "props": "プロップス",
    "state": "ステート",
    "hook": "フック",
    "hooks": "フックス",
    "webpack": "ウェブパック",
    "TypeScript": "タイプスクリプト",
    "JavaScript": "ジャバスクリプト",
    "Python": "パイソン",
    "Prisma": "プリズマ",
    "Docker": "ドッカー",
    "Dockerfile": "ドッカーファイル",
    "Kubernetes": "クバネティス",
    "Terraform": "テラフォーム",
    "Lambda": "ラムダ",
    "Fargate": "ファーゲート",
    "Cognito": "コグニート",
    "DynamoDB": "ダイナモディービー",
    "Redshift": "レッドシフト",
    "Athena": "アテナ",
    "Glue": "グルー",
    "Kinesis": "キネシス",
    "EventBridge": "イベントブリッジ",
    "Datadog": "データドッグ",
    "Grafana": "グラファナ",
    "Prometheus": "プロメテウス",
    "Splunk": "スプランク",
    "Sentry": "セントリー",
    "Okta": "オクタ",
    "Memcached": "メムキャッシュド",
    "RabbitMQ": "ラビットエムキュー",
    "GitHub": "ギットハブ",
    "GitLab": "ギットラブ",
    "DevOps": "デブオプス",
    "localhost": "ローカルホスト",
    "frontend": "フロントエンド",
    "backend": "バックエンド",
    "fullstack": "フルスタック",
    "middleware": "ミドルウェア",
    "microservice": "マイクロサービス",
    "microservices": "マイクロサービス",
    "monolith": "モノリス",
    "serverless": "サーバーレス",
    "webhook": "ウェブフック",
    "WebSocket": "ウェブソケット",
}

# Number pronunciations (English-style for tech context)
NUMBER_MAP = {
    "0": "ゼロ",
    "1": "ワン",
    "2": "ツー",
    "3": "スリー",
    "4": "フォー",
    "5": "ファイブ",
    "6": "シックス",
    "7": "セブン",
    "8": "エイト",
    "9": "ナイン",
}

# Introductory adverbs/phrases that benefit from comma after
# These typically appear at the start of sentences or clauses
ADVERBS = [
    # Sequence
    "まず",  # first
    "次に",  # next
    "最初に",  # first (formal)
    "最後に",  # finally
    "その前に",  # before that
    "その後",  # after that
    "そして",  # and then
    "それから",  # after that
    # Addition
    "また",  # also
    "さらに",  # furthermore
    "しかも",  # moreover
    # Contrast
    "しかし",  # however
    "ただし",  # however/provided that
    "ただ",  # just/however
    # Examples/Specifics
    "例えば",  # for example
    "特に",  # especially
    "具体的には",  # specifically
    "基本的には",  # basically
    # Actuality
    "実は",  # actually
    "実際には",  # actually/in practice
    "本当は",  # really/truthfully
    # Conditions
    "もし",  # if
    "仮に",  # supposing
    # Emphasis
    "確かに",  # certainly
    "当然",  # naturally
    "もちろん",  # of course
    # Time
    "今すぐ",  # right now
    "後で",  # later
    "先に",  # first/ahead
]


def extract_furigana(text: str) -> str:
    """Extract furigana readings from annotated text.

    Converts: 昼食【ちゅうしょく】前【まえ】に → ちゅうしょくまえに
    Converts: 2日【ふつか】 → ふつか (handles numbers before kanji)

    Pattern: [digits]kanji【reading】 → reading
    All other text is preserved as-is.
    """
    # Pattern matches: optional digits + kanji (with optional okurigana) followed by 【reading】
    # Kanji range: \u4e00-\u9fff (CJK Unified Ideographs)
    # Hiragana range: \u3040-\u309f, Katakana range: \u30a0-\u30ff
    # Matches kanji (with optional okurigana) immediately before 【reading】
    # \u3005 is 々 (ideographic iteration mark, e.g. 別々)
    # Handles compound patterns like 忘れ物【】, 持ち帰り【】 (kanji-kana-kanji before bracket)
    # Uses atomic-style matching: find 【 first, then look back for the kanji+kana group
    def replace_with_reading(match):
        return match.group(2)

    # First pass: handle sequences with kana between kanji (e.g. 忘れ物【わすれもの】)
    # These have kana sandwiched between kanji, all before 【
    text = re.sub(
        r"([0-9]*[\u4e00-\u9fff\u3005](?:[\u3040-\u309f\u30a0-\u30ff]+[\u4e00-\u9fff\u3005])+[\u3040-\u309f\u30a0-\u30ff]*)【([^】]+)】",
        replace_with_reading, text,
    )
    # Second pass: simple kanji+optional okurigana (e.g. 食べ【たべ】, 天気【てんき】)
    text = re.sub(
        r"([0-9]*[\u4e00-\u9fff\u3005]+[\u3040-\u309f\u30a0-\u30ff]*)【([^】]+)】",
        replace_with_reading, text,
    )
    return text


def to_ruby_html(text: str) -> str:
    """Convert bracket notation to HTML ruby tags for furigana display.

    Converts: 会議【かいぎ】は10時【じ】に → <ruby>会議<rt>かいぎ</rt></ruby>は10<ruby>時<rt>じ</rt></ruby>に
    Also handles okurigana: 食べ【たべ】 → <ruby>食べ<rt>たべ</rt></ruby>

    Pattern: kanji【reading】 → <ruby>kanji<rt>reading</rt></ruby>
    Only kanji characters are wrapped in ruby tags, not preceding numbers.
    """
    def replace_with_ruby(match):
        base = match.group(1)
        reading = match.group(2)
        return f"<ruby>{base}<rt>{reading}</rt></ruby>"

    # First pass: compound kanji-kana-kanji patterns (e.g. 忘れ物【わすれもの】)
    # \u3005 is 々 (ideographic iteration mark)
    text = re.sub(
        r"([\u4e00-\u9fff\u3005](?:[\u3040-\u309f\u30a0-\u30ff]+[\u4e00-\u9fff\u3005])+[\u3040-\u309f\u30a0-\u30ff]*)【([^】]+)】",
        replace_with_ruby, text,
    )
    # Second pass: simple kanji+optional okurigana (e.g. 食べ【たべ】, 天気【てんき】)
    text = re.sub(
        r"([\u4e00-\u9fff\u3005]+[\u3040-\u309f\u30a0-\u30ff]*)【([^】]+)】",
        replace_with_ruby, text,
    )
    return text


def convert_acronym(match: re.Match) -> str:
    """Convert an English acronym/word to katakana."""
    word = match.group(0)

    # Check for exact match in acronym map (case-insensitive for some)
    if word in ACRONYM_MAP:
        return ACRONYM_MAP[word]
    if word.upper() in ACRONYM_MAP:
        return ACRONYM_MAP[word.upper()]

    # Check if it's an AWS service pattern like EC2, S3, etc.
    ec2_match = re.match(r"^([A-Z]+)(\d+)$", word)
    if ec2_match:
        letters, numbers = ec2_match.groups()
        letter_part = "".join(LETTER_MAP.get(c, c) for c in letters)
        number_part = "".join(NUMBER_MAP.get(c, c) for c in numbers)
        return letter_part + number_part

    # For unknown acronyms (2-5 uppercase letters), spell them out
    if re.match(r"^[A-Z]{2,5}$", word):
        return "".join(LETTER_MAP.get(c, c) for c in word)

    # For mixed case or longer words, return as-is (TTS might handle it)
    return word


def convert_english_terms(text: str) -> str:
    """Convert English acronyms and terms to katakana pronunciation."""
    # Pattern to match English words/acronyms
    pattern = r"[A-Za-z][A-Za-z0-9]*"
    return re.sub(pattern, convert_acronym, text)


def insert_particle_pauses(text: str) -> str:
    """Insert commas after particles for natural TTS pauses.

    Based on Kokoro TTS experiments:
    - を (object marker): Always insert comma - を is always a particle
    """
    # を is always the object marker particle in Japanese
    # Insert comma after を unless already followed by punctuation
    text = re.sub(r"を([^、。！？\s])", r"を、\1", text)
    return text


def should_add_comma_after_ga(sentence: str, ga_pos: int) -> bool:
    """Determine if が at position ga_pos needs a comma after it.

    Returns True if comma should be added.
    """
    before = sentence[:ga_pos]
    after = sentence[ga_pos + 1 :]

    # Skip if already has comma
    if after.startswith("、"):
        return False

    # Skip: ありがとう
    if before.endswith("ありがと") or "ありがとう" in sentence[max(0, ga_pos - 5) : ga_pos + 5]:
        return False

    # Skip: 方がいい (ほうがいい) - が is part of grammar pattern
    # Handle both plain text and furigana-annotated text
    before_stripped = re.sub(r"【[^】]+】$", "", before)  # Remove trailing furigana
    if before_stripped.endswith("方") or before_stripped.endswith("ほう"):
        return False

    # Skip: ながら (while doing)
    if before.endswith("な") and after.startswith("ら"):
        return False

    # Skip: が is part of verb stem (e.g., 上がる、下がる、広がる)
    # These verbs have が as part of the verb, not as particle
    verb_stem_chars = ["上", "下", "広", "拡", "あ", "さ", "ひろ"]
    if any(before.endswith(c) for c in verb_stem_chars):
        if after and after[0] in "りるっれろ":
            return False

    # Skip: が followed by end of sentence or punctuation immediately
    if not after or after[0] in "。、！？":
        return False

    # Add comma: が followed by verb-like patterns (hiragana, kanji, or katakana)
    # This covers subject marker が followed by predicates
    verb_patterns = [
        # Hiragana
        r"^[あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽっ]",
        # Kanji (CJK Unified Ideographs)
        r"^[\u4e00-\u9fff]",
        # Katakana
        r"^[\u30a0-\u30ff]",
    ]

    for pattern in verb_patterns:
        if re.match(pattern, after):
            return True

    return False


def add_ga_commas(text: str) -> str:
    """Add commas after が subject markers in text."""
    result = []
    i = 0

    while i < len(text):
        if text[i] == "が":
            result.append("が")
            if should_add_comma_after_ga(text, i):
                result.append("、")
        else:
            result.append(text[i])
        i += 1

    return "".join(result)


def adverb_to_furigana_pattern(adverb: str) -> str:
    """Convert adverb to regex pattern that matches with optional furigana.

    Example: 実は → 実(?:【[^】]+】)?は
    This allows matching both 実は and 実【じつ】は
    """
    parts = []
    for char in adverb:
        # Each character can optionally be followed by furigana annotation
        parts.append(re.escape(char) + r"(?:【[^】]+】)?")
    return "".join(parts)


def add_adverb_commas(text: str) -> str:
    """Add commas after introductory adverbs in text.

    Handles both plain text (実は) and furigana-annotated text (実【じつ】は).
    """
    result = text

    for adverb in ADVERBS:
        # Create pattern that matches adverb with optional furigana
        furigana_pattern = adverb_to_furigana_pattern(adverb)

        # At start of sentence: capture adverb (with possible furigana), add comma
        def add_comma_start(m):
            return m.group(1) + "、" + m.group(2)

        pattern = f"^({furigana_pattern})([^、。！？])"
        result = re.sub(pattern, add_comma_start, result)

        # After period (new sentence in same field)
        def add_comma_after_period(m):
            return "。" + m.group(1) + "、" + m.group(2)

        pattern = f"。({furigana_pattern})([^、。！？])"
        result = re.sub(pattern, add_comma_after_period, result)

    return result


def preprocess_for_tts(pronunciation_field: str) -> str:
    """Full preprocessing pipeline for TTS input.

    1. Insert adverb pauses (まず → まず、) - before furigana extraction
    2. Extract furigana readings
    3. Convert English terms to katakana
    4. Insert particle pauses (を → を、)
    5. Insert が subject marker pauses (context-aware)
    6. Clean up any remaining issues
    """
    text = pronunciation_field

    # Step 1: Insert adverb pauses at sentence start (before furigana extraction
    # so patterns like 実【じつ】は can be matched)
    text = add_adverb_commas(text)

    # Step 2: Extract furigana
    text = extract_furigana(text)

    # Step 3: Convert English terms
    text = convert_english_terms(text)

    # Step 4: Insert particle pauses for natural TTS rhythm
    text = insert_particle_pauses(text)

    # Step 5: Insert が subject marker pauses (context-aware)
    text = add_ga_commas(text)

    # Step 6: Clean up
    # Remove any remaining brackets that might have been missed
    text = re.sub(r"【[^】]*】", "", text)

    # Normalize whitespace
    text = " ".join(text.split())

    return text
