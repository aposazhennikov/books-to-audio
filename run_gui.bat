@echo off
setlocal

cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    call install.bat --no-system-check
    if errorlevel 1 goto error
)

"%VENV_PY%" -c "import PyQt6, book_normalizer" >nul 2>nul
if errorlevel 1 (
    call install.bat --no-system-check
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
