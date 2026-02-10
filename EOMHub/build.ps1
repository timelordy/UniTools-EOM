# UniTools Hub Build Script
# Usage: .\build.ps1
# Prerequisites: Python 3.10+, Node.js 18+

param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$Dev,
    [string]$PythonPath
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "      UniTools Hub Build Script     " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Find Python
$pythonExe = $null

if ($PythonPath) {
    $pythonExe = $PythonPath
    if (-not (Test-Path $PythonPath)) {
        Write-Host "ERROR: Python path not found: $PythonPath" -ForegroundColor Red
        exit 1
    }
} else {
    # Try to find Python in common locations
    $pythonPaths = @(
        "python",
        "python3",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:PROGRAMFILES\Python310\python.exe",
        "$env:PROGRAMFILES\Python311\python.exe",
        "$env:PROGRAMFILES\Python312\python.exe",
        "$env:PROGRAMFILES\Python313\python.exe",
        "$env:APPDATA\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\python.exe"
    )

    foreach ($path in $pythonPaths) {
        try {
            $version = & $path --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                $pythonExe = $path
                Write-Host "Found Python: $pythonExe ($version)" -ForegroundColor Green
                break
            }
        } catch {
            # Continue searching
        }
    }

    if (-not $pythonExe) {
        Write-Host "ERROR: Python not found. Install Python 3.10+ or use -PythonPath parameter" -ForegroundColor Red
        exit 1
    }
}

# Check prerequisites for Node.js
function Test-Command($Command) {
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

if (-not (Test-Command "node")) {
    Write-Host "ERROR: Node.js not found. Install Node.js 18+" -ForegroundColor Red
    exit 1
}

# Step 1: Install Python dependencies
Write-Host "`n[1/4] Installing Python dependencies..." -ForegroundColor Yellow
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r requirements.txt
& $pythonExe -m pip install pyinstaller

# Step 2: Build Frontend
if (-not $SkipFrontend) {
    Write-Host "`n[2/4] Building frontend..." -ForegroundColor Yellow
    Set-Location frontend
    
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing npm packages..." -ForegroundColor Gray
        npm install
    }
    
    npm run build
    Set-Location ..
    
    if (-not (Test-Path "frontend/dist/index.html")) {
        Write-Host "ERROR: Frontend build failed - dist/index.html not found" -ForegroundColor Red
        exit 1
    }
    Write-Host "Frontend built successfully!" -ForegroundColor Green
} else {
    Write-Host "`n[2/4] Skipping frontend build" -ForegroundColor Gray
}

# Step 3: Build EXE
if (-not $SkipBackend) {
    Write-Host "`n[3/4] Building EOMHub.exe..." -ForegroundColor Yellow

    # Clean previous build
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

    # Run PyInstaller
    & $pythonExe -m PyInstaller EOMHub.spec --clean --noconfirm

    if (-not (Test-Path "dist/EOMHub.exe")) {
        Write-Host "ERROR: PyInstaller build failed - EOMHub.exe not found" -ForegroundColor Red
        exit 1
    }
    Write-Host "EOMHub.exe built successfully!" -ForegroundColor Green
} else {
    Write-Host "`n[3/4] Skipping backend build" -ForegroundColor Gray
}

# Step 4: Install canonical EXE and mirror to pyRevit extension
Write-Host "`n[4/4] Installing canonical EOMHub.exe..." -ForegroundColor Yellow

$canonicalExt = Join-Path $PSScriptRoot "..\EOMTemplateTools.extension\bin"
if (-not (Test-Path $canonicalExt)) {
    New-Item -ItemType Directory -Path $canonicalExt -Force | Out-Null
}
$canonicalExe = Join-Path $canonicalExt "EOMHub.exe"

$pyrevitExt = "$env:APPDATA\pyRevit\Extensions\EOMTemplateTools.extension\bin"
if (-not (Test-Path $pyrevitExt)) {
    New-Item -ItemType Directory -Path $pyrevitExt -Force | Out-Null
}

$pyrevitExe = Join-Path $pyrevitExt "EOMHub.exe"

# EOMHub.exe can be running (or held by Revit/WebView), locking the destination.
# Stop it and retry copy once.
try {
    Get-Process EOMHub -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
} catch {
    # ignore
}

try {
    Copy-Item "dist/EOMHub.exe" $canonicalExe -Force -ErrorAction Stop
    Write-Host "Canonical copy updated: $canonicalExe" -ForegroundColor Green

    $mirrorNeeded = $true
    if (Test-Path $pyrevitExe) {
        try {
            $canonicalHash = (Get-FileHash $canonicalExe -Algorithm SHA256).Hash
            $pyrevitHash = (Get-FileHash $pyrevitExe -Algorithm SHA256).Hash
            if ($canonicalHash -eq $pyrevitHash) {
                $mirrorNeeded = $false
            }
        } catch {
            $mirrorNeeded = $true
        }
    }

    if ($mirrorNeeded) {
        Copy-Item $canonicalExe $pyrevitExe -Force -ErrorAction Stop
        Write-Host "Mirrored to: $pyrevitExe" -ForegroundColor Green
    } else {
        Write-Host "Mirror is up to date: $pyrevitExe" -ForegroundColor Gray
    }
} catch {
    Write-Host "WARNING: Failed to install/mirror EOMHub.exe (file may be locked)." -ForegroundColor Yellow
    Write-Host "Close Revit / stop EOMHub.exe and rerun build.ps1." -ForegroundColor Yellow
}

# Summary
Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "        Build Complete!              " -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Output: dist/EOMHub.exe" -ForegroundColor White
Write-Host "Canonical install: $canonicalExt" -ForegroundColor White
Write-Host "Mirror install: $pyrevitExt" -ForegroundColor White

if ($Dev) {
    Write-Host "`nStarting in dev mode..." -ForegroundColor Yellow
    & $pythonExe -m src.app --dev
}
