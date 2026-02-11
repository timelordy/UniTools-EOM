# Kill EOMHub process and sync canonical EXE + mirror
Write-Host "Stopping EOMHub processes..."
Get-Process -Name "EOMHub" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$repoRoot = Split-Path -Parent $PSScriptRoot
$canonical = Join-Path $repoRoot "EOMTemplateTools.extension\bin\EOMHub.exe"
$mirror = Join-Path $env:APPDATA "pyRevit\Extensions\EOMTemplateTools.extension\bin\EOMHub.exe"

if (-not (Test-Path $canonical)) {
    throw "Canonical EXE not found: $canonical"
}

Write-Host "Canonical EXE source: $canonical"

Write-Host "Updating mirror EXE: $mirror"
New-Item -ItemType Directory -Path (Split-Path -Parent $mirror) -Force | Out-Null
Copy-Item -Path $canonical -Destination $mirror -Force

$canonicalItem = Get-Item $canonical
$mirrorItem = Get-Item $mirror
Write-Host "Canonical: $($canonicalItem.Length) bytes, $($canonicalItem.LastWriteTime)"
Write-Host "Mirror:    $($mirrorItem.Length) bytes, $($mirrorItem.LastWriteTime)"
