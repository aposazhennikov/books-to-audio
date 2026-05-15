@echo off
setlocal

cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"
set "PYTHON_CMD="

if not exist "%VENV_PY%" (
    call :find_python
    if errorlevel 1 goto no_python

    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto error
)

"%VENV_PY%" -c "import PyQt6, book_normalizer" >nul 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    "%VENV_PY%" -m pip install --upgrade pip
    if errorlevel 1 goto error

    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 goto error

    "%VENV_PY%" -m pip install -e .
    if errorlevel 1 goto error
)

echo Starting books-to-audio GUI...
"%VENV_PY%" -m book_normalizer.gui.app
if errorlevel 1 goto error

exit /b 0

:error
echo.
echo Failed to start the program. Check the messages above.
pause
exit /b 1

:no_python
echo.
echo Python 3.10 or newer was not found.
echo Install Python from https://www.python.org/downloads/ and enable "Add python.exe to PATH".
pause
exit /b 1

:find_python
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    exit /b 0
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    exit /b 0
)

exit /b 1
