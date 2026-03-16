# Digital Labour Distributed Command Center Launcher
# One-command setup and launch for the entire distributed system

param(
    [switch]$SetupAll,
    [switch]$SetupLocal,
    [switch]$SetupCloud,
    [switch]$Launch,
    [switch]$Status,
    [switch]$Stop,
    [switch]$QuickStart,
    [switch]$Interactive
)

# Colors for PowerShell
$Colors = @{
    Red = [ConsoleColor]::Red
    Green = [ConsoleColor]::Green
    Yellow = [ConsoleColor]::Yellow
    Blue = [ConsoleColor]::Blue
    White = [ConsoleColor]::White
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::White
    )
    $OriginalColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $Color
    Write-Host $Message
    $Host.UI.RawUI.ForegroundColor = $OriginalColor
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput "[INFO] $Message" $Colors.Blue
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "[SUCCESS] $Message" $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "[WARNING] $Message" $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "[ERROR] $Message" $Colors.Red
}

# Detect platform
function Get-Platform {
    if ($IsMacOS) { return "macos" }
    if ($IsLinux) { return "linux" }
    if ($IsWindows -or $env:OS -eq "Windows_NT") { return "windows" }
    return "unknown"
}

$PLATFORM = Get-Platform

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."

    switch ($PLATFORM) {
        "macos" {
            if (!(Get-Command brew -ErrorAction SilentlyContinue)) {
                Write-Error "Homebrew not found. Install from https://brew.sh/"
                exit 1
            }
        }
        "linux" {
            if (!(Get-Command apt-get -ErrorAction SilentlyContinue) -and
                !(Get-Command yum -ErrorAction SilentlyContinue)) {
                Write-Warning "Package manager not detected. Manual installation may be required."
            }
        }
        "windows" {
            if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
                Write-Error "Chocolatey not found. Install from https://chocolatey.org/"
                exit 1
            }
        }
    }

    Write-Success "Prerequisites check passed"
}

# Setup local environment
function Invoke-LocalSetup {
    Write-Info "Setting up local environment..."

    switch ($PLATFORM) {
        "macos" {
            if (Test-Path "setup/macos-setup.sh") {
                & chmod +x setup/macos-setup.sh
                & ./setup/macos-setup.sh
            } else {
                Write-Error "macOS setup script not found"
                exit 1
            }
        }
        "windows" {
            if (Test-Path "setup/windows-setup.ps1") {
                & powershell -ExecutionPolicy Bypass -File setup/windows-setup.ps1
            } else {
                Write-Error "Windows setup script not found"
                exit 1
            }
        }
        "linux" {
            Write-Warning "Linux setup not yet implemented. Please set up manually."
        }
    }

    Write-Success "Local environment setup complete"
}

# Setup cloud infrastructure
function Invoke-CloudSetup {
    Write-Info "Setting up cloud infrastructure..."

    if (!(Get-Command terraform -ErrorAction SilentlyContinue)) {
        Write-Error "Terraform not found. Install from https://terraform.io/"
        exit 1
    }

    if (!(Get-Command aws -ErrorAction SilentlyContinue)) {
        Write-Error "AWS CLI not found. Install from https://aws.amazon.com/cli/"
        exit 1
    }

    Push-Location infrastructure

    # Check AWS credentials
    try {
        aws sts get-caller-identity | Out-Null
    } catch {
        Write-Error "AWS credentials not configured. Run 'aws configure'"
        exit 1
    }

    # Initialize and apply Terraform
    & terraform init
    & terraform validate
    & terraform plan -out=tfplan
    & terraform apply tfplan

    Pop-Location
    Write-Success "Cloud infrastructure setup complete"
}

# Launch services
function Start-Services {
    Write-Info "Launching command center services..."

    # Launch Matrix Monitor
    if ((Test-Path "matrix_monitor.py") -or (Test-Path "matrix_monitor" -PathType Container)) {
        Write-Info "Starting Matrix Monitor..."
        $process = Start-Process python -ArgumentList "-m matrix_monitor" -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath ".matrix_monitor.pid"
    }

    # Launch Operations Interface
    if (Test-Path "operations_launcher.py") {
        Write-Info "Starting Operations Interface..."
        $process = Start-Process python -ArgumentList "operations_launcher.py" -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath ".operations.pid"
    }

    # Launch Galactia Doctrine (if configured)
    if (Test-Path "galactia_config.json") {
        Write-Info "Starting Galactia Doctrine..."
        $process = Start-Process python -ArgumentList "-m galactia_integration" -NoNewWindow -PassThru
        $process.Id | Out-File -FilePath ".galactia.pid"
    }

    # Launch iOS app (if on macOS)
    if (($PLATFORM -eq "macos") -and (Test-Path "ios/DIGITAL LABOURCommand" -PathType Container)) {
        Write-Info "Opening iOS project..."
        & open ios/DIGITAL LABOURCommand/DIGITAL LABOURCommand.xcodeproj
    }

    Write-Success "Services launched successfully"
}

