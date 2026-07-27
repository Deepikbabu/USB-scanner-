@echo off
setlocal EnableExtensions
set ROOT=%~dp0
cd /d "%ROOT%"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH.
    echo Install Python 3.10 or newer and enable "Add Python to PATH".
    exit /b 1
)

if not exist ".venv" (
    echo [*] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment is incomplete: .venv\Scripts\python.exe is missing.
    exit /b 1
)

echo [*] Installing Python dependencies...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    exit /b 1
)

echo [*] Starting USB Security Interface...
set PYTHONPATH=%ROOT%
.venv\Scripts\python.exe ui\sentinel\main_sys.py
if errorlevel 1 (
    echo [ERROR] Dashboard exited with an error.
    exit /b 1
)
pause
