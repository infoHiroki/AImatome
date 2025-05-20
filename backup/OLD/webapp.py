#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, send_file
import openai
import os
import json
import glob
from datetime import datetime
from dotenv import load_dotenv
import threading
import time

# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# 処理状態を管理するための変数
processing_status = {
    "is_processing": False,
    "current_file": "",
    "processed_count": 0,
    "total_count": 0,
    "results": [],
    "last_activity": None
}

# 処理履歴を保存
processing_history = []

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
        return False, f"ファイル読み込みエラー: {e}"
    
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
        return False, f"API呼び出しエラー: {e}"
    
    # 出力ファイルパスを決定
    base_name = os.path.basename(input_file)
    output_name = base_name.replace(".txt", "_議事録.txt")
    output_file = os.path.join(output_dir, output_name)
    
    # 結果を保存
    os.makedirs(output_dir, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(minutes)
    
    return True, output_file

def process_folder_async(input_dir, output_dir):
    """非同期でフォルダ内のファイルを処理"""
    global processing_status, processing_history
    
    processing_status["is_processing"] = True
    processing_status["results"] = []
    processing_status["last_activity"] = datetime.now()
    
    # テキストファイルを検索
    txt_files = glob.glob(os.path.join(input_dir, "*.txt"))
    processing_status["total_count"] = len(txt_files)
    processing_status["processed_count"] = 0
    
    # 各ファイルを処理
    for txt_file in txt_files:
        processing_status["current_file"] = os.path.basename(txt_file)
        processing_status["last_activity"] = datetime.now()
        success, result = create_minutes(txt_file, output_dir)
        
        processing_status["results"].append({
            "file": os.path.basename(txt_file),
            "success": success,
            "output": result,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        processing_status["processed_count"] += 1
        time.sleep(0.1)  # UI更新のための短い待機
    
    processing_status["is_processing"] = False
    processing_status["current_file"] = ""
    
    # 処理履歴に追加（最大100件保持）
    processing_history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_dir": input_dir,
        "output_dir": output_dir,
        "total_files": processing_status["total_count"],
        "results": processing_status["results"].copy()
    })
    if len(processing_history) > 100:
        processing_history.pop(0)

@app.route('/')
def index():
    """メインページ"""
    # config.jsonを読み込み
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except:
        config = {"input_folder": "transcripts", "output_folder": "minutes"}
    
    return render_template('index.html', config=config)

@app.route('/process', methods=['POST'])
def process():
    """議事録生成処理を開始"""
    global processing_status
    
    if processing_status["is_processing"]:
        return jsonify({"error": "既に処理中です"}), 400
    
    data = request.json
    input_folder = data.get('input_folder', 'transcripts')
    output_folder = data.get('output_folder', 'minutes')
    
    # 設定を保存
    config = {
        "input_folder": input_folder,
        "output_folder": output_folder
    }
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    # 入力フォルダの確認
    if not os.path.exists(input_folder):
        return jsonify({"error": f"入力フォルダが存在しません: {input_folder}"}), 400
    
    # 非同期で処理を開始
    thread = threading.Thread(
        target=process_folder_async,
        args=(input_folder, output_folder)
    )
    thread.start()
    
    return jsonify({"message": "処理を開始しました"})

@app.route('/status')
def status():
    """処理状態を返す"""
    # セキュリティのため、最終活動時刻を文字列形式で返す
    status_copy = processing_status.copy()
    if status_copy["last_activity"]:
        status_copy["last_activity"] = status_copy["last_activity"].strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(status_copy)

@app.route('/history')
def history():
    """処理履歴を返す"""
    return jsonify(processing_history)

@app.route('/files/<folder>')
def list_files(folder):
    """フォルダ内のファイル一覧を返す"""
    if not os.path.exists(folder):
        return jsonify([])
    
    files = []
    for file in glob.glob(os.path.join(folder, "*.txt")):
        files.append({
            "name": os.path.basename(file),
            "size": os.path.getsize(file),
            "modified": datetime.fromtimestamp(os.path.getmtime(file)).strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return jsonify(files)

@app.route('/download/<folder>/<filename>')
def download_file(folder, filename):
    """ファイルをダウンロード"""
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "ファイルが見つかりません", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)