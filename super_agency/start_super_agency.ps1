# ============================================
# Bit Rage Systems LAUNCHER
# ============================================
# Activates venv, sets encoding, launches runtime.
# Designed to be called by Windows Task Scheduler.
# ============================================

$ErrorActionPreference = "Continue"

$WorkspacePath = "C:\Dev\SuperAgency-Shared"
$VenvActivate = "$WorkspacePath\.venv\Scripts\Activate.ps1"
$PythonExe = "$WorkspacePath\.venv\Scripts\python.exe"
$Script = "$WorkspacePath\run_super_agency.py"
$LogDir = "$WorkspacePath\startup_logs"

# Create log directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LogFile = "$LogDir\startup_$Timestamp.log"

function Write-Log {
    param([string]$Message)
    $entry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Add-Content -Path $LogFile -Value $entry
    Write-Host $entry
}

Write-Log "[LAUNCHER] Bit Rage Systems startup initiated"
Write-Log "[LAUNCHER] Workspace: $WorkspacePath"

# Validate prerequisites
if (-not (Test-Path $PythonExe)) {
    Write-Log "[LAUNCHER] FATAL: Python not found at $PythonExe"
    exit 1
}
if (-not (Test-Path $Script)) {
    Write-Log "[LAUNCHER] FATAL: run_super_agency.py not found"
    exit 1
}

# Set working directory
Set-Location $WorkspacePath

# Activate virtual environment
if (Test-Path $VenvActivate) {
    . $VenvActivate
    Write-Log "[LAUNCHER] Virtual environment activated"
} else {
    Write-Log "[LAUNCHER] WARNING: venv not found, using bare python"
}

# Critical: prevent cp1252 UnicodeEncodeError on Windows console
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Write-Log "[LAUNCHER] PYTHONIOENCODING=$env:PYTHONIOENCODING"
Write-Log "[LAUNCHER] Starting run_super_agency.py ..."

# Write PID-tracking state file for health checker
$proc = Start-Process -FilePath $PythonExe `
    -ArgumentList "`"$Script`"" `
    -WorkingDirectory $WorkspacePath `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput "$LogDir\stdout_$Timestamp.log" `
    -RedirectStandardError "$LogDir\stderr_$Timestamp.log"

$state = @{
    pid       = $proc.Id
    started   = (Get-Date).ToString("o")
    script    = $Script
    workspace = $WorkspacePath
} | ConvertTo-Json

$state | Set-Content "$WorkspacePath\startup_state.json" -Encoding UTF8

Write-Log "[LAUNCHER] Process started PID=$($proc.Id)"
Write-Log "[LAUNCHER] State written to startup_state.json"

# Wait for the process so Task Scheduler keeps the task "Running"
$proc.WaitForExit()
$exitCode = $proc.ExitCode
Write-Log "[LAUNCHER] Process exited with code $exitCode"
exit $exitCode
