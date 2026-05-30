@echo off
setlocal
cd /d "%~dp0"
set "THAI_PDF_EDITOR_ARGS=%*"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root=(Resolve-Path -LiteralPath '.').Path; $pidPath=Join-Path $root 'data\temp\app.pid'; $logPath=Join-Path $root 'data\logs\launcher.log'; New-Item -ItemType Directory -Force -Path (Split-Path -Parent $pidPath),(Split-Path -Parent $logPath) | Out-Null; if(Test-Path -LiteralPath $pidPath){$oldText=(Get-Content -LiteralPath $pidPath -ErrorAction SilentlyContinue); $oldId=0; if([int]::TryParse([string]$oldText,[ref]$oldId)){$existing=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $oldId) -ErrorAction SilentlyContinue; if($existing){$cmd=[string]$existing.CommandLine; if($cmd -like '*run_app.py*' -and $cmd -like ('*' + $root + '*')){Write-Host ('Thai PDF Editor is already running. PID=' + $oldId); exit 0}}}}; $venvPython=Join-Path $root '.venv\Scripts\python.exe'; if(Test-Path -LiteralPath $venvPython){$pythonExe=$venvPython}else{$pythonExe=(Get-Command python).Source}; $scriptPath=Join-Path $root 'run_app.py'; $quotedScript=([char]34) + $scriptPath + ([char]34); $extraArgs=[string]$env:THAI_PDF_EDITOR_ARGS; if([string]::IsNullOrWhiteSpace($extraArgs)){$argumentList=$quotedScript}else{$argumentList=$quotedScript + ' ' + $extraArgs}; $proc=Start-Process -FilePath $pythonExe -ArgumentList $argumentList -WorkingDirectory $root -PassThru -WindowStyle Normal; Set-Content -LiteralPath $pidPath -Value $proc.Id -Encoding ASCII; Add-Content -LiteralPath $logPath -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' start pid=' + $proc.Id); Write-Host ('Started Thai PDF Editor. PID=' + $proc.Id)"

if errorlevel 1 (
    echo Failed to start Thai PDF Editor.
    exit /b 1
)

endlocal
