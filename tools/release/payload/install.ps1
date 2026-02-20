[CmdletBinding()]
param(
    [switch]$Silent
)

$ErrorActionPreference = 'Stop'

function Get-PyRevitCliPath {
    try {
        $cmd = Get-Command pyrevit.exe -ErrorAction Stop
        if ($cmd -and (Test-Path $cmd.Source)) {
            return $cmd.Source
        }
    } catch {
        # ignore
    }

    $candidates = @(
        (Join-Path $env:APPDATA 'pyRevit-Master\bin\pyrevit.exe'),
        (Join-Path $env:LOCALAPPDATA 'pyRevit-Master\bin\pyrevit.exe'),
        (Join-Path $env:APPDATA 'pyRevit\bin\pyrevit.exe'),
        (Join-Path $env:LOCALAPPDATA 'pyRevit\bin\pyrevit.exe')
    )

    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) {
            return $path
        }
    }

    return $null
}

function Test-PyRevitInstalled {
    $markers = @(
        (Join-Path $env:APPDATA 'pyRevit'),
        (Join-Path $env:APPDATA 'pyRevit-Master'),
        (Join-Path $env:LOCALAPPDATA 'pyRevit-Master')
    )

    foreach ($marker in $markers) {
        if ($marker -and (Test-Path $marker)) {
            return $true
        }
    }

    if (Get-PyRevitCliPath) {
        return $true
    }

    return $false
}

function Invoke-InstallerAttempt {
    param(
        [string]$InstallerPath,
        [string[]]$Arguments
    )

    $argText = '<none>'
    if ($Arguments -and $Arguments.Count -gt 0) {
        $argText = ($Arguments -join ' ')
    }
    Write-Host ("Running installer with args: {0}" -f $argText) -ForegroundColor Gray

    if ($Arguments -and $Arguments.Count -gt 0) {
        $p = Start-Process -FilePath $InstallerPath -ArgumentList $Arguments -Wait -PassThru
    } else {
        $p = Start-Process -FilePath $InstallerPath -Wait -PassThru
    }

    Write-Host ("Installer exit code: {0}" -f $p.ExitCode) -ForegroundColor Gray
    return [int]$p.ExitCode
}

