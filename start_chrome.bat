@echo off
echo ======================================================================
echo Launching Google Chrome with Dedicated Agent Profile & Port 9222
echo ======================================================================

set "PROFILE_DIR=%~dp0chrome_debug_profile"
set "URLS=https://mail.google.com https://www.linkedin.com/jobs https://www.naukri.com"

echo Using Profile: %PROFILE_DIR%
echo Debugging Port: 9222
echo.

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%" %URLS%
    goto done
)

if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%" %URLS%
    goto done
)

start "" chrome.exe --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%" %URLS%

:done
echo Chrome opened with Gmail, LinkedIn, and Naukri tabs!
echo.
echo 1. Sign in to your accounts in this Chrome window (only needed once).
echo 2. Once signed in, keep the window open and run:
echo      .venv\Scripts\python.exe main.py run
