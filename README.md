# AImatome - 議事録自動生成システム

## 概要
AImatomeは、文字起こしファイルから自動で議事録を生成するシステムです。  
一般ユーザー向けの簡単なUIを備え、技術知識がなくても使用できます。

## 特徴
- 🎯 文字起こしファイル(.txt)からAIを使って議事録を自動生成
- 🔄 フォルダ監視による自動処理（30分ごと）
- 📊 日本語表示の状態確認
- 💻 Windows対応の起動・停止機能
- 🚀 プログラミング知識不要

## 一般ユーザー向け 使い方

### 1. 初期設定（初回のみ）
「APIキー設定方法.txt」を参照して、`.env` ファイルにAPIキーを設定：
```
OPENAI_API_KEY=あなたのAPIキー
```

### 2. システムの起動
- `run.bat` をダブルクリック

### 3. ファイルの処理
1. `input` フォルダに文字起こしファイル（.txt）を配置
2. 30分ごとに自動チェック・処理
3. `output` フォルダに結果が保存される
4. 処理済みファイルは `archive` フォルダに移動

### 4. 状態確認
`status.txt` を開いて処理状況やエラーを確認

### 5. システムの停止
- システムを停止するには、起動時に開いたコマンドウィンドウを閉じるだけです。

## フォルダ構成
```
AImatome/
├── input/               # 入力ファイルを配置
├── output/              # 生成された議事録
├── archive/             # 処理後の元ファイル
├── auto_processor.py    # メイン処理ファイル
├── auto_config.json     # 設定ファイル
├── .env                 # APIキー設定 
├── run.bat              # 起動バッチファイル
├── start.py             # UIスクリプト
└── status.txt           # 状態表示
```

## 開発者向け情報

### 必要な環境
- Python 3.8以上
- OpenAI API キー

### セットアップ
1. 依存ライブラリのインストール
```bash
pip install -r requirements.txt
```

2. APIキーの設定
`.env`ファイルを作成：
```
OPENAI_API_KEY=あなたのAPIキー
```

### 直接実行
```bash
python auto_processor.py
```

### 設定ファイル
- `auto_config.json`: メイン設定ファイル
```json
{
  "watch_folder": "input",
  "output_folder": "output",
  "processed_folder": "archive",
  "check_interval": 30,
  "system_prompt": "議事録生成プロンプト...",
  "model": "gpt-4-turbo",
  "max_tokens": 4096,
  "temperature": 0.3
}
```

※ フォルダパスには相対パスまたは絶対パス（例: "C:\\Users\\xxxx\\Documents\\Output"）が指定可能です。
※ check_intervalはチェック間隔（分）を表します。
※ モデルの変更方法については `モデル情報.txt` を参照してください。

### 生成される議事録の形式
```
# 議事録
## 日時・参加者
## 議題
## 決定事項
## アクションアイテム
- 誰が、何を、いつまでに
## 次回予定
```

## トラブルシューティング
- エラーが発生した場合は `status.txt` を確認
- APIキーが正しく設定されているか確認
- Python環境とライブラリがインストールされているか確認
- `auto_processor.log` で詳細なログを確認

## セキュリティについて
- APIキーは絶対にGitHubなどに公開しないでください
- `.gitignore`ファイルに`.env`が含まれています
- 処理済みファイルは自動的に別フォルダに移動されます

## ライセンス
MIT