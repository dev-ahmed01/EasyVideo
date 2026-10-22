@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo Python launcher is missing. Install Python 3.11 or newer.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 py -3 -m venv .venv
 if errorlevel 1 (pause & exit /b 1)
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup-piper.ps1"
if errorlevel 1 (
 echo Voice setup was not completed. No cloud account or paid API is required.
 pause
 exit /b 1
)
echo.
echo Piper has been prepared. Start the app with start-windows.bat.
pause
