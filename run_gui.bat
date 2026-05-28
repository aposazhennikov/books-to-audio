@echo off
setlocal

cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

set "VENV_PY=.venv-windows\Scripts\python.exe"
set "CHECK_ONLY="
if /i "%~1"=="--check" (
    set "CHECK_ONLY=1"
    shift
)

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import PyQt6, book_normalizer, huggingface_hub" >nul 2>nul
    if not errorlevel 1 goto launch_windows
)

if defined CHECK_ONLY goto check_failed

set "BOOKS_TO_AUDIO_FROM_RUN_GUI=1"
call install.bat --no-system-check
if errorlevel 1 goto error

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import PyQt6, book_normalizer, huggingface_hub" >nul 2>nul
    if not errorlevel 1 goto launch_windows
)

echo GUI dependencies were not installed in Windows .venv-windows.
echo run_gui.bat only starts the native Windows GUI.
echo For Linux or macOS use run_gui.sh separately.
goto error

:check_failed
echo Native Windows GUI environment is not ready.
call :say_ru_b64 "0J3QsNGC0LjQstC90LDRjyBXaW5kb3dzLdGB0YDQtdC00LAgR1VJINC90LUg0LPQvtGC0L7QstCwLg=="
echo Run install.bat first, then try run_gui.bat --check again.
call :say_ru_b64 "0KHQvdCw0YfQsNC70LAg0LfQsNC/0YPRgdGC0LjRgtC1IGluc3RhbGwuYmF0LCDQt9Cw0YLQtdC8INC/0L7QstGC0L7RgNC40YLQtSBydW5fZ3VpLmJhdCAtLWNoZWNrLg=="
exit /b 1

:launch_windows
if defined CHECK_ONLY (
    echo Native Windows GUI environment OK.
    call :say_ru_b64 "0J3QsNGC0LjQstC90LDRjyBXaW5kb3dzLdGB0YDQtdC00LAgR1VJINCz0L7RgtC+0LLQsC4="
    exit /b 0
)
echo Checking local Ollama server...
"%VENV_PY%" -m book_normalizer.llm.ollama_server 30
if errorlevel 1 (
    echo Ollama is not ready. GUI will start; LLM features require Ollama setup.
    call :say_ru_b64 "T2xsYW1hINC90LUg0LPQvtGC0L7QstCwLiBHVUkg0LfQsNC/0YPRgdGC0LjRgtGB0Y86IExMTS3RhNGD0L3QutGG0LjQuCDRgtGA0LXQsdGD0Y7RgiBPbGxhbWEu"
)

echo Starting books-to-audio GUI...
"%VENV_PY%" -m book_normalizer.gui.app %*
if errorlevel 1 goto error

exit /b 0

:say_ru_b64
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); Write-Host ('   ' + [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('%~1')))"
exit /b 0

:error
echo.
echo Failed to start the program. Check the messages above.
pause
exit /b 1
