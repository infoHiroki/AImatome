@echo off
cd /d "%~dp0システム"
echo 議事録自動生成を開始します...
start /b python auto_processor.py > nul 2>&1
echo.
echo 開始しました！処理はバックグラウンドで実行されています。
echo 「現在の状態.txt」で状況を確認できます。
echo.
echo このウィンドウは閉じても大丈夫です。
pause