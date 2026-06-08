@echo off
title Beam Mechanics Simulator v2 - PyQt5
color 0A
echo.
echo  ============================================
echo    Beam Mechanics Simulator v2
echo    PyQt5 Edition - SFD ^& BMD Analysis
echo  ============================================
echo.

:: -- Step 1: Check / Create virtual environment --
if exist "beam_sim_env\" (
    echo  [OK] Virtual environment already exists. Skipping creation.
) else (
    echo  [..] Creating virtual environment 'beam_sim_env'...
    python -m venv beam_sim_env
    if errorlevel 1 (
        echo.
        echo  [ERROR] Failed to create virtual environment.
        echo  Make sure Python is installed and added to PATH.
        echo.
        pause
        exit /b 1
    )
    echo  [OK] Virtual environment created.
)

echo.

:: -- Step 2: Activate virtual environment --
echo  [..] Activating virtual environment...
call beam_sim_env\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo  [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo  [OK] Virtual environment activated.
echo.

:: -- Step 3: Install dependencies silently --
echo  [..] Installing dependencies (numpy, matplotlib, PyQt5)...
pip install numpy matplotlib PyQt5 -q --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo  [ERROR] Failed to install dependencies.
    echo  Check your internet connection and try again.
    pause
    exit /b 1
)
echo  [OK] Dependencies installed.
echo.

:: -- Step 4: Run the simulation --
echo  [>>] Launching Beam Mechanics Simulator...
echo  ============================================
echo.
python beam_simulation.py
if errorlevel 1 (
    echo.
    echo  [ERROR] Simulation exited with an error.
    pause
    exit /b 1
)

echo.
echo  [OK] Simulation closed normally.
echo.
pause
