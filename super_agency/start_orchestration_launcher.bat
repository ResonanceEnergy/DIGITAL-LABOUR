@echo off
REM Digital Labour Orchestration Frequency Launcher
REM Choose your preferred monitoring frequency

echo 🚀 Digital Labour Orchestration Frequency Launcher
echo.
echo Choose your monitoring frequency:
echo [1] HIGH FREQUENCY   - 5 minutes  (⚡ Fast monitoring, high resource usage)
echo [2] MODERATE FREQUENCY - 10 minutes (🔄 Balanced monitoring)
echo [3] STANDARD FREQUENCY - 30 minutes (🧠 Current default, conservative)
echo [4] TEST MODE        - 10 seconds (🧪 Testing only)
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    echo ⚡ Starting HIGH FREQUENCY monitoring (5-minute intervals)...
    echo ⚠️  WARNING: Monitor system resources closely!
    powershell -ExecutionPolicy Bypass -File "continuous_orchestration_runner_high_freq.ps1" -IntervalMinutes 5 -SafeMode
) else if "%choice%"=="2" (
    echo 🔄 Starting MODERATE FREQUENCY monitoring (10-minute intervals)...
    powershell -ExecutionPolicy Bypass -File "continuous_orchestration_runner_moderate.ps1" -IntervalMinutes 10
) else if "%choice%"=="3" (
    echo 🧠 Starting STANDARD FREQUENCY monitoring (30-minute intervals)...
    powershell -ExecutionPolicy Bypass -File "continuous_orchestration_runner.ps1" -IntervalMinutes 30
) else if "%choice%"=="4" (
    echo 🧪 Starting TEST MODE (10-second intervals)...
    powershell -ExecutionPolicy Bypass -File "continuous_orchestration_runner_high_freq.ps1" -IntervalMinutes 1 -TestMode
) else (
    echo ❌ Invalid choice. Please run again and select 1-4.
    pause
    exit /b 1
)

echo.
echo ✅ Orchestration monitoring started!
echo 📊 Check the respective log files for monitoring data
pause
