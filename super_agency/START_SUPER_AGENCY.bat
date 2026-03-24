@echo off
REM Bit Rage Systems Startup - Enhanced with REPO DEPOT, QFORGE, QUSAR
REM ResonanceEnergy Enterprise

echo.
echo ============================================
echo       Bit Rage Systems STARTUP SYSTEM
echo         ResonanceEnergy Enterprise
echo ============================================
echo.

cd /d "%~dp0"

REM Check for flags
set SKIP_SYNC=
set NO_MONITOR=
set MINIMAL=

:parse_args
if "%~1"=="" goto :run
if /i "%~1"=="--skip-sync" set SKIP_SYNC=-SkipSync
if /i "%~1"=="--no-monitor" set NO_MONITOR=-NoMonitor
if /i "%~1"=="--minimal" set MINIMAL=-Minimal
shift
goto :parse_args

:run
powershell -ExecutionPolicy Bypass -File "start_super_agency.ps1" %SKIP_SYNC% %NO_MONITOR% %MINIMAL%

pause
