@echo off
setlocal

set SCRIPT_DIR=%~dp0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install.ps1" -Silent

set "EC=%ERRORLEVEL%"
endlocal
exit /b %EC%
