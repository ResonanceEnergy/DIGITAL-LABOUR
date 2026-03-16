@echo off
REM ============================================
REM REPO DEPOT FAILSAFE - QUICK START
REM ============================================
REM CRITICAL INFRASTRUCTURE - 24/7/365 OPERATION
REM Run this to ensure Repo Depot is always alive
REM ============================================

cd /d "C:\Dev\DIGITAL LABOUR-Shared"

echo ============================================
echo   REPO DEPOT FAILSAFE STARTUP
echo   CRITICAL INFRASTRUCTURE
echo ============================================

REM Start Repo Depot
start "" /B .venv\Scripts\python.exe optimus_repo_depot_launcher.py

REM Start Watchdog
start "" /B .venv\Scripts\python.exe repo_depot_watchdog.py

echo.
echo   Repo Depot: STARTED
echo   Watchdog:   STARTED
echo.
echo   Status: Check repo_depot_status.json
echo ============================================
