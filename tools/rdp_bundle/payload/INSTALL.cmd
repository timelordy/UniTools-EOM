@echo off
setlocal EnableExtensions

cd /d "%~dp0"

REM One-click installer for RDP host.
REM - Adds firewall rule
REM - Adds portproxy (listen 0.0.0.0:<port> -> 127.0.0.1:<port>)
REM - Creates scheduled task to auto-start EOMHub on logon
REM - Starts EOMHub now

set "PORT=8090"
if exist "port.txt" (
  set /p PORT=<port.txt
)

set "SERVER_IP=10.10.8.190"
if exist "server_ip.txt" (
  set /p SERVER_IP=<server_ip.txt
)

echo =====================================
echo  EOMHub RDP Server Install
echo  Port: %PORT%
echo =====================================

REM Ensure admin
net session >nul 2>&1
if not %ERRORLEVEL%==0 (
  echo ERROR: Run as Administrator.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0\install_rdp.ps1" -Port %PORT% -ServerIp "%SERVER_IP%"
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo Install failed with exit code %EC%
  pause
  exit /b %EC%
)

echo.
echo OK. Open in browser: http://%SERVER_IP%:%PORT%
echo.
pause
endlocal
