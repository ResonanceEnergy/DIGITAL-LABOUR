<#
.SYNOPSIS
    OPTIMUS MASTER STARTUP — Single entry point for all SuperAgency services.
    Replaces all fragmented schedulers and startup scripts.

.DESCRIPTION
    Launch order (dependency-aware):
      Phase 1 — OpenClaw Gateway       (ws://127.0.0.1:18789)
      Phase 2 — OPTIMUS Engine         (9 subsystems, ports 8080/8501/8890/8891)
      Phase 3 — Resonance Repo Auto    (git sync, no push on startup)

    Scheduled tasks left as independent timers (they run at fixed intervals):
      - NCC-Doctrine Daily/Weekly Backup
      - NCC_Backup_Operations / NCC_Daily_Maintenance / NCC_System_Monitoring
      - SuperAgency-DailyOperations  (daily @ 06:00)
      - SuperAgency-MemoryDoctrine   (daily @ 02:00)
      - Resonance Repo Auto - Daily  (daily @ 06:00)

.NOTES
    Created: 2026-02-27
    Author:  OPTIMUS Engine
    Run as:  Current user (logon trigger)
#>

param(
    [switch]$SkipBrowser,      # Don't open dashboards in browser
    [switch]$SkipResonance,    # Don't run resonance repo auto
    [switch]$DryRun,           # Print plan without executing
    [int]$GatewayWaitSecs = 8  # Seconds to wait for gateway before launching engine
)

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
$ErrorActionPreference = 'Continue'

$WORKSPACE   = "C:\Dev\SuperAgency-Shared"
$PYTHON      = "C:\Python314\python.exe"
$GATEWAY_CMD = "$env:USERPROFILE\.openclaw\gateway.cmd"
$ENGINE_SCRIPT = Join-Path $WORKSPACE "optimus_openclaw_depot.py"
$RESONANCE_SCRIPT = "C:\resonance-uy-py\run-auto.ps1"
$LOG_DIR     = Join-Path $WORKSPACE "startup_logs"
$STAMP       = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LOG_FILE    = Join-Path $LOG_DIR "startup_$STAMP.log"
$STATE_FILE  = Join-Path $WORKSPACE "startup_state.json"
$LOCK_FILE   = Join-Path $LOG_DIR "startup.lock"

# Ports to check
$PORTS = @{
    'OpenClaw Gateway' = 18789
    'Matrix Monitor'   = 8501
    'Matrix Maximizer' = 8080
    'PingChat Send'    = 8890
    'PingChat Recv'    = 8891
}

# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────
if (!(Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null }

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line -ForegroundColor $(switch($Level) {
        'OK'    { 'Green' }
        'WARN'  { 'Yellow' }
        'ERROR' { 'Red' }
        'PHASE' { 'Cyan' }
        default { 'White' }
    })
    Add-Content -Path $LOG_FILE -Value $line -ErrorAction SilentlyContinue
}

# ──────────────────────────────────────────────
# LOCK — prevent double-launch
# ──────────────────────────────────────────────
if (Test-Path $LOCK_FILE) {
    $lockAge = (Get-Date) - (Get-Item $LOCK_FILE).LastWriteTime
    if ($lockAge.TotalMinutes -lt 3) {
        Write-Log "Another startup is already running (lock age: $([int]$lockAge.TotalSeconds)s). Aborting." 'WARN'
        exit 0
    }
    Remove-Item $LOCK_FILE -Force -ErrorAction SilentlyContinue
}
Set-Content -Path $LOCK_FILE -Value (Get-Date -Format o) -ErrorAction SilentlyContinue

try {

# ──────────────────────────────────────────────
# BANNER
# ──────────────────────────────────────────────
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     OPTIMUS MASTER STARTUP — RESONANCE ENERGY        ║" -ForegroundColor Cyan
Write-Host "║     SuperAgency • OpenClaw • RepoDepot • Matrix      ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Log "OPTIMUS MASTER STARTUP initiated" 'PHASE'
Write-Log "Workspace: $WORKSPACE"
Write-Log "Python: $PYTHON"

if ($DryRun) {
    Write-Log "DRY RUN — no services will be started" 'WARN'
}

# ──────────────────────────────────────────────
# ENVIRONMENT VARIABLES
# ──────────────────────────────────────────────
Write-Log "Setting environment variables..."

# Load user-level env vars into this session
$userEnv = [Environment]::GetEnvironmentVariables("User")
foreach ($key in $userEnv.Keys) {
    if ($key -match 'API_KEY|OPENCLAW|ANTHROPIC|XAI|OPENAI|GOOGLE') {
        [Environment]::SetEnvironmentVariable($key, $userEnv[$key], "Process")
    }
}

# Verify critical keys
$criticalKeys = @('ANTHROPIC_API_KEY', 'XAI_API_KEY')
foreach ($k in $criticalKeys) {
    $val = [Environment]::GetEnvironmentVariable($k, "Process")
    if ($val) {
        Write-Log "  $k = $($val.Substring(0, [Math]::Min(12, $val.Length)))..." 'OK'
    } else {
        Write-Log "  $k = NOT SET" 'WARN'
    }
}

# ──────────────────────────────────────────────
# HELPER: Check if a port is listening
# ──────────────────────────────────────────────
function Test-PortListening {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $conn -and $conn.Count -gt 0)
}

# ──────────────────────────────────────────────
# HELPER: Wait for port with timeout
# ──────────────────────────────────────────────
function Wait-ForPort {
    param([int]$Port, [string]$Name, [int]$TimeoutSecs = 15)
    Write-Log "  Waiting for $Name on :$Port..." 
    for ($i = 0; $i -lt $TimeoutSecs; $i++) {
        if (Test-PortListening -Port $Port) {
            Write-Log "  $Name is UP on :$Port" 'OK'
            return $true
        }
        Start-Sleep -Seconds 1
    }
    Write-Log "  $Name did not come up on :$Port within ${TimeoutSecs}s" 'WARN'
    return $false
}

# ──────────────────────────────────────────────
# HELPER: Kill stale processes on a port
# ──────────────────────────────────────────────
function Stop-StaleProcess {
    param([int]$Port, [string]$Name)
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        foreach ($c in $conns) {
            $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Log "  Killing stale $Name (PID $($proc.Id)) on :$Port" 'WARN'
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Seconds 2
    }
}

# ══════════════════════════════════════════════
# PHASE 0 — PRE-FLIGHT: Kill stale engines
# ══════════════════════════════════════════════
Write-Log "" 'PHASE'
Write-Log "═══ PHASE 0: PRE-FLIGHT CLEANUP ═══" 'PHASE'

# Kill any orphaned engine processes (but not the gateway — we'll handle it separately)
$staleEngines = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -match 'optimus_openclaw_depot|matrix_monitor|matrix_maximizer|optimus_repo_depot_launcher' }

if ($staleEngines) {
    foreach ($se in $staleEngines) {
        Write-Log "  Killing stale engine process PID $($se.ProcessId): $($se.CommandLine.Substring(0, [Math]::Min(80, $se.CommandLine.Length)))" 'WARN'
        if (-not $DryRun) {
            Stop-Process -Id $se.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 3
} else {
    Write-Log "  No stale engine processes found" 'OK'
}

# ══════════════════════════════════════════════
# PHASE 1 — OPENCLAW GATEWAY
# ══════════════════════════════════════════════
Write-Log "" 'PHASE'
Write-Log "═══ PHASE 1: OPENCLAW GATEWAY ═══" 'PHASE'

if (Test-PortListening -Port 18789) {
    Write-Log "  OpenClaw Gateway already running on :18789" 'OK'
} else {
    if (Test-Path $GATEWAY_CMD) {
        Write-Log "  Launching OpenClaw Gateway..."
        if (-not $DryRun) {
            # Launch gateway in background via hidden window
            $gatewayArgs = "/c `"$GATEWAY_CMD`""
            Start-Process -FilePath "cmd.exe" -ArgumentList $gatewayArgs -WindowStyle Hidden -WorkingDirectory $WORKSPACE
            
            # Wait for gateway to come up
            $gwUp = Wait-ForPort -Port 18789 -Name "OpenClaw Gateway" -TimeoutSecs $GatewayWaitSecs
            if (-not $gwUp) {
                Write-Log "  Gateway slow to start — engine will retry connection" 'WARN'
            }
        }
    } else {
        Write-Log "  gateway.cmd not found at $GATEWAY_CMD — run 'openclaw setup' first" 'ERROR'
    }
}

# ══════════════════════════════════════════════
# PHASE 2 — OPTIMUS ENGINE (9 subsystems)
# ══════════════════════════════════════════════
Write-Log "" 'PHASE'
Write-Log "═══ PHASE 2: OPTIMUS OPENCLAW DEPOT ENGINE ═══" 'PHASE'

# Check if engine is already running
$engineRunning = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'optimus_openclaw_depot' }

if ($engineRunning) {
    Write-Log "  OPTIMUS engine already running (PID $($engineRunning.ProcessId))" 'OK'
} else {
    if (Test-Path $ENGINE_SCRIPT) {
        Write-Log "  Launching OPTIMUS OPENCLAW DEPOT ENGINE..."
        Write-Log "  Subsystems: PingChat, SharedFiles, TaskExec, Gasket, OpenClaw, RepoDepot, Sync, Monitor, Maximizer"
        if (-not $DryRun) {
            $engineArgs = @(
                $ENGINE_SCRIPT,
                "--peer", "192.168.1.100"
            )
            if ($SkipBrowser) {
                # Note: engine doesn't have this flag yet but we can set env to signal it
                $env:OPTIMUS_SKIP_BROWSER = "1"
            }
            Start-Process -FilePath $PYTHON -ArgumentList $engineArgs -WindowStyle Hidden -WorkingDirectory $WORKSPACE
            
            # Wait for engine subsystems to come up
            Write-Log "  Waiting for engine subsystems..."
            Start-Sleep -Seconds 5
            
            # Check critical ports
            $allUp = $true
            foreach ($svc in @(@{N='Matrix Monitor';P=8501}, @{N='Matrix Maximizer';P=8080}, @{N='PingChat';P=8890})) {
                $up = Wait-ForPort -Port $svc.P -Name $svc.N -TimeoutSecs 20
                if (-not $up) { $allUp = $false }
            }
            
            if ($allUp) {
                Write-Log "  OPTIMUS ENGINE: All subsystems ONLINE" 'OK'
            } else {
                Write-Log "  OPTIMUS ENGINE: Some subsystems slow to start — check logs" 'WARN'
            }
        }
    } else {
        Write-Log "  Engine script not found: $ENGINE_SCRIPT" 'ERROR'
    }
}

# ══════════════════════════════════════════════
# PHASE 3 — RESONANCE REPO AUTO (git sync)
# ══════════════════════════════════════════════
Write-Log "" 'PHASE'
Write-Log "═══ PHASE 3: RESONANCE REPO AUTO ═══" 'PHASE'

if ($SkipResonance) {
    Write-Log "  Skipped (flag)" 'WARN'
} elseif (Test-Path $RESONANCE_SCRIPT) {
    Write-Log "  Running Resonance Repo Auto (no push on startup)..."
    if (-not $DryRun) {
        Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", $RESONANCE_SCRIPT,
            "-NoPush"
        ) -WindowStyle Hidden -WorkingDirectory "C:\resonance-uy-py"
        Write-Log "  Resonance Repo Auto launched in background" 'OK'
    }
} else {
    Write-Log "  Resonance script not found: $RESONANCE_SCRIPT" 'WARN'
}

# ══════════════════════════════════════════════
# PHASE 4 — STATUS REPORT
# ══════════════════════════════════════════════
Write-Log "" 'PHASE'
Write-Log "═══ PHASE 4: STATUS REPORT ═══" 'PHASE'

if (-not $DryRun) {
    Start-Sleep -Seconds 3

    foreach ($svc in $PORTS.GetEnumerator()) {
        if (Test-PortListening -Port $svc.Value) {
            Write-Log "  $($svc.Key) [:$($svc.Value)] — ONLINE" 'OK'
        } else {
            Write-Log "  $($svc.Key) [:$($svc.Value)] — OFFLINE" 'ERROR'
        }
    }

    # Count engine processes
    $engineProcs = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'optimus_openclaw_depot|matrix_monitor|matrix_maximizer' })
    $nodeProcs = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'openclaw' })

    Write-Log ""
    Write-Log "  Python processes: $($engineProcs.Count)" 'OK'
    Write-Log "  Node processes:   $($nodeProcs.Count)" 'OK'

    # Write state file
    $state = @{
        timestamp    = (Get-Date -Format o)
        status       = 'RUNNING'
        services     = @{}
        python_pids  = $engineProcs | ForEach-Object { $_.ProcessId }
        node_pids    = $nodeProcs | ForEach-Object { $_.ProcessId }
    }
    foreach ($svc in $PORTS.GetEnumerator()) {
        $state.services[$svc.Key] = @{
            port   = $svc.Value
            online = (Test-PortListening -Port $svc.Value)
        }
    }
    $state | ConvertTo-Json -Depth 4 | Set-Content -Path $STATE_FILE -Encoding UTF8
    Write-Log "  State written to: $STATE_FILE" 'OK'
}

# ──────────────────────────────────────────────
# DONE
# ──────────────────────────────────────────────
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║        OPTIMUS MASTER STARTUP — COMPLETE             ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Log "OPTIMUS MASTER STARTUP complete" 'PHASE'
Write-Log "Log: $LOG_FILE"

} finally {
    # Always clean up lock
    Remove-Item $LOCK_FILE -Force -ErrorAction SilentlyContinue
}
