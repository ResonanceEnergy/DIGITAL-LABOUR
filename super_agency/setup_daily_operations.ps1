#!/usr/bin/env pwsh
# Bit Rage Systems - Daily Operations Scheduler
# Creates Windows Task Scheduler jobs for automated system operations.
# Run as Administrator: powershell -ExecutionPolicy Bypass -File setup_daily_operations.ps1

param(
    [switch]$Uninstall
)

$Root = $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$LogDir = Join-Path $Root "logs"

# Ensure log directory
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# --- Task definitions ---
$Tasks = @(
    @{
        Name        = "SuperAgency-Orchestrator"
        Description = "Run repo sentry, daily brief, research, council, audit, autotier"
        Script      = "agents\orchestrator.py"
        Interval    = 240  # every 4 hours
    },
    @{
        Name        = "SuperAgency-DailyBrief"
        Description = "Generate daily operations brief at 06:00"
        Script      = "departments\operations_command\system_monitoring\daily_brief.py"
        TriggerTime = "06:00"
    },
    @{
        Name        = "SuperAgency-SystemAudit"
        Description = "Run auto system audit every 15 minutes"
        Script      = "auto_system_audit.py"
        Interval    = 15
    }
)

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] Run as Administrator." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $Python)) {
    Write-Host "[ERROR] Python venv not found at $Python" -ForegroundColor Red
    exit 1
}

if ($Uninstall) {
    foreach ($t in $Tasks) {
        Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "[OK] Removed $($t.Name)" -ForegroundColor Yellow
    }
    Write-Host "All SuperAgency tasks removed." -ForegroundColor Cyan
    exit 0
}

Write-Host "=== Bit Rage Systems Scheduled Task Setup ===" -ForegroundColor Cyan
Write-Host "Python: $Python" -ForegroundColor Gray
Write-Host ""

foreach ($t in $Tasks) {
    $scriptPath = Join-Path $Root $t.Script
    if (-not (Test-Path $scriptPath)) {
        Write-Host "[SKIP] Script not found: $($t.Script)" -ForegroundColor Yellow
        continue
    }

    $logFile = Join-Path $LogDir "$($t.Name).log"
    $argStr = "-ExecutionPolicy Bypass -Command `"& '$Python' '$scriptPath' >> '$logFile' 2>&1`""
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argStr -WorkingDirectory $Root

    if ($t.ContainsKey("TriggerTime")) {
        $trigger = New-ScheduledTaskTrigger -Daily -At $t.TriggerTime
    } else {
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
            -RepetitionInterval (New-TimeSpan -Minutes $t.Interval) `
            -RepetitionDuration (New-TimeSpan -Days 365)
    }

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1)

    Register-ScheduledTask -TaskName $t.Name -Action $action -Trigger $trigger `
        -Settings $settings -Description $t.Description -Force | Out-Null

    Write-Host "[OK] $($t.Name) - $($t.Description)" -ForegroundColor Green
}

Write-Host ""
Write-Host "All tasks registered. Verify with:" -ForegroundColor Cyan
Write-Host "  schtasks /query /fo TABLE | findstr SuperAgency" -ForegroundColor Gray
Write-Host ""
Write-Host "To remove all tasks:" -ForegroundColor Cyan
Write-Host "  .\setup_daily_operations.ps1 -Uninstall" -ForegroundColor Gray
