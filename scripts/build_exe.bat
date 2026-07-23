@echo off
setlocal
cd /d "%~dp0\.."

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $root=(Resolve-Path -LiteralPath '.').Path; $exe=Join-Path $root 'dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe'; $matches=Get-Process | Where-Object { $_.Path -eq $exe }; foreach($process in $matches){ $null=$process.CloseMainWindow() }; Start-Sleep -Milliseconds 1000; Get-Process | Where-Object { $_.Path -eq $exe } | Stop-Process -Force"

if exist "dist\ThaiLocalPdfEditor" (
  attrib -R "dist\ThaiLocalPdfEditor\*" /S /D >nul 2>nul
)

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name ThaiLocalPdfEditor ^
  --paths "." ^
  --collect-all customtkinter ^
  --collect-all tkinterdnd2 ^
  --exclude-module pytest ^
  --exclude-module _pytest ^
  --exclude-module pandas ^
  --exclude-module matplotlib ^
  --exclude-module openpyxl ^
  --exclude-module lxml ^
  --exclude-module numpy ^
  --exclude-module cryptography ^
  --exclude-module OpenSSL ^
  --exclude-module twisted ^
  --icon "%CD%\assets\icons\pdf_editor.ico" ^
  --add-data "%CD%\assets;assets" ^
  --distpath "dist" ^
  --workpath "build" ^
  --specpath "packaging" ^
  "run_app.py"

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo Build completed: dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe
endlocal
