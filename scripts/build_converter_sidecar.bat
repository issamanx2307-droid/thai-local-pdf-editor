@echo off
setlocal

REM Build the converter from its canonical source next to this repository.
REM The converter has its own dependencies; use its venv when available.
for %%I in ("%~dp0..\..\pdf_doc") do set "SOURCE_DIR=%%~fI"
if not exist "%SOURCE_DIR%\run_converter_sidecar.py" (
  echo PDF-to-Word source was not found: %SOURCE_DIR%
  exit /b 1
)

set "PYTHON=%SOURCE_DIR%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

pushd "%SOURCE_DIR%"
"%PYTHON%" -m PyInstaller --noconfirm --clean --onedir --contents-directory converter_internal --name pdf-converter --paths "." --collect-all fitz --distpath "build\converter_sidecar_dist" --workpath "build\converter_sidecar" --specpath "packaging" "run_converter_sidecar.py"
if errorlevel 1 (
  popd
  exit /b 1
)

set "TARGET_DIR=%~dp0..\react_shell\src-tauri\binaries"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
if exist "%TARGET_DIR%\converter_internal" rmdir /S /Q "%TARGET_DIR%\converter_internal"
move /Y "build\converter_sidecar_dist\pdf-converter\pdf-converter.exe" "%TARGET_DIR%\pdf-converter-x86_64-pc-windows-msvc.exe" >nul
move /Y "build\converter_sidecar_dist\pdf-converter\converter_internal" "%TARGET_DIR%\converter_internal" >nul
popd
endlocal
