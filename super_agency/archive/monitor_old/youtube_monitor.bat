@echo off
REM Inner Council Intelligence Monitor Runner
REM Monitors Inner Council YouTube channels for daily policy adjustments

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "DATA_DIR=%ROOT_DIR%\inner_council_intelligence"
set "POLICY_DIR=%ROOT_DIR%\daily_policy_directives"
set "REPORTS_DIR=%ROOT_DIR%\reports"

REM Create directories
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%POLICY_DIR%" mkdir "%POLICY_DIR%"
if not exist "%REPORTS_DIR%" mkdir "%REPORTS_DIR%"

REM Colors
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "PURPLE=[95m"
set "CYAN=[96m"
set "NC=[0m"

:log_info
echo %BLUE%[INFO]%NC% %~1
goto :eof

:log_success
echo %GREEN%[SUCCESS]%NC% %~1
goto :eof

:log_warning
echo %YELLOW%[WARNING]%NC% %~1
goto :eof

:run_inner_council
call :log_info "Starting Inner Council Intelligence Session..."

cd /d "%ROOT_DIR%"

REM Check if config exists
if not exist "inner_council_config.json" (
    call :log_warning "Configuration file not found: inner_council_config.json"
    goto :eof
)

REM Run the Inner Council intelligence monitor
python youtube_intelligence_monitor.py

if %ERRORLEVEL% equ 0 (
    call :log_success "Inner Council intelligence session completed"
) else (
    call :log_warning "Inner Council intelligence session encountered issues"
)
goto :eof

REM Main execution
if "%1"=="run" goto run_inner_council

REM Default: run Inner Council session
goto run_inner_council