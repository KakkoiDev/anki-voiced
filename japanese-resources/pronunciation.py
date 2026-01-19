#!/usr/bin/env python3
"""Japanese pronunciation preprocessing for TTS engines.

This module converts Japanese text with furigana annotations into clean text
that TTS engines (like Kokoro) can pronounce correctly.

Key Features:
1. Furigana extraction: 昼食【ちゅうしょく】 → ちゅうしょく
2. Number+kanji handling: 2日【ふつか】 → ふつか
3. English acronym conversion: API → エーピーアイ, EC2 → イーシーツー
4. IT term pronunciation: JSON → ジェイソン, AWS → エーダブリューエス

Usage:
    from pronunciation import preprocess_for_tts

    # With furigana annotations (recommended)
    text = "APIの応答【おうとう】が遅【おそ】い"
    tts_input = preprocess_for_tts(text)
    # Result: "エーピーアイのおうとうがおそい"

Design Philosophy:
    - Furigana readings are authoritative - always use them when provided
    - English terms need conversion because TTS models mispronounce them
    - Numbers in English context (EC2, S3) use English-style katakana (ツー, スリー)
    - Numbers in Japanese context use furigana (2日【ふつか】 → ふつか)
"""

import re
from typing import Optional

# English letter → Japanese katakana mapping
LETTER_MAP = {
    'A': 'エー', 'B': 'ビー', 'C': 'シー', 'D': 'ディー', 'E': 'イー',
    'F': 'エフ', 'G': 'ジー', 'H': 'エイチ', 'I': 'アイ', 'J': 'ジェー',
    'K': 'ケー', 'L': 'エル', 'M': 'エム', 'N': 'エヌ', 'O': 'オー',
    'P': 'ピー', 'Q': 'キュー', 'R': 'アール', 'S': 'エス', 'T': 'ティー',
    'U': 'ユー', 'V': 'ブイ', 'W': 'ダブリュー', 'X': 'エックス',
    'Y': 'ワイ', 'Z': 'ゼット',
}

# Number pronunciations (English-style for tech context like EC2, S3)
NUMBER_MAP = {
    '0': 'ゼロ', '1': 'ワン', '2': 'ツー', '3': 'スリー', '4': 'フォー',
    '5': 'ファイブ', '6': 'シックス', '7': 'セブン', '8': 'エイト', '9': 'ナイン',
}

