@echo off
setlocal
cd /d "%~dp0"
echo EasyVideo - optional natural offline narration
echo This installs Piper and downloads a single ~137 MB English voice model.
echo It is free; review its CC BY 4.0 dataset attribution before business use.
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (echo Python 3 is required.& pause& exit /b 1)
)
".venv\Scripts\python.exe" -m pip install piper-tts
if errorlevel 1 (
    echo Piper installation failed.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-NeuralVoice.ps1"
if errorlevel 1 (
    echo Voice download did not complete. You can retry.
    pause
    exit /b 1
)
echo.
echo Neural speech installed. Restart start-windows.bat to use it.
pause