function Install-PyRevit {
    param(
        [string]$InstallerPath,
        [switch]$Silent
    )

    if (-not (Test-Path $InstallerPath)) {
        throw "pyRevit installer not found: $InstallerPath"
    }

    Write-Host 'pyRevit is not installed. Starting installer...' -ForegroundColor Yellow

    $successCodes = @(0, 1641, 3010)

    if ($Silent) {
        # Enforce per-user install to avoid any elevation/UAC path.
        $silentAttempts = @(
            @('/SP-', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER'),
            @('/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER'),
            @('/S', '/CURRENTUSER'),
            @('/SP-', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/ALLUSERS=0'),
            @('/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/ALLUSERS=0'),
            @('/S', '/ALLUSERS=0')
        )

        foreach ($attempt in $silentAttempts) {
            $exitCode = Invoke-InstallerAttempt -InstallerPath $InstallerPath -Arguments $attempt

            Start-Sleep -Seconds 2
            if (Test-PyRevitInstalled) {
                return
            }

            if ($exitCode -eq 740) {
                throw 'pyRevit installer requested elevation (UAC). Only per-user non-admin install is allowed.'
            }

            if ($successCodes -contains $exitCode) {
                continue
            }
        }

        Write-Host 'Silent per-user install did not finish. Falling back to interactive per-user mode...' -ForegroundColor Yellow
    }

    $interactiveAttempts = @(
        @('/CURRENTUSER'),
        @('/ALLUSERS=0')
    )

    foreach ($attempt in $interactiveAttempts) {
        $exitCode = Invoke-InstallerAttempt -InstallerPath $InstallerPath -Arguments $attempt
        Start-Sleep -Seconds 2

        if (Test-PyRevitInstalled) {
            return
        }

        if ($exitCode -eq 740) {
            throw 'pyRevit installer requested elevation (UAC). Per-user mode failed; admin install is intentionally blocked.'
        }
    }

    throw 'pyRevit still not detected after per-user install attempts. Admin install is disabled by policy.'
}

function Install-Extension {
    param(
        [string]$ExtensionZip
    )

    if (-not (Test-Path $ExtensionZip)) {
        throw "Extension zip not found: $ExtensionZip"
    }

    $extensionsRoot = Join-Path $env:APPDATA 'pyRevit\Extensions'
    $destExt = Join-Path $extensionsRoot 'EOMTemplateTools.extension'

    New-Item -ItemType Directory -Path $extensionsRoot -Force | Out-Null

    if (Test-Path $destExt) {
        Remove-Item -Recurse -Force $destExt
    }

    Write-Host "Installing extension into: $extensionsRoot" -ForegroundColor Yellow
    Expand-Archive -Path $ExtensionZip -DestinationPath $extensionsRoot -Force

    if (-not (Test-Path $destExt)) {
        throw "Install failed: destination folder not found after extraction: $destExt"
    }

    Ensure-ExtensionIcons -ExtensionRoot $destExt
}

function Ensure-ExtensionIcons {
    param(
        [string]$ExtensionRoot
    )

    if (-not (Test-Path $ExtensionRoot)) {
        return
    }

    $fallbackCandidates = @(
        (Join-Path $ExtensionRoot 'EOM.tab\01_Хаб.panel\Hub.pushbutton\icon.png'),
        (Join-Path $ExtensionRoot 'EOM.tab\00_Хаб.panel\01_Хаб.pushbutton\icon.png')
    )

    $fallbackIcon = $null
    foreach ($candidate in $fallbackCandidates) {
        if ($candidate -and (Test-Path $candidate)) {
            $fallbackIcon = $candidate
            break
        }
    }

    if (-not $fallbackIcon) {
        Write-Host 'WARNING: fallback icon.png not found; missing plugin icons were not patched.' -ForegroundColor Yellow
        return
    }

    $pushbuttons = Get-ChildItem -Path $ExtensionRoot -Recurse -Directory -Filter '*.pushbutton'
    $patchedCount = 0

    foreach ($pushbutton in $pushbuttons) {
        $iconPng = Join-Path $pushbutton.FullName 'icon.png'
        if (-not (Test-Path $iconPng)) {
            Copy-Item -Path $fallbackIcon -Destination $iconPng -Force
            $patchedCount++
        }
    }

    if ($patchedCount -gt 0) {
        Write-Host ("Patched icon.png for {0} plugin(s)." -f $patchedCount) -ForegroundColor Yellow
    } else {
        Write-Host 'All plugins already have icon.png.' -ForegroundColor Gray
    }
}

function Try-AttachPyRevit {
    param(
        [string]$CloneName = 'EOM-pyRevit'
    )

    $pyrevitExe = Get-PyRevitCliPath
    if (-not $pyrevitExe) {
        return
    }

    try {
        & $pyrevitExe clones add this $CloneName --force | Out-Null
    } catch {
        # ignore
    }

    try {
        & $pyrevitExe attach $CloneName default --installed | Out-Null
    } catch {
        # ignore
    }
}

$payloadDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyRevitInstaller = Join-Path $payloadDir 'pyRevitSetup.exe'
$extensionZip = Join-Path $payloadDir 'EOMTemplateTools.extension.zip'

Write-Host '=====================================' -ForegroundColor Cyan
Write-Host 'EOMTemplateTools Installer' -ForegroundColor Green
Write-Host '=====================================' -ForegroundColor Cyan

if (-not (Test-PyRevitInstalled)) {
    Install-PyRevit -InstallerPath $pyRevitInstaller -Silent:$Silent

    if (-not (Test-PyRevitInstalled)) {
        throw 'pyRevit still not detected after installer run.'
    }
} else {
    Write-Host 'pyRevit detected.' -ForegroundColor Green
}

Install-Extension -ExtensionZip $extensionZip

Try-AttachPyRevit

Write-Host ''
Write-Host 'Done.' -ForegroundColor Green
Write-Host 'Next steps:' -ForegroundColor White
Write-Host '  1) Restart Revit (or pyRevit Reload).' -ForegroundColor White
Write-Host '  2) Open "EOM" tab in the ribbon.' -ForegroundColor White
