#!/usr/bin/env python3
import os
import json
import time
import glob
import shutil
from datetime import datetime, timedelta
from dotenv import load_dotenv
import openai
import logging
import sys

# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_processor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 状態管理
status_data = {
    "is_running": False,
    "last_check": None,
    "next_check": None,
    "processed_count": 0,
    "error_count": 0,
    "last_error": None,
    "current_processing": None,  # 現在処理中のファイル名
    "last_processed": None       # 最後に処理したファイル名
}

def update_status_file():
    """ユーザー向けの状態ファイルを更新"""
    try:
        current_processing = f"現在処理中: {status_data['current_processing']}" if status_data['current_processing'] else "現在処理中: なし"
        last_processed = f"最後に処理したファイル: {status_data['last_processed']}" if status_data['last_processed'] else "まだファイルは処理されていません"
        
        status_text = f"""議事録自動生成システム 状態確認
=================================
状態: {'実行中' if status_data['is_running'] else '停止中'}
最終チェック: {status_data['last_check'].strftime('%Y年%m月%d日 %H時%M分') if status_data['last_check'] else 'まだ実行されていません'}
次回チェック: {status_data['next_check'].strftime('%Y年%m月%d日 %H時%M分') if status_data['next_check'] else '---'}
処理済みファイル数: {status_data['processed_count']}個
{current_processing}
{last_processed}
エラー数: {status_data['error_count']}個
最終エラー: {status_data['last_error'] or 'なし'}

更新時刻: {datetime.now().strftime('%Y年%m月%d日 %H時%M分%S秒')}
"""
        # パス参照を修正
        status_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.txt")
        with open(status_path, "w", encoding="utf-8") as f:
            f.write(status_text)
    except Exception as e:
        logging.error(f"状態ファイル更新エラー: {e}")

def load_config():
    """設定ファイルを読み込み"""
    config_file = "auto_config.json"
    default_config = {
        "watch_folder": "input",
        "output_folder": "output",
        "processed_folder": "archive",
        "check_interval": 30,  # 30分
        "system_prompt": "会議の文字起こしから議事録を作成してください。以下の形式で：\n\n# 議事録\n## 日時・参加者\n## 議題\n## 決定事項\n## アクションアイテム\n- 誰が、何を、いつまでに\n## 次回予定",
        "model": "gpt-4-turbo",
        "max_tokens": 4096,
        "temperature": 0.3
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
    model = config.get("model", "gpt-4-turbo")
    max_tokens = config.get("max_tokens", 4096)
    temperature = config.get("temperature", 0.3)
    
    # 文字数チェック（オプション）
    if len(transcript_text) > 200000:
        logging.warning(f"文字起こしが長大です: {len(transcript_text)}文字")
    
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcript_text}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"API呼び出しエラー: {e}")
        status_data['error_count'] += 1
        status_data['last_error'] = f"API呼び出しエラー: {str(e)}"
        update_status_file()
        return None

def process_file(file_path, output_folder, processed_folder, config):
    """単一ファイルを処理して移動"""
    logging.info(f"処理開始: {file_path}")
    
    # 進捗状況を更新
    status_data['current_processing'] = os.path.basename(file_path)
    update_status_file()
    
    # ファイルを読み込み
    encodings = ['utf-8', 'shift_jis', 'cp932', 'euc_jp']
    transcript = None
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                transcript = f.read()
            break  # 成功したらループを抜ける
        except UnicodeDecodeError:
            continue  # 次のエンコーディングを試す
        except Exception as e:
            logging.error(f"ファイル読み込みエラー: {file_path} - {e}")
            status_data['error_count'] += 1
            status_data['last_error'] = f"ファイル読み込みエラー: {os.path.basename(file_path)}"
            update_status_file()
            return False

    if transcript is None:
        logging.error(f"全てのエンコーディングで読み込みに失敗: {file_path}")
        status_data['error_count'] += 1
        status_data['last_error'] = f"エンコーディングエラー: {os.path.basename(file_path)}"
        update_status_file()
        return False
    
    # 議事録を生成
    minutes = create_minutes(transcript, config)
    if not minutes:
        logging.error(f"議事録生成に失敗: {file_path}")
        status_data['current_processing'] = None  # 処理完了
        status_data['last_error'] = f"議事録生成に失敗: {os.path.basename(file_path)}"
        update_status_file()
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
        status_data['current_processing'] = None  # 処理完了
        status_data['last_error'] = f"保存エラー: {os.path.basename(file_path)}"
        update_status_file()
        return False
    
    # 処理済みフォルダに移動
    os.makedirs(processed_folder, exist_ok=True)
    processed_path = os.path.join(processed_folder, base_name)
    
    try:
        shutil.move(file_path, processed_path)
        logging.info(f"ファイルを移動: {file_path} → {processed_path}")
        status_data['processed_count'] += 1
        status_data['last_processed'] = os.path.basename(file_path)  # 追加
        status_data['current_processing'] = None  # 処理完了
        update_status_file()
        return True
    except Exception as e:
        logging.error(f"移動エラー: {e}")
        status_data['error_count'] += 1
        status_data['last_error'] = f"ファイル移動エラー: {os.path.basename(file_path)}"
        status_data['current_processing'] = None  # 処理完了
        update_status_file()
        return False

def resolve_path(config_path):
    """絶対パスと相対パスを適切に解決する"""
    if os.path.isabs(config_path):
        return config_path
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), config_path)

def check_and_process():
    """新しいファイルをチェックして処理"""
    config = load_config()
    
    # パス参照の解決（絶対パスと相対パスの両方をサポート）
    watch_folder = resolve_path(config["watch_folder"])
    output_folder = resolve_path(config["output_folder"])
    processed_folder = resolve_path(config["processed_folder"])
    
    # 状態を更新
    status_data['last_check'] = datetime.now()
    # 直接分単位で指定
    status_data['next_check'] = datetime.now() + timedelta(minutes=config["check_interval"])
    update_status_file()
    
    # 監視フォルダをチェック
    if not os.path.exists(watch_folder):
        logging.warning(f"監視フォルダが存在しません: {watch_folder}")
        status_data['last_error'] = f"監視フォルダが存在しません: {watch_folder}"
        update_status_file()
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
    interval = config["check_interval"]  # これは分単位の値
    
    # 状態を初期化
    status_data['is_running'] = True
    status_data['processed_count'] = 0
    status_data['error_count'] = 0
    update_status_file()
    
    logging.info(f"自動処理を開始（チェック間隔: {interval}分）")
    
    try:
        while True:
            try:
                check_and_process()
            except Exception as e:
                logging.error(f"エラー: {e}")
                status_data['error_count'] += 1
                status_data['last_error'] = str(e)
                update_status_file()
            
            logging.info(f"次のチェックまで{interval}分待機...")
            time.sleep(interval * 60)  # 分→秒に変換
    finally:
        status_data['is_running'] = False
        status_data['next_check'] = None
        update_status_file()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("処理を停止します")