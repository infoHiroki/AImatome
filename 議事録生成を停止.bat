@echo off
cd /d "%~dp0システム"
echo 議事録自動生成を停止します...
for /f "tokens=2" %%i in ('tasklist ^| findstr python') do (
    taskkill /PID %%i /F >nul 2>&1
)
echo.
echo 停止しました。
echo.
pause