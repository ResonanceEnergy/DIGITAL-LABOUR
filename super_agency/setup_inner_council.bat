@echo off
echo ========================================
echo Inner Council Intelligence Setup
echo ========================================
echo.
echo This script will help you set up your YouTube API key
echo for the Inner Council Intelligence System.
echo.
echo You need a YouTube Data API v3 key from Google Cloud Console.
echo.

set /p API_KEY="Enter your YouTube API Key: "

if "%API_KEY%"=="" (
    echo.
    echo ERROR: No API key entered. Setup cancelled.
    echo.
    pause
    exit /b 1
)

echo.
echo Setting YOUTUBE_API_KEY environment variable...
setx YOUTUBE_API_KEY "%API_KEY%" /M

echo.
echo API key set successfully!
echo.
echo Testing the setup...

python youtube_intelligence_monitor.py

echo.
echo Setup complete! The Inner Council Intelligence System is now ready.
echo.
echo You can now run daily intelligence sessions with:
echo   python youtube_intelligence_monitor.py
echo   or
echo   .\youtube_monitor.bat
echo.
pause