import os
import time
import sys
import subprocess
import signal
from datetime import datetime

# プロセス管理用の変数
processor_process = None
is_processing = False

def clear_screen():
    """画面をクリアする"""
    os.system('cls' if os.name == 'nt' else 'clear')

def parse_status_file():
    """ステータスファイルを解析する"""
    status_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.txt")
    last_check = None
    next_check = None
    processed_count = 0
    error_count = 0
    last_error = None
    current_processing = None  # 追加
    last_processed = None      # 追加
    
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if "最終チェック:" in line:
                    last_check = line.split(":", 1)[1].strip()
                    if last_check == "まだ実行されていません":
                        last_check = None
                elif "次回予定:" in line or "次回チェック:" in line:
                    next_check = line.split(":", 1)[1].strip()
                    if next_check == "---":
                        next_check = None
                elif "処理済みファイル数:" in line:
                    try:
                        processed_count = int(line.split(":", 1)[1].strip().replace("個", ""))
                    except ValueError:
                        processed_count = 0
                elif "エラー数:" in line:
                    try:
                        error_count = int(line.split(":", 1)[1].strip().replace("個", ""))
                    except ValueError:
                        error_count = 0
                elif "最終エラー:" in line:
                    last_error = line.split(":", 1)[1].strip()
                    if last_error == "なし":
                        last_error = None
                # 追加: 新しいステータス項目
                elif "現在処理中:" in line:
                    current_processing = line.split(":", 1)[1].strip()
                    if current_processing == "なし":
                        current_processing = None
                elif "最後に処理したファイル:" in line:
                    last_processed = line.split(":", 1)[1].strip()
                    if last_processed == "まだファイルは処理されていません":
                        last_processed = None
    except Exception as e:
        print(f"ステータスファイル読み込みエラー: {e}")
    
    # 戻り値に新しいパラメータを追加
    return last_check, next_check, processed_count, error_count, last_error, current_processing, last_processed

def parse_log_file():
    """ログファイルを解析する"""
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_processor.log")
    logs = []
    
    try:
        if os.path.exists(log_path):
            # UTF-8を最初に試し、それから他のエンコーディングを試す
            encodings = ['utf-8', 'shift_jis', 'cp932', 'euc_jp']
            for encoding in encodings:
                try:
                    with open(log_path, "r", encoding=encoding) as f:
                        logs = f.readlines()[-5:]  # 最新の5行を取得
                    break  # 成功したらループを抜ける
                except UnicodeDecodeError:
                    continue  # 次のエンコーディングを試す
            
            if not logs:  # すべてのエンコーディングが失敗した場合
                logs = ["ログファイルの読み込みに失敗しました。エンコーディングの問題かもしれません。"]
    except Exception as e:
        logs = [f"ログファイル読み込みエラー: {e}"]
    
    return logs

def get_file_info():
    """フォルダ内のファイル情報を取得する"""
    root_path = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(root_path, "input")
    output_path = os.path.join(root_path, "output")
    archive_path = os.path.join(root_path, "archive")
    
    input_files = [f for f in os.listdir(input_path) if f.endswith('.txt')] if os.path.exists(input_path) else []
    output_files = [f for f in os.listdir(output_path) if f.endswith('.txt')] if os.path.exists(output_path) else []
    archive_files = [f for f in os.listdir(archive_path) if f.endswith('.txt')] if os.path.exists(archive_path) else []
    
    return input_files, output_files, archive_files

