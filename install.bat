@echo off
setlocal

cd /d "%~dp0"

set "VENV_DIR=.venv-windows"
set "VENV_ARGS=--venv %VENV_DIR%"
set "USE_EXISTING_VENV=1"
for %%A in (%*) do (
    if "%%~A"=="--recreate" set "USE_EXISTING_VENV="
    if /i "%%~A"=="--venv" set "VENV_ARGS="
)

if defined USE_EXISTING_VENV if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" install.py %VENV_ARGS% %*
    set "EXIT_CODE=%errorlevel%"
    goto done
)

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
    py -3 install.py %VENV_ARGS% %*
    set "EXIT_CODE=%errorlevel%"
    goto done
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
    python install.py %VENV_ARGS% %*
    set "EXIT_CODE=%errorlevel%"
    goto done
)

echo Python 3.10 or newer was not found on Windows.
echo The Windows launcher may be pointing to a missing Python installation.
echo Install Python 3.12 for Windows and enable "Add python.exe to PATH":
echo   https://www.python.org/downloads/
echo.
echo Or run:
echo   winget install -e --id Python.Python.3.12 --scope user
echo.
echo After installation, close this window and run install.bat again.
set "EXIT_CODE=1"

:done
if not defined BOOKS_TO_AUDIO_FROM_RUN_GUI (
    echo.
    echo Press any key to exit terminal...
    echo Нажмите любую кнопку для выхода из терминала...
    pause >nul
)
exit /b %EXIT_CODE%
