[CmdletBinding()]
param(
    [switch]$Silent
)

$ErrorActionPreference = 'Stop'

function Test-PyRevitInstalled {
    if (Test-Path (Join-Path $env:APPDATA 'pyRevit')) {
        return $true
    }

    try {
        $cmd = Get-Command pyrevit.exe -ErrorAction Stop
        if ($cmd -and (Test-Path $cmd.Source)) {
            return $true
        }
    } catch {
        # ignore
    }

    return $false
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

    $args = @()
    if ($Silent) {
        # We don't know which installer tech is used (NSIS/Inno/etc). Try common flags.
        $args = @('/S', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
    }

    $p = Start-Process -FilePath $InstallerPath -ArgumentList $args -Wait -PassThru
    Write-Host ("pyRevit installer exited with code: {0}" -f $p.ExitCode) -ForegroundColor Gray
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
}

function Try-AttachPyRevit {
    param(
        [string]$CloneName = 'EOM-pyRevit'
    )

    $pyrevitCmd = $null
    try {
        $pyrevitCmd = Get-Command pyrevit.exe -ErrorAction Stop
    } catch {
        return
    }

    try {
        & $pyrevitCmd.Source clones add this $CloneName --force | Out-Null
    } catch {
        # ignore
    }

    try {
        & $pyrevitCmd.Source attach $CloneName default --installed | Out-Null
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
        throw 'pyRevit still not detected after installer run. Please rerun installer after completing pyRevit setup.'
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
