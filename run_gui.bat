@echo off
setlocal

cd /d "%~dp0"

set "VENV_PY=.venv-windows\Scripts\python.exe"

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import PyQt6, book_normalizer, huggingface_hub" >nul 2>nul
    if not errorlevel 1 goto launch_windows
)

set "BOOKS_TO_AUDIO_FROM_RUN_GUI=1"
call install.bat --no-system-check
if errorlevel 1 goto error

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import PyQt6, book_normalizer, huggingface_hub" >nul 2>nul
    if not errorlevel 1 goto launch_windows
)

echo GUI dependencies were not installed in Windows .venv-windows.
echo run_gui.bat only starts the native Windows GUI.
echo For Linux/WSL use run_gui.sh separately.
goto error

:launch_windows
echo Starting books-to-audio GUI...
"%VENV_PY%" -m book_normalizer.gui.app
if errorlevel 1 goto error

exit /b 0

:error
echo.
echo Failed to start the program. Check the messages above.
pause
exit /b 1
