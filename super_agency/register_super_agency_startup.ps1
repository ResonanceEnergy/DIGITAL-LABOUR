# ============================================
# Bit Rage Systems 24/7/365 FAILSAFE - TASK SCHEDULER
# ============================================
# COPY AND PASTE THIS ENTIRE SCRIPT INTO AN ADMIN POWERSHELL WINDOW
# ============================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Bit Rage Systems 24/7/365 FAILSAFE SETUP" -ForegroundColor Cyan
Write-Host "  NCC CONTINUOUS OPERATIONS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$WorkspacePath = "C:\Dev\SuperAgency-Shared"
$LauncherScript = "$WorkspacePath\start_super_agency.ps1"
$HealthScript = "$WorkspacePath\ensure_super_agency_running.ps1"

# Validate files exist
if (-not (Test-Path $LauncherScript)) {
    Write-Host "FATAL: $LauncherScript not found" -ForegroundColor Red
    exit 1
}

# ============================================
# TASK 1: Start Bit Rage Systems on Boot/Logon
# ============================================
Write-Host "[1/2] Creating SuperAgency_Failsafe task..." -ForegroundColor Cyan

$TaskName1 = "SuperAgency_Failsafe"
Unregister-ScheduledTask -TaskName $TaskName1 -Confirm:$false -ErrorAction SilentlyContinue

$Action1 = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$LauncherScript`"" `
    -WorkingDirectory $WorkspacePath

$Trigger1 = New-ScheduledTaskTrigger -AtLogOn
$Trigger2 = New-ScheduledTaskTrigger -AtStartup

$Settings1 = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 9999)

Register-ScheduledTask `
    -TaskName $TaskName1 `
    -Action $Action1 `
    -Trigger $Trigger1, $Trigger2 `
    -Settings $Settings1 `
    -Description "CRITICAL: Bit Rage Systems starts on boot and logon, restarts on failure" | Out-Null

Write-Host "  [OK] $TaskName1 created" -ForegroundColor Green

# ============================================
# TASK 2: Health Check Every 5 Minutes
# ============================================
Write-Host "[2/2] Creating SuperAgency_HealthCheck task..." -ForegroundColor Cyan

$TaskName2 = "SuperAgency_HealthCheck"
Unregister-ScheduledTask -TaskName $TaskName2 -Confirm:$false -ErrorAction SilentlyContinue

$Action2 = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$HealthScript`"" `
    -WorkingDirectory $WorkspacePath

$Trigger3 = New-ScheduledTaskTrigger -Daily -At "00:00"
$Trigger3.Repetition.Interval = "PT5M"  # Every 5 minutes

$Settings2 = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName2 `
    -Action $Action2 `
    -Trigger $Trigger3 `
    -Settings $Settings2 `
    -Description "CRITICAL: Checks Bit Rage Systems every 5 minutes, restarts if down" | Out-Null

Write-Host "  [OK] $TaskName2 created" -ForegroundColor Green

# ============================================
# VERIFY
# ============================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  FAILSAFE TASKS CREATED SUCCESSFULLY" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

Get-ScheduledTask | Where-Object { $_.TaskName -match "SuperAgency" } | Format-Table TaskName, State, @{N = "Triggers"; E = { $_.Triggers.Count } } -AutoSize

Write-Host ""
Write-Host "Bit Rage Systems will now:" -ForegroundColor Yellow
Write-Host "  - Start automatically on boot" -ForegroundColor Yellow
Write-Host "  - Start automatically on logon" -ForegroundColor Yellow
Write-Host "  - Restart automatically if it crashes (up to 999 retries)" -ForegroundColor Yellow
Write-Host "  - Be health-checked every 5 minutes and restarted if down" -ForegroundColor Yellow
Write-Host ""
Write-Host "24/7/365 CONTINUOUS OPERATIONS ENABLED" -ForegroundColor Green
