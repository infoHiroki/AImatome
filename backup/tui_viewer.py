#!/usr/bin/env python3
import os
import time
import json
import glob
import subprocess
import signal
from datetime import datetime, timedelta
import sys

# richライブラリが必要です: pip install rich
try:
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.console import Console
    from rich.text import Text
    from rich.table import Table
    from rich import box
except ImportError:
    print("richライブラリがインストールされていません。")
    print("インストールするには: pip install rich")
    sys.exit(1)

# プロセス管理用の変数
processor_process = None
is_processing = False

# 設定をロード
def load_config():
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_config.json")
    default_config = {
        "watch_folder": "input",
        "output_folder": "output", 
        "processed_folder": "archive",
        "check_interval": 1800  # 30分
    }
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # 設定ファイルがなければデフォルト設定を返す
        return default_config

# ヘッダーセクションを生成
def generate_header(is_processing):
    grid = Table.grid(expand=True)
    grid.add_column(justify="center")
    grid.add_row("[bold blue]AImatome[/bold blue] - 議事録自動生成システム")
    
    # システム状態の表示行
    status_grid = Table.grid(expand=True)
    status_grid.add_column(justify="center")
    
    if is_processing:
        status_grid.add_row("[bold green]== 実行中 ==[/bold green]")
        return Panel(Column(grid, status_grid), style="white on blue")
    else:
        status_grid.add_row("[bold red]-- 停止中 --[/bold red]")
        return Panel(Column(grid, status_grid), style="white on blue")

# ステータスセクションを生成
def generate_status(last_check, next_check, processed_count, error_count, last_error):
    table = Table(box=box.SIMPLE)
    table.add_column("項目", style="cyan", width=20)
    table.add_column("値", style="green")
    
    # 処理状態を追加
    global is_processing
    if is_processing:
        table.add_row("処理状態", "[bold green]実行中[/bold green]")
    else:
        table.add_row("処理状態", "[bold red]停止中[/bold red]")
        
    table.add_row("最終チェック", last_check or "未実行")
    table.add_row("次回予定", next_check or "---")
    table.add_row("処理済みファイル", f"[bold]{processed_count}[/bold]個")
    
    if error_count > 0:
        table.add_row("エラー数", f"[bold red]{error_count}[/bold red]個")
        table.add_row("最終エラー", f"[red]{last_error}[/red]")
    else:
        table.add_row("エラー数", "0個")
        table.add_row("最終エラー", "なし")
    
    return Panel(table, title="システム状況", border_style="green")

# ファイルセクションを生成
def generate_files_section(input_files, output_files, archive_files):
    table = Table(box=box.SIMPLE)
    table.add_column("フォルダ", style="cyan")
    table.add_column("ファイル数", style="yellow")
    table.add_column("最新ファイル", style="green", no_wrap=False)
    
    table.add_row("input/", str(len(input_files)), input_files[-1] if input_files else "なし")
    table.add_row("output/", str(len(output_files)), output_files[-1] if output_files else "なし")
    table.add_row("archive/", str(len(archive_files)), archive_files[-1] if archive_files else "なし")
    
    return Panel(table, title="ファイル状況", border_style="yellow")

# ログセクションを生成
def generate_log_section(logs):
    log_text = "\n".join(logs[-8:])  # 最新の8行を表示
    return Panel(log_text, title="ログ", border_style="magenta")

# ヘルプセクションを生成
def generate_help():
    help_text = """
    [bold cyan]キー操作[/bold cyan]
    [yellow]q[/yellow]: 終了   [yellow]r[/yellow]: 画面更新   [yellow]s[/yellow]: 処理開始/停止
    """
    return Panel(help_text, title="ヘルプ", border_style="blue")

# レイアウトを生成
def generate_layout(last_check, next_check, processed_count, error_count, last_error, 
                    input_files, output_files, archive_files, logs):
    layout = Layout()
    
    layout.split(
        Layout(generate_header(), size=3),
        Layout(name="main"),
        Layout(generate_log_section(logs), size=10),
        Layout(generate_help(), size=5)
    )
    
    layout["main"].split_row(
        Layout(generate_status(last_check, next_check, processed_count, error_count, last_error), ratio=1),
        Layout(generate_files_section(input_files, output_files, archive_files), ratio=1)
    )
    
    return layout

