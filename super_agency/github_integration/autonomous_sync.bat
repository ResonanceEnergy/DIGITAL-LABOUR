@echo off
REM Bit Rage Systems Autonomous GitHub Sync
REM Called by the main orchestration system

echo 🤖 Bit Rage Systems Autonomous GitHub Sync
echo =====================================

cd /d "%~dp0"

echo 📍 Working directory: %CD%
echo 🚀 Starting autonomous sync...

REM Run the sync
call run_github_integration.bat sync

echo ✅ Autonomous sync complete!
echo 📊 Check https://github.com/ResonanceEnergy for your repositories

REM Log completion
echo %DATE% %TIME% - Autonomous sync completed >> autonomous_sync.log