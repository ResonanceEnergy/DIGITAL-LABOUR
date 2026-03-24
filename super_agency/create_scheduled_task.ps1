# Digital Labour Cross-Platform Refresh Task Creator
# Run this script as Administrator to create the scheduled task

param(
    [string]$TaskName = "DIGITAL LABOUR CrossPlatform Refresh",
    [string]$ScriptPath = "$PSScriptRoot\cross_platform_refresh_windows.ps1",
    [int]$IntervalMinutes = 5
)

Write-Host "Digital Labour Cross-Platform Refresh Task Creator" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Check if running as administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click the script and select 'Run as administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Running as Administrator" -ForegroundColor Green

# Verify the script exists
if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: Refresh script not found at: $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Refresh script found: $ScriptPath" -ForegroundColor Green

# Remove existing task if it exists
Write-Host "Removing existing task (if any)..." -ForegroundColor Yellow
try {
    schtasks /delete /tn "$TaskName" /f 2>$null
    Write-Host "Removed existing task" -ForegroundColor Green
}
catch {
    Write-Host "No existing task to remove" -ForegroundColor Blue
}

# Create the scheduled task using PowerShell cmdlets (more reliable with paths)
Write-Host "Creating scheduled task..." -ForegroundColor Yellow

try {
    # Create the action
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`""

    # Create the trigger (repeat every 5 minutes indefinitely)
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 365)

    # Create settings
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)

    # Register the task
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null

    Write-Host "Scheduled task created successfully!" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Failed to create scheduled task" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Verify the task was created
Write-Host "Verifying task creation..." -ForegroundColor Yellow
try {
    $taskInfo = schtasks /query /tn "$TaskName" 2>$null
    if ($taskInfo) {
        Write-Host "Task verification successful" -ForegroundColor Green
    }
    else {
        Write-Host "Task verification failed" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "Task verification failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Display task information
Write-Host ""
Write-Host "Task Configuration:" -ForegroundColor Cyan
Write-Host "   Name: $TaskName" -ForegroundColor White
Write-Host "   Interval: Every $IntervalMinutes minutes" -ForegroundColor White
Write-Host "   Command: $taskCommand $taskArgs" -ForegroundColor White
Write-Host "   Run Level: Highest privileges" -ForegroundColor White

Write-Host ""
Write-Host "Task Management Commands:" -ForegroundColor Cyan
Write-Host "   Check status: schtasks /query /tn `"$TaskName`"" -ForegroundColor White
Write-Host "   Run manually: schtasks /run /tn `"$TaskName`"" -ForegroundColor White
Write-Host "   Delete task: schtasks /delete /tn `"$TaskName`"" -ForegroundColor White

Write-Host ""
Write-Host "Setup Complete! The cross-platform refresh will run every $IntervalMinutes minutes." -ForegroundColor Green
Write-Host "Digital Labour automation is now active!" -ForegroundColor Green