# ファイル情報を取得
def get_file_info(root_path, config):
    input_path = os.path.join(root_path, config["watch_folder"])
    output_path = os.path.join(root_path, config["output_folder"])
    archive_path = os.path.join(root_path, config["processed_folder"])
    
    input_files = [f for f in os.listdir(input_path) if f.endswith('.txt')] if os.path.exists(input_path) else []
    output_files = [f for f in os.listdir(output_path) if f.endswith('.txt')] if os.path.exists(output_path) else []
    archive_files = [f for f in os.listdir(archive_path) if f.endswith('.txt')] if os.path.exists(archive_path) else []
    
    return input_files, output_files, archive_files

# ステータスファイルから情報を取得
def parse_status_file(root_path):
    status_path = os.path.join(root_path, "status.txt")
    last_check = None
    next_check = None
    processed_count = 0
    error_count = 0
    last_error = None
    
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
    except Exception as e:
        print(f"ステータスファイル読み込みエラー: {e}")
    
    return last_check, next_check, processed_count, error_count, last_error

# ログファイルから情報を取得
def parse_log_file(root_path):
    log_path = os.path.join(root_path, "system", "auto_processor.log")
    logs = []
    
    try:
        if os.path.exists(log_path):
            # 複数のエンコーディングを試す
            encodings = ['utf-8', 'shift_jis', 'cp932', 'euc_jp']
            for encoding in encodings:
                try:
                    with open(log_path, "r", encoding=encoding) as f:
                        logs = f.readlines()[-20:]  # 最新の20行を取得
                    break  # 成功したらループを抜ける
                except UnicodeDecodeError:
                    continue  # 次のエンコーディングを試す
            
            if not logs:  # すべてのエンコーディングが失敗した場合
                logs = ["ログファイルの読み込みに失敗しました。エンコーディングの問題かもしれません。"]
    except Exception as e:
        logs = [f"ログファイル読み込みエラー: {e}"]
    
    return logs

# プロセスの開始
def start_processor(root_path):
    global processor_process, is_processing
    if not is_processing:
        try:
            # サブプロセスとしてauto_processor.pyを実行
            script_path = os.path.join(root_path, "system", "auto_processor.py")
            
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

# プロセスの停止
def stop_processor():
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

# メイン関数
def main():
    # 初期設定
    console = Console()
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config = load_config()
    
    # ログ保存用のリスト
    custom_logs = []
    
    # msvcrtをインポート（Windowsでのキー入力用）
    try:
        import msvcrt
    except ImportError:
        print("msvcrtモジュールをインポートできません。Windowsでのみ実行できます。")
        sys.exit(1)
    
    # 最初の情報を取得
    last_check, next_check, processed_count, error_count, last_error = parse_status_file(root_path)
    logs = parse_log_file(root_path)
    input_files, output_files, archive_files = get_file_info(root_path, config)
    
    # TUIを表示
    with Live(auto_refresh=False) as live:
        while True:
            # 情報を更新
            last_check, next_check, processed_count, error_count, last_error = parse_status_file(root_path)
            file_logs = parse_log_file(root_path)
            input_files, output_files, archive_files = get_file_info(root_path, config)
            
            # ログを結合
            all_logs = custom_logs[-4:] + file_logs[-4:]  # 両方から最新の4件ずつ
            
            # レイアウトを更新
            layout = generate_layout(
                last_check, next_check, processed_count, error_count, last_error,
                input_files, output_files, archive_files, all_logs
            )
            
            live.update(layout, refresh=True)
            
            # キー入力を待機（非ブロッキングで）
            start_time = time.time()
            while time.time() - start_time < 1:  # 1秒間キー入力をチェック
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                    if key == 'q':  # 終了
                        # 実行中のプロセスがあれば停止
                        if is_processing:
                            custom_logs.append(stop_processor())
                        print("\nTUIを終了します。")
                        return
                    elif key == 'r':  # 画面更新
                        custom_logs.append("画面を更新しました")
                        break
                    elif key == 's':  # 処理開始/停止
                        if is_processing:
                            custom_logs.append(stop_processor())
                        else:
                            custom_logs.append(start_processor(root_path))
                time.sleep(0.1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # 実行中のプロセスがあれば停止
        if is_processing and processor_process:
            stop_processor()
        print("\nTUIを終了します。")
        sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTUIを終了します。")
        sys.exit(0)