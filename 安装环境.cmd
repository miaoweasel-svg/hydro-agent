@echo off
setlocal
cd /d "%~dp0"
title Install Hydro Agent

echo ========================================
echo   Hydro Agent - Environment Installer
echo ========================================
echo This window will remain visible during installation.
echo The first installation requires an internet connection.

if exist ".venv\Scripts\python.exe" goto use_venv

where py.exe >nul 2>nul
if errorlevel 1 goto try_python
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto try_python
goto use_py

:try_python
where python.exe >nul 2>nul
if errorlevel 1 goto install_python
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto install_python
goto use_python

:install_python
where winget.exe >nul 2>nul
if errorlevel 1 goto python_missing
echo.
echo Python 3.10 or newer was not found.
echo Installing Python 3.12 for the current Windows user with winget...
winget install --id Python.Python.3.12 --exact --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto python_install_failed
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" goto use_installed_python
goto python_restart_needed

:use_venv
".venv\Scripts\python.exe" scripts\install_environment.py
goto finish

:use_py
py -3 scripts\install_environment.py
goto finish

:use_python
python scripts\install_environment.py
goto finish

:use_installed_python
"%LocalAppData%\Programs\Python\Python312\python.exe" scripts\install_environment.py
goto finish

:python_missing
echo.
echo Python and Windows Package Manager were not found.
echo Install Python 3.10 or newer from https://www.python.org/downloads/windows/
echo Select "Add python.exe to PATH", then run this installer again.
goto failed

:python_install_failed
echo.
echo Automatic Python installation failed.
echo Install Python 3.10 or newer manually, then run this installer again.
goto failed

:python_restart_needed
echo.
echo Python was installed, but this window cannot locate it yet.
echo Close this window and double-click this installer once more.
echo.
pause
exit /b 0

:finish
if errorlevel 1 goto failed

:success
echo.
echo Installation completed. You can now double-click the start script.
echo.
pause
exit /b 0

:failed
echo.
echo Installation was not completed. Review the message above.
echo.
pause
exit /b 1