def draw_ui(status="停止中", message="", system_info=None, file_info=None, logs=None):
    """シンプルなUIを描画"""
    clear_screen()
    width = 70
    
    print("=" * width)
    print("AImatome - 議事録自動生成システム".center(width))
    print("=" * width)
    print(f"状態: {status}")
    print("-" * width)
    
    # システム情報
    print("システム情報:")
    if system_info:
        # アンパックの更新
        last_check, next_check, processed_count, error_count, last_error, current_processing, last_processed = system_info
        print(f"  最終チェック: {last_check or '--'}")
        print(f"  次回予定: {next_check or '--'}")
        print(f"  処理済みファイル: {processed_count}個")
        print(f"  現在処理中: {current_processing or 'なし'}")
        print(f"  最後に処理: {last_processed or '--'}")
        print(f"  エラー数: {error_count}個")
        if last_error:
            print(f"  最終エラー: {last_error}")
    else:
        print("  情報が取得できませんでした")
    
    # ファイル情報
    print("-" * width)
    print("ファイル状況:")
    if file_info:
        input_files, output_files, archive_files = file_info
        print(f"  input/: {len(input_files)}件" + (f" (最新: {input_files[-1]})" if input_files else ""))
        print(f"  output/: {len(output_files)}件" + (f" (最新: {output_files[-1]})" if output_files else ""))
        print(f"  archive/: {len(archive_files)}件" + (f" (最新: {archive_files[-1]})" if archive_files else ""))
    else:
        print("  情報が取得できませんでした")
    
    # ログ表示
    if logs and len(logs) > 0:
        print("-" * width)
        print("最新ログ:")
        for log in logs:
            # タイムスタンプを除去して表示
            parts = log.split(" - ", 1)
            if len(parts) > 1:
                log_text = parts[1].strip()
            else:
                log_text = log.strip()
            
            # 長いテキストは切り詰める
            if len(log_text) > width - 2:
                log_text = log_text[:width - 5] + "..."
            
            print(f"  {log_text}")
    
    # コマンドヘルプ
    print("-" * width)
    print("コマンド:")
    if is_processing:
        print("  [S] 停止する")
    else:
        print("  [S] 開始する")
    print("  [R] 画面更新")
    print("  [Q] 終了")
    
    # メッセージ表示
    if message:
        print("-" * width)
        print(f"メッセージ: {message}")
    
    print("=" * width)

def start_processor():
    """処理を開始する"""
    global processor_process, is_processing
    if not is_processing:
        try:
            # サブプロセスとしてauto_processor.pyを実行
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_processor.py")
            
            # スクリプトが存在するか確認
            if not os.path.exists(script_path):
                return f"エラー: {script_path} が見つかりません"
            
            # Windowsでは新しいコンソールウィンドウを作成せずに実行
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE
            
            processor_process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            
            is_processing = True
            return "処理を開始しました"
        except Exception as e:
            return f"処理の開始に失敗しました: {e}"
    else:
        return "すでに処理は実行中です"

def stop_processor():
    """処理を停止する"""
    global processor_process, is_processing
    if is_processing and processor_process:
        try:
            # Windowsの場合
            if os.name == 'nt':
                # TASKKILL を使用してプロセスツリーを終了
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(processor_process.pid)], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                # Unix系の場合
                os.killpg(os.getpgid(processor_process.pid), signal.SIGTERM)
            
            processor_process = None
            is_processing = False
            return "処理を停止しました"
        except Exception as e:
            return f"処理の停止に失敗しました: {e}"
    else:
        return "処理は実行されていません"

def main():
    """メイン関数"""
    message = "AImatomeモニターを起動しました"
    
    # msvcrtをインポート（Windowsでのキー入力用）
    try:
        import msvcrt
    except ImportError:
        print("msvcrtモジュールをインポートできません。Windowsでのみ実行できます。")
        sys.exit(1)
    
    # メインループ
    while True:
        # 情報を取得
        system_info = parse_status_file()
        logs = parse_log_file()
        file_info = get_file_info()
        
        # 画面を描画
        status = "実行中" if is_processing else "停止中"
        draw_ui(status, message, system_info, file_info, logs)
        
        # キー入力を待機
        start_time = time.time()
        while time.time() - start_time < 60:  # 60秒間キー入力をチェック
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                if key == 'q':  # 終了
                    # 実行中のプロセスがあれば停止
                    if is_processing:
                        stop_processor()
                    clear_screen()
                    print("AImatomeモニターを終了します。")
                    return
                elif key == 'r':  # 画面更新
                    message = "画面を更新しました"
                    break
                elif key == 's':  # 処理開始/停止
                    if is_processing:
                        message = stop_processor()
                    else:
                        message = start_processor()
                    break
            time.sleep(0.1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # 実行中のプロセスがあれば停止
        if is_processing and processor_process:
            stop_processor()
        print("\nAImatomeモニターを終了します。")
        sys.exit(0)