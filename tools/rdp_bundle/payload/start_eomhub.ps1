[CmdletBinding()]
param(
    # Public port that users will access in browser (portproxy listen port).
    [int]$PublicPort = 8090,
    # Internal port that EOMHub will bind to on localhost.
    [int]$StartPort = 18090,
    [int]$MaxAttempts = 50,
    [string]$BindHost = '127.0.0.1',
    [string]$ListenAddress = '0.0.0.0'
)

$ErrorActionPreference = 'Stop'

$payloadDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $payloadDir 'EOMHub.exe'

if (-not (Test-Path $exePath)) {
    throw "EOMHub.exe not found: $exePath"
}

function Test-PortFree {
    param(
        [string]$BindHost,
        [int]$Port
    )

    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse($BindHost), $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

$portFile = Join-Path $payloadDir 'active_port.txt'

$port = $null
if (Test-Path $portFile) {
    try {
        $existing = [int](Get-Content -Raw $portFile)
        if (Test-PortFree -BindHost $BindHost -Port $existing) {
            $port = $existing
        }
    } catch {
        # ignore
    }
}

if (-not $port) {
    $port = $StartPort
}

for ($i = 0; $i -lt $MaxAttempts; $i++) {
    if (Test-PortFree -BindHost $BindHost -Port $port) {
        break
    }
    $port++
}

if (-not (Test-PortFree -BindHost $BindHost -Port $port)) {
    throw "Could not find a free port in range ${StartPort}..$($StartPort + $MaxAttempts - 1)"
}

Set-Content -Path $portFile -Value $port -Encoding ASCII

# Best-effort stop existing hub
Get-Process EOMHub -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 250

$env:EOM_HUB_HEADLESS = '1'

$args = @('--headless', '--host', $BindHost, '--port', $port)
Start-Process -FilePath $exePath -ArgumentList $args -WorkingDirectory $payloadDir -WindowStyle Hidden | Out-Null

try {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        & netsh interface portproxy delete v4tov4 listenport=$PublicPort listenaddress=$ListenAddress | Out-Null
        & netsh interface portproxy add v4tov4 listenport=$PublicPort listenaddress=$ListenAddress connectport=$port connectaddress=$BindHost | Out-Null
        Write-Output "Portproxy configured: ${ListenAddress}:${PublicPort} -> ${BindHost}:${port}"
    } else {
        Write-Output 'WARNING: not running as admin; portproxy not configured.'
    }
} catch {
    Write-Output "WARNING: failed to configure portproxy: $($_.Exception.Message)"
}

Write-Output "EOMHub started (internal): http://${BindHost}:$port"