# Show status
function Show-Status {
    Write-Host ""
    Write-Success "Digital Labour Command Center Status"
    Write-Host "====================================="

    # Check local services
    Write-Host "Local Services:"
    if ((Test-Path ".matrix_monitor.pid") -and (Get-Process -Id (Get-Content ".matrix_monitor.pid") -ErrorAction SilentlyContinue)) {
        Write-Host "  ✅ Matrix Monitor: Running (PID: $(Get-Content '.matrix_monitor.pid'))"
    } else {
        Write-Host "  ❌ Matrix Monitor: Not running"
    }

    if ((Test-Path ".operations.pid") -and (Get-Process -Id (Get-Content ".operations.pid") -ErrorAction SilentlyContinue)) {
        Write-Host "  ✅ Operations Interface: Running (PID: $(Get-Content '.operations.pid'))"
    } else {
        Write-Host "  ❌ Operations Interface: Not running"
    }

    if ((Test-Path ".galactia.pid") -and (Get-Process -Id (Get-Content ".galactia.pid") -ErrorAction SilentlyContinue)) {
        Write-Host "  ✅ Galactia Doctrine: Running (PID: $(Get-Content '.galactia.pid'))"
    } else {
        Write-Host "  ❌ Galactia Doctrine: Not running"
    }

    # Check cloud status
    Write-Host ""
    Write-Host "Cloud Infrastructure:"
    if ((Get-Command aws -ErrorAction SilentlyContinue) -and (aws sts get-caller-identity 2>$null)) {
        Write-Host "  ✅ AWS: Configured"

        # Check EC2 instances
        try {
            $instanceCount = aws ec2 describe-instances --filters "Name=tag:Project,Values=Digital Labour" "Name=instance-state-name,Values=running" --query 'length(Reservations[*].Instances[*])' --output text 2>$null
            if (!$instanceCount) { $instanceCount = "0" }
            Write-Host "  📊 EC2 Instances: $instanceCount running"
        } catch {
            Write-Host "  📊 EC2 Instances: Unable to check"
        }

        # Check S3 bucket
        try {
            aws s3 ls s3://Digital-Labour-storage 2>$null | Out-Null
            Write-Host "  ✅ S3 Storage: Available"
        } catch {
            Write-Host "  ❌ S3 Storage: Not accessible"
        }
    } else {
        Write-Host "  ❌ AWS: Not configured"
    }

    Write-Host ""
    Write-Host "Access Points:"
    Write-Host "  🌐 Matrix Monitor: http://localhost:3000"
    Write-Host "  🎯 Operations: http://localhost:5000"
    Write-Host "  📱 iOS App: Open in Xcode (macOS only)"
    Write-Host "  ☁️  Cloud API: Check Terraform outputs"
}

# Stop services
function Stop-Services {
    Write-Info "Stopping command center services..."

    # Stop local services
    $pidFiles = Get-ChildItem ".*.pid" -File
    foreach ($pidFile in $pidFiles) {
        if (Test-Path $pidFile) {
            $pid = Get-Content $pidFile
            if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
                Stop-Process -Id $pid -Force
                Write-Success "Stopped $($pidFile.BaseName.TrimStart('.')) (PID: $pid)"
            }
            Remove-Item $pidFile
        }
    }

    Write-Success "All services stopped"
}

# Show menu
function Show-Menu {
    Write-Host ""
    Write-Host "Digital Labour Command Center Menu"
    Write-Host "================================="
    Write-Host "1. Setup Everything (Local + Cloud)"
    Write-Host "2. Setup Local Only"
    Write-Host "3. Setup Cloud Only"
    Write-Host "4. Launch Services"
    Write-Host "5. Show Status"
    Write-Host "6. Stop Services"
    Write-Host "7. Quick Start (Setup + Launch)"
    Write-Host "8. Exit"
    Write-Host ""
}

# Main logic
function Invoke-Main {
    # Handle command line switches
    if ($SetupAll) {
        Test-Prerequisites
        Invoke-LocalSetup
        Invoke-CloudSetup
        Start-Services
        Show-Status
        return
    }

    if ($SetupLocal) {
        Test-Prerequisites
        Invoke-LocalSetup
        return
    }

    if ($SetupCloud) {
        Invoke-CloudSetup
        return
    }

    if ($Launch) {
        Start-Services
        Show-Status
        return
    }

    if ($Status) {
        Show-Status
        return
    }

    if ($Stop) {
        Stop-Services
        return
    }

    if ($QuickStart) {
        Test-Prerequisites
        Invoke-LocalSetup
        Start-Services
        Show-Status
        return
    }

    # Interactive menu
    while ($true) {
        Show-Menu
        $choice = Read-Host "Choose an option (1-8)"

        switch ($choice) {
            "1" {
                Test-Prerequisites
                Invoke-LocalSetup
                Invoke-CloudSetup
                Start-Services
                Show-Status
            }
            "2" {
                Test-Prerequisites
                Invoke-LocalSetup
            }
            "3" {
                Invoke-CloudSetup
            }
            "4" {
                Start-Services
                Show-Status
            }
            "5" {
                Show-Status
            }
            "6" {
                Stop-Services
            }
            "7" {
                Test-Prerequisites
                Invoke-LocalSetup
                Start-Services
                Show-Status
            }
            "8" {
                Write-Success "Goodbye! 👋"
                exit 0
            }
            default {
                Write-Error "Invalid option. Please choose 1-8."
            }
        }

        Write-Host ""
        Read-Host "Press Enter to continue"
    }
}

# Run main function
Write-Host "🚀 Digital Labour Distributed Command Center"
Write-Host "=========================================="
Write-Host ""

Invoke-Main