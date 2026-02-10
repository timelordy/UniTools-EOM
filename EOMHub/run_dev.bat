@echo off
setlocal EnableExtensions
echo Starting EOM Hub in development mode...
cd /d "%~dp0"

set "PY_CMD="
set "PY_DESC="

call :try_python "C:\Program Files\pyRevit-Master\bin\python.exe" "pyRevit Python"
call :try_python "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "Python 3.13 (LocalAppData)"
call :try_python "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "Python 3.12 (LocalAppData)"
call :try_python "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "Python 3.11 (LocalAppData)"
call :try_python "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" "Python 3.10 (LocalAppData)"
call :try_python "%ProgramFiles%\Python313\python.exe" "Python 3.13 (Program Files)"
call :try_python "%ProgramFiles%\Python312\python.exe" "Python 3.12 (Program Files)"
call :try_python "%ProgramFiles%\Python311\python.exe" "Python 3.11 (Program Files)"
call :try_python "%ProgramFiles%\Python310\python.exe" "Python 3.10 (Program Files)"

if not defined PY_CMD (
    python --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PY_CMD=python"
        set "PY_DESC=python (PATH)"
    )
)

if not defined PY_CMD (
    py --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PY_CMD=py"
        set "PY_DESC=py launcher"
    )
)

if not defined PY_CMD (
    echo ERROR: Python not found!
    echo Установите Python 3.10+ или обновите run_dev.bat с корректным путем.
    goto :end
)

echo Using %PY_DESC%...
"%PY_CMD%" -m src.app --dev
goto :end

:try_python
if defined PY_CMD goto :eof
set "CANDIDATE=%~1"
if exist "%CANDIDATE%" (
    set "PY_CMD=%CANDIDATE%"
    set "PY_DESC=%~2"
)
goto :eof

:end
echo.
pause
endlocal
