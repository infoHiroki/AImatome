@echo off
chcp 932
echo 議事録自動生成を停止します...

echo Pythonプロセスを停止中...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM pythonw.exe /T 2>nul

echo.
echo 停止しました。
echo 「現在の状態.txt」で状況を確認できます。
echo.
pause