@echo off
title CareerPilot AI — Autonomous Career Command Center
echo ======================================================================
echo           ⚡ CAREERPILOT AI — AUTONOMOUS CAREER COMMAND CENTER
echo ======================================================================
echo Candidate: Poorna Chandra Rao J
echo Engine: OpenRouter (Google Gemini 2.5 Flash)
echo Portals: LinkedIn (Easy Apply & External ATS) + Naukri (1-Click)
echo ======================================================================
echo.

set "PROFILE_DIR=%~dp0chrome_debug_profile"
set "URLS=https://mail.google.com https://www.linkedin.com/jobs https://www.naukri.com http://localhost:8000"

echo [1/2] Launching Google Chrome (Port 9222) with authenticated profile...
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%" %URLS%
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%" %URLS%
) else (
    start "" chrome.exe --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%" %URLS%
)

echo [2/2] Starting CareerPilot Web Command Center at http://localhost:8000...
echo.
echo ======================================================================
echo Command Center is LIVE! Dashboard: http://localhost:8000
echo Keep this terminal window open while using CareerPilot AI.
echo ======================================================================
echo.

.venv\Scripts\python.exe main.py dashboard --port 8000

