#!/usr/bin/env python3
import openai
import os
import json
import glob
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む（存在する場合）
load_dotenv()

# APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

def create_minutes(input_file, output_dir):
    """文字起こしファイルから議事録を生成"""
    
    # 設定ファイルを読み込み
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            prompt = config.get("system_prompt", "会議の文字起こしから議事録を作成してください。")
    except:
        prompt = "会議の文字起こしから議事録を作成してください。"
    
    # ファイルを読み込み
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            transcript = f.read()
    except Exception as e:
        print(f"エラー: ファイルが読み込めません - {e}")
        return False
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.3
        )
        minutes = response.choices[0].message.content
    except Exception as e:
        print(f"エラー: API呼び出しに失敗しました - {e}")
        return False
    
    # 出力ファイルパスを決定
    base_name = os.path.basename(input_file)
    output_name = base_name.replace(".txt", "_議事録.txt")
    output_file = os.path.join(output_dir, output_name)
    
    # 結果を保存
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(minutes)
    
    print(f"議事録を作成しました: {output_file}")
    return True

def process_folder(config):
    """設定ファイルに基づいてフォルダ内のファイルを処理"""
    
    input_dir = config["input_folder"]
    output_dir = config["output_folder"]
    
    # 入力フォルダの確認
    if not os.path.exists(input_dir):
        print(f"エラー: 入力フォルダが存在しません - {input_dir}")
        return
    
    # 出力フォルダの作成
    os.makedirs(output_dir, exist_ok=True)
    
    # テキストファイルを検索
    txt_files = glob.glob(os.path.join(input_dir, "*.txt"))
    
    if not txt_files:
        print(f"エラー: {input_dir} にテキストファイルが見つかりません")
        return
    
    print(f"{len(txt_files)}個のファイルを処理します...")
    
    # 各ファイルを処理
    success_count = 0
    for txt_file in txt_files:
        print(f"\n処理中: {os.path.basename(txt_file)}")
        if create_minutes(txt_file, output_dir):
            success_count += 1
    
    print(f"\n完了: {success_count}/{len(txt_files)}個のファイルを処理しました")

def main():
    """メイン処理"""
    
    # APIキーの確認
    if not openai.api_key:
        print("エラー: 環境変数OPENAI_API_KEYまたは.envファイルにAPIキーを設定してください")
        print("\n設定方法:")
        print("1. .envファイルを作成してOPENAI_API_KEY=あなたのAPIキーを追加")
        print("2. または環境変数を設定: export OPENAI_API_KEY=あなたのAPIキー")
        return
    
    # 設定ファイルの読み込み
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("エラー: config.jsonファイルが見つかりません")
        print("\n以下の内容でconfig.jsonを作成してください:")
        print(json.dumps({
            "input_folder": "transcripts",
            "output_folder": "minutes"
        }, indent=2, ensure_ascii=False))
        return
    except json.JSONDecodeError:
        print("エラー: config.jsonの形式が正しくありません")
        return
    
    # 処理実行
    process_folder(config)

if __name__ == "__main__":
    main()