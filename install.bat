@echo off
title CareerPilot AI — 1-Click Automated Installer
echo ======================================================================
echo           ⚡ CAREERPILOT AI — AUTOMATED INSTALLER & SETUP
echo ======================================================================
echo.

rem Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10 or higher from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/4] Setting up Python virtual environment (.venv)...
if not exist ".venv" (
    python -m venv .venv
)

echo [2/4] Installing dependencies from requirements.txt...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt

echo [3/4] Installing Playwright Chromium browser binary...
.venv\Scripts\playwright.exe install chromium

echo [4/4] Checking configuration (.env)...
if not exist ".env" (
    copy .env.example .env
    echo Created .env from .env.example!
)

echo.
echo ======================================================================
echo           ✅ INSTALLATION COMPLETE!
echo ======================================================================
echo To start using CareerPilot AI:
echo   1. Edit your .env file to add your OpenRouter/Gemini API key.
echo   2. Double-click "start_careerpilot.bat" to launch the Command Center!
echo ======================================================================
echo.
pause

