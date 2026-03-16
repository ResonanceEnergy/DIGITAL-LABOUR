@echo off
REM Digital Labour Local Runner (Windows)
REM Comprehensive step-by-step execution and monitoring

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "PROGRESS_FILE=%ROOT_DIR%\.dl_progress"
set "MONITORING_DIR=%ROOT_DIR%\monitoring"
set "REPORTS_DIR=%ROOT_DIR%\reports"

REM Create directories
if not exist "%MONITORING_DIR%" mkdir "%MONITORING_DIR%"
if not exist "%REPORTS_DIR%" mkdir "%REPORTS_DIR%"

REM Colors (using color codes)
set "RED=[91m"
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

:log_error
echo %RED%[ERROR]%NC% %~1
goto :eof

:log_header
echo %PURPLE%========================================%NC%
echo %PURPLE%%~1%NC%
echo %PURPLE%========================================%NC%
goto :eof

:update_progress
set "step=%~1"
set "status=%~2"
set "details=%~3"
echo %date% %time%^|%step%^|%status%^|%details% >> "%PROGRESS_FILE%"

if "%status%"=="STARTED" (
    call :log_info "Started: %step%"
) else if "%status%"=="COMPLETED" (
    call :log_success "Completed: %step%"
) else if "%status%"=="FAILED" (
    call :log_error "Failed: %step% - %details%"
)
goto :eof

:check_dependencies
call :log_header "CHECKING DEPENDENCIES"

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    call :log_success "Python found: !PYTHON_VERSION!"
) else (
    call :log_error "Python not found. Please install Python 3.7+"
    exit /b 1
)

REM Check required packages
call :log_info "Checking Python packages..."
python -c "import flask, multiprocessing, sqlite3, json" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    call :log_success "Required Python packages available"
) else (
    call :log_warning "Some Python packages may be missing"
    if exist "%ROOT_DIR%\repos\AAC\requirements.txt" (
        pip install -r "%ROOT_DIR%\repos\AAC\requirements.txt" >nul 2>&1
        if %ERRORLEVEL% neq 0 (
            call :log_warning "Could not install AAC requirements"
        )
    )
)

REM Check system resources
for /f "tokens=*" %%i in ('wmic cpu get NumberOfCores /value ^| find "NumberOfCores"') do set %%i
set CPU_CORES=%NumberOfCores%
if "%CPU_CORES%"=="" set CPU_CORES=Unknown

for /f "tokens=2" %%i in ('systeminfo ^| find "Total Physical Memory"') do set TOTAL_MEM=%%i
if "%TOTAL_MEM%"=="" set TOTAL_MEM=Unknown

call :log_info "System Resources: %CPU_CORES% CPU cores, %TOTAL_MEM% RAM"
goto :eof

:start_inner_council
call :log_header "STARTING INNER COUNCIL"

call :update_progress "inner_council" "STARTED" "Deploying autonomous agents"

cd /d "%ROOT_DIR%\inner_council"

REM Start Inner Council agents
call :log_info "Deploying Inner Council agents..."
python deploy_agents.py --mode deploy --duration 300
if %ERRORLEVEL% equ 0 (
    call :update_progress "inner_council" "COMPLETED" "Agents deployed successfully"
    call :log_success "Inner Council agents deployed"
) else (
    call :update_progress "inner_council" "FAILED" "Agent deployment failed"
    call :log_error "Inner Council deployment failed"
    goto :eof
)
goto :eof

:start_aac_system
call :log_header "STARTING AAC FINANCIAL SYSTEM"

call :update_progress "aac_system" "STARTED" "Initializing financial operations"

cd /d "%ROOT_DIR%\repos\AAC"

REM Initialize AAC database
call :log_info "Initializing AAC accounting engine..."
python aac_engine.py
if %ERRORLEVEL% equ 0 (
    call :log_success "AAC engine initialized"
) else (
    call :log_error "AAC engine initialization failed"
    call :update_progress "aac_system" "FAILED" "Engine initialization failed"
    goto :eof
)

REM Start compliance monitoring
call :log_info "Starting compliance monitoring..."
start /B python aac_compliance.py >nul 2>&1
echo %ERRORLEVEL% > "%MONITORING_DIR%\compliance.pid"

REM Start financial intelligence
call :log_info "Starting financial intelligence..."
start /B python aac_intelligence.py >nul 2>&1
echo %ERRORLEVEL% > "%MONITORING_DIR%\intelligence.pid"

REM Start web dashboard
call :log_info "Starting AAC web dashboard..."
start /B python run_aac.py --web >nul 2>&1
echo %ERRORLEVEL% > "%MONITORING_DIR%\aac_web.pid"

call :update_progress "aac_system" "COMPLETED" "AAC system fully operational"
call :log_success "AAC system started - Dashboard at http://localhost:5000"
goto :eof

:start_cpu_maximization
set "mode=%~1"
set "duration=%~2"

if "%mode%"=="" set "mode=balanced"
if "%duration%"=="" set "duration=10"

call :log_header "STARTING CPU MAXIMIZATION (%mode% mode, %duration%min)"

call :update_progress "cpu_maximization" "STARTED" "Mode: %mode%, Duration: %duration%min"

cd /d "%ROOT_DIR%"

call :log_info "Starting CPU maximization in %mode% mode..."
python cpu_control_center.py "%mode%" --duration "%duration%"
if %ERRORLEVEL% equ 0 (
    call :update_progress "cpu_maximization" "COMPLETED" "CPU maximization completed successfully"
    call :log_success "CPU maximization completed"
) else (
    call :update_progress "cpu_maximization" "FAILED" "CPU maximization failed"
    call :log_error "CPU maximization failed"
)
goto :eof

:run_daily_operations
call :log_header "RUNNING DAILY OPERATIONS"

call :update_progress "daily_operations" "STARTED" "Executing daily operational cycle"

cd /d "%ROOT_DIR%"

call :log_info "Running daily operations cycle..."
call bin\run_daily.sh
if %ERRORLEVEL% equ 0 (
    call :update_progress "daily_operations" "COMPLETED" "Daily operations completed"
    call :log_success "Daily operations completed"
) else (
    call :update_progress "daily_operations" "FAILED" "Daily operations failed"
    call :log_error "Daily operations failed"
)
goto :eof

:monitor_system
set "duration=%~1"
if "%duration%"=="" set "duration=300"

call :log_header "SYSTEM MONITORING ACTIVE"

call :log_info "Starting system monitoring for %duration%s..."

REM Create monitoring script
echo @echo off > "%MONITORING_DIR%\monitor.bat"
echo :loop >> "%MONITORING_DIR%\monitor.bat"
echo for /f "tokens=*" %%i in ('powershell -command "Get-Counter '\Processor(_Total)\%% Processor Time' -SampleInterval 1 -MaxSamples 1 ^| Select-Object -ExpandProperty CounterSamples ^| Select-Object -ExpandProperty CookedValue" 2^>nul') do set cpu=%%i >> "%MONITORING_DIR%\monitor.bat"
echo if "!cpu!"=="" set cpu=Unknown >> "%MONITORING_DIR%\monitor.bat"
echo for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /nh ^| find /c "python.exe"') do set proc=%%i >> "%MONITORING_DIR%\monitor.bat"
echo echo !date! !time!^|CPU:!cpu!%%^|PROCESSES:!proc! >> "%MONITORING_DIR%\system_metrics.log" >> "%MONITORING_DIR%\monitor.bat"
echo timeout /t 5 /nobreak ^>nul >> "%MONITORING_DIR%\monitor.bat"
echo goto loop >> "%MONITORING_DIR%\monitor.bat"

REM Run monitoring in background
start /B "%MONITORING_DIR%\monitor.bat"

REM Wait for specified duration
timeout /t %duration% /nobreak >nul

REM Stop monitoring
taskkill /f /im cmd.exe /fi "windowtitle eq %MONITORING_DIR%\monitor.bat" >nul 2>&1

call :log_success "Monitoring completed - check %MONITORING_DIR%\system_metrics.log"
goto :eof

:generate_reports
call :log_header "GENERATING SYSTEM REPORTS"

call :update_progress "report_generation" "STARTED" "Creating comprehensive reports"

set "timestamp=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "timestamp=%timestamp: =0%"
set "report_file=%REPORTS_DIR%\DL_REPOrt_%timestamp%.md"

echo # Digital Labour System Report > "%report_file%"
echo **Generated:** %date% %time% >> "%report_file%"
echo **Duration:** Session run >> "%report_file%"
echo **Status:** Active >> "%report_file%"
echo. >> "%report_file%"
echo ## System Status >> "%report_file%"

REM Add system information
echo ### System Resources >> "%report_file%"
echo - CPU Cores: %CPU_CORES% >> "%report_file%"
echo - Total Memory: %TOTAL_MEM% >> "%report_file%"
for /f "tokens=3" %%i in ('dir /-c %ROOT_DIR% ^| find "bytes free"') do set free_space=%%i
echo - Disk Free: !free_space! bytes >> "%report_file%"

REM Add progress information
echo. >> "%report_file%"
echo ### Progress Summary >> "%report_file%"
if exist "%PROGRESS_FILE%" (
    echo ^| Timestamp ^| Step ^| Status ^| Details ^| >> "%report_file%"
    echo ^|-----------^|------^|--------^|---------^| >> "%report_file%"
    powershell -command "Get-Content '%PROGRESS_FILE%' | Select-Object -Last 20 | ForEach-Object { $fields = $_.Split('|'); \"| $($fields[0]) | $($fields[1]) | $($fields[2]) | $($fields[3]) |\" }" >> "%report_file%"
)

REM Add performance metrics
if exist "%MONITORING_DIR%\system_metrics.log" (
    echo. >> "%report_file%"
    echo ### Performance Metrics >> "%report_file%"
    echo ``` >> "%report_file%"
    powershell -command "Get-Content '%MONITORING_DIR%\system_metrics.log' | Select-Object -Last 10" >> "%report_file%"
    echo ``` >> "%report_file%"
)

