@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Truth Lens - One Click Launcher

if not exist ".env" (
    echo.
    echo [ERROR] .env file is missing.
    echo Create .env in this folder with:
    echo GEMINI_API_KEY=YOUR_API_KEY_HERE
    echo.
    pause
    exit /b 1
)

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo [ERROR] Python was not found on this PC.
    echo Install Python 3.11+ and run this file again.
    pause
    exit /b 1
)

echo ============================================================
echo              AI TRUTH LENS - ONE CLICK
echo ============================================================
echo.
echo [1/4] Checking Python environment...

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m pip --version >nul 2>nul
    if errorlevel 1 (
        echo [INFO] Repairing broken virtual environment...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create virtual environment.
        pause
        exit /b 1
    )
)

.venv\Scripts\python.exe -m pip --version >nul 2>nul
if errorlevel 1 (
    echo [INFO] Installing pip inside virtual environment...
    .venv\Scripts\python.exe -m ensurepip --upgrade >nul 2>nul
)

.venv\Scripts\python.exe -m pip --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] pip could not be installed in the virtual environment.
    pause
    exit /b 1
)

echo [2/4] Installing required packages...
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Package installation failed.
    pause
    exit /b 1
)

echo [3/4] Starting AI Truth Lens...
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000"

echo [4/4] Server starting at http://127.0.0.1:5000
.venv\Scripts\python.exe app.py

set "EXITCODE=%ERRORLEVEL%"
echo.
echo AI Truth Lens stopped. Exit code: %EXITCODE%
pause
exit /b %EXITCODE%
