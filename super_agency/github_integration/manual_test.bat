@echo off
echo 🔐 Manual GitHub Authentication Test
echo =====================================
cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -File "manual_test.ps1"

echo.
echo =====================================
echo 🎯 If successful, run: run_github_integration.bat sync
pause