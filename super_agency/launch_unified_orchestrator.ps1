# Unified Digital Labour Orchestrator Launcher
# Bypasses QUSAR interception and launches the integrated monitoring system

param(
    [switch]$Start,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Restart,
    [string]$ConfigFile = "unified_orchestrator_config.json",
    [int]$Port = 5000
)

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$OrchestratorScript = Join-Path $ScriptPath "unified_digital_labour_orchestrator.py"
$ConfigPath = Join-Path $ScriptPath $ConfigFile
$LogFile = Join-Path $ScriptPath "logs\unified_orchestrator_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$PidFile = Join-Path $ScriptPath "unified_orchestrator.pid"

# Ensure log directory exists
$LogDir = Split-Path $LogFile -Parent
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

function Test-PythonEnvironment {
    try {
        $pythonVersion = & python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)\.") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -ge 3 -and $minor -ge 8) {
                Write-Log "Python environment validated: $pythonVersion"
                return $true
            }
            else {
                Write-Log "Python version too old: $pythonVersion (requires 3.8+)" "ERROR"
                return $false
            }
        }
    }
    catch {
        Write-Log "Python not found in PATH" "ERROR"
        return $false
    }
    return $false
}

function Test-ConfigFile {
    if (!(Test-Path $ConfigPath)) {
        Write-Log "Configuration file not found: $ConfigPath" "ERROR"
        return $false
    }

    try {
        $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
        Write-Log "Configuration file validated"
        return $true
    }
    catch {
        Write-Log "Invalid configuration file: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Get-RunningProcess {
    if (Test-Path $PidFile) {
        $pid = Get-Content $PidFile -ErrorAction SilentlyContinue
        if ($pid) {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($process -and $process.ProcessName -eq "python") {
                return $process
            }
        }
    }
    return $null
}

function Start-Orchestrator {
    Write-Log "Starting Unified Digital Labour Orchestrator..."

    # Check prerequisites
    if (!(Test-PythonEnvironment)) {
        Write-Log "Cannot start orchestrator: Python environment check failed" "ERROR"
        exit 1
    }

    if (!(Test-ConfigFile)) {
        Write-Log "Cannot start orchestrator: Configuration check failed" "ERROR"
        exit 1
    }

    # Check if already running
    $existingProcess = Get-RunningProcess
    if ($existingProcess) {
        Write-Log "Orchestrator already running (PID: $($existingProcess.Id))" "WARNING"
        return
    }

    # Start the orchestrator
    try {
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = "python"
        $startInfo.Arguments = "`"$OrchestratorScript`""
        $startInfo.WorkingDirectory = $ScriptPath
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.CreateNoWindow = $true

        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $startInfo

        if ($process.Start()) {
            # Save PID
            $process.Id | Out-File $PidFile -Encoding ASCII

            Write-Log "Orchestrator started successfully (PID: $($process.Id))"
            Write-Log "Web interface will be available at: http://localhost:$Port"
            Write-Log "Monitor logs at: $LogFile"

            # Wait a moment for startup
            Start-Sleep -Seconds 3

            # Test if web interface is responding
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$Port" -TimeoutSec 10 -ErrorAction Stop
                Write-Log "Web interface is responding (HTTP $($response.StatusCode))"
            }
            catch {
                Write-Log "Web interface not responding yet, but process started" "WARNING"
            }
        }
        else {
            Write-Log "Failed to start orchestrator process" "ERROR"
            exit 1
        }
    }
    catch {
        Write-Log "Error starting orchestrator: $($_.Exception.Message)" "ERROR"
        exit 1
    }
}

function Stop-Orchestrator {
    Write-Log "Stopping Unified Digital Labour Orchestrator..."

    $process = Get-RunningProcess
    if ($process) {
        try {
            # Try graceful shutdown first
            Write-Log "Attempting graceful shutdown..."
            $webResponse = Invoke-WebRequest -Uri "http://localhost:$Port/api/control/emergency_stop" -Method POST -TimeoutSec 5 -ErrorAction SilentlyContinue

            # Wait for graceful shutdown
            Start-Sleep -Seconds 5

            # Force kill if still running
            $process = Get-RunningProcess
            if ($process) {
                Write-Log "Force stopping process (PID: $($process.Id))"
                Stop-Process -Id $process.Id -Force
            }

            # Clean up PID file
            if (Test-Path $PidFile) {
                Remove-Item $PidFile -Force
            }

            Write-Log "Orchestrator stopped successfully"
        }
        catch {
            Write-Log "Error stopping orchestrator: $($_.Exception.Message)" "ERROR"
            exit 1
        }
    }
    else {
        Write-Log "Orchestrator is not running"
    }
}

function Get-OrchestratorStatus {
    Write-Log "Checking Unified Digital Labour Orchestrator status..."

    $process = Get-RunningProcess
    $webStatus = "Unknown"
    $configStatus = "Invalid"

    # Check configuration
    if (Test-ConfigFile) {
        $configStatus = "Valid"
    }

    # Check web interface
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/api/health" -TimeoutSec 5 -ErrorAction Stop
        $webStatus = "Responding (HTTP $($response.StatusCode))"
    }
    catch {
        $webStatus = "Not responding"
    }

    # Check process
    if ($process) {
        Write-Log "Process Status: Running (PID: $($process.Id))"
        Write-Log "Memory Usage: $([math]::Round($process.WorkingSet64 / 1MB, 2)) MB"
        Write-Log "CPU Time: $($process.TotalProcessorTime)"
    }
    else {
        Write-Log "Process Status: Not running"
    }

    Write-Log "Web Interface: $webStatus"
    Write-Log "Configuration: $configStatus"
    Write-Log "Log File: $LogFile"
    Write-Log "PID File: $(if (Test-Path $PidFile) { 'Present' } else { 'Not present' })"

    # Show recent log entries
    if (Test-Path $LogFile) {
        Write-Log "Recent Log Entries:"
        Get-Content $LogFile -Tail 5 | ForEach-Object { Write-Host "  $_" }
    }
}

function Restart-Orchestrator {
    Write-Log "Restarting Unified Digital Labour Orchestrator..."
    Stop-Orchestrator
    Start-Sleep -Seconds 2
    Start-Orchestrator
}

# Main execution logic
switch {
    $Start {
        Start-Orchestrator
    }
    $Stop {
        Stop-Orchestrator
    }
    $Status {
        Get-OrchestratorStatus
    }
    $Restart {
        Restart-Orchestrator
    }
    default {
        Write-Host "Unified Digital Labour Orchestrator Launcher"
        Write-Host "Usage:"
        Write-Host "  .\launch_unified_orchestrator.ps1 -Start    # Start the orchestrator"
        Write-Host "  .\launch_unified_orchestrator.ps1 -Stop     # Stop the orchestrator"
        Write-Host "  .\launch_unified_orchestrator.ps1 -Status   # Check status"
        Write-Host "  .\launch_unified_orchestrator.ps1 -Restart  # Restart the orchestrator"
        Write-Host ""
        Write-Host "Parameters:"
        Write-Host "  -ConfigFile <file>  # Configuration file path (default: unified_orchestrator_config.json)"
        Write-Host "  -Port <number>      # Web interface port (default: 5000)"
    }
}
