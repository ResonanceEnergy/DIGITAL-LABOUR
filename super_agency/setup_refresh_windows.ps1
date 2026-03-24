# Bit Rage Systems Cross-Platform Refresh Setup - Windows (QUANTUM FORGE)
# Installs and configures the 5-minute refresh system using Task Scheduler

param(
    [string]$TaskName = "SuperAgency CrossPlatform Refresh",
    [string]$ScriptDir = $PSScriptRoot,
    [string]$LogFile = "$ScriptDir\logs\setup_refresh_windows.log"
)

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logMessage = "[$timestamp] Starting Cross-Platform Refresh setup on QUANTUM FORGE"

# Ensure log directory exists
$logDir = Split-Path $LogFile -Parent
if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Function to log messages
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $logEntry
    Write-Host $logEntry
}

Write-Log "Setting up Cross-Platform Refresh on QUANTUM FORGE (Windows)"
Write-Log "==========================================================="

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Log "Python found: $pythonVersion"
} catch {
    Write-Log "Python not found. Please install Python 3 first." "ERROR"
    exit 1
}

# Test the refresh script
Write-Log "Testing refresh script..."
try {
    $testResult = & python "$ScriptDir\cross_platform_refresh.py"
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Refresh script test passed"
    } else {
        Write-Log "Refresh script test failed with exit code: $LASTEXITCODE" "ERROR"
        exit 1
    }
} catch {
    Write-Log "Failed to test refresh script: $($_.Exception.Message)" "ERROR"
    exit 1
}

# Check if running as administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Log "Please run this script as Administrator to create scheduled tasks." "WARNING"
    Write-Log "You can still create the task manually using Task Scheduler." "INFO"
    $createTask = $false
} else {
    $createTask = $true
}

if ($createTask) {
    Write-Log "Creating scheduled task..."

    # Remove existing task if it exists
    try {
        schtasks /delete /tn "$TaskName" /f 2>$null
        Write-Log "Removed existing task"
    } catch {
        # Task didn't exist, that's fine
    }

    # Create new scheduled task
    $taskCommand = "powershell.exe"
    $taskArgs = "-ExecutionPolicy Bypass -File `"$ScriptDir\cross_platform_refresh_windows.ps1`""

    $createTaskCmd = @"
schtasks /create /tn "$TaskName" /tr "$taskCommand $taskArgs" /sc minute /mo 5 /rl highest /f
"@

    try {
        Invoke-Expression $createTaskCmd
        Write-Log "Scheduled task created successfully"
    } catch {
        Write-Log "Failed to create scheduled task: $($_.Exception.Message)" "ERROR"
        Write-Log "You can create it manually using Task Scheduler" "INFO"
    }

    # Verify task was created
    try {
        $taskInfo = schtasks /query /tn "$TaskName" 2>$null
        if ($taskInfo) {
            Write-Log "Task verification successful"
        }
    } catch {
        Write-Log "Task verification failed" "WARNING"
    }
} else {
    Write-Log "Skipping task creation - not running as Administrator"
    Write-Log "Manual setup instructions:" "INFO"
    Write-Log "1. Open Task Scheduler" "INFO"
    Write-Log "2. Create new task: $TaskName" "INFO"
    Write-Log "3. Set trigger: Every 5 minutes" "INFO"
    Write-Log "4. Set action: Start program - powershell.exe" "INFO"
    Write-Log "5. Add argument: -ExecutionPolicy Bypass -File `"$ScriptDir\cross_platform_refresh_windows.ps1`"" "INFO"
}

Write-Log ""
Write-Log "Cross-Platform Refresh setup complete!" "SUCCESS"
Write-Log "========================================" "SUCCESS"
Write-Log "Task Name: $TaskName" "INFO"
Write-Log "Runs every: 5 minutes" "INFO"
Write-Log "Script: $ScriptDir\cross_platform_refresh_windows.ps1" "INFO"
Write-Log "Logs: $ScriptDir\logs\" "INFO"

if ($createTask) {
    Write-Log ""
    Write-Log "To check status: schtasks /query /tn `"$TaskName`"" "INFO"
    Write-Log "To run manually: schtasks /run /tn `"$TaskName`"" "INFO"
    Write-Log "To delete: schtasks /delete /tn `"$TaskName`"" "INFO"
}

Write-Log "Setup completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "SUCCESS"</content>
<parameter name="filePath">$HOME/repos/SuperAgency-Shared/setup_refresh_windows.ps1