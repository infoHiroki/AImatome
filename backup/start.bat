@echo off
cd /d "%~dp0system"
echo Starting...
echo.
echo 重要: プログラム実行中はこのウィンドウを閉じないでください。
echo 閉じると処理が停止します。必要に応じて最小化してください。
echo.
python auto_processor.py
pause