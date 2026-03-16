# REPO DEPOT HEALTH CHECK - 5 Minute Failsafe
# =============================================
# CRITICAL INFRASTRUCTURE - BREAD AND BUTTER
#
# This script runs every 5 minutes via Task Scheduler
# If Repo Depot is not running, it starts it immediately

$ErrorActionPreference = "SilentlyContinue"

$WorkspacePath = "C:\Dev\DIGITAL LABOUR-Shared"
$PythonExe = "$WorkspacePath\.venv\Scripts\python.exe"
$RepoDepotScript = "$WorkspacePath\optimus_repo_depot_launcher.py"
$WatchdogScript = "$WorkspacePath\repo_depot_watchdog.py"
$LogFile = "$WorkspacePath\repo_depot_failsafe.log"

function Write-Log {
    param($Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Timestamp - $Message" | Out-File -Append -FilePath $LogFile
}

# Check if Repo Depot is running
$RepoDepotRunning = Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
        if ($cmdline -match "optimus_repo_depot|repo_depot_launcher") {
            return $true
        }
    }
    catch {}
} | Where-Object { $_ -eq $true }

if (-not $RepoDepotRunning) {
    Write-Log "🔴 REPO DEPOT DOWN - STARTING IMMEDIATELY"

    # Start Repo Depot
    Start-Process -FilePath $PythonExe -ArgumentList "`"$RepoDepotScript`"" -WorkingDirectory $WorkspacePath -WindowStyle Hidden

    Write-Log "✅ Repo Depot started"

    # Also check watchdog
    $WatchdogRunning = Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
            if ($cmdline -match "repo_depot_watchdog") {
                return $true
            }
        }
        catch {}
    } | Where-Object { $_ -eq $true }

    if (-not $WatchdogRunning) {
        Write-Log "🔴 WATCHDOG DOWN - STARTING"
        Start-Process -FilePath $PythonExe -ArgumentList "`"$WatchdogScript`"" -WorkingDirectory $WorkspacePath -WindowStyle Hidden
        Write-Log "✅ Watchdog started"
    }
}

# Also check status file age
$StatusFile = "$WorkspacePath\repo_depot_status.json"
if (Test-Path $StatusFile) {
    $Age = ((Get-Date) - (Get-Item $StatusFile).LastWriteTime).TotalMinutes
    if ($Age -gt 10) {
        Write-Log "⚠️ Status file is $([int]$Age) minutes old - may be stale"
    }
}
