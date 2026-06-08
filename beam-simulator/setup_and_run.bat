@echo off
title Beam Mechanics Simulator - Pro Edition
color 0A
echo.
echo  ============================================
echo   BEAM MECHANICS SIMULATOR - PRO EDITION
echo   Electron + Flask + Chart.js + Groq AI
echo  ============================================
echo.

:: Set Groq API key for AI explanations (set your own before running)
if "%GROQ_API_KEY%"=="" (
    echo  [!] GROQ_API_KEY not set. AI explanations will be disabled.
    echo  Set it with: set GROQ_API_KEY=your_key_here
)

echo [1/4] Checking Python virtual environment...
if exist "beam_env\" (
    echo  [OK] Virtual environment exists.
) else (
    echo  [...] Creating virtual environment...
    python -m venv beam_env
    if errorlevel 1 (
        echo.
        echo  [ERROR] Failed to create virtual environment.
        echo  Make sure Python 3.8+ is installed and in PATH.
        pause
        exit /b 1
    )
    echo  [OK] Virtual environment created.
)
echo.

echo [2/4] Installing Python dependencies...
call beam_env\Scripts\activate.bat
pip install flask flask-cors numpy groq -q --disable-pip-version-check
if errorlevel 1 (
    echo  [ERROR] Failed to install Python packages.
    pause
    exit /b 1
)
echo  [OK] Python packages ready.
echo.

echo [3/4] Checking Node dependencies...
if exist "node_modules\electron" (
    echo  [OK] Node modules exist.
) else (
    echo  [...] Running npm install - this takes 1-2 minutes...
    call npm install
    if errorlevel 1 (
        echo  [ERROR] npm install failed.
        echo  Make sure Node.js and npm are installed.
        pause
        exit /b 1
    )
    echo  [OK] Node modules installed.
)
echo.

echo [4/4] Launching application...
echo  ============================================
echo  The Beam Simulator window will appear shortly.
echo  Keep this console open - closing it will stop the app.
echo  ============================================
echo.
npm start

echo.
echo  [DONE] Application closed.
pause
