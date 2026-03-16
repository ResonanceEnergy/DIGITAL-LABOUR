@echo off
REM Digital Labour Daily Operations Script
REM Run this daily to execute the full orchestration cycle

echo ========================================
echo  🚀 Digital Labour - DAILY OPERATIONS
echo ========================================
echo Date: %DATE% %TIME%
echo Location: %~dp0
echo.

cd /d "%~dp0"

echo [1/3] Running Repo Sentry...
python agents\orchestrator.py
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Repo Sentry failed with code %ERRORLEVEL%
    goto :error
)
echo ✅ Repo Sentry complete
echo.

echo [2/3] Checking Daily Brief...
if exist "reports\daily\brief_%DATE:~-4%-%DATE:~4,2%-%DATE:~7,2%.md" (
    echo ✅ Daily brief generated successfully
    echo File: reports\daily\brief_%DATE:~-4%-%DATE:~4,2%-%DATE:~7,2%.md
) else (
    echo ⚠️ Daily brief not found (this may be normal)
)
echo.

echo [3/3] System Health Check...
python -c "import sys; print('✅ Python operational'); print(f'Version: {sys.version}')"

echo.
echo ========================================
echo 🎉 DAILY OPERATIONS COMPLETE
echo ========================================
echo Next run: Tomorrow at 6:00 AM (schedule with Task Scheduler)
echo.
echo Quick commands:
echo - View latest brief: type reports\daily\brief_*.md
echo - Check logs: (check console output above)
echo - Manual run: python agents\orchestrator.py
echo.
goto :end

:error
echo.
echo ❌ OPERATIONS FAILED
echo Check the error messages above and resolve issues.
echo Contact council if problems persist.
pause
exit /b 1

:end
echo Press any key to continue...
pause >nul