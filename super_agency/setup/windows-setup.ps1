# Bit Rage Systems Windows Build Environment Setup
# Run this script as Administrator in PowerShell

param(
    [switch]$SkipVSCode,
    [switch]$SkipDocker,
    [switch]$SkipGitHubCLI
)

Write-Host "🚀 Bit Rage Systems Windows Build Environment Setup" -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue

# Check if running as administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "❌ Please run this script as Administrator" -ForegroundColor Red
    exit 1
}

# Function to write colored output
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Install Chocolatey if not installed
function Install-Chocolatey {
    Write-Info "Checking Chocolatey installation..."
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Info "Installing Chocolatey..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
        Write-Success "Chocolatey installed"
    } else {
        Write-Success "Chocolatey already installed"
    }
}

# Install development tools
function Install-DevTools {
    Write-Info "Installing development tools..."

    # Update Chocolatey
    choco upgrade chocolatey

    # Install Python
    choco install python311 -y
    Write-Success "Python 3.11 installed"

    # Install Git
    choco install git -y
    Write-Success "Git installed"

    # Install GitHub CLI
    if (-not $SkipGitHubCLI) {
        choco install gh -y
        Write-Success "GitHub CLI installed"
    }

    # Install Node.js
    choco install nodejs -y
    Write-Success "Node.js installed"

    # Install Docker Desktop
    if (-not $SkipDocker) {
        choco install docker-desktop -y
        Write-Success "Docker Desktop installed"
    }

    # Install VS Code
    if (-not $SkipVSCode) {
        choco install vscode -y
        Write-Success "VS Code installed"
    }

    # Install build tools
    choco install cmake -y
    choco install visualstudio2019buildtools -y
    Write-Success "Build tools installed"
}

# Set up Bit Rage Systems project
function Setup-SuperAgency {
    Write-Info "Setting up Bit Rage Systems project..."

    # Create Bit Rage Systems directory
    $superAgencyDir = "$env:USERPROFILE\Super-Agency"
    if (-not (Test-Path $superAgencyDir)) {
        New-Item -ItemType Directory -Path $superAgencyDir -Force
        Write-Success "Bit Rage Systems directory created"
    } else {
        Write-Warning "Bit Rage Systems directory already exists"
    }

    Set-Location $superAgencyDir

    # Clone or update repository
    if (-not (Test-Path ".git")) {
        Write-Info "Cloning Bit Rage Systems repository..."
        gh repo clone ResonanceEnergy/Super-Agency .
        Write-Success "Repository cloned"
    } else {
        Write-Info "Updating existing repository..."
        git pull origin main
        Write-Success "Repository updated"
    }

    # Set up Python virtual environment
    if (-not (Test-Path "venv")) {
        Write-Info "Creating Python virtual environment..."
        python -m venv venv
        Write-Success "Virtual environment created"
    }

    # Activate virtual environment and install dependencies
    Write-Info "Installing Python dependencies..."
    & ".\venv\Scripts\Activate.ps1"

    # Upgrade pip
    python -m pip install --upgrade pip

    # Install requirements if they exist
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt
        Write-Success "Python dependencies installed"
    } else {
        Write-Warning "requirements.txt not found, installing basic packages"
        pip install requests python-dotenv pyyaml pywin32
    }

    # Install development dependencies
    if (Test-Path "requirements-dev.txt") {
        pip install -r requirements-dev.txt
    }

    # Install build-specific packages
    pip install pyinstaller cx_Freeze nuitka
    Write-Success "Build tools installed"
}

