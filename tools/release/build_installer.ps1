# Build an offline-ish Windows EXE installer for EOMTemplateTools.
#
# Output:
#   dist/release/<Version>/UniTools - EOM Setup <Version>.exe
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

function Set-ExecutableIconFromIco {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExePath,
        [Parameter(Mandatory = $true)]
        [string]$IcoPath,
        [UInt16]$GroupIconId = 1,
        [UInt16]$LanguageId = 0
    )

    if (-not (Test-Path $ExePath)) {
        throw "Executable not found: $ExePath"
    }
    if (-not (Test-Path $IcoPath)) {
        throw "ICO file not found: $IcoPath"
    }

    if (-not ('Win32IconResourceUpdater' -as [type])) {
        Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class Win32IconResourceUpdater {
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern IntPtr BeginUpdateResource(string pFileName, bool bDeleteExistingResources);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool UpdateResource(
        IntPtr hUpdate,
        IntPtr lpType,
        IntPtr lpName,
        ushort wLanguage,
        byte[] lpData,
        uint cbData
    );

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool EndUpdateResource(IntPtr hUpdate, bool fDiscard);
}
"@ -Language CSharp
    }

    $icoBytes = [System.IO.File]::ReadAllBytes($IcoPath)
    $icoStream = New-Object System.IO.MemoryStream(, $icoBytes)
    $reader = New-Object System.IO.BinaryReader($icoStream)

    $reserved = $reader.ReadUInt16()
    $icoType = $reader.ReadUInt16()
    $count = $reader.ReadUInt16()

    if ($reserved -ne 0 -or $icoType -ne 1 -or $count -le 0) {
        throw "Invalid ICO format: $IcoPath"
    }

    $entries = @()
    for ($i = 0; $i -lt $count; $i++) {
        $entries += [PSCustomObject]@{
            Width = $reader.ReadByte()
            Height = $reader.ReadByte()
            ColorCount = $reader.ReadByte()
            Reserved = $reader.ReadByte()
            Planes = $reader.ReadUInt16()
            BitCount = $reader.ReadUInt16()
            BytesInRes = $reader.ReadUInt32()
            ImageOffset = $reader.ReadUInt32()
            IconId = [UInt16]($i + 1)
        }
    }

    $hUpdate = [Win32IconResourceUpdater]::BeginUpdateResource($ExePath, $false)
    if ($hUpdate -eq [IntPtr]::Zero) {
        $code = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        throw "BeginUpdateResource failed (Win32=$code): $ExePath"
    }

    $success = $false
    try {
        foreach ($entry in $entries) {
            $icoStream.Position = $entry.ImageOffset
            $imgBytes = $reader.ReadBytes([int]$entry.BytesInRes)
            $ok = [Win32IconResourceUpdater]::UpdateResource(
                $hUpdate,
                [IntPtr]3,                # RT_ICON
                [IntPtr]([int]$entry.IconId),
                $LanguageId,
                $imgBytes,
                [uint32]$imgBytes.Length
            )
            if (-not $ok) {
                $code = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
                throw "UpdateResource(RT_ICON) failed (Win32=$code, id=$($entry.IconId))"
            }
        }

        $groupStream = New-Object System.IO.MemoryStream
        $groupWriter = New-Object System.IO.BinaryWriter($groupStream)
        $groupWriter.Write([UInt16]0)           # Reserved
        $groupWriter.Write([UInt16]1)           # Type (icon)
        $groupWriter.Write([UInt16]$count)      # Count
        foreach ($entry in $entries) {
            $groupWriter.Write([byte]$entry.Width)
            $groupWriter.Write([byte]$entry.Height)
            $groupWriter.Write([byte]$entry.ColorCount)
            $groupWriter.Write([byte]$entry.Reserved)
            $groupWriter.Write([UInt16]$entry.Planes)
            $groupWriter.Write([UInt16]$entry.BitCount)
            $groupWriter.Write([UInt32]$entry.BytesInRes)
            $groupWriter.Write([UInt16]$entry.IconId)  # Resource ID in RT_ICON
        }

        $groupBytes = $groupStream.ToArray()
        $okGroup = [Win32IconResourceUpdater]::UpdateResource(
            $hUpdate,
            [IntPtr]14,               # RT_GROUP_ICON
            [IntPtr]([int]$GroupIconId),
            $LanguageId,
            $groupBytes,
            [uint32]$groupBytes.Length
        )
        if (-not $okGroup) {
            $code = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
            throw "UpdateResource(RT_GROUP_ICON) failed (Win32=$code, id=$GroupIconId)"
        }

        $success = $true
    }
    finally {
        try {
            [void][Win32IconResourceUpdater]::EndUpdateResource($hUpdate, (-not $success))
        } finally {
            try { $reader.Close() } catch {}
            try { $icoStream.Close() } catch {}
        }
    }
}

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
    $api = 'https://api.github.com/repos/pyrevitlabs/pyRevit/releases/latest'
    $headers = @{ 'User-Agent' = 'EOMTemplateTools-ReleaseScript' }
    $release = Invoke-RestMethod -Uri $api -Headers $headers

    if (-not $release.assets) {
        throw 'pyRevit GitHub release has no assets'
    }

    $exeAssets = @($release.assets | Where-Object { $_.name -match '\.exe$' })
    if ($exeAssets.Count -eq 0) {
        throw 'pyRevit latest release has no .exe assets'
    }

    # Never pick admin installers: target is per-user setup without elevation.
    $nonAdmin = @(
        $exeAssets | Where-Object { $_.name -notmatch '(?i)admin' }
    )
    if ($nonAdmin.Count -eq 0) {
        throw 'pyRevit latest release has only admin installers; cannot build non-admin package'
    }

    # Prefer full pyRevit installer (not CLI-only), then fallback to any non-admin exe.
    $preferred = @(
        $nonAdmin | Where-Object { $_.name -match '(?i)^pyrevit_(?!cli_).+\.exe$' }
    )
    if ($preferred.Count -eq 0) {
        $preferred = @(
            $nonAdmin | Where-Object { $_.name -notmatch '(?i)cli' }
        )
    }
    if ($preferred.Count -eq 0) {
        $preferred = $nonAdmin
    }

    $selected = $preferred | Sort-Object size -Descending | Select-Object -First 1
    Write-Host ("Selected pyRevit installer asset: {0}" -f $selected.name) -ForegroundColor Gray
    return $selected.browser_download_url
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

$installerExe = Join-Path $releaseDir ("UniTools - EOM Setup {0}.exe" -f $Version)
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
$sed += ('FriendlyName=UniTools - EOM Installer {0}' -f $Version)
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

$hubInstallerIcon = Join-Path $repoRoot 'EOMHub\web\icons\icon.ico'
if (Test-Path $hubInstallerIcon) {
    Write-Host "Applying Hub icon to installer..." -ForegroundColor Yellow
    try {
        Set-ExecutableIconFromIco -ExePath $installerExe -IcoPath $hubInstallerIcon
        Write-Host "Installer icon updated from: $hubInstallerIcon" -ForegroundColor Green
    } catch {
        Write-Host "WARNING: Failed to apply installer icon: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "WARNING: Hub icon not found, skipping installer icon patch: $hubInstallerIcon" -ForegroundColor Yellow
}

Write-Host '=====================================' -ForegroundColor Cyan
Write-Host 'Release artifacts:' -ForegroundColor Green
Write-Host "  Installer: $installerExe" -ForegroundColor White
Write-Host "  Extension zip: $extZip" -ForegroundColor White
Write-Host "  pyRevit setup: $pyRevitOut" -ForegroundColor White
Write-Host '=====================================' -ForegroundColor Cyan
