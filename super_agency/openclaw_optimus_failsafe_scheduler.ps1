# ═══════════════════════════════════════════════════════════════════════
# OPENCLAW OPTIMUS FAILSAFE - Windows Scheduled Task Installer
# Creates a Windows Task Scheduler job that runs the failsafe every 15 min
# Run as Administrator: .\openclaw_optimus_failsafe_scheduler.ps1
# ═══════════════════════════════════════════════════════════════════════

$TaskName = "OpenClaw_Optimus_Failsafe"
$TaskDescription = "Monitors OpenClaw gateway + Discord every 15 minutes and auto-restarts if down"
$ScriptPath = Join-Path $PSScriptRoot "openclaw_optimus_failsafe.py"
$PythonExe = "python"

# Verify the failsafe script exists
if (-Not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: Failsafe script not found at $ScriptPath" -ForegroundColor Red
    exit 1
}

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Task '$TaskName' already exists. Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Build the action: python openclaw_optimus_failsafe.py (single check mode)
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScriptPath`"" `
    -WorkingDirectory $PSScriptRoot

# Trigger: every 15 minutes, indefinitely
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)

# Settings: run whether user is logged in, don't stop on idle, restart on failure
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $TaskDescription `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -RunLevel Highest `
        -Force

    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  OPENCLAW OPTIMUS FAILSAFE SCHEDULED" -ForegroundColor Green
    Write-Host "  Task: $TaskName" -ForegroundColor Green
    Write-Host "  Interval: Every 15 minutes" -ForegroundColor Green
    Write-Host "  Script: $ScriptPath" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Cyan
    Write-Host "  Check status:  Get-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  Run now:       Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  Disable:       Disable-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  Remove:        Unregister-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  View history:  python `"$ScriptPath`" --status"
    Write-Host ""
    Write-Host "Or run as daemon instead:" -ForegroundColor Cyan
    Write-Host "  python `"$ScriptPath`" --daemon"
    Write-Host ""
}
catch {
    Write-Host "ERROR: Failed to register scheduled task: $_" -ForegroundColor Red
    Write-Host "Try running this script as Administrator." -ForegroundColor Yellow
    exit 1
}