# Configure VS Code
function Setup-VSCode {
    if ($SkipVSCode) {
        Write-Info "Skipping VS Code setup"
        return
    }

    Write-Info "Configuring VS Code..."

    # Install essential extensions
    $extensions = @(
        "ms-python.python",
        "ms-vscode.vscode-json",
        "github.copilot",
        "ms-vscode-remote.remote-ssh",
        "ms-vscode.vscode-typescript-next",
        "esbenp.prettier-vscode",
        "ms-vscode-remote.remote-containers",
        "github.copilot-chat",
        "ms-vscode.cmake-tools",
        "ms-vscode.cpptools"
    )

    foreach ($extension in $extensions) {
        code --install-extension $extension
    }

    Write-Success "VS Code extensions installed"

    # Create workspace settings
    $settings = @{
        "python.defaultInterpreterPath" = "./venv/Scripts/python.exe"
        "python.terminal.activateEnvironment" = $true
        "python.linting.enabled" = $true
        "python.linting.pylintEnabled" = $true
        "python.formatting.provider" = "black"
        "editor.formatOnSave" = $true
        "editor.codeActionsOnSave" = @{
            "source.organizeImports" = $true
        }
        "git.autofetch" = $true
        "git.enableSmartCommit" = $true
        "github.copilot.enable" = @{
            "*" = $true
        }
        "cmake.configureOnOpen" = $true
        "C_Cpp.default.compilerPath" = "cl.exe"
    }

    $settings | ConvertTo-Json -Depth 10 | Out-File -FilePath ".vscode\settings.json" -Encoding UTF8

    Write-Success "VS Code workspace settings configured"
}

# Set up build environment
function Setup-BuildEnvironment {
    Write-Info "Setting up build environment..."

    # Create build directories
    $buildDirs = @("build", "dist", "artifacts", "temp")
    foreach ($dir in $buildDirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force
        }
    }

    # Create build configuration
    $buildConfig = @{
        "build" = @{
            "python_version" = "3.11"
            "target_platforms" = @("win_amd64", "win32")
            "build_tools" = @("pyinstaller", "cx_Freeze", "nuitka")
            "output_formats" = @("exe", "msi", "app")
        }
        "cross_compilation" = @{
            "enabled" = $true
            "target_architectures" = @("x86", "x64", "arm64")
            "mingw_support" = $true
        }
        "ci_cd" = @{
            "github_actions" = $true
            "azure_devops" = $false
            "appveyor" = $false
        }
        "testing" = @{
            "unit_tests" = $true
            "integration_tests" = $true
            "performance_tests" = $false
            "cross_platform_tests" = $true
        }
    }

    $buildConfig | ConvertTo-Json -Depth 10 | Out-File -FilePath "build_config.json" -Encoding UTF8

    Write-Success "Build environment configured"
}

# Set up CI/CD integration
function Setup-CICD {
    Write-Info "Setting up CI/CD integration..."

    # Create GitHub Actions workflow directory
    $githubDir = ".github"
    $workflowsDir = "$githubDir\workflows"

    if (-not (Test-Path $githubDir)) {
        New-Item -ItemType Directory -Path $githubDir -Force
    }
    if (-not (Test-Path $workflowsDir)) {
        New-Item -ItemType Directory -Path $workflowsDir -Force
    }

    # Create CI/CD workflow
    $workflow = @"
name: Bit Rage Systems Windows CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  test:
    runs-on: windows-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        pytest tests/ -v --cov=super_agency --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: windows-latest
    strategy:
      matrix:
        python-version: [3.11]
        architecture: [x64, x86]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        architecture: ${{ matrix.architecture }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller cx_Freeze

    - name: Build executable
      run: |
        # PyInstaller build
        pyinstaller --onefile --name super-agency-windows-${{ matrix.architecture }} operations_launcher.py

        # cx_Freeze build
        cxfreeze operations_launcher.py --target-dir dist/cx_freeze

    - name: Upload build artifacts
      uses: actions/upload-artifact@v3
      with:
        name: super-agency-windows-${{ matrix.python-version }}-${{ matrix.architecture }}
        path: |
          dist/
          build/

  deploy:
    needs: build
    runs-on: windows-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    steps:
    - name: Download build artifacts
      uses: actions/download-artifact@v3
      with:
        path: ./artifacts

    - name: Create release
      uses: actions/create-release@v1
      id: create_release
      with:
        draft: false
        prerelease: false
        release_name: Bit Rage Systems v${{ github.run_number }}
        tag_name: v${{ github.run_number }}
      env:
        GITHUB_TOKEN: ${{ github.token }}

    - name: Upload release assets
      uses: actions/upload-release-asset@v1
      env:
        GITHUB_TOKEN: ${{ github.token }}
      with:
        upload_url: ${{ steps.create_release.outputs.upload_url }}
        asset_path: ./artifacts/super-agency-windows-3.11-x64/super-agency-windows-3.11-x64.exe
        asset_name: super-agency-windows-x64.exe
        asset_content_type: application/octet-stream
"@

    $workflow | Out-File -FilePath "$workflowsDir\windows-ci-cd.yml" -Encoding UTF8

    Write-Success "CI/CD integration configured"
}

# Create launch scripts
function Create-LaunchScripts {
    Write-Info "Creating launch scripts..."

    # Create main launch script
    $launchScript = @"
# Bit Rage Systems Windows Command Center Launcher
Write-Host "🚀 Bit Rage Systems Windows Command Center" -ForegroundColor Blue
Write-Host "=========================================" -ForegroundColor Blue

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "❌ Virtual environment not found. Run setup first." -ForegroundColor Red
    exit 1
}

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1"

# Launch Operations Interface
Write-Host "🎯 Starting Operations Interface..." -ForegroundColor Green
Start-Process -FilePath "python" -ArgumentList "operations_launcher.py" -NoNewWindow

# Launch build monitor (if available)
if (Test-Path "build_monitor.py") {
    Write-Host "🔨 Starting Build Monitor..." -ForegroundColor Green
    Start-Process -FilePath "python" -ArgumentList "build_monitor.py" -NoNewWindow
}

Write-Host "✅ Windows Command Center launched!" -ForegroundColor Green
Write-Host "🎯 Operations Interface: Running" -ForegroundColor Cyan
Write-Host "" -ForegroundColor White
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow

# Wait for user interrupt
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "🛑 Shutting down Command Center..." -ForegroundColor Yellow
    Get-Process -Name "python" | Where-Object { $_.MainWindowTitle -like "*Bit Rage Systems*" } | Stop-Process -Force
}
"@

    $launchScript | Out-File -FilePath "launch_command_center.ps1" -Encoding UTF8

    # Create build script
    $buildScript = @"
