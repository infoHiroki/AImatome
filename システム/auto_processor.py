#!/usr/bin/env python3
import os
import json
import time
import glob
import shutil
from datetime import datetime
from dotenv import load_dotenv
import openai
import logging

# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_processor.log'),
        logging.StreamHandler()
    ]
)

def load_config():
    """設定ファイルを読み込み"""
    config_file = "auto_config.json"
    default_config = {
        "watch_folder": "transcripts",
        "output_folder": "minutes",
        "processed_folder": "processed",
        "check_interval": 1800,  # 30分
        "system_prompt": "会議の文字起こしから議事録を作成してください。以下の形式で：\n\n# 議事録\n## 日時・参加者\n## 議題\n## 決定事項\n## アクションアイテム\n- 誰が、何を、いつまでに\n## 次回予定"
    }
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config

def create_minutes(transcript_text, config):
    """議事録を生成"""
    prompt = config.get("system_prompt", "会議の文字起こしから議事録を作成してください。")
    
    # 文字数チェック（オプション）
    if len(transcript_text) > 200000:
        logging.warning(f"文字起こしが長大です: {len(transcript_text)}文字")
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcript_text}
            ],
            temperature=0.3,
            max_tokens=4000  # 出力制限を明示
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"API呼び出しエラー: {e}")
        return None

def process_file(file_path, output_folder, processed_folder, config):
    """単一ファイルを処理して移動"""
    logging.info(f"処理開始: {file_path}")
    
    # ファイルを読み込み
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            transcript = f.read()
    except Exception as e:
        logging.error(f"ファイル読み込みエラー: {file_path} - {e}")
        return False
    
    # 議事録を生成
    minutes = create_minutes(transcript, config)
    if not minutes:
        logging.error(f"議事録生成に失敗: {file_path}")
        return False
    
    # 出力ファイルパスを決定
    base_name = os.path.basename(file_path)
    # タイムスタンプを追加してユニークなファイル名にする（オプション）
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # output_name = base_name.replace(".txt", f"_議事録_{timestamp}.txt")
    output_name = base_name.replace(".txt", "_議事録.txt")
    output_path = os.path.join(output_folder, output_name)
    
    # フォルダを作成
    os.makedirs(output_folder, exist_ok=True)
    
    # 議事録を保存
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(minutes)
        logging.info(f"議事録を保存: {output_path}")
    except Exception as e:
        logging.error(f"保存エラー: {output_path} - {e}")
        return False
    
    # 処理済みフォルダに移動
    os.makedirs(processed_folder, exist_ok=True)
    processed_path = os.path.join(processed_folder, base_name)
    
    try:
        shutil.move(file_path, processed_path)
        logging.info(f"ファイルを移動: {file_path} → {processed_path}")
        return True
    except Exception as e:
        logging.error(f"移動エラー: {e}")
        return False

def check_and_process():
    """新しいファイルをチェックして処理"""
    config = load_config()
    watch_folder = config["watch_folder"]
    output_folder = config["output_folder"]
    processed_folder = config["processed_folder"]
    
    # 監視フォルダをチェック
    if not os.path.exists(watch_folder):
        logging.warning(f"監視フォルダが存在しません: {watch_folder}")
        return
    
    # txtファイルを検索
    txt_files = glob.glob(os.path.join(watch_folder, "*.txt"))
    
    if not txt_files:
        logging.info("新しいファイルはありません")
        return
    
    logging.info(f"{len(txt_files)}個のファイルを発見")
    
    for file_path in txt_files:
        # ファイルが完全に書き込まれるのを待つ
        time.sleep(5)
        process_file(file_path, output_folder, processed_folder, config)

def main():
    """メイン処理ループ"""
    config = load_config()
    interval = config["check_interval"]
    
    logging.info(f"自動処理を開始（チェック間隔: {interval}秒）")
    
    while True:
        try:
            check_and_process()
        except Exception as e:
            logging.error(f"エラー: {e}")
        
        logging.info(f"次のチェックまで{interval}秒待機...")
        time.sleep(interval)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("処理を停止します")