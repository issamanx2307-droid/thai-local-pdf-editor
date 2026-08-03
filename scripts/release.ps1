<#
  release.ps1 - build, sign, publish, and deploy a new version of Thai Local PDF Editor.

  Usage:
    scripts\release.bat 0.3.0 "Release notes here"

  Steps:
    1. Refuse to run if the git working tree isn't clean.
    2. Bump version in tauri.conf.json, Cargo.toml, and package.json.
    3. Build the production bundle (tsc + vite + cargo release + NSIS),
       signed with the updater private key.
    4. Rename installer/signature to a space-free filename, write latest.json.
    5. Commit + push the version bump.
    6. Publish a GitHub Release with installer, signature, latest.json.
    7. Copy the freshly built binaries into the locally installed app.

  Requirements (local only, never committed to git):
    - C:\Users\WINDOWS\.thai-pdf-editor-keys\updater_signing_key
    - C:\Users\WINDOWS\.thai-pdf-editor-keys\updater_signing_key.password
    - gh CLI authenticated (gh auth status)
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,

    [string]$Notes = "Bug fixes and improvements"
)

$ErrorActionPreference = "Stop"

$repoRoot    = "D:\PDF editor"
$reactShell  = "$repoRoot\react_shell"
$bundleDir   = "$reactShell\src-tauri\target\release\bundle\nsis"
$keyDir      = "C:\Users\WINDOWS\.thai-pdf-editor-keys"
$keyPath     = "$keyDir\updater_signing_key"
$keyPwdPath  = "$keyDir\updater_signing_key.password"
$githubRepo  = "issamanx2307-droid/thai-local-pdf-editor"
$installDir  = "C:\Users\WINDOWS\AppData\Local\Programs\Thai Local PDF Editor"

function Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

if (-not (Test-Path $keyPath))    { throw "Signing key not found at $keyPath" }
if (-not (Test-Path $keyPwdPath)) { throw "Signing key password file not found at $keyPwdPath" }

Step "Closing running app instance (if any)"
Get-Process -Name "app" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Step "Checking git working tree is clean"
Set-Location $repoRoot
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host $gitStatus
    throw "Uncommitted changes found. Commit or stash before releasing."
}

Step "Bumping version to $Version"
$tauriConfPath = "$reactShell\src-tauri\tauri.conf.json"
(Get-Content $tauriConfPath -Raw) -replace '"version":\s*"[\d\.]+"', "`"version`": `"$Version`"" |
    Set-Content -Path $tauriConfPath -NoNewline

$cargoTomlPath = "$reactShell\src-tauri\Cargo.toml"
(Get-Content $cargoTomlPath -Raw) -replace '(?m)^version = "[\d\.]+"', "version = `"$Version`"" |
    Set-Content -Path $cargoTomlPath -NoNewline

Set-Location $reactShell
npm pkg set version="$Version" | Out-Null

Step "Setting up signing environment"
$env:NODE_ENV = ""
$env:TAURI_SIGNING_PRIVATE_KEY = (Get-Content $keyPath -Raw)
$env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD = (Get-Content $keyPwdPath -Raw).Trim()

Step "Building production bundle (tsc + vite + cargo release + NSIS + sign)"
npm run tauri:build
if ($LASTEXITCODE -ne 0) { throw "Build failed (exit $LASTEXITCODE)" }

Step "Preparing release assets"
$originalExe = "$bundleDir\Thai Local PDF Editor_${Version}_x64-setup.exe"
if (-not (Test-Path $originalExe)) { throw "Expected installer not found: $originalExe" }
$assetName = "ThaiLocalPDFEditor_${Version}_x64-setup.exe"
$assetExe  = "$bundleDir\$assetName"
$assetSig  = "$assetExe.sig"
Copy-Item $originalExe $assetExe -Force
Copy-Item "$originalExe.sig" $assetSig -Force

Step "Generating latest.json"
$signature  = (Get-Content $assetSig -Raw).Trim()
$releaseDir = "$repoRoot\_release_tmp"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
$pubDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$latestJsonObj = [ordered]@{
    version   = $Version
    notes     = $Notes
    pub_date  = $pubDate
    platforms = [ordered]@{
        "windows-x86_64" = [ordered]@{
            signature = $signature
            url       = "https://github.com/$githubRepo/releases/download/v$Version/$assetName"
        }
    }
}
$latestJsonObj | ConvertTo-Json -Depth 5 | Out-String |
    ForEach-Object { [System.IO.File]::WriteAllText("$releaseDir\latest.json", $_.TrimEnd(), [System.Text.UTF8Encoding]::new($false)) }

Step "Committing and pushing version bump"
Set-Location $repoRoot
git add "react_shell/package.json" "react_shell/package-lock.json" `
        "react_shell/src-tauri/Cargo.toml" "react_shell/src-tauri/Cargo.lock" `
        "react_shell/src-tauri/tauri.conf.json"
git commit -m "chore: bump version to $Version"
git push

Step "Publishing GitHub Release v$Version"
gh release create "v$Version" "$assetExe" "$assetSig" "$releaseDir\latest.json" `
    --title "v$Version" --notes "$Notes"

Step "Updating the locally installed app"
$src = "$reactShell\src-tauri\target\release"
Copy-Item "$src\app.exe" "$installDir\app.exe" -Force
Copy-Item "$src\pdf-bridge.exe" "$installDir\pdf-bridge.exe" -Force
Copy-Item "$src\pdf-converter.exe" "$installDir\pdf-converter.exe" -Force
Remove-Item "$installDir\_internal" -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item "$src\_internal" "$installDir\_internal" -Recurse -Force
Remove-Item "$installDir\converter_internal" -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item "$src\converter_internal" "$installDir\converter_internal" -Recurse -Force

Step "Cleaning up temp files"
Remove-Item $releaseDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$originalExe" -Force -ErrorAction SilentlyContinue
Remove-Item "$originalExe.sig" -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Done! Release v$Version published: https://github.com/$githubRepo/releases/tag/v$Version" -ForegroundColor Green
