# NERVE Health Check
# Runs every 5 minutes via Windows Task Scheduler.
# Ensures the watchdog process is alive; restarts it if not.
# Logs to data/health_check.log.

param(
    [switch]$Verbose
)

$ProjectRoot = "c:\dev\DIGITAL LABOUR\DIGITAL LABOUR"
$PythonExe   = "$ProjectRoot\.venv\Scripts\python.exe"
$LogFile     = "$ProjectRoot\data\health_check.log"
$StatusFile  = "$ProjectRoot\data\watchdog_status.json"

function Write-Log {
    param([string]$Msg, [string]$Level = "INFO")
    $ts   = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] [$Level] $Msg"
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
    if ($Verbose) { Write-Host $line }
}

# ── Rotate log if >1 MB ──────────────────────────────────────────────────────
if (Test-Path $LogFile) {
    $size = (Get-Item $LogFile).Length
    if ($size -gt 1MB) {
        Move-Item $LogFile "$LogFile.old" -Force
        Write-Log "Log rotated (was $([math]::Round($size/1KB, 0)) KB)"
    }
}

Write-Log "Health check started"

# ── Is the watchdog already running? ────────────────────────────────────────
$watchdogProcs = Get-WmiObject Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*automation.watchdog*" }

if ($watchdogProcs) {
    $pids = ($watchdogProcs | ForEach-Object { $_.ProcessId }) -join ", "
    Write-Log "Watchdog is running (PID: $pids) — OK"
    exit 0
}

# ── Watchdog not found — check whether it stopped cleanly or crashed ─────────
$stoppedClean = $false
if (Test-Path $StatusFile) {
    try {
        $s = Get-Content $StatusFile -Raw | ConvertFrom-Json
        $stoppedClean = ($s.status -eq "stopped")
    } catch {}
}

if ($stoppedClean) {
    Write-Log "Watchdog was stopped intentionally — not restarting." "INFO"
    exit 0
}

# ── Restart watchdog ─────────────────────────────────────────────────────────
Write-Log "Watchdog not running — starting now..." "WARN"

$env:PYTHONIOENCODING = "utf-8"
Start-Process `
    -FilePath $PythonExe `
    -ArgumentList "-m", "automation.watchdog" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden

Start-Sleep -Seconds 5

$recheck = Get-WmiObject Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*automation.watchdog*" }

if ($recheck) {
    $newPid = ($recheck | Select-Object -First 1).ProcessId
    Write-Log "Watchdog restarted successfully (PID: $newPid)" "OK"
} else {
    Write-Log "Watchdog FAILED to start — manual intervention required!" "ERROR"
    exit 1
}
