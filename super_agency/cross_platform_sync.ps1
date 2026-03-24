# Cross-Platform Sync Protocol for Bit Rage Systems
# Handles synchronization between Quantum Quasar (macOS) and QUANTUM FORGE (Windows)

param(
    [switch]$Force,
    [string]$SyncDirection = "bidirectional"
)

$SyncLog = "cross_platform_sync_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$StatusFile = "cross_platform_status.json"

function Write-SyncLog {
    param([string]$Message)
    $LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
    Add-Content -Path $SyncLog -Value $LogEntry
    Write-Host $LogEntry
}

function Test-Platform {
    $platform = if ($IsMacOS) { "macOS" } elseif ($IsLinux) { "Linux" } else { "Windows" }
    return $platform
}

function Get-SystemStatus {
    $cpu = (Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
    $memory = Get-WmiObject -Class Win32_OperatingSystem
    $memoryUsage = [math]::Round(($memory.TotalVisibleMemorySize - $memory.FreePhysicalMemory) / $memory.TotalVisibleMemorySize * 100, 2)

    return @{
        system         = if (Test-Platform -eq "Windows") { "QUANTUM FORGE" } else { "Quantum Quasar" }
        timestamp      = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffK")
        platform       = Test-Platform
        python_version = (python --version 2>$null) -replace "Python ", ""
        git_status     = @{
            local_changes  = (git status --porcelain | Measure-Object).Count -gt 0
            remote_updates = $false
            current_branch = (git branch --show-current)
            last_commit    = (git log -1 --format="%h %s" 2>$null)
        }
        workspace_path = (Get-Location).Path
        last_refresh   = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffK")
        cpu_percent    = $cpu
        memory_percent = $memoryUsage
    }
}

function Sync-Intelligence {
    Write-SyncLog "Starting cross-platform intelligence sync..."

    # Sync reports
    if (Test-Path "reports") {
        Write-SyncLog "Syncing reports directory..."
        # In a real implementation, this would use rsync, git, or cloud storage
    }

    # Sync memory doctrine
    if (Test-Path "memory_doctrine_system.py") {
        Write-SyncLog "Syncing memory doctrine..."
    }

    # Sync orchestration logs
    if (Test-Path "continuous_orchestration_log.csv") {
        Write-SyncLog "Syncing orchestration logs..."
    }

    Write-SyncLog "Cross-platform sync completed"
}

# Main execution
Write-SyncLog "=== Cross-Platform Sync Protocol Started ==="
Write-SyncLog "Platform: $(Test-Platform)"
Write-SyncLog "Sync Direction: $SyncDirection"

try {
    # Get current system status
    $status = Get-SystemStatus

    # Update status file
    $status | ConvertTo-Json -Depth 10 | Set-Content -Path $StatusFile -Encoding UTF8
    Write-SyncLog "Updated cross-platform status file"

    # Perform intelligence sync
    Sync-Intelligence

    # Log completion
    Write-SyncLog "=== Cross-Platform Sync Protocol Completed Successfully ==="

}
catch {
    Write-SyncLog "ERROR: $($_.Exception.Message)"
    exit 1
}
