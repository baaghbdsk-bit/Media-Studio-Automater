@echo off
cd /d "%~dp0"
echo ==========================================
echo Media Studio Automater - Automation Setup
echo ==========================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as administrator
) else (
    echo [WARNING] Not running as administrator - Task Scheduler may need admin rights
    echo.
)

:: Get Python path
set PYTHON_EXE=python
where python >nul 2>&1
if %errorLevel% neq 0 (
    set PYTHON_EXE=python.exe
)

:: Create Windows Task Scheduler tasks
echo.
echo Creating Task 1: Media Studio - Reels/Shorts (5:15 PM & 7:15 PM)
schtasks /create /tn "Media Studio - Reels Shorts" /tr "%PYTHON_EXE% %~dp0src\automation_daemon.py schedule-reels-shorts" /sc daily /st 17:15 /ru %USERNAME% /f
if %errorLevel% == 0 echo [OK] Task 1 created
echo.
schtasks /create /tn "Media Studio - Reels Shorts 2" /tr "%PYTHON_EXE% %~dp0src\automation_daemon.py schedule-reels-shorts" /sc daily /st 19:15 /ru %USERNAME% /f
if %errorLevel% == 0 echo [OK] Task 1b created

echo.
echo Creating Task 2: Media Studio - Explainer (9:15 PM alternate days)
schtasks /create /tn "Media Studio - Explainer" /tr "%PYTHON_EXE% %~dp0src\automation_daemon.py schedule-explainer" /sc daily /st 21:15 /ru %USERNAME% /f
if %errorLevel% == 0 echo [OK] Task 2 created

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Tasks created:
echo   1. Media Studio - Reels Shorts  - Daily at 5:15 PM
echo   2. Media Studio - Reels Shorts 2 - Daily at 7:15 PM  
echo   3. Media Studio - Explainer - Daily at 9:15 PM (alternate days)
echo.
echo To run now: python src\automation_daemon.py
echo To test:    python main.py schedule-today
echo.
pause