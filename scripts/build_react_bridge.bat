@echo off
setlocal
cd /d "%~dp0\.."

set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

%PYTHON% -m PyInstaller --noconfirm --clean --onefile --name pdf-bridge --paths "." --collect-all fitz --distpath "react_shell\src-tauri\binaries" --workpath "build\react_bridge" --specpath "packaging" "run_react_bridge.py"
if errorlevel 1 exit /b 1

if exist "react_shell\src-tauri\binaries\pdf-bridge.exe" (
  move /Y "react_shell\src-tauri\binaries\pdf-bridge.exe" "react_shell\src-tauri\binaries\pdf-bridge-x86_64-pc-windows-msvc.exe" >nul
)
endlocal