# Common acronyms and IT terms with preferred pronunciations
# These override letter-by-letter conversion
ACRONYM_MAP = {
    # Data formats & protocols
    'JSON': 'ジェイソン',
    'XML': 'エックスエムエル',
    'YAML': 'ヤムル',
    'CSV': 'シーエスブイ',
    'REST': 'レスト',
    'RESTful': 'レストフル',
    'GraphQL': 'グラフキューエル',
    'gRPC': 'ジーアールピーシー',
    'SQL': 'エスキューエル',
    'NoSQL': 'ノーエスキューエル',
    'NULL': 'ヌル',
    'CRUD': 'クラッド',

    # Security & Auth
    'JWT': 'ジェーダブリューティー',
    'OAuth': 'オーオース',
    'SAML': 'サムル',
    'SSO': 'エスエスオー',
    'MFA': 'エムエフエー',
    'RBAC': 'アールバック',
    'CORS': 'コース',
    'CSRF': 'シーエスアールエフ',
    'XSS': 'エックスエスエス',
    'SSL': 'エスエスエル',
    'TLS': 'ティーエルエス',
    'SSH': 'エスエスエイチ',
    'HTTPS': 'エイチティーティーピーエス',
    'HTTP': 'エイチティーティーピー',

    # Networking
    'DNS': 'ディーエヌエス',
    'TCP': 'ティーシーピー',
    'UDP': 'ユーディーピー',
    'VPN': 'ブイピーエヌ',
    'CDN': 'シーディーエヌ',
    'TTL': 'ティーティーエル',
    'URL': 'ユーアールエル',
    'URI': 'ユーアールアイ',
    'IP': 'アイピー',

    # Cloud - AWS
    'AWS': 'エーダブリューエス',
    'VPC': 'ブイピーシー',
    'IAM': 'アイエーエム',
    'EBS': 'イービーエス',
    'RDS': 'アールディーエス',
    'SQS': 'エスキューエス',
    'SNS': 'エスエヌエス',
    'ECS': 'イーシーエス',
    'EKS': 'イーケーエス',
    'ALB': 'エーエルビー',
    'NLB': 'エヌエルビー',
    'AMI': 'エーエムアイ',
    'KMS': 'ケーエムエス',
    'Lambda': 'ラムダ',
    'Fargate': 'ファーゲート',
    'Cognito': 'コグニート',
    'DynamoDB': 'ダイナモディービー',
    'Redshift': 'レッドシフト',
    'Athena': 'アテナ',
    'Glue': 'グルー',
    'Kinesis': 'キネシス',
    'EventBridge': 'イベントブリッジ',
    'CloudFormation': 'クラウドフォーメーション',
    'CloudWatch': 'クラウドウォッチ',
    'CloudTrail': 'クラウドトレイル',
    'CloudFront': 'クラウドフロント',
    'CodeBuild': 'コードビルド',
    'CodeDeploy': 'コードデプロイ',
    'CodePipeline': 'コードパイプライン',

    # Cloud - GCP
    'GCP': 'ジーシーピー',
    'GKE': 'ジーケーイー',
    'BigQuery': 'ビッグクエリ',

    # DevOps & Tools
    'CI': 'シーアイ',
    'CD': 'シーディー',
    'Docker': 'ドッカー',
    'Dockerfile': 'ドッカーファイル',
    'Kubernetes': 'クバネティス',
    'Terraform': 'テラフォーム',
    'Ansible': 'アンシブル',
    'Jenkins': 'ジェンキンス',
    'GitHub': 'ギットハブ',
    'GitLab': 'ギットラブ',
    'DevOps': 'デブオプス',
    'DevTools': 'デブツールズ',
    'git': 'ギット',
    'npm': 'エヌピーエム',
    'yarn': 'ヤーン',
    'pip': 'ピップ',
    'cron': 'クーロン',
    'grep': 'グレップ',
    'sudo': 'スードゥー',
    'bash': 'バッシュ',
    'vim': 'ビム',

    # Monitoring
    'Datadog': 'データドッグ',
    'Grafana': 'グラファナ',
    'Prometheus': 'プロメテウス',
    'Splunk': 'スプランク',
    'Sentry': 'セントリー',
    'SSD': 'エスエスディー',
    'IOPS': 'アイオプス',

    # Databases & Caching
    'Redis': 'レディス',
    'Memcached': 'メムキャッシュド',
    'Kafka': 'カフカ',
    'RabbitMQ': 'ラビットエムキュー',
    'MongoDB': 'モンゴディービー',
    'PostgreSQL': 'ポストグレスキューエル',
    'MySQL': 'マイエスキューエル',
    'Prisma': 'プリズマ',
    'ORM': 'オーアールエム',

    # Frontend
    'React': 'リアクト',
    'Vue': 'ビュー',
    'Angular': 'アンギュラー',
    'Svelte': 'スベルト',
    'Node': 'ノード',
    'Webpack': 'ウェブパック',
    'Vite': 'ヴィート',
    'TypeScript': 'タイプスクリプト',
    'JavaScript': 'ジャバスクリプト',
    'CSS': 'シーエスエス',
    'DOM': 'ドム',
    'ARIA': 'アリア',
    'Flexbox': 'フレックスボックス',
    'SSR': 'エスエスアール',
    'CSR': 'シーエスアール',
    'SEO': 'エスイーオー',
    'async': 'エイシンク',
    'await': 'アウェイト',
    'props': 'プロップス',
    'state': 'ステート',
    'hook': 'フック',
    'hooks': 'フックス',

    # Backend & Architecture
    'Python': 'パイソン',
    'nginx': 'エンジンエックス',
    'Apache': 'アパッチ',
    'MVC': 'エムブイシー',
    'MVVM': 'エムブイブイエム',
    'DRY': 'ドライ',
    'SOLID': 'ソリッド',
    'GUI': 'ジーユーアイ',
    'CLI': 'シーエルアイ',
    'API': 'エーピーアイ',
    'SDK': 'エスディーケー',
    'ETL': 'イーティーエル',
    'localhost': 'ローカルホスト',
    'frontend': 'フロントエンド',
    'backend': 'バックエンド',
    'fullstack': 'フルスタック',
    'middleware': 'ミドルウェア',
    'microservice': 'マイクロサービス',
    'microservices': 'マイクロサービス',
    'monolith': 'モノリス',
    'serverless': 'サーバーレス',
    'webhook': 'ウェブフック',
    'websocket': 'ウェブソケット',
    'WebSocket': 'ウェブソケット',

    # Communication Tools
    'Slack': 'スラック',
    'Jira': 'ジラ',
    'Okta': 'オクタ',

    # File Formats
    'Parquet': 'パーケット',
    'Avro': 'アブロ',

    # Testing
    'Lighthouse': 'ライトハウス',
    'Jest': 'ジェスト',
    'Cypress': 'サイプレス',

    # Compliance
    'GDPR': 'ジーディーピーアール',
    'PCI': 'ピーシーアイ',
    'SOC': 'ソック',
    'WAF': 'ワフ',
    'DDoS': 'ディードス',
}


