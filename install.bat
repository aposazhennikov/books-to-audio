@echo off
setlocal

cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "C_INFO=0B"
set "C_WARN=0E"
set "C_ERR=0C"
set "C_OK=0A"
set "C_RESET=07"

set "VENV_DIR=.venv-windows"
set "VENV_ARGS=--venv %VENV_DIR%"
set "USE_EXISTING_VENV=1"
for %%A in (%*) do (
    if "%%~A"=="--recreate" set "USE_EXISTING_VENV="
    if /i "%%~A"=="--venv" set "VENV_ARGS="
)

if not defined USE_EXISTING_VENV goto check_python
if not exist "%VENV_DIR%\Scripts\python.exe" goto check_python
"%VENV_DIR%\Scripts\python.exe" install.py %VENV_ARGS% %*
set "EXIT_CODE=%errorlevel%"
goto done

:check_python
python -c "import sys, venv; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto check_py_launcher
python install.py %VENV_ARGS% %*
set "EXIT_CODE=%errorlevel%"
goto done

:check_py_launcher
py -3 -c "import sys, venv; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto bootstrap_python
py -3 install.py %VENV_ARGS% %*
set "EXIT_CODE=%errorlevel%"
goto done

:bootstrap_python
color %C_ERR% >nul 2>nul
echo Python 3.10 or newer was not found on Windows.
echo    Python 3.10+ не найден в Windows.
color %C_RESET% >nul 2>nul
echo.
where winget >nul 2>nul
if errorlevel 1 goto python_manual_help
color %C_INFO% >nul 2>nul
echo Installing Python 3.12 with native Windows winget...
echo    Устанавливаю Python 3.12 через нативный Windows winget...
color %C_RESET% >nul 2>nul
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto python_manual_help
color %C_OK% >nul 2>nul
echo Retrying installer with the newly installed Python...
echo    Повторно запускаю установщик с новым Python...
color %C_RESET% >nul 2>nul
if not exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" goto retry_python_path
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" install.py %VENV_ARGS% %*
set "EXIT_CODE=%errorlevel%"
goto done

:retry_python_path
python -c "import sys, venv; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto retry_py_launcher
python install.py %VENV_ARGS% %*
set "EXIT_CODE=%errorlevel%"
goto done

:retry_py_launcher
py -3 -c "import sys, venv; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto python_manual_help
py -3 install.py %VENV_ARGS% %*
set "EXIT_CODE=%errorlevel%"
goto done

:python_manual_help
echo.
color %C_ERR% >nul 2>nul
echo Python 3.10 or newer was not found on Windows.
echo    Python 3.10+ не найден в Windows.
color %C_WARN% >nul 2>nul
echo Install Python 3.12 for Windows and enable "Add python.exe to PATH":
echo    Установите Python 3.12 для Windows и включите "Add python.exe to PATH":
color %C_INFO% >nul 2>nul
echo   https://www.python.org/downloads/
color %C_RESET% >nul 2>nul
echo.
color %C_INFO% >nul 2>nul
echo Or run / Или запустите:
echo   winget install -e --id Python.Python.3.12 --scope user
color %C_RESET% >nul 2>nul
echo.
color %C_WARN% >nul 2>nul
echo After installation, close this window and run install.bat again.
echo    После установки закройте окно и запустите install.bat снова.
color %C_RESET% >nul 2>nul
set "EXIT_CODE=1"

:done
if not defined BOOKS_TO_AUDIO_FROM_RUN_GUI (
    echo.
    color %C_INFO% >nul 2>nul
    echo Press any key to exit terminal...
    echo    Нажмите любую кнопку для выхода из терминала...
    color %C_RESET% >nul 2>nul
    pause >nul
)
exit /b %EXIT_CODE%
