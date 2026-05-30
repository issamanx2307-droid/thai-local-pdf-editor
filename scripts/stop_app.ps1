$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$pidPath = Join-Path $root "data\temp\app.pid"
$logPath = Join-Path $root "data\logs\launcher.log"
$packagedExe = Join-Path $root "dist\ThaiLocalPdfEditor\ThaiLocalPdfEditor.exe"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $pidPath), (Split-Path -Parent $logPath) | Out-Null

function Test-ThaiPdfEditorProcess {
    param($ProcessInfo)

    $commandLine = [string]$ProcessInfo.CommandLine
    $executablePath = [string]$ProcessInfo.ExecutablePath
    $isSourceLaunch = $commandLine -like "*run_app.py*" -and $commandLine -like "*$root*"
    $isPackagedLaunch = $executablePath -ieq $packagedExe -or $commandLine -like "*$packagedExe*"
    return $isSourceLaunch -or $isPackagedLaunch
}

$matches = @()
if (Test-Path -LiteralPath $pidPath) {
    $pidText = Get-Content -LiteralPath $pidPath -ErrorAction SilentlyContinue
    $pidValue = 0
    if ([int]::TryParse([string]$pidText, [ref]$pidValue)) {
        $tracked = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $pidValue) -ErrorAction SilentlyContinue
        if ($tracked -and (Test-ThaiPdfEditorProcess $tracked)) {
            $matches += $pidValue
        }
    }
}

foreach ($item in Get-CimInstance Win32_Process) {
    if (Test-ThaiPdfEditorProcess $item) {
        $matches += [int]$item.ProcessId
    }
}

$matches = @($matches | Sort-Object -Unique)
if ($matches.Count -eq 0) {
    if (Test-Path -LiteralPath $pidPath) {
        Remove-Item -LiteralPath $pidPath -Force
    }
    Write-Host "No Thai PDF Editor process is running."
    exit 0
}

foreach ($processId in $matches) {
    Stop-Process -Id $processId -Force
    Add-Content -LiteralPath $logPath -Value ((Get-Date -Format "yyyy-MM-dd HH:mm:ss") + " stop pid=" + $processId)
    Write-Host ("Stopped Thai PDF Editor. PID=" + $processId)
}

if (Test-Path -LiteralPath $pidPath) {
    Remove-Item -LiteralPath $pidPath -Force
}
