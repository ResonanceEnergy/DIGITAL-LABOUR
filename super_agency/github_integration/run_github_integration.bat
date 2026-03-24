@echo off
REM Bit Rage Systems GitHub Integration Runner (Windows)
REM Usage: run_github_integration.bat [command] [options]

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Colors (using Windows color codes)
set RED=[91m
set GREEN=[92m
set YELLOW=[93m
set BLUE=[94m
set PURPLE=[95m
set CYAN=[96m
set NC=[0m

:log_info
echo [INFO] %TIME% - %~1
goto :eof

:log_success
echo [SUCCESS] %TIME% - %~1
goto :eof

:log_warning
echo [WARNING] %TIME% - %~1
goto :eof

:log_error
echo [ERROR] %TIME% - %~1
goto :eof

REM Check prerequisites
:check_prerequisites
call :log_info "Checking prerequisites..."

REM Check if GitHub CLI is installed
gh --version >nul 2>&1
if %errorlevel% neq 0 (
    call :log_error "GitHub CLI (gh) is not installed. Please install it first:"
    call :log_error "  - Download from: https://cli.github.com/"
    exit /b 1
)

REM Check if user is authenticated
gh auth status >nul 2>&1
if %errorlevel% neq 0 (
    call :log_warning "GitHub CLI is not authenticated. Running setup..."
    gh auth login
)

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :log_error "Python is not available. Please install Python."
    exit /b 1
)

call :log_success "Prerequisites check passed"
goto :eof

REM Setup virtual environment
:setup_venv
call :log_info "Setting up virtual environment..."

if not exist "venv" (
    python -m venv venv
    call :log_success "Virtual environment created"
)

call venv\Scripts\activate.bat
pip install -q -r requirements.txt
call :log_success "Dependencies installed"
goto :eof

REM Main command processing
set COMMAND=%1
if "%COMMAND%"=="" set COMMAND=help
shift

if "%COMMAND%"=="sync" (
    call :log_info "Syncing portfolio repositories..."
    call :check_prerequisites
    call :setup_venv
    python github_integration_system.py
) else if "%COMMAND%"=="create" (
    set REPO_NAME=%1
    if "!REPO_NAME!"=="" (
        call :log_error "Repository name required. Usage: run_github_integration.bat create <repo-name>"
        exit /b 1
    )
    call :log_info "Creating repository: !REPO_NAME!"
    call :check_prerequisites
    call :setup_venv
    python -c "
from github_integration_system import GitHubIntegrationSystem
system = GitHubIntegrationSystem()
system.create_repository('!REPO_NAME!', '!REPO_NAME! - Bit Rage Systems Project', True)
"
) else if "%COMMAND%"=="setup" (
    set REPO_NAME=%1
    if "!REPO_NAME!"=="" (
        call :log_error "Repository name required. Usage: run_github_integration.bat setup <repo-name>"
        exit /b 1
    )
    call :log_info "Setting up repository: !REPO_NAME!"
    call :check_prerequisites
    call :setup_venv
    python -c "
from github_integration_system import GitHubIntegrationSystem
system = GitHubIntegrationSystem()
system.setup_repository_protection('!REPO_NAME!')
system.setup_security_features('!REPO_NAME!')
"
) else if "%COMMAND%"=="pr" (
    set REPO_NAME=%1
    set TITLE=%2
    set BODY=%3
    if "!REPO_NAME!"=="" if "!TITLE!"=="" (
        call :log_error "Usage: run_github_integration.bat pr <repo-name> <title> <body>"
        exit /b 1
    )
    call :log_info "Creating PR in !REPO_NAME!: !TITLE!"
    call :check_prerequisites
    call :setup_venv
    python -c "
from github_integration_system import GitHubIntegrationSystem
system = GitHubIntegrationSystem()
system.create_pull_request('!REPO_NAME!', '!TITLE!', '!BODY!', 'feature-branch')
"
) else (
    echo Bit Rage Systems GitHub Integration Runner
    echo Usage: run_github_integration.bat [command] [options]
    echo.
    echo Commands:
    echo   sync                    Sync all portfolio repositories
    echo   create ^<repo-name^>      Create a new repository
    echo   setup ^<repo-name^>       Setup protection and security for repository
    echo   pr ^<repo-name^> ^<title^> ^<body^>  Create a pull request
    echo   help                    Show this help message
    echo.
    echo Examples:
    echo   run_github_integration.bat sync
    echo   run_github_integration.bat create my-new-project
    echo   run_github_integration.bat setup my-project
)