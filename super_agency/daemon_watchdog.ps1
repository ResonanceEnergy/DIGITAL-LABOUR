# Bit Rage Systems Health Watchdog
# Quick check for daemon health - can be run from Task Scheduler as backup
# Restarts daemon if unresponsive

param(
    [switch]$Verbose,
    [int]$MaxHeartbeatAge = 300  # 5 minutes
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServiceName = "SuperAgencyDaemon"
$HeartbeatFile = Join-Path $ScriptDir "daemon_heartbeat.txt"
$HealthFile = Join-Path $ScriptDir "daemon_health.json"
$LogFile = Join-Path $ScriptDir "logs\watchdog.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $logLine -ErrorAction SilentlyContinue
    if ($Verbose) {
        $color = switch ($Level) {
            "ERROR" { "Red" }
            "WARN" { "Yellow" }
            "OK" { "Green" }
            default { "White" }
        }
        Write-Host $logLine -ForegroundColor $color
    }
}

function Test-DaemonHealth {
    $issues = @()

    # Check service status
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (!$service) {
        $issues += "Service not installed"
        return @{ Healthy = $false; Issues = $issues }
    }

    if ($service.Status -ne 'Running') {
        $issues += "Service not running (Status: $($service.Status))"
    }

    # Check heartbeat
    if (Test-Path $HeartbeatFile) {
        try {
            $lastHeartbeat = Get-Content $HeartbeatFile
            $heartbeatTime = [DateTime]::Parse($lastHeartbeat)
            $age = ((Get-Date) - $heartbeatTime).TotalSeconds

            if ($age -gt $MaxHeartbeatAge) {
                $issues += "Heartbeat stale ($([int]$age) seconds old)"
            }
        }
        catch {
            $issues += "Cannot parse heartbeat file"
        }
    }
    else {
        $issues += "No heartbeat file found"
    }

    # Check health file
    if (Test-Path $HealthFile) {
        try {
            $health = Get-Content $HealthFile -Raw | ConvertFrom-Json
            if ($health.status -eq 'critical') {
                $issues += "Health status is critical"
            }
            # Check for resource issues
            if ($health.metrics.memory_percent -gt 90) {
                $issues += "High memory usage: $($health.metrics.memory_percent)%"
            }
            if ($health.metrics.disk_percent -gt 95) {
                $issues += "Critical disk usage: $($health.metrics.disk_percent)%"
            }
        }
        catch {
            # Health file parse error - not critical
        }
    }

    return @{
        Healthy = ($issues.Count -eq 0 -or ($issues.Count -eq 1 -and $service.Status -eq 'Running'))
        Issues  = $issues
    }
}

function Restart-Daemon {
    Write-Log "Restarting daemon service..." "WARN"

    try {
        Restart-Service -Name $ServiceName -Force
        Start-Sleep -Seconds 5

        $service = Get-Service -Name $ServiceName
        if ($service.Status -eq 'Running') {
            Write-Log "Daemon restarted successfully" "OK"
            return $true
        }
        else {
            Write-Log "Daemon failed to restart" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Error restarting daemon: $_" "ERROR"
        return $false
    }
}

# Main execution
Write-Log "Watchdog check started"

$result = Test-DaemonHealth

if ($result.Healthy) {
    Write-Log "Daemon is healthy" "OK"
    exit 0
}
else {
    Write-Log "Issues detected: $($result.Issues -join '; ')" "WARN"

    # Check if service exists and attempt restart
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        if (Restart-Daemon) {
            exit 0
        }
    }
    else {
        Write-Log "Cannot restart - service not installed. Run install_daemon_service.ps1" "ERROR"
    }
    exit 1
}
