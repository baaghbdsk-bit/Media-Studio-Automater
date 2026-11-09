@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo Media Studio Automater - Automation Setup
echo ==========================================
echo.

echo Registering daily tasks for the current Windows user...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_automation.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] Automation task setup failed. See the error above.
    pause
    exit /b 1
)

echo.
echo Setup complete. Verify with:
echo   schtasks /query /tn "Media Studio - Reels Shorts" /fo LIST /v
echo   schtasks /query /tn "Media Studio - Reels Shorts 2" /fo LIST /v
echo   schtasks /query /tn "Media Studio - Explainer" /fo LIST /v
echo.
pause
exit /b 0