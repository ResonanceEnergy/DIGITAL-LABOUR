@echo off
REM Digital Labour CPU Maximizer Quick Start (Windows)
REM Maximum CPU utilization for all repositories

echo 🔥 Digital Labour CPU Maximizer Quick Start
echo ==========================================
cd /d "%~dp0.."
set "ROOT_DIR=%CD%"
echo Root Directory: %ROOT_DIR%

REM Get CPU count
for /f "tokens=*" %%i in ('wmic cpu get NumberOfCores /value ^| find "NumberOfCores"') do set %%i
set CPU_CORES=%NumberOfCores%
if "%CPU_CORES%"=="" set CPU_CORES=Unknown
echo CPU Cores: %CPU_CORES%
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python not found. Please install Python 3.7+
    pause
    exit /b 1
)
echo Using Python: 
python --version
echo.

REM Function to run with timing
:run_with_timing
set "name=%~1"
set "cmd=%~2"

echo 🚀 Running %name%...
set start_time=%time%

call %cmd%
if %ERRORLEVEL% equ 0 (
    echo ✅ %name% completed successfully
) else (
    echo ❌ %name% failed with error code %ERRORLEVEL%
)
goto :eof

REM Options
:run_single
echo 📊 Option 1: Single CPU Maximizer
call :run_with_timing "CPU Maximizer" "python cpu_maximizer.py"
goto :eof

:run_parallel
echo 📊 Option 2: Parallel Orchestrator
call :run_with_timing "Parallel Orchestrator" "python parallel_orchestrator.py"
goto :eof

:run_batch
set cycles=%1
if "%cycles%"=="" set cycles=5
echo 📊 Option 3: Batch Processing (%cycles% cycles)
call :run_with_timing "Batch Processor" "python batch_processor.py --cycles %cycles%"
goto :eof

:run_control
set mode=%1
set duration=%2
if "%mode%"=="" set mode=balanced
if "%duration%"=="" set duration=5
echo 📊 Option 4: CPU Control Center (Mode: %mode%, Duration: %duration%m)
call :run_with_timing "CPU Control Center" "python cpu_control_center.py %mode% --duration %duration%"
goto :eof

:run_maximum
set duration=%1
if "%duration%"=="" set duration=3
echo 🚀 Option 5: MAXIMUM OVERDRIVE MODE (%duration% minutes)
echo Warning: This will launch all systems simultaneously!
echo Press Ctrl+C to stop early
echo.
call :run_with_timing "Maximum CPU Mode" "python cpu_control_center.py maximum --duration %duration%"
goto :eof

:run_continuous
set duration=%1
if "%duration%"=="" set duration=10
echo 📊 Option 6: Continuous Processing (%duration% minutes)
call :run_with_timing "Continuous Batch" "python batch_processor.py --continuous %duration%"
goto :eof

:run_all
echo 🔄 Running all CPU maximization options sequentially...
echo.
call :run_single
echo.
call :run_parallel
echo.
call :run_batch 3
echo.
call :run_control diagnostic
echo.
call :run_continuous 2
echo.
echo 🎯 All CPU maximization options completed!
goto :eof

REM Main menu
:menu
cls
echo Select CPU maximization option:
echo 1^) Single CPU Maximizer ^(Basic^)
echo 2^) Parallel Orchestrator ^(Agents^)
echo 3^) Batch Processing ^(Multiple cycles^)
echo 4^) CPU Control Center ^(Advanced^)
echo 5^) MAXIMUM OVERDRIVE ^(All systems - Use with caution!^)
echo 6^) Continuous Processing ^(Long-running^)
echo 7^) Run All Options Sequentially
echo 8^) Exit
echo.
set /p choice="Enter choice (1-8): "

if "%choice%"=="1" goto run_single
if "%choice%"=="2" goto run_parallel
if "%choice%"=="3" (
    set /p cycles="Number of cycles [5]: "
    if "%cycles%"=="" set cycles=5
    call :run_batch %cycles%
)
if "%choice%"=="4" (
    set /p mode="Mode (maximum/balanced/diagnostic) [balanced]: "
    if "%mode%"=="" set mode=balanced
    set /p duration="Duration in minutes [5]: "
    if "%duration%"=="" set duration=5
    call :run_control %mode% %duration%
)
if "%choice%"=="5" (
    set /p duration="Duration in minutes [3]: "
    if "%duration%"=="" set duration=3
    call :run_maximum %duration%
)
if "%choice%"=="6" (
    set /p duration="Duration in minutes [10]: "
    if "%duration%"=="" set duration=10
    call :run_continuous %duration%
)
if "%choice%"=="7" goto run_all
if "%choice%"=="8" goto exit
echo Invalid option. Please try again.
timeout /t 2 >nul
goto menu

REM Command line mode
if "%1"=="single" goto run_single
if "%1"=="parallel" goto run_parallel
if "%1"=="batch" (
    if "%2"=="" (call :run_batch 5) else call :run_batch %2
    goto end
)
if "%1"=="control" (
    if "%2"=="" (call :run_control balanced 5) else (
        if "%3"=="" (call :run_control %2 5) else call :run_control %2 %3
    )
    goto end
)
if "%1"=="maximum" (
    if "%2"=="" (call :run_maximum 3) else call :run_maximum %2
    goto end
)
if "%1"=="continuous" (
    if "%2"=="" (call :run_continuous 10) else call :run_continuous %2
    goto end
)
if "%1"=="all" goto run_all

REM If no arguments, show menu
if "%1"=="" goto menu

REM Help
echo Usage: %0 [single^|parallel^|batch [cycles]^|control [mode] [duration]^|maximum [duration]^|continuous [duration]^|all]
echo.
echo Examples:
echo   %0 single                    ^# Basic CPU maximizer
echo   %0 batch 10                  ^# Batch processing with 10 cycles
echo   %0 control maximum 15        ^# Control center in maximum mode for 15 min
echo   %0 maximum 5                 ^# Maximum overdrive for 5 minutes
echo   %0 all                       ^# Run all options sequentially
echo.
echo Or run without arguments for interactive menu.
goto end

:exit
echo Goodbye!

:end
pause