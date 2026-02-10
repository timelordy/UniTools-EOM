@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "PUBLIC_PORT=8090"
if exist "port.txt" (
  set /p PUBLIC_PORT=<port.txt
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0\start_eomhub.ps1" -PublicPort %PUBLIC_PORT% -BindHost 127.0.0.1

endlocal
