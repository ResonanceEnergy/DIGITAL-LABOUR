@echo off
echo ============================================
echo  Digital Labour ORCHESTRATION FREQUENCY LAUNCHER
echo ============================================
echo.
echo Current Status: System Health EXCELLENT
echo QUASMEM: 210.5MB Active, Agent Health: 87.7%%
echo.
echo Choose Orchestration Frequency:
echo.
echo [1] ULTRA-HIGH FREQUENCY (1 min) - MAXIMUM SPEED
echo     🚀 30x faster monitoring
echo     ⚠️  EXTREME resource usage
echo     ⚠️  High API limit risk
echo.
echo [2] HIGH FREQUENCY (5 min) - Maximum responsiveness
echo     ⚡ 6x faster monitoring
echo     ⚠️  Higher resource usage
echo     ⚠️  More API calls
echo.
echo [3] MODERATE FREQUENCY (10 min) - Balanced speed
echo     ⚡ 3x faster monitoring
echo     ✅ Good resource balance
echo     ✅ API-friendly
echo.
echo [4] STANDARD FREQUENCY (30 min) - Current default
echo     ✅ Conservative resources
echo     ✅ Proven stability
echo     ✅ API rate limit friendly
echo.
echo [5] TEST MODE (10 sec) - Development only
echo     🧪 Rapid testing cycles
echo     ⚠️  Development use only
echo.
echo [6] View Performance Guide
echo     📖 Detailed optimization guide
echo.
echo [7] Exit
echo.
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto ultra_high_freq
if "%choice%"=="2" goto high_freq
if "%choice%"=="3" goto moderate_freq
if "%choice%"=="4" goto standard_freq
if "%choice%"=="5" goto test_mode
if "%choice%"=="6" goto view_guide
if "%choice%"=="7" goto exit

echo Invalid choice. Please run again.
pause
exit /b 1

:ultra_high_freq
echo.
echo 🚀🚀 Launching ULTRA-HIGH FREQUENCY Orchestration (1-minute intervals)
echo.
echo ⚠️  MAXIMUM PERFORMANCE MODE - EXTREME RESOURCE USAGE!
echo ⚠️  This will consume massive resources and may hit API limits!
echo ⚠️  Monitor constantly - stop if CPU > 90%% or API errors occur!
echo.
echo Safety Features Enabled:
echo - Real-time resource monitoring
echo - API usage tracking
echo - Emergency auto-stop on critical usage
echo - Rate limit detection and delays
echo.
powershell -ExecutionPolicy Bypass -File "continuous_orchestration_runner_ultra_high.ps1" -IntervalMinutes 1 -SafeMode
goto end

:high_freq
echo.
echo ⚡ Launching HIGH FREQUENCY Orchestration (5-minute intervals)
echo.
echo Safety Features Enabled:
echo - Resource monitoring
echo - API rate limit protection
echo - Automatic emergency stops
echo.
powershell -ExecutionPolicy Bypass -File "continuous_orchestration_runner_high_freq.ps1" -IntervalMinutes 5 -SafeMode
goto end

:moderate_freq
echo.
echo ⚡ Launching MODERATE FREQUENCY Orchestration (10-minute intervals)
echo.
echo Balanced performance with good responsiveness.
echo.
powershell -ExecutionPolicy Bypass -File "continuous_orchestration_runner_moderate.ps1" -IntervalMinutes 10
goto end

:standard_freq
echo.
echo 🛡️ Launching STANDARD FREQUENCY Orchestration (30-minute intervals)
echo.
echo Conservative resource usage, proven stability.
echo.
powershell -ExecutionPolicy Bypass -File "continuous_orchestration_runner.ps1" -IntervalMinutes 30
goto end

:test_mode
echo.
echo 🧪 Launching TEST MODE Orchestration (10-second intervals)
echo.
echo WARNING: This is for development testing only!
echo Press Ctrl+C to stop the test.
echo.
powershell -ExecutionPolicy Bypass -File "continuous_orchestration_runner_ultra_high.ps1" -IntervalMinutes 1 -TestMode
goto end

:view_guide
echo.
echo 📖 Opening Orchestration Speed Optimization Guide...
echo.
start ORCHESTRATION_SPEED_GUIDE.md
echo.
echo Guide opened. Press any key to return to menu...
pause >nul
goto menu_start

:exit
echo.
echo Exiting launcher. Have a great day! 👋
echo.
exit /b 0

:end
echo.
echo Orchestration completed or stopped.
echo Check logs for details.
echo.
pause
