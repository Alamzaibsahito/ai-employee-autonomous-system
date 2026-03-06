@echo off
REM ============================================================
REM Process Tasks Startup Script for Windows/PM2
REM ============================================================
REM This script ensures proper virtual environment activation
REM before running process_tasks.py under PM2.
REM
REM Usage:
REM   start_process_tasks.bat
REM ============================================================

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Activate virtual environment if it exists
if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" (
    call "%SCRIPT_DIR%venv\Scripts\activate.bat"
    echo Virtual environment activated: %SCRIPT_DIR%venv
) else if exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
    call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
    echo Virtual environment activated: %SCRIPT_DIR%.venv
) else (
    echo No virtual environment found, using system Python
)

REM Ensure Python can find site modules
set PYTHONHOME=
set PYTHONPATH=

REM Change to script directory
cd /d "%SCRIPT_DIR%"

REM Run process_tasks.py with the activated Python
python "%SCRIPT_DIR%process_tasks.py" %*
