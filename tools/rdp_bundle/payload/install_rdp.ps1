[CmdletBinding()]
param(
    [int]$Port = 8090,
    [string]$ServerIp = '10.10.8.190',
    [string]$TaskName = 'EOMHubServer',
    [string]$FirewallRuleName = 'EOMHub Server',
    [string]$ListenAddress = '',
    [string]$ConnectAddress = '127.0.0.1'
)

$ErrorActionPreference = 'Stop'

function Assert-Admin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Administrator privileges required.'
    }
}

Assert-Admin

if (-not $ListenAddress) {
    # IMPORTANT: do not use 0.0.0.0 here, otherwise the portproxy listener
    # will also grab 127.0.0.1:<Port> and EOMHub won't be able to bind.
    $ListenAddress = $ServerIp
}

$payloadDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $payloadDir 'EOMHub.exe'
$startCmd = Join-Path $payloadDir 'start_eomhub.cmd'
$activePortFile = Join-Path $payloadDir 'active_port.txt'

if (-not (Test-Path $exePath)) {
    throw "EOMHub.exe not found next to installer: $exePath"
}

Write-Host "Installing EOMHub RDP server..." -ForegroundColor Cyan
Write-Host "  Payload: $payloadDir" -ForegroundColor Gray
Write-Host "  Preferred port: $Port" -ForegroundColor Gray

# 1) Scheduled task (auto-start on logon)
Write-Host "Creating Scheduled Task: $TaskName" -ForegroundColor Yellow
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
} catch {
    # ignore
}

$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ("/c \"{0}\"" -f $startCmd)
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Run with highest privileges under current user (typical for RDP admin user)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType InteractiveToken -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null

# 2) Start now (it will auto-pick internal free port and write active_port.txt)
Write-Host 'Starting EOMHub...' -ForegroundColor Yellow
& $startCmd

Start-Sleep -Seconds 1

$activeInternalPort = $null
if (Test-Path $activePortFile) {
    try {
        $activeInternalPort = [int](Get-Content -Raw $activePortFile)
    } catch {
        $activeInternalPort = $null
    }
}

if (-not $activeInternalPort) {
    $activeInternalPort = 18090
}

# 3) Firewall rule on public browser port
try {
    $existing = Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Firewall rule already exists: $FirewallRuleName" -ForegroundColor Gray
    } else {
        New-NetFirewallRule -DisplayName $FirewallRuleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
        Write-Host "Firewall rule created: $FirewallRuleName" -ForegroundColor Green
    }
} catch {
    Write-Host "WARNING: Failed to configure firewall rule. Error: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 4) Port proxy (listen public port -> localhost internal active port)
Write-Host "Configuring portproxy: $ListenAddress:$Port -> $ConnectAddress:$activeInternalPort" -ForegroundColor Yellow
& netsh interface portproxy delete v4tov4 listenport=$Port listenaddress=$ListenAddress | Out-Null
& netsh interface portproxy add v4tov4 listenport=$Port listenaddress=$ListenAddress connectport=$activeInternalPort connectaddress=$ConnectAddress | Out-Null

Write-Host 'Done.' -ForegroundColor Green
Write-Host ("Open: http://{0}:{1}" -f $ServerIp, $Port) -ForegroundColor Cyan
