# Bit Rage Systems Cross-Platform Refresh - Windows PowerShell Script
# Consolidated refresh: sync, backup, backlog (replaces separate refresh_5min.ps1)
# Runs on schedule to sync with Quantum Quasar

param(
    [string]$LogFile = "$PSScriptRoot\logs\refresh_scheduler.log"
)

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logMessage = "[$timestamp] Starting Cross-Platform Refresh on QUANTUM FORGE"

# Ensure log directory exists
$logDir = Split-Path $LogFile -Parent
if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Log start
Add-Content -Path $LogFile -Value $logMessage

try {
    # Change to script directory
    Set-Location $PSScriptRoot

    # --- Phase 1: Memory/Doctrine Backup (merged from refresh_5min.ps1) ---
    $backupScript = Join-Path $PSScriptRoot "backup_memory_doctrine_logs.ps1"
    if (Test-Path $backupScript) {
        $backupMsg = "[$timestamp] Running memory/doctrine backup..."
        Add-Content -Path $LogFile -Value $backupMsg
        try {
            & $backupScript
            Add-Content -Path $LogFile -Value "[$timestamp] Backup completed"
        }
        catch {
            Add-Content -Path $LogFile -Value "[$timestamp] Backup warning: $($_.Exception.Message)"
        }
    }

    # --- Phase 2: Backlog Management (merged from refresh_5min.ps1) ---
    $backlogScript = Join-Path $PSScriptRoot "backlog_management_system.py"
    if (Test-Path $backlogScript) {
        $backlogMsg = "[$timestamp] Running backlog update..."
        Add-Content -Path $LogFile -Value $backlogMsg
        try {
            $backlogProc = Start-Process -FilePath "python" -ArgumentList "`"$backlogScript`"" -Wait -PassThru -NoNewWindow
            if ($backlogProc.ExitCode -eq 0) {
                Add-Content -Path $LogFile -Value "[$timestamp] Backlog update completed"
            } else {
                Add-Content -Path $LogFile -Value "[$timestamp] Backlog update exited with code: $($backlogProc.ExitCode)"
            }
        }
        catch {
            Add-Content -Path $LogFile -Value "[$timestamp] Backlog warning: $($_.Exception.Message)"
        }
    }

    # --- Phase 3: Cross-Platform Sync ---
    $pythonPath = Join-Path $PSScriptRoot "cross_platform_refresh.py"
    $escapedPath = "`"$pythonPath`""
    $process = Start-Process -FilePath "python" -ArgumentList $escapedPath -Wait -PassThru -NoNewWindow

    if ($process.ExitCode -eq 0) {
        $successMsg = "[$timestamp] Refresh completed successfully"
        Add-Content -Path $LogFile -Value $successMsg
        Write-Host $successMsg -ForegroundColor Green
    }
    else {
        $errorMsg = "[$timestamp] Refresh failed with exit code: $($process.ExitCode)"
        Add-Content -Path $LogFile -Value $errorMsg
        Write-Host $errorMsg -ForegroundColor Red
    }
}
catch {
    $errorMsg = "[$timestamp] PowerShell error: $($_.Exception.Message)"
    Add-Content -Path $LogFile -Value $errorMsg
    Write-Host $errorMsg -ForegroundColor Red
}

$completeMsg = "[$timestamp] Cross-Platform Refresh cycle complete"
Add-Content -Path $LogFile -Value $completeMsg
Add-Content -Path $LogFile -Value ""  # Empty line for readability

Write-Host $completeMsg -ForegroundColor Cyan