call :log_success "Report generated: %report_file%"
call :update_progress "report_generation" "COMPLETED" "Report saved to %report_file%"
goto :eof

:run_youtube_intelligence
call :log_header "STARTING YOUTUBE INTELLIGENCE MONITOR"

call :update_progress "youtube_intelligence" "STARTED" "Monitoring thought leader channels"

cd /d "%ROOT_DIR%"

call :log_info "Running YouTube intelligence monitor..."
call youtube_monitor.bat run

if %ERRORLEVEL% equ 0 (
    call :update_progress "youtube_intelligence" "COMPLETED" "Intelligence gathering completed"
    call :log_success "YouTube intelligence monitoring completed"
) else (
    call :update_progress "youtube_intelligence" "FAILED" "Intelligence monitoring failed"
    call :log_warning "YouTube intelligence monitoring encountered issues"
)
goto :eof

:show_menu
echo.
call :log_header "Digital Labour LOCAL RUNNER (WINDOWS)"
echo 1^) Run Full System ^(Recommended^)
echo 2^) Start Inner Council Only
echo 3^) Start AAC System Only
echo 4^) Run CPU Maximization Only
echo 5^) Run Daily Operations
echo 6^) Monitor System ^(5 minutes^)
echo 7^) Run Inner Council Intelligence
echo 8^) Generate Reports
echo 9^) Cleanup Processes
echo 10^) Exit
echo.
goto :eof

:run_full_system
call :log_header "RUNNING FULL Digital Labour SYSTEM"

call :update_progress "full_system" "STARTED" "Complete system deployment"

REM Step 1: Check dependencies
call :check_dependencies

REM Step 2: Start Inner Council
call :start_inner_council

REM Step 3: Start AAC System
call :start_aac_system

REM Step 4: Run CPU Maximization
call :start_cpu_maximization "balanced" "5"

REM Step 5: Run Daily Operations
call :run_daily_operations

REM Step 6: Generate Reports
call :generate_reports

call :update_progress "full_system" "COMPLETED" "Full system run completed"
call :log_success "Full Digital Labour system run completed!"
goto :eof

REM Main execution
if "%1"=="full" goto run_full_system
if "%1"=="council" (call :check_dependencies && goto start_inner_council)
if "%1"=="aac" (call :check_dependencies && goto start_aac_system)
if "%1"=="cpu" (call :check_dependencies && call :start_cpu_maximization "%~2" "%~3" && goto :eof)
if "%1"=="daily" (call :check_dependencies && goto run_daily_operations)
if "%1"=="monitor" (call :monitor_system "%~2" && goto :eof)
if "%1"=="youtube" (goto run_inner_council)
if "%1"=="reports" (goto generate_reports)
if "%1"=="cleanup" (goto cleanup_processes)
if "%1"=="deps" (goto check_dependencies)

REM Interactive mode
:menu_loop
call :show_menu
set /p choice="Select option (1-9): "

if "%choice%"=="1" goto run_full_system
if "%choice%"=="2" (call :check_dependencies && goto start_inner_council)
if "%choice%"=="3" (call :check_dependencies && goto start_aac_system)
if "%choice%"=="4" (
    set /p mode="Mode (maximum/balanced/diagnostic) [balanced]: "
    if "!mode!"=="" set "mode=balanced"
    set /p duration="Duration in minutes [5]: "
    if "!duration!"=="" set "duration=5"
    call :check_dependencies && call :start_cpu_maximization "!mode!" "!duration!"
)
if "%choice%"=="5" (call :check_dependencies && goto run_daily_operations)
if "%choice%"=="6" (
    set /p duration="Monitoring duration in seconds [300]: "
    if "!duration!"=="" set "duration=300"
    call :monitor_system "!duration!"
)
if "%choice%"=="7" goto run_inner_council
if "%choice%"=="8" goto generate_reports
if "%choice%"=="9" goto cleanup_processes
if "%choice%"=="10" (call :log_info "Goodbye!" && goto :eof)

call :log_warning "Invalid option. Please try again."
goto menu_loop

REM ========================================
REM Inner Council Intelligence Functions
REM ========================================

:run_inner_council
call :log_header "Inner Council Intelligence System"
call :log_info "Starting Inner Council intelligence gathering session..."

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Python not found. Please install Python 3.x"
    goto :eof
)

REM Check if config file exists
if not exist "inner_council_config.json" (
    call :log_error "inner_council_config.json not found. Please ensure the Inner Council is properly configured."
    goto :eof
)

REM Run the Inner Council intelligence system
call :log_info "Running Inner Council intelligence monitor..."
python youtube_intelligence_monitor.py

if errorlevel 1 (
    call :log_error "Inner Council intelligence session failed."
    goto :eof
)

call :log_success "Inner Council intelligence session completed successfully."
call :log_info "Check inner_council_intelligence/ directory for reports."
goto :eof

goto :eof