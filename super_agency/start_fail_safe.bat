@echo off
REM Bit Rage Systems ULTIMATE FAIL-SAFE STARTUP SCRIPT
REM Launches the watchdog service for 24/7/365 operation
REM This script ensures the entire agency remains online forever

echo.
echo ===============================================
echo   Bit Rage Systems ULTIMATE FAIL-SAFE STARTUP
echo ===============================================
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check if watchdog service is already running
tasklist /FI "IMAGENAME eq python.exe" /FO CSV | findstr /C:"watchdog_service.py" >nul
if %errorlevel% equ 0 (
    echo WARNING: Watchdog service appears to be already running
    echo If you're sure it's not running, you can kill existing Python processes
    echo.
    choice /C YN /M "Do you want to continue anyway? (Y/N)"
    if errorlevel 2 goto :eof
)

echo Starting Watchdog Service...
echo This will launch the fail-safe orchestrator and ensure 24/7 operation
echo.

REM Start the watchdog service in a new window
start "Bit Rage Systems WATCHDOG" cmd /c "python watchdog_service.py"

REM Wait a moment for startup
timeout /t 3 /nobreak >nul

echo Watchdog service started!
echo.
echo SYSTEM STATUS:
echo   - Watchdog Service: ACTIVE (monitoring fail-safe orchestrator)
echo   - Fail-Safe Orchestrator: Starting... (will be monitored by watchdog)
echo   - All Agency Components: Will be started by orchestrator
echo.
echo To monitor the system:
echo   - Check watchdog_service.log for watchdog activity
echo   - Check fail_safe_orchestrator.log for orchestrator activity
echo   - Check alerts.log for any system alerts
echo.
echo The system will now run continuously in the background.
echo Press Ctrl+C in the watchdog window to stop everything gracefully.
echo.

REM Keep this window open briefly to show status
echo Press any key to close this window...
pause >nul
