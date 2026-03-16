# REPO DEPOT GitHub Sync - Scheduled Task Setup
# Creates Windows Task Scheduler job for regular GitHub syncs

param(
    [int]$IntervalMinutes = 30,
    [switch]$Remove,
    [switch]$RunNow
)

$TaskName = "RepoDepot_GitHub_Sync"
$WorkDir = $PSScriptRoot
$PythonScript = Join-Path $WorkDir "repo_depot_github_sync.py"

function Write-Status {
    param([string]$Message, [string]$Color = "Cyan")
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

function Create-SyncTask {
    Write-Status "Creating scheduled task: $TaskName" "Yellow"

    # Check if task exists
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Status "Removing existing task..." "Yellow"
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    # Create the action
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) {
        $python = "python"
    }

    $action = New-ScheduledTaskAction `
        -Execute $python `
        -Argument "`"$PythonScript`"" `
        -WorkingDirectory $WorkDir

    # Create trigger (every N minutes)
    $trigger = New-ScheduledTaskTrigger `
        -Once `
        -At (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
        -RepetitionDuration ([TimeSpan]::MaxValue)

    # Create settings
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable `
        -MultipleInstances IgnoreNew

    # Register the task
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "REPO DEPOT GitHub Sync - Syncs local repos with ResonanceEnergy GitHub org" `
        -Force

    Write-Status "Scheduled task created successfully!" "Green"
    Write-Status "  Task: $TaskName" "White"
    Write-Status "  Interval: Every $IntervalMinutes minutes" "White"
    Write-Status "  Script: $PythonScript" "White"
}

function Remove-SyncTask {
    Write-Status "Removing scheduled task: $TaskName" "Yellow"

    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Status "Task removed successfully!" "Green"
    }
    else {
        Write-Status "Task not found" "Yellow"
    }
}

function Run-SyncNow {
    Write-Status "Running REPO DEPOT GitHub Sync..." "Cyan"

    Push-Location $WorkDir
    try {
        python $PythonScript
    }
    finally {
        Pop-Location
    }
}

# Main
Write-Host ""
Write-Host "============================================" -ForegroundColor Red
Write-Host "   REPO DEPOT GITHUB SYNC SCHEDULER" -ForegroundColor Red
Write-Host "   ResonanceEnergy Organization" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red
Write-Host ""

if ($Remove) {
    Remove-SyncTask
}
elseif ($RunNow) {
    Run-SyncNow
}
else {
    Create-SyncTask

    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\schedule_github_sync.ps1              # Create scheduled task (30 min default)" -ForegroundColor White
    Write-Host "  .\schedule_github_sync.ps1 -IntervalMinutes 15  # Custom interval" -ForegroundColor White
    Write-Host "  .\schedule_github_sync.ps1 -Remove      # Remove scheduled task" -ForegroundColor White
    Write-Host "  .\schedule_github_sync.ps1 -RunNow      # Run sync immediately" -ForegroundColor White
}