# Bit Rage Systems Windows Build Script
param(
    [string]$Tool = "pyinstaller",
    [string]$Target = "operations_launcher.py",
    [switch]$Clean,
    [switch]$Test
)

Write-Host "🔨 Bit Rage Systems Windows Build" -ForegroundColor Blue
Write-Host "==============================" -ForegroundColor Blue

if ($Clean) {
    Write-Host "🧹 Cleaning build directories..." -ForegroundColor Yellow
    Remove-Item -Path "build", "dist" -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path "build", "dist" -Force | Out-Null
}

# Activate virtual environment
if (Test-Path "venv") {
    & ".\venv\Scripts\Activate.ps1"
}

if ($Test) {
    Write-Host "🧪 Running tests..." -ForegroundColor Green
    pytest tests/ -v
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Tests failed!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "🔨 Building with $Tool..." -ForegroundColor Green

switch ($Tool) {
    "pyinstaller" {
        pyinstaller --onefile --name super-agency-windows --clean $Target
    }
    "cx_Freeze" {
        cxfreeze $Target --target-dir dist/cx_freeze
    }
    "nuitka" {
        python -m nuitka --onefile --output-dir=dist $Target
    }
    default {
        Write-Host "❌ Unknown build tool: $Tool" -ForegroundColor Red
        exit 1
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build completed successfully!" -ForegroundColor Green
    Get-ChildItem -Path "dist" -Recurse
} else {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}
"@

    $buildScript | Out-File -FilePath "build_windows.ps1" -Encoding UTF8

    Write-Success "Launch and build scripts created"
}

# Main setup function
function Main {
    Write-Host ""
    Write-Info "Starting Bit Rage Systems Windows Build Environment Setup..."
    Write-Host ""

    Install-Chocolatey
    Install-DevTools
    Setup-SuperAgency
    Setup-VSCode
    Setup-BuildEnvironment
    Setup-CICD
    Create-LaunchScripts

    Write-Host ""
    Write-Success "🎉 Bit Rage Systems Windows Build Environment Setup Complete!"
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Run: .\launch_command_center.ps1" -ForegroundColor White
    Write-Host "2. Open VS Code: code ." -ForegroundColor White
    Write-Host "3. Configure API keys in environment variables" -ForegroundColor White
    Write-Host "4. Set up GitHub authentication: gh auth login" -ForegroundColor White
    Write-Host "5. Build: .\build_windows.ps1 -Test -Tool pyinstaller" -ForegroundColor White
    Write-Host ""
    Write-Host "Happy building! 🔨⚡🤖" -ForegroundColor Green
}

# Run main setup
Main