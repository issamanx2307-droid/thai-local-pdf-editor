@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_app.ps1"

if errorlevel 1 (
    echo Failed to stop Thai PDF Editor.
    exit /b 1
)

endlocal
