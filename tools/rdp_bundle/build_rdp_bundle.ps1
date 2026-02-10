[CmdletBinding()]
param(
    [string]$BundleName = 'EOMHub_RDP_Server',
    [int]$Port = 8090,
    [string]$ServerIp = '10.10.8.190',
    [switch]$RebuildEOMHub,
    [switch]$SkipFrontend,
    [switch]$KeepStaging
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $repoRoot
Set-Location $repoRoot

$eomHubDir = Join-Path $repoRoot 'EOMHub'
$eomHubExe = Join-Path $eomHubDir 'dist\EOMHub.exe'

if ($RebuildEOMHub) {
    Write-Host 'Building EOMHub.exe...' -ForegroundColor Yellow
    $buildArgs = @()
    if ($SkipFrontend) { $buildArgs += '-SkipFrontend' }
    & (Join-Path $eomHubDir 'build.ps1') @buildArgs
}

if (-not (Test-Path $eomHubExe)) {
    throw "EOMHub.exe not found: $eomHubExe. Build it first or pass -RebuildEOMHub."
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$distRoot = Join-Path $repoRoot 'dist\rdp_bundle'
$bundleDir = Join-Path $distRoot ("{0}_{1}" -f $BundleName, $stamp)
$stagingDir = Join-Path $bundleDir 'payload'

if (Test-Path $bundleDir) {
    Remove-Item -Recurse -Force $bundleDir
}

New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null

$payloadSrc = Join-Path $repoRoot 'tools\rdp_bundle\payload'
if (-not (Test-Path $payloadSrc)) {
    throw "Payload directory not found: $payloadSrc"
}

Copy-Item -Path (Join-Path $payloadSrc '*') -Destination $stagingDir -Recurse -Force
Copy-Item -Path $eomHubExe -Destination (Join-Path $stagingDir 'EOMHub.exe') -Force

Set-Content -Path (Join-Path $stagingDir 'port.txt') -Value $Port -Encoding ASCII
Set-Content -Path (Join-Path $stagingDir 'server_ip.txt') -Value $ServerIp -Encoding ASCII

$readmePath = Join-Path $bundleDir 'README_RDP.txt'
$readme = @(
    'EOMHub RDP Server Bundle',
    '',
    '1) Copy this folder or zip to RDP host.',
    '2) Extract archive.',
    '3) Run payload\INSTALL.cmd as Administrator (or double-click).',
    '',
    ('After install open: http://{0}:{1}' -f $ServerIp, $Port),
    '',
    'Files:',
    ' - payload\INSTALL.cmd : full one-click install',
    ' - payload\start_eomhub.cmd : manual start',
    ' - payload\stop_eomhub.cmd : manual stop',
    ' - payload\uninstall_rdp.ps1 : remove task/firewall/portproxy',
    '',
    'Notes:',
    ' - Bundle is self-contained (uses EOMHub.exe).',
    ' - No Python/Node installation required on RDP host.',
    ' - Installer configures firewall and netsh portproxy for external browser access.'
)
$readme | Set-Content -Path $readmePath -Encoding UTF8

$zipPath = "{0}.zip" -f $bundleDir
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Compress-Archive -Path (Join-Path $bundleDir '*') -DestinationPath $zipPath -Force

if (-not $KeepStaging) {
    Remove-Item -Recurse -Force $bundleDir
}

Write-Host '=====================================' -ForegroundColor Cyan
Write-Host 'RDP bundle created:' -ForegroundColor Green
Write-Host "  $zipPath" -ForegroundColor White
Write-Host '=====================================' -ForegroundColor Cyan

