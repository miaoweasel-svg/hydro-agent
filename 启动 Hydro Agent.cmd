@echo off
setlocal
cd /d "%~dp0"
title Hydro Agent

if exist ".venv\Scripts\python.exe" goto use_venv

where python.exe >nul 2>nul
if errorlevel 1 (
    echo The Hydro Agent environment was not found.
    echo Double-click the environment installer first.
    pause
    exit /b 1
)

python scripts\launch_app.py
goto check_result

:use_venv
".venv\Scripts\python.exe" scripts\launch_app.py

:check_result
if errorlevel 1 (
    echo.
    echo Hydro Agent stopped with an error.
    pause
)
