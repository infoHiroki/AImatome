@echo off
cd /d "%~dp0"
echo AImatome Starting...

python start.py
if errorlevel 1 (
    echo Error occurred while running start.py
    pause
    exit /b 1
)

pause