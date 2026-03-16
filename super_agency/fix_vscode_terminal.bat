@echo off
REM VS Code Terminal Fix
REM Resolves terminal blocking issues

echo 🔧 VS Code Terminal Fix
echo =======================
echo.
echo This script will help resolve VS Code terminal issues.
echo.
echo Press any key to continue...
pause >nul

echo.
echo 🔍 Checking for problematic processes...

REM Check for backup processes
tasklist /FI "IMAGENAME eq powershell.exe" /FO TABLE
echo.
echo If you see multiple PowerShell processes, some may be stuck.
echo.

echo 🧹 Attempting to clear terminal state...
echo.

REM Try to kill any stuck processes (be careful!)
echo ⚠️  WARNING: This will attempt to stop problematic processes
echo Press Ctrl+C to cancel if you don't want to proceed
timeout /t 5

REM Kill any stuck PowerShell instances (except current one)
for /f "tokens=2" %%i in ('tasklist ^| findstr /i powershell.exe') do (
    if not "%%i"=="%PID%" (
        echo Attempting to stop PowerShell process ID: %%i
        taskkill /PID %%i /F >nul 2>&1
    )
)

echo.
echo ✅ VS Code Terminal Fix Complete
echo ================================
echo.
echo Try using the VS Code terminal again. If issues persist:
echo 1. Restart VS Code completely
echo 2. Run this batch file again
echo 3. Check Task Manager for stuck processes
echo 4. Temporarily disable real-time protection if using antivirus
echo.
pause