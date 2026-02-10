[CmdletBinding()]
param(
    [int]$Port = 8090,
    [string]$TaskName = 'EOMHubServer',
    [string]$FirewallRuleName = 'EOMHub Server',
    [string]$ListenAddress = ''
)

$ErrorActionPreference = 'Stop'

$payloadDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$activePortFile = Join-Path $payloadDir 'active_port.txt'

if (Test-Path $activePortFile) {
    try {
        $Port = [int](Get-Content -Raw $activePortFile)
    } catch {
        # ignore
    }
}

if (-not $ListenAddress) {
    # Default: try to remove mapping created by installer (server_ip.txt), fallback to 10.10.8.190.
    $serverIpFile = Join-Path $payloadDir 'server_ip.txt'
    if (Test-Path $serverIpFile) {
        try {
            $ListenAddress = (Get-Content -Raw $serverIpFile).Trim()
        } catch {
            $ListenAddress = ''
        }
    }
    if (-not $ListenAddress) {
        $ListenAddress = '10.10.8.190'
    }
}

Write-Host 'Stopping EOMHub...' -ForegroundColor Yellow
Get-Process EOMHub -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host 'Removing scheduled task...' -ForegroundColor Yellow
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null

Write-Host 'Removing firewall rule...' -ForegroundColor Yellow
Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue

Write-Host 'Removing portproxy rule...' -ForegroundColor Yellow
& netsh interface portproxy delete v4tov4 listenport=$Port listenaddress=$ListenAddress | Out-Null

Write-Host 'Uninstall completed.' -ForegroundColor Green
