# REPO DEPOT WATCHDOG - Windows Task Scheduler Setup
# ===================================================
# CRITICAL INFRASTRUCTURE - 24/7/365 OPERATION
#
# This script creates Windows Scheduled Tasks to ensure:
# 1. Watchdog starts on system boot
# 2. Watchdog restarts every 5 minutes if not running
# 3. Repo Depot is ALWAYS operational
#
# RUN AS ADMINISTRATOR

$ErrorActionPreference = "Stop"

$WorkspacePath = "C:\Dev\SuperAgency-Shared"
$PythonExe = "$WorkspacePath\.venv\Scripts\python.exe"
$WatchdogScript = "$WorkspacePath\repo_depot_watchdog.py"
$RepoDepotScript = "$WorkspacePath\optimus_repo_depot_launcher.py"

Write-Host "=" * 60
Write-Host "  REPO DEPOT FAILSAFE - Task Scheduler Setup"
Write-Host "  CRITICAL INFRASTRUCTURE - 24/7/365 OPERATION"
Write-Host "=" * 60

# Task 1: Watchdog on Boot
$TaskName1 = "RepoDepotWatchdog_OnBoot"
Write-Host "`n[1/3] Creating boot task: $TaskName1"

$Action1 = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$WatchdogScript`"" -WorkingDirectory $WorkspacePath
$Trigger1 = New-ScheduledTaskTrigger -AtStartup
$Settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$Principal1 = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -RunLevel Highest

# Remove if exists
Unregister-ScheduledTask -TaskName $TaskName1 -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $TaskName1 -Action $Action1 -Trigger $Trigger1 -Settings $Settings1 -Principal $Principal1 -Description "CRITICAL: Starts Repo Depot Watchdog on system boot"
Write-Host "  ✅ Created: $TaskName1"

# Task 2: Watchdog every 5 minutes (failsafe check)
$TaskName2 = "RepoDepotWatchdog_HealthCheck"
Write-Host "`n[2/3] Creating health check task: $TaskName2"

$Action2 = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WorkspacePath\ensure_repo_depot_running.ps1`"" -WorkingDirectory $WorkspacePath
$Trigger2 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)
$Settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Unregister-ScheduledTask -TaskName $TaskName2 -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $TaskName2 -Action $Action2 -Trigger $Trigger2 -Settings $Settings2 -Principal $Principal1 -Description "CRITICAL: Ensures Repo Depot is running every 5 minutes"
Write-Host "  ✅ Created: $TaskName2"

# Task 3: Repo Depot direct start on logon
$TaskName3 = "RepoDepot_OnLogon"
Write-Host "`n[3/3] Creating logon task: $TaskName3"

$Action3 = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$RepoDepotScript`"" -WorkingDirectory $WorkspacePath
$Trigger3 = New-ScheduledTaskTrigger -AtLogOn
$Settings3 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Unregister-ScheduledTask -TaskName $TaskName3 -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $TaskName3 -Action $Action3 -Trigger $Trigger3 -Settings $Settings3 -Principal $Principal1 -Description "CRITICAL: Starts Repo Depot on user logon"
Write-Host "  ✅ Created: $TaskName3"

Write-Host "`n" + "=" * 60
Write-Host "  ALL TASKS CREATED SUCCESSFULLY"
Write-Host "  Repo Depot failsafe is now ACTIVE"
Write-Host "=" * 60

# Verify
Write-Host "`nScheduled Tasks:"
Get-ScheduledTask | Where-Object { $_.TaskName -match "RepoDepot" } | Format-Table TaskName, State -AutoSize
