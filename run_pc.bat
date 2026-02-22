@echo off
setlocal

:: NutriScale Windows Run Script

:: Go to script directory
cd /d "%~dp0"

echo [+] Checking for virtual environment...
if exist .venv\Scripts\activate.bat (
    echo [+] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [-] .venv\Scripts\activate.bat not found. Running with system python...
)

echo [+] Starting NutriScale Server...
python -m backend.app

pause
