@echo off
setlocal
cd /d "%~dp0\.."

set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

REM --onedir instead of --onefile: onefile self-extracts to a temp dir on
REM EVERY launch (~3.5s cold start measured), onedir runs directly from
REM disk with no extraction step. Costs: output is a folder, not one exe,
REM so Tauri's externalBin only takes the exe; the "_internal" dependency
REM folder is bundled separately via tauri.conf.json "resources" so it
REM ends up sitting next to the sidecar exe at install time (PyInstaller
REM onedir requires "_internal" to be a sibling of the exe to run).
%PYTHON% -m PyInstaller --noconfirm --clean --onedir --name pdf-bridge --paths "." --collect-all fitz --distpath "build\react_bridge_dist" --workpath "build\react_bridge" --specpath "packaging" "run_react_bridge.py"
if errorlevel 1 exit /b 1

if not exist "react_shell\src-tauri\binaries" mkdir "react_shell\src-tauri\binaries"
if exist "react_shell\src-tauri\binaries\_internal" rmdir /S /Q "react_shell\src-tauri\binaries\_internal"

move /Y "build\react_bridge_dist\pdf-bridge\pdf-bridge.exe" "react_shell\src-tauri\binaries\pdf-bridge-x86_64-pc-windows-msvc.exe" >nul
move /Y "build\react_bridge_dist\pdf-bridge\_internal" "react_shell\src-tauri\binaries\_internal" >nul
endlocal
