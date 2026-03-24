# NERVE Service — Windows Task Scheduler Installer
#
# Replaces the old watchdog.py + health_check.ps1 two-layer system.
# Registers a single Task Scheduler entry that:
#   • Launches at Startup AND At Logon (whichever fires first)
#   • Auto-restarts up to 3 times if it crashes (2-minute cooldown)
#   • Runs indefinitely (365-day execution limit)
#   • Uses the venv python.exe directly — no wrong-Python fallback
#
# Run ONCE as Administrator:
#   powershell -ExecutionPolicy Bypass -File scripts\nerve_service.ps1 -Install
#
# Other actions:
#   -Status    Show task + NERVE process status
#   -Stop      Stop NERVE gracefully (writes stop flag + sends SIGTERM via Python)
#   -Start     Start NERVE daemon now (without reinstalling the task)
#   -Uninstall Remove the scheduled task

param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Status,
    [switch]$Start,
    [switch]$Stop
)

$TaskName    = "DigitalLabour_NERVE"
$ProjectRoot = "c:\dev\DIGITAL LABOUR\DIGITAL LABOUR"
$PythonExe   = "$ProjectRoot\.venv\Scripts\python.exe"
$PidFile     = "$ProjectRoot\data\nerve.pid"
$StopFlag    = "$ProjectRoot\data\nerve_stop.flag"
$LogFile     = "$ProjectRoot\data\nerve_logs\nerve_service.log"

function Write-Log {
    param([string]$Msg, [string]$Level = "INFO")
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] [$Level] $Msg"
    $null = New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) -ErrorAction SilentlyContinue
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
    Write-Host $line
}

function Require-Admin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $p  = New-Object System.Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "ERROR: Run this script as Administrator." -ForegroundColor Red
        exit 1
    }
}

function Get-NervePid {
    if (Test-Path $PidFile) {
        return (Get-Content $PidFile -Raw).Trim()
    }
    return $null
}

function Show-Status {
    Write-Host "`n=== Task Scheduler ===" -ForegroundColor Cyan
    try {
        $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        Write-Host "  $TaskName : $($t.State)" -ForegroundColor Green
        $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($info) {
            Write-Host "  Last run : $($info.LastRunTime)"
            Write-Host "  Last result: $($info.LastTaskResult)"
            Write-Host "  Next run : $($info.NextRunTime)"
        }
    } catch {
        Write-Host "  $TaskName : NOT FOUND" -ForegroundColor Yellow
    }

    Write-Host "`n=== NERVE Process ===" -ForegroundColor Cyan
    $pid = Get-NervePid
    if ($pid) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  PID $pid — RUNNING ($($proc.Name))" -ForegroundColor Green
            Write-Host "  CPU: $($proc.CPU)s | Memory: $([math]::Round($proc.WorkingSet64/1MB,1)) MB"
        } else {
            Write-Host "  PID file says $pid but process is DEAD (stale PID file)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  No PID file — NERVE not running or PID not written yet." -ForegroundColor Yellow
    }

    $stateFile = "$ProjectRoot\data\nerve_state.json"
    if (Test-Path $stateFile) {
        Write-Host "`n=== NERVE State ===" -ForegroundColor Cyan
        Get-Content $stateFile | Write-Host
    }
}

function Start-Nerve {
    if (Test-Path $StopFlag) { Remove-Item $StopFlag -Force }
    $env:PYTHONIOENCODING = "utf-8"
    $logPath = "$ProjectRoot\data\nerve_logs\nerve_daemon.log"
    $null = New-Item -ItemType Directory -Force -Path (Split-Path $logPath) -ErrorAction SilentlyContinue
    Write-Log "Starting NERVE daemon..."
    $proc = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList "-m", "automation.nerve", "--daemon" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $logPath `
        -PassThru
    Write-Log "NERVE started — PID $($proc.Id)" "OK"
}

function Stop-Nerve {
    # Write stop flag — NERVE daemon polls this every second during its wait loop
    [System.IO.File]::WriteAllText($StopFlag, (Get-Date -Format "o"))
    Write-Log "Stop flag written to $StopFlag"

    $pid = Get-NervePid
    if ($pid) {
        Write-Log "Sending stop signal to PID $pid..."
        & $PythonExe -c "
import os, signal
try:
    os.kill($pid, signal.SIGTERM)
    print('SIGTERM sent to PID $pid')
except OSError as e:
    print(f'Signal failed: {e}')
"
    } else {
        Write-Log "No running NERVE PID found — stop flag is sufficient." "WARN"
    }
}

function Install-Task {
    Require-Admin

    if (-not (Test-Path $PythonExe)) {
        Write-Host "ERROR: venv Python not found at $PythonExe" -ForegroundColor Red
        Write-Host "Run: python -m venv .venv  (from project root)" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "`n======================================" -ForegroundColor Cyan
    Write-Host "  DIGITAL LABOUR — NERVE Installer"   -ForegroundColor Cyan
    Write-Host "  Task: $TaskName"                     -ForegroundColor Cyan
    Write-Host "======================================`n" -ForegroundColor Cyan

    # Remove stale task if exists
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

    $action = New-ScheduledTaskAction `
        -Execute $PythonExe `
        -Argument "-m automation.nerve --daemon" `
        -WorkingDirectory $ProjectRoot

    $triggerBoot  = New-ScheduledTaskTrigger -AtStartup
    $triggerLogon = New-ScheduledTaskTrigger -AtLogOn

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 2) `
        -ExecutionTimeLimit (New-TimeSpan -Days 365) `
        -MultipleInstances IgnoreNew

    $principal = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -RunLevel Highest `
        -LogonType Interactive

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger @($triggerBoot, $triggerLogon) `
        -Settings $settings `
        -Principal $principal `
        -Description "NERVE Daemon — DIGITAL LABOUR autonomous 24/7 operator" | Out-Null

    Write-Host "[OK] Task '$TaskName' registered." -ForegroundColor Green
    Write-Host ""
    Write-Host "NERVE will auto-start on next boot/logon." -ForegroundColor Cyan
    Write-Host "To start immediately: .\scripts\nerve_service.ps1 -Start" -ForegroundColor Cyan
    Write-Host "To check status:      .\scripts\nerve_service.ps1 -Status" -ForegroundColor Cyan

    Write-Log "Task installed: $TaskName" "OK"
}

function Uninstall-Task {
    Require-Admin
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Task '$TaskName' removed. NERVE will no longer auto-start." -ForegroundColor Yellow
    Write-Log "Task uninstalled: $TaskName" "WARN"
}

# ── Dispatch ────────────────────────────────────────────────────────────────

if ($Install)   { Install-Task }
elseif ($Uninstall) { Uninstall-Task }
elseif ($Status)    { Show-Status }
elseif ($Start)     { Start-Nerve }
elseif ($Stop)      { Stop-Nerve }
else {
    Write-Host "Usage:"
    Write-Host "  -Install    Register Task Scheduler entry (run as Admin, once)"
    Write-Host "  -Uninstall  Remove the task"
    Write-Host "  -Status     Show task + NERVE process status"
    Write-Host "  -Start      Start NERVE daemon now"
    Write-Host "  -Stop       Stop running NERVE daemon gracefully"
}
