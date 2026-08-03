@echo off
REM release.bat - wrapper for release.ps1
REM Usage: scripts\release.bat 0.3.0 "แก้บั๊กและเพิ่มฟีเจอร์ X"
setlocal
set VERSION=%~1
set NOTES=%~2
if "%VERSION%"=="" (
    echo Usage: scripts\release.bat ^<version^> ["release notes"]
    echo Example: scripts\release.bat 0.3.0 "Bug fixes"
    exit /b 1
)
if "%NOTES%"=="" set NOTES=Bug fixes and improvements
powershell -ExecutionPolicy Bypass -File "%~dp0release.ps1" -Version "%VERSION%" -Notes "%NOTES%"
endlocal
