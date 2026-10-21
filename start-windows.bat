@echo off
setlocal
cd /d "%~dp0"
where ffmpeg >nul 2>nul
if errorlevel 1 (
 echo FFmpeg is missing. Install it, add its bin directory to PATH, and retry.
 echo Install guide: https://ffmpeg.org/download.html
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 py -3 -m venv .venv
 if errorlevel 1 (echo Python 3 was not found. Install Python 3.11+.& pause& exit /b 1)
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (echo Python package installation failed.& pause& exit /b 1)
echo.
echo EasyVideo starting on http://127.0.0.1:8000
echo Windows SAPI voiceover will be used unless Piper is configured.
start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn easyvideo.server:app --host 127.0.0.1 --port 8000
pause