def extract_furigana(text: str) -> str:
    """Extract furigana readings from annotated text.

    Converts: 昼食【ちゅうしょく】前【まえ】に → ちゅうしょくまえに
    Converts: 2日【ふつか】 → ふつか (handles numbers before kanji)

    Pattern: [digits]kanji【reading】 → reading
    All other text is preserved as-is.

    Args:
        text: Japanese text with furigana in 【】brackets

    Returns:
        Text with kanji replaced by their readings
    """
    # Pattern matches: optional digits + one or more kanji followed by 【reading】
    # Kanji range: \u4e00-\u9fff (CJK Unified Ideographs)
    # This handles cases like 2日【ふつか】, 3時【さんじ】, 10人【じゅうにん】
    pattern = r'([0-9]*[\u4e00-\u9fff]+)【([^】]+)】'

    def replace_with_reading(match):
        return match.group(2)  # Return the reading, discard kanji+digits

    return re.sub(pattern, replace_with_reading, text)


def convert_acronym(match: re.Match) -> str:
    """Convert an English acronym/word to katakana."""
    word = match.group(0)

    # Check for exact match in acronym map
    if word in ACRONYM_MAP:
        return ACRONYM_MAP[word]
    if word.upper() in ACRONYM_MAP:
        return ACRONYM_MAP[word.upper()]

    # Handle AWS service patterns like EC2, S3, P3, G4dn
    ec2_match = re.match(r'^([A-Z]+)(\d+)([a-z]*)$', word)
    if ec2_match:
        letters, numbers, suffix = ec2_match.groups()
        letter_part = ''.join(LETTER_MAP.get(c, c) for c in letters)
        number_part = ''.join(NUMBER_MAP.get(c, c) for c in numbers)
        return letter_part + number_part + suffix

    # For unknown acronyms (2-5 uppercase letters), spell them out
    if re.match(r'^[A-Z]{2,5}$', word):
        return ''.join(LETTER_MAP.get(c, c) for c in word)

    # For mixed case or longer words, return as-is (TTS might handle it)
    return word


def convert_english_terms(text: str) -> str:
    """Convert English acronyms and terms to katakana pronunciation.

    Args:
        text: Text potentially containing English terms

    Returns:
        Text with English terms converted to katakana
    """
    # Match sequences of ASCII letters/numbers that start with a letter
    # Don't use \b as word boundaries don't work with Japanese text
    pattern = r'[A-Za-z][A-Za-z0-9]*'
    return re.sub(pattern, convert_acronym, text)


def preprocess_for_tts(text: str) -> str:
    """Full preprocessing pipeline for TTS input.

    Processing order:
    1. Extract furigana readings (authoritative pronunciation)
    2. Convert English terms to katakana
    3. Clean up any remaining brackets

    Args:
        text: Japanese text with optional furigana annotations

    Returns:
        Clean text optimized for TTS pronunciation

    Example:
        >>> preprocess_for_tts("APIの応答【おうとう】が遅【おそ】い")
        'エーピーアイのおうとうがおそい'
    """
    # Step 1: Extract furigana (always trust provided readings)
    result = extract_furigana(text)

    # Step 2: Convert English terms
    result = convert_english_terms(result)

    # Step 3: Clean up any remaining brackets
    result = re.sub(r'【[^】]*】', '', result)

    # Normalize whitespace
    result = ' '.join(result.split())

    return result


def add_acronym(acronym: str, pronunciation: str) -> None:
    """Add a custom acronym pronunciation at runtime.

    Args:
        acronym: The English acronym (e.g., "MQTT")
        pronunciation: Katakana pronunciation (e.g., "エムキューティーティー")
    """
    ACRONYM_MAP[acronym] = pronunciation


if __name__ == '__main__':
    test_cases = [
        ('昼食【ちゅうしょく】前【まえ】にこのバグを修正【しゅうせい】します。',
         'ちゅうしょくまえにこのバグをしゅうせいします。'),
        ('APIチームと同期【どうき】してください。',
         'エーピーアイチームとどうきしてください。'),
        ('EC2インスタンスで実行【じっこう】しています。',
         'イーシーツーインスタンスでじっこうしています。'),
        ('2日【ふつか】かかります。',
         'ふつかかかります。'),
        ('今日中【きょうじゅう】にできますか？',
         'きょうじゅうにできますか？'),
    ]

    print("Japanese TTS Pronunciation Preprocessor\n")
    print("=" * 60)

    all_pass = True
    for original, expected in test_cases:
        result = preprocess_for_tts(original)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_pass = False
        print(f"\n{status} Input:    {original}")
        print(f"  Output:   {result}")
        if result != expected:
            print(f"  Expected: {expected}")

    print("\n" + "=" * 60)
    print(f"Result: {'All tests passed' if all_pass else 'Some tests failed'}")
