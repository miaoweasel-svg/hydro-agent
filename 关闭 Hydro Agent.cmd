@echo off
setlocal
cd /d "%~dp0"
title Stop Hydro Agent

if exist ".venv\Scripts\python.exe" goto use_venv

where python.exe >nul 2>nul
if errorlevel 1 (
    echo Python was not found.
    pause
    exit /b 1
)

python scripts\stop_app.py
goto finished

:use_venv
".venv\Scripts\python.exe" scripts\stop_app.py

:finished
echo.
pause
