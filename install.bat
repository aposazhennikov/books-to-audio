@echo off
setlocal

cd /d "%~dp0"

set "USE_EXISTING_VENV=1"
for %%A in (%*) do (
    if "%%~A"=="--recreate" set "USE_EXISTING_VENV="
)

if defined USE_EXISTING_VENV if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" install.py %*
    exit /b %errorlevel%
)

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
    py -3 install.py %*
    exit /b %errorlevel%
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 (
    python install.py %*
    exit /b %errorlevel%
)

echo Python 3.10 or newer was not found.
echo Install Python from https://www.python.org/downloads/ and enable "Add python.exe to PATH".
exit /b 1
