# DEPRECATED — Use bitrage.py start (consolidated daemon management)
#
# Original: NERVE Startup Installer
# Registers Windows Task Scheduler tasks so NERVE + Watchdog run automatically
# on every boot and stay alive via a 5-minute health check.
#
# TASKS CREATED:
#   DigitalLabour_Watchdog      — At startup + At logon → starts watchdog (which starts NERVE)
#   DigitalLabour_HealthCheck   — Every 5 minutes      → restarts watchdog if it died
#
# Run this script ONCE as Administrator:
#   powershell -ExecutionPolicy Bypass -File "scripts\startup_install.ps1"
#
# To REMOVE both tasks:
#   powershell -ExecutionPolicy Bypass -File "scripts\startup_install.ps1" -Uninstall

param(
    [switch]$Uninstall,
    [switch]$Status
)

$ProjectRoot     = "c:\dev\DIGITAL LABOUR\DIGITAL LABOUR"
$PythonExe       = "$ProjectRoot\.venv\Scripts\python.exe"
$HealthScript    = "$ProjectRoot\scripts\health_check.ps1"
$TaskWatchdog    = "DigitalLabour_Watchdog"
$TaskHealthCheck = "DigitalLabour_HealthCheck"

function Require-Admin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $p  = New-Object System.Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "ERROR: Run this script as Administrator." -ForegroundColor Red
        exit 1
    }
}

function Show-Status {
    Write-Host "`n=== Task Scheduler Status ===" -ForegroundColor Cyan
    foreach ($name in @($TaskWatchdog, $TaskHealthCheck)) {
        try {
            $t = Get-ScheduledTask -TaskName $name -ErrorAction Stop
            Write-Host "  $name : $($t.State)" -ForegroundColor Green
        } catch {
            Write-Host "  $name : NOT FOUND" -ForegroundColor Yellow
        }
    }

    Write-Host "`n=== Watchdog Process ===" -ForegroundColor Cyan
    $procs = Get-WmiObject Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like "*automation.watchdog*" }
    if ($procs) {
        foreach ($p in $procs) {
            Write-Host "  PID $($p.ProcessId) — $($p.CommandLine)" -ForegroundColor Green
        }
    } else {
        Write-Host "  Watchdog not running." -ForegroundColor Yellow
    }

    $statusFile = "$ProjectRoot\data\watchdog_status.json"
    if (Test-Path $statusFile) {
        Write-Host "`n=== Watchdog Status ===" -ForegroundColor Cyan
        Get-Content $statusFile | Write-Host
    }
}

function Uninstall-Tasks {
    Write-Host "`nRemoving tasks..." -ForegroundColor Yellow
    foreach ($name in @($TaskWatchdog, $TaskHealthCheck)) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "  Removed: $name" -ForegroundColor Gray
    }
    Write-Host "Done. NERVE will no longer start automatically." -ForegroundColor Yellow
}

function Install-Tasks {
    Require-Admin

    # Validate paths
    if (-not (Test-Path $PythonExe)) {
        Write-Host "ERROR: Python not found at $PythonExe" -ForegroundColor Red
        Write-Host "Activate the venv first, then re-run." -ForegroundColor Yellow
        exit 1
    }
    if (-not (Test-Path $HealthScript)) {
        Write-Host "ERROR: Health check script not found at $HealthScript" -ForegroundColor Red
        exit 1
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  DIGITAL LABOUR — Startup Installer" -ForegroundColor Cyan
    Write-Host "  Tasks: $TaskWatchdog + $TaskHealthCheck" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    # ── Task 1: Watchdog on Startup + Logon ─────────────────────────────────
    Write-Host "[1/2] Registering $TaskWatchdog ..." -ForegroundColor Cyan

    Unregister-ScheduledTask -TaskName $TaskWatchdog -Confirm:$false -ErrorAction SilentlyContinue

    $action1 = New-ScheduledTaskAction `
        -Execute $PythonExe `
        -Argument "-m automation.watchdog" `
        -WorkingDirectory $ProjectRoot

    $triggerBoot   = New-ScheduledTaskTrigger -AtStartup
    $triggerLogon  = New-ScheduledTaskTrigger -AtLogOn

    $settings1 = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 2) `
        -ExecutionTimeLimit (New-TimeSpan -Days 365) `
        -MultipleInstances IgnoreNew

    # RunLevel Highest so it can manage processes
    $principal1 = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -RunLevel Highest `
        -LogonType Interactive

    Register-ScheduledTask `
        -TaskName $TaskWatchdog `
        -Description "Starts NERVE watchdog on boot/logon. Watchdog keeps NERVE daemon alive 24/7." `
        -Action $action1 `
        -Trigger $triggerBoot, $triggerLogon `
        -Settings $settings1 `
        -Principal $principal1 `
        -Force | Out-Null

    Write-Host "  [OK] $TaskWatchdog registered" -ForegroundColor Green

    # ── Task 2: Health Check every 5 minutes ────────────────────────────────
    Write-Host "[2/2] Registering $TaskHealthCheck ..." -ForegroundColor Cyan

    Unregister-ScheduledTask -TaskName $TaskHealthCheck -Confirm:$false -ErrorAction SilentlyContinue

    $action2 = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$HealthScript`"" `
        -WorkingDirectory $ProjectRoot

    # Repeating trigger: start at boot, repeat every 5 min indefinitely
    $triggerRepeat = New-ScheduledTaskTrigger `
        -Once `
        -At (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Minutes 5) `
        -RepetitionDuration ([TimeSpan]::MaxValue)

    $settings2 = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 3) `
        -MultipleInstances IgnoreNew

    $principal2 = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -RunLevel Highest `
        -LogonType Interactive

    Register-ScheduledTask `
        -TaskName $TaskHealthCheck `
        -Description "Every 5 min: ensure NERVE watchdog is alive; restart if crashed." `
        -Action $action2 `
        -Trigger $triggerRepeat `
        -Settings $settings2 `
        -Principal $principal2 `
        -Force | Out-Null

    Write-Host "  [OK] $TaskHealthCheck registered" -ForegroundColor Green

    # ── Summary ──────────────────────────────────────────────────────────────
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "  INSTALLATION COMPLETE" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  $TaskWatchdog" -ForegroundColor White
    Write-Host "    Trigger : At Startup + At Logon" -ForegroundColor Gray
    Write-Host "    Action  : $PythonExe -m automation.watchdog" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  $TaskHealthCheck" -ForegroundColor White
    Write-Host "    Trigger : Every 5 minutes" -ForegroundColor Gray
    Write-Host "    Action  : health_check.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Start now (no reboot needed):" -ForegroundColor Yellow
    Write-Host "    Start-ScheduledTask -TaskName '$TaskWatchdog'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Check status anytime:" -ForegroundColor Yellow
    Write-Host "    powershell scripts\startup_install.ps1 -Status" -ForegroundColor Gray
    Write-Host "    python -m automation.watchdog --status" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Stop everything:" -ForegroundColor Yellow
    Write-Host "    python -m automation.watchdog --stop" -ForegroundColor Gray
    Write-Host "    powershell scripts\startup_install.ps1 -Uninstall" -ForegroundColor Gray
    Write-Host ""
}

# ── Entry point ───────────────────────────────────────────────────────────────
if ($Status) {
    Show-Status
} elseif ($Uninstall) {
    Require-Admin
    Uninstall-Tasks
} else {
    Install-Tasks
}
