# Build an offline-ish Windows EXE installer for EOMTemplateTools.
#
# Output:
#   dist/release/<Version>/EOMTemplateTools_Setup_<Version>.exe
#   dist/release/<Version>/EOMTemplateTools.extension.zip
#   dist/release/<Version>/pyRevitSetup.exe

[CmdletBinding()]
param(
    [string]$Version,
    [switch]$BuildEOMHub,
    [switch]$SkipFrontend,
    [string]$PyRevitInstallerPath,
    [string]$PyRevitInstallerUrl
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $repoRoot
Set-Location $repoRoot

function Get-ProjectVersion {
    param([string]$PyProjectPath)

    if (-not (Test-Path $PyProjectPath)) {
        throw "pyproject.toml not found: $PyProjectPath"
    }

    $content = Get-Content -Raw $PyProjectPath
    $match = [regex]::Match($content, '(?m)^\s*version\s*=\s*"(?<v>[^"]+)"\s*$')
    if (-not $match.Success) {
        throw "Could not parse version from $PyProjectPath"
    }
    return $match.Groups['v'].Value
}

function Get-LatestPyRevitInstallerUrl {
    $api = 'https://api.github.com/repos/eirannejad/pyRevit/releases/latest'
    $headers = @{ 'User-Agent' = 'EOMTemplateTools-ReleaseScript' }
    $release = Invoke-RestMethod -Uri $api -Headers $headers

    if (-not $release.assets) {
        throw 'pyRevit GitHub release has no assets'
    }

    $exeAssets = @($release.assets | Where-Object { $_.name -match '\.exe$' })
    if ($exeAssets.Count -eq 0) {
        throw 'pyRevit latest release has no .exe assets'
    }

    # Prefer typical installer naming, otherwise pick the largest .exe.
    $preferred = @(
        $exeAssets | Where-Object { $_.name -match 'setup|installer|install' }
    )
    if ($preferred.Count -gt 0) {
        return ($preferred | Sort-Object size -Descending | Select-Object -First 1).browser_download_url
    }

    return ($exeAssets | Sort-Object size -Descending | Select-Object -First 1).browser_download_url
}

if (-not $Version) {
    $Version = Get-ProjectVersion -PyProjectPath (Join-Path $repoRoot 'pyproject.toml')
}

$distRoot = Join-Path $repoRoot 'dist'
$releaseDir = Join-Path $distRoot (Join-Path 'release' $Version)
$stagingDir = Join-Path $distRoot (Join-Path 'installer_staging' $Version)
$payloadDir = Join-Path $stagingDir 'payload'

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
if (Test-Path $stagingDir) {
    Remove-Item -Recurse -Force $stagingDir
}
New-Item -ItemType Directory -Path $payloadDir -Force | Out-Null

if ($BuildEOMHub) {
    Write-Host "Building EOMHub.exe..." -ForegroundColor Yellow
    $buildArgs = @()
    if ($SkipFrontend) { $buildArgs += '-SkipFrontend' }
    & (Join-Path $repoRoot 'EOMHub\build.ps1') @buildArgs
}

$extZip = Join-Path $releaseDir 'EOMTemplateTools.extension.zip'
Write-Host "Creating extension archive: $extZip" -ForegroundColor Yellow
if (Test-Path $extZip) { Remove-Item -Force $extZip }

# Zip the whole folder to preserve unicode paths inside.
Compress-Archive -Path (Join-Path $repoRoot 'EOMTemplateTools.extension') -DestinationPath $extZip -Force

$pyRevitOut = Join-Path $releaseDir 'pyRevitSetup.exe'

if ($PyRevitInstallerPath) {
    if (-not (Test-Path $PyRevitInstallerPath)) {
        throw "PyRevitInstallerPath not found: $PyRevitInstallerPath"
    }
    Copy-Item -Path $PyRevitInstallerPath -Destination $pyRevitOut -Force
} else {
    if (-not (Test-Path $pyRevitOut)) {
        if (-not $PyRevitInstallerUrl) {
            $PyRevitInstallerUrl = Get-LatestPyRevitInstallerUrl
        }

        Write-Host "Downloading pyRevit installer..." -ForegroundColor Yellow
        Write-Host "  $PyRevitInstallerUrl" -ForegroundColor Gray
        Invoke-WebRequest -Uri $PyRevitInstallerUrl -OutFile $pyRevitOut
    } else {
        Write-Host "Reusing existing pyRevit installer: $pyRevitOut" -ForegroundColor Gray
    }
}

# Stage payload
Copy-Item -Path (Join-Path $repoRoot 'tools\release\payload\install.ps1') -Destination (Join-Path $payloadDir 'install.ps1') -Force
Copy-Item -Path (Join-Path $repoRoot 'tools\release\payload\install.cmd') -Destination (Join-Path $payloadDir 'install.cmd') -Force
Copy-Item -Path $extZip -Destination (Join-Path $payloadDir 'EOMTemplateTools.extension.zip') -Force
Copy-Item -Path $pyRevitOut -Destination (Join-Path $payloadDir 'pyRevitSetup.exe') -Force

$installerExe = Join-Path $releaseDir ("EOMTemplateTools_Setup_{0}.exe" -f $Version)
$sedPath = Join-Path $stagingDir 'installer.sed'

$sed = @()
$sed += '[Version]'
$sed += 'Class=IEXPRESS'
$sed += 'SEDVersion=3'
$sed += '[Options]'
$sed += 'PackagePurpose=InstallApp'
$sed += 'ShowInstallProgramWindow=0'
$sed += 'HideExtractAnimation=1'
$sed += 'UseLongFileName=1'
$sed += 'InsideCompressed=1'
$sed += 'CAB_FixedSize=0'
$sed += 'CAB_ResvCodeSigning=0'
$sed += 'RebootMode=N'
$sed += 'InstallPrompt=%InstallPrompt%'
$sed += 'DisplayLicense=%DisplayLicense%'
$sed += 'FinishMessage=%FinishMessage%'
$sed += 'TargetName=%TargetName%'
$sed += 'FriendlyName=%FriendlyName%'
$sed += 'AppLaunched=%AppLaunched%'
$sed += 'PostInstallCmd=%PostInstallCmd%'
$sed += 'AdminQuietInstCmd=%AdminQuietInstCmd%'
$sed += 'UserQuietInstCmd=%UserQuietInstCmd%'
$sed += 'SourceFiles=SourceFiles'
$sed += '[Strings]'
$sed += 'InstallPrompt='
$sed += 'DisplayLicense='
$sed += 'FinishMessage='
$sed += ('TargetName={0}' -f $installerExe)
$sed += ('FriendlyName=EOMTemplateTools Installer {0}' -f $Version)
$sed += 'AppLaunched=install.cmd'
$sed += 'PostInstallCmd=<None>'
$sed += 'AdminQuietInstCmd=install.cmd'
$sed += 'UserQuietInstCmd=install.cmd'
$sed += 'FILE0=install.cmd'
$sed += 'FILE1=install.ps1'
$sed += 'FILE2=EOMTemplateTools.extension.zip'
$sed += 'FILE3=pyRevitSetup.exe'
$sed += '[SourceFiles]'
$sed += ('SourceFiles0={0}' -f $payloadDir)
$sed += '[SourceFiles0]'
$sed += '%FILE0%='
$sed += '%FILE1%='
$sed += '%FILE2%='
$sed += '%FILE3%='

Set-Content -Path $sedPath -Value ($sed -join "`r`n") -Encoding ASCII

Write-Host "Building installer: $installerExe" -ForegroundColor Yellow
& "$env:SystemRoot\System32\iexpress.exe" /N /Q $sedPath
$iexpressExit = $LASTEXITCODE
Write-Host ("IExpress exit code: {0}" -f $iexpressExit) -ForegroundColor Gray

# IExpress sometimes returns before the target EXE is fully written.
$timeoutSeconds = 180
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while ($sw.Elapsed.TotalSeconds -lt $timeoutSeconds) {
    if (Test-Path $installerExe) {
        try {
            $size1 = (Get-Item $installerExe).Length
            Start-Sleep -Seconds 1
            $size2 = (Get-Item $installerExe).Length
            if ($size1 -eq $size2 -and $size2 -gt 0) {
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    } else {
        Start-Sleep -Seconds 1
    }
}

if (-not (Test-Path $installerExe)) {
    Write-Host 'IExpress did not produce the installer exe in time.' -ForegroundColor Red
    Write-Host 'Artifacts near releaseDir:' -ForegroundColor Yellow
    Get-ChildItem -Force $releaseDir | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize | Out-String | Write-Host
    throw "Installer build failed: $installerExe not found"
}

Write-Host '=====================================' -ForegroundColor Cyan
Write-Host 'Release artifacts:' -ForegroundColor Green
Write-Host "  Installer: $installerExe" -ForegroundColor White
Write-Host "  Extension zip: $extZip" -ForegroundColor White
Write-Host "  pyRevit setup: $pyRevitOut" -ForegroundColor White
Write-Host '=====================================' -ForegroundColor Cyan
