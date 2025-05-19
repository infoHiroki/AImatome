# 議事録自動生成ツール

GPT-4 APIを使って、会議の文字起こしから議事録を自動生成します。

## セットアップ

1. Pythonライブラリをインストール
```bash
pip install -r requirements.txt
```

2. APIキーを設定（以下のいずれかの方法）

### 方法1: .envファイル（推奨）
`.env`ファイルを作成して、以下を記入：
```
OPENAI_API_KEY=あなたのAPIキー
```

### 方法2: 環境変数
```bash
export OPENAI_API_KEY="あなたのAPIキー"
```

3. フォルダ設定
`config.json`ファイルでフォルダを指定：
```json
{
  "input_folder": "transcripts",
  "output_folder": "minutes"
}
```

## 使い方

### 自動処理版（24時間監視）

音声データから文字起こし→議事録作成を完全自動化する場合：

1. 自動処理を開始
```bash
python auto_processor.py
```

2. 設定（`auto_config.json`）
```json
{
  "watch_folder": "transcripts",   // 監視フォルダ（文字起こし結果）
  "output_folder": "minutes",      // 出力フォルダ（議事録）
  "processed_folder": "processed", // 処理済みファイル保管
  "check_interval": 1800          // チェック間隔（秒）30分
}
```

**動作の流れ：**
1. `transcripts/`フォルダに新しいテキストファイルが見つかる
2. 議事録を生成して`minutes/`に保存
3. 元ファイルを`processed/`に移動（重複処理防止）

**特徴：**
- シンプルで確実な重複処理防止
- ファイルシステムベースの状態管理
- 処理状態が目で見える
- ログファイル（`auto_processor.log`）に全記録

### WebUI版（手動操作）

1. WebUIを起動
```bash
python webapp.py
```

2. ブラウザでアクセス
```
http://localhost:5000
```

3. WebUIから操作
- 入力・出力フォルダを設定
- 「処理を開始」ボタンをクリック
- リアルタイムで進捗を確認
- 完成した議事録をダウンロード

### コマンドライン版

```bash
python minutes_generator.py
```

これで`config.json`で指定した入力フォルダ内のすべての.txtファイルを処理し、出力フォルダに議事録を保存します。

## 実行例

```bash
# config.jsonで "input_folder": "transcripts", "output_folder": "minutes" を設定

python minutes_generator.py

# 実行結果:
# 2個のファイルを処理します...
# 処理中: sample_transcript.txt
# 議事録を作成しました: minutes/sample_transcript_議事録.txt
# 処理中: medical_transcript.txt  
# 議事録を作成しました: minutes/medical_transcript_議事録.txt
# 完了: 2/2個のファイルを処理しました
```

## ファイル構成

```
project/
├── webapp.py             # WebUIアプリケーション（新機能）
├── minutes_generator.py  # コマンドライン版
├── config.json          # フォルダ設定
├── .env                 # APIキー設定（Gitから除外）
├── requirements.txt     # 必要なライブラリ
├── templates/           # HTMLテンプレート
│   └── index.html      # WebUI画面
├── transcripts/         # 入力フォルダ（文字起こしファイル）
│   ├── sample_transcript.txt
│   └── medical_transcript.txt
└── minutes/             # 出力フォルダ（議事録）
    ├── sample_transcript_議事録.txt
    └── medical_transcript_議事録.txt
```

## 生成される議事録の形式

```
# 議事録
## 日時・参加者
## 議題
## 決定事項
## アクションアイテム
- 誰が、何を、いつまでに
## 次回予定
```

## セキュリティについて

- APIキーは絶対にGitHubなどに公開しないでください
- `.gitignore`ファイルに`.env`が含まれているので、.envファイルは自動的にGitから除外されます