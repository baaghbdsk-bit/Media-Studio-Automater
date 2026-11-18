@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo YouTube Re-Authentication (one click)
echo ==========================================
echo.
echo A browser will open. Sign in with:
echo   aidevradar982@gmail.com
echo then click Allow.
echo.
python scripts\login_youtube.py
if errorlevel 1 (
    echo.
    echo [ERROR] YouTube login failed. See the messages above.
    pause
    exit /b 1
)
echo.
echo YouTube login finished. Check the sync message above.
echo If it says the secret was updated, you are done.
echo Otherwise set the YOUTUBE_TOKEN_BASE64 secret manually from
echo tools\YOUTUBE_TOKEN_BASE64.txt
echo.
pause
exit /b 0
