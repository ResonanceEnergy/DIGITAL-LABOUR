# Digital Labour Service Installer
# Uses NSSM (Non-Sucking Service Manager) for reliable Windows service management
#
# Features:
# - Auto-restart on crash
# - Log rotation
# - Health monitoring
# - Graceful shutdown
#
# Prerequisites: Download NSSM from https://nssm.cc/download
#
# Run as Administrator!

param(
    [string]$NssmPath = "C:\Tools\nssm\win64\nssm.exe",
    [switch]$Uninstall,
    [switch]$Status
)

$ServiceName = "DIGITAL LABOURDaemon"
$DisplayName = "Digital Labour Background Daemon"
$Description = "Manages Digital Labour operations, health monitoring, and auto-recovery"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = Join-Path $ScriptDir "venv\Scripts\python.exe"
$DaemonScript = Join-Path $ScriptDir "digital_labour_daemon.py"
$LogDir = Join-Path $ScriptDir "logs"

# Ensure log directory exists
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Test-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-NSSM {
    Write-Host "NSSM not found. Would you like to download it?" -ForegroundColor Yellow
    $response = Read-Host "Download NSSM? (Y/N)"
    if ($response -eq 'Y') {
        $downloadUrl = "https://nssm.cc/release/nssm-2.24.zip"
        $zipPath = "$env:TEMP\nssm.zip"
        $extractPath = "C:\Tools"

        Write-Host "Downloading NSSM..." -ForegroundColor Cyan
        try {
            Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
            Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
            Move-Item "$extractPath\nssm-2.24" "$extractPath\nssm" -Force -ErrorAction SilentlyContinue
            Remove-Item $zipPath -Force
            Write-Host "NSSM installed to C:\Tools\nssm" -ForegroundColor Green
            return "C:\Tools\nssm\win64\nssm.exe"
        }
        catch {
            Write-Host "Failed to download NSSM: $_" -ForegroundColor Red
            Write-Host "Please download manually from https://nssm.cc/download" -ForegroundColor Yellow
            exit 1
        }
    }
    exit 1
}

function Get-ServiceStatus {
    Write-Host "`n=== Digital Labour SERVICE STATUS ===" -ForegroundColor Cyan

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Write-Host "Service Name:    $ServiceName" -ForegroundColor White
        Write-Host "Display Name:    $($service.DisplayName)" -ForegroundColor White
        Write-Host "Status:          $($service.Status)" -ForegroundColor $(if ($service.Status -eq 'Running') { 'Green' } else { 'Yellow' })
        Write-Host "Start Type:      $($service.StartType)" -ForegroundColor White

        # Check daemon health file
        $healthFile = Join-Path $ScriptDir "daemon_health.json"
        if (Test-Path $healthFile) {
            $health = Get-Content $healthFile | ConvertFrom-Json
            Write-Host "`n--- Health Status ---" -ForegroundColor Cyan
            Write-Host "Status:          $($health.status)" -ForegroundColor $(
                switch ($health.status) {
                    'healthy' { 'Green' }
                    'warning' { 'Yellow' }
                    'critical' { 'Red' }
                    default { 'White' }
                }
            )
            Write-Host "Last Check:      $($health.last_check)" -ForegroundColor White
            if ($health.metrics) {
                Write-Host "CPU:             $($health.metrics.cpu_percent)%" -ForegroundColor White
                Write-Host "Memory:          $($health.metrics.memory_percent)%" -ForegroundColor White
                Write-Host "Disk:            $($health.metrics.disk_percent)%" -ForegroundColor White
            }
            if ($health.issues -and $health.issues.Count -gt 0) {
                Write-Host "`nIssues:" -ForegroundColor Yellow
                $health.issues | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
            }
        }

        # Check heartbeat
        $heartbeatFile = Join-Path $ScriptDir "daemon_heartbeat.txt"
        if (Test-Path $heartbeatFile) {
            $lastHeartbeat = Get-Content $heartbeatFile
            $heartbeatTime = [DateTime]::Parse($lastHeartbeat)
            $age = (Get-Date) - $heartbeatTime
            $color = if ($age.TotalMinutes -lt 1) { 'Green' } elseif ($age.TotalMinutes -lt 5) { 'Yellow' } else { 'Red' }
            Write-Host "`nLast Heartbeat:  $([int]$age.TotalSeconds) seconds ago" -ForegroundColor $color
        }
    }
    else {
        Write-Host "Service not installed" -ForegroundColor Yellow
    }
    Write-Host ""
}

function Uninstall-Service {
    Write-Host "`n=== UNINSTALLING SERVICE ===" -ForegroundColor Yellow

    # Stop service if running
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        if ($service.Status -eq 'Running') {
            Write-Host "Stopping service..." -ForegroundColor Yellow
            Stop-Service -Name $ServiceName -Force
            Start-Sleep -Seconds 2
        }
    }

    # Remove with NSSM
    if (Test-Path $NssmPath) {
        Write-Host "Removing service..." -ForegroundColor Yellow
        & $NssmPath remove $ServiceName confirm
        Write-Host "Service removed" -ForegroundColor Green
    }
    else {
        # Try with sc.exe
        & sc.exe delete $ServiceName
    }
}

function Install-Service {
    Write-Host "`n=== INSTALLING Digital Labour DAEMON SERVICE ===" -ForegroundColor Green

    # Check NSSM
    if (!(Test-Path $NssmPath)) {
        $NssmPath = Install-NSSM
    }

    # Check Python
    if (!(Test-Path $PythonPath)) {
        $PythonPath = "python.exe"  # Fall back to system Python
        Write-Host "Using system Python (venv not found)" -ForegroundColor Yellow
    }

    # Check daemon script
    if (!(Test-Path $DaemonScript)) {
        Write-Host "Daemon script not found: $DaemonScript" -ForegroundColor Red
        exit 1
    }

    Write-Host "NSSM:     $NssmPath" -ForegroundColor Cyan
    Write-Host "Python:   $PythonPath" -ForegroundColor Cyan
    Write-Host "Script:   $DaemonScript" -ForegroundColor Cyan
    Write-Host "Logs:     $LogDir" -ForegroundColor Cyan

    # Install service
    Write-Host "`nInstalling service..." -ForegroundColor Yellow
    & $NssmPath install $ServiceName $PythonPath $DaemonScript

    # Configure service
    & $NssmPath set $ServiceName DisplayName $DisplayName
    & $NssmPath set $ServiceName Description $Description
    & $NssmPath set $ServiceName AppDirectory $ScriptDir

    # Auto-start on boot
    & $NssmPath set $ServiceName Start SERVICE_AUTO_START

    # Restart on failure
    & $NssmPath set $ServiceName AppExit Default Restart
    & $NssmPath set $ServiceName AppRestartDelay 5000  # 5 seconds

    # Logging
    & $NssmPath set $ServiceName AppStdout "$LogDir\daemon_stdout.log"
    & $NssmPath set $ServiceName AppStderr "$LogDir\daemon_stderr.log"
    & $NssmPath set $ServiceName AppRotateFiles 1
    & $NssmPath set $ServiceName AppRotateBytes 10485760  # 10 MB

    # Graceful shutdown
    & $NssmPath set $ServiceName AppStopMethodSkip 0
    & $NssmPath set $ServiceName AppStopMethodConsole 3000
    & $NssmPath set $ServiceName AppStopMethodWindow 3000
    & $NssmPath set $ServiceName AppStopMethodThreads 1000

    Write-Host "`nService installed successfully!" -ForegroundColor Green

    # Start service
    Write-Host "Starting service..." -ForegroundColor Yellow
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 3

    Get-ServiceStatus
}

# Main execution
if (!(Test-Admin)) {
    Write-Host "Please run this script as Administrator" -ForegroundColor Red
    exit 1
}

if ($Status) {
    Get-ServiceStatus
}
elseif ($Uninstall) {
    Uninstall-Service
}
else {
    Install-Service
}

Write-Host "`n=== SCHEDULED TASK CLEANUP RECOMMENDATIONS ===" -ForegroundColor Cyan
Write-Host "The daemon replaces these scheduled tasks:" -ForegroundColor Yellow
Write-Host "  - DIGITAL LABOUR CrossPlatform Refresh  (now: daemon refresh cycle)" -ForegroundColor White
Write-Host "  - DIGITAL LABOUR_5Min_Refresh           (now: daemon refresh cycle)" -ForegroundColor White
Write-Host "  - DIGITAL LABOUR-MemoryDoctrine         (now: daemon doctrine task)" -ForegroundColor White
Write-Host ""
Write-Host "Run these commands to disable duplicate tasks:" -ForegroundColor Yellow
Write-Host '  schtasks /Change /TN "DIGITAL LABOUR CrossPlatform Refresh" /Disable' -ForegroundColor Gray
Write-Host '  schtasks /Change /TN "DIGITAL LABOUR_5Min_Refresh" /Disable' -ForegroundColor Gray
Write-Host '  schtasks /Change /TN "DIGITAL LABOUR-MemoryDoctrine" /Disable' -ForegroundColor Gray
Write-Host ""
