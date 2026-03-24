# QFORGE PowerShell Optimizer
# Windows-specific performance enhancements for Bit Rage Systems operations

param(
    [switch]$Optimize,
    [switch]$Monitor,
    [switch]$Cleanup,
    [switch]$Status
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Configuration
$QFORGE_CONFIG = @{
    ProcessPriority = "High"
    CpuAffinity     = "0-7"  # Use first 8 cores
    MemoryLimit     = 4096MB  # 4GB limit for Bit Rage Systems processes
    WorkingSetMin   = 128MB
    WorkingSetMax   = 1024MB  # Reduced from 2048MB to fit Int32
}

function Write-QFORGE {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] QFORGE-$Level $Message" -ForegroundColor $color
}

function Get-SystemInfo {
    $cpu = Get-WmiObject Win32_Processor
    $memory = Get-WmiObject Win32_OperatingSystem
    $totalMemory = [math]::Round($memory.TotalVisibleMemorySize / 1MB, 2)

    return @{
        CPU      = @{
            Name    = $cpu.Name
            Cores   = $cpu.NumberOfCores
            Logical = $cpu.NumberOfLogicalProcessors
            Load    = (Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
        }
        Memory   = @{
            TotalGB      = $totalMemory
            AvailableGB  = [math]::Round($memory.FreePhysicalMemory / 1MB, 2)
            UsagePercent = [math]::Round(($totalMemory - ($memory.FreePhysicalMemory / 1MB)) / $totalMemory * 100, 1)
        }
        Platform = "QFORGE"
    }
}

function Optimize-ProcessPriority {
    Write-QFORGE "Optimizing process priorities"

    # Find Python processes related to Bit Rage Systems
    $pythonProcesses = Get-Process | Where-Object {
        $_.ProcessName -like "*python*"
    }

    $optimized = 0
    foreach ($proc in $pythonProcesses) {
        try {
            $proc.PriorityClass = "High"
            $optimized++
            Write-QFORGE "Set priority HIGH for $($proc.ProcessName) (PID: $($proc.Id))"
        }
        catch {
            Write-QFORGE "Failed to set priority for $($proc.ProcessName): $($_.Exception.Message)" "WARN"
        }
    }

    return @{ ProcessesOptimized = $optimized }
}

function Optimize-CPUAffinity {
    Write-QFORGE "Optimizing CPU affinity"

    # Get CPU core count
    $cpuInfo = Get-SystemInfo
    $coreCount = $cpuInfo.CPU.Logical

    # Use first 8 cores for performance, leave system cores free
    if ($coreCount -ge 8) {
        $affinityMask = 0xFF  # First 8 cores (11111111 in binary)
        $affinityDescription = "First 8 cores"
    }
    else {
        $affinityMask = [math]::Pow(2, $coreCount) - 1  # All cores
        $affinityDescription = "All $coreCount cores"
    }

    $pythonProcesses = Get-Process | Where-Object {
        $_.ProcessName -like "*python*"
    }

    $optimized = 0
    foreach ($proc in $pythonProcesses) {
        try {
            $proc.ProcessorAffinity = $affinityMask
            $optimized++
            Write-QFORGE "Set CPU affinity ($affinityDescription) for $($proc.ProcessName) (PID: $($proc.Id))"
        }
        catch {
            Write-QFORGE "Failed to set affinity for $($proc.ProcessName): $($_.Exception.Message)" "WARN"
        }
    }

    return @{
        AffinityMask       = "0x$($affinityMask.ToString('X'))"
        CoresUsed          = $affinityDescription
        ProcessesOptimized = $optimized
    }
}

function Optimize-MemoryManagement {
    Write-QFORGE "Optimizing memory management"

    $pythonProcesses = Get-Process | Where-Object {
        $_.ProcessName -like "*python*"
    }

    $optimized = 0
    foreach ($proc in $pythonProcesses) {
        try {
            # Set working set limits for better memory management
            $minWorkingSet = $QFORGE_CONFIG.WorkingSetMin
            $maxWorkingSet = $QFORGE_CONFIG.WorkingSetMax

            # Use Windows API to set working set
            $kernel32 = Add-Type -MemberDefinition @"
                [DllImport("kernel32.dll")]
                public static extern bool SetProcessWorkingSetSize(IntPtr hProcess, int dwMinimumWorkingSetSize, int dwMaximumWorkingSetSize);
"@ -Name "Kernel32" -Namespace "Win32" -PassThru

            $handle = $proc.Handle
            $result = $kernel32::SetProcessWorkingSetSize($handle, $minWorkingSet, $maxWorkingSet)

            if ($result) {
                $optimized++
                Write-QFORGE "Set memory limits for $($proc.ProcessName) (PID: $($proc.Id))"
            }
        }
        catch {
            Write-QFORGE "Failed to optimize memory for $($proc.ProcessName): $($_.Exception.Message)" "WARN"
        }
    }

    return @{ ProcessesOptimized = $optimized }
}

function Start-SystemMonitoring {
    Write-QFORGE "Starting system monitoring"

    # Create a background job for monitoring
    $monitorScript = {
        while ($true) {
            $cpu = (Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
            $memory = Get-WmiObject Win32_OperatingSystem
            $memUsage = [math]::Round(($memory.TotalVisibleMemorySize - $memory.FreePhysicalMemory) / $memory.TotalVisibleMemorySize * 100, 1)

            if ($cpu -gt 90 -or $memUsage -gt 90) {
                Write-Host "[$(Get-Date)] QFORGE-MONITOR HIGH LOAD - CPU: $cpu%, Memory: $memUsage%" -ForegroundColor Red
            }

            Start-Sleep -Seconds 30
        }
    }

    try {
        $job = Start-Job -ScriptBlock $monitorScript -Name "QFORGE-Monitor"
        Write-QFORGE "System monitoring started (Job ID: $($job.Id))"
        return @{ MonitorJobId = $job.Id; Status = "Started" }
    }
    catch {
        Write-QFORGE "Failed to start monitoring: $($_.Exception.Message)" "ERROR"
        return @{ Status = "Failed"; Error = $_.Exception.Message }
    }
}

function Get-QFORGEStatus {
    $systemInfo = Get-SystemInfo

    Write-QFORGE "QFORGE System Status"
    Write-Host "=========================="
    Write-Host "Platform: $($systemInfo.Platform)"
    Write-Host "CPU: $($systemInfo.CPU.Name)"
    Write-Host "Cores: $($systemInfo.CPU.Cores) physical, $($systemInfo.CPU.Logical) logical"
    Write-Host "CPU Load: $($systemInfo.CPU.Load)%"
    Write-Host "Memory: $($systemInfo.Memory.UsagePercent)% used ($($systemInfo.Memory.AvailableGB)GB available)"
    Write-Host ""

    # Check Bit Rage Systems processes
    $saProcesses = Get-Process | Where-Object {
        $_.ProcessName -like "*python*"
    }

    Write-Host "Bit Rage Systems Processes:"
    if ($saProcesses.Count -eq 0) {
        Write-Host "  No active Bit Rage Systems processes" -ForegroundColor Yellow
    }
    else {
        foreach ($proc in $saProcesses) {
            Write-Host "  $($proc.ProcessName) (PID: $($proc.Id)) - CPU: $($proc.CPU)% Memory: $([math]::Round($proc.WorkingSet / 1MB, 1))MB"
        }
    }

    return @{
        SystemInfo           = $systemInfo
        SuperAgencyProcesses = $saProcesses.Count
    }
}

function Invoke-SystemCleanup {
    Write-QFORGE "Performing system cleanup"

    # Clear temporary files
    try {
        $tempPath = $env:TEMP
        $filesCleaned = (Get-ChildItem $tempPath -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } | Remove-Item -Force | Measure-Object).Count
        Write-QFORGE "Cleaned $filesCleaned temporary files"
    }
    catch {
        Write-QFORGE "Failed to clean temp files: $($_.Exception.Message)" "WARN"
    }

    # Clear Windows prefetch
    try {
        $prefetchPath = "$env:SystemRoot\Prefetch"
        if (Test-Path $prefetchPath) {
            $prefetchFiles = Get-ChildItem $prefetchPath -File | Measure-Object
            Write-QFORGE "Prefetch contains $($prefetchFiles.Count) files (keeping for performance)"
        }
    }
    catch {
        Write-QFORGE "Could not check prefetch: $($_.Exception.Message)" "WARN"
    }

    return @{ TempFilesCleaned = $filesCleaned }
}

# Main execution
Write-QFORGE "PowerShell Optimizer Started"

if ($Status) {
    Get-QFORGEStatus
    exit
}

if ($Optimize) {
    Write-QFORGE "Applying QFORGE Optimizations"

    $results = @{
        ProcessPriority  = Optimize-ProcessPriority
        CPUAffinity      = Optimize-CPUAffinity
        MemoryManagement = Optimize-MemoryManagement
        SystemCleanup    = Invoke-SystemCleanup
    }

    Write-QFORGE "Optimization Complete!" "SUCCESS"
    Write-Host "Results:" -ForegroundColor Green
    $results | ConvertTo-Json | Write-Host

    exit
}

if ($Monitor) {
    $monitorResult = Start-SystemMonitoring
    if ($monitorResult.Status -eq "Started") {
        Write-QFORGE "Monitoring active. Press Ctrl+C to stop." "SUCCESS"
        try {
            while ($true) { Start-Sleep -Seconds 1 }
        }
        catch {
            Write-QFORGE "Monitoring stopped"
        }
    }
    exit
}

if ($Cleanup) {
    Invoke-SystemCleanup
    exit
}

# Default: Show usage
Write-Host "QFORGE PowerShell Optimizer" -ForegroundColor Cyan
Write-Host "Usage:" -ForegroundColor White
Write-Host "  .\qforge_optimizer.ps1 -Optimize    # Apply all optimizations"
Write-Host "  .\qforge_optimizer.ps1 -Monitor     # Start system monitoring"
Write-Host "  .\qforge_optimizer.ps1 -Cleanup     # Perform system cleanup"
Write-Host "  .\qforge_optimizer.ps1 -Status      # Show system status"
Write-Host ""
Write-Host "Examples:" -ForegroundColor Gray
Write-Host "  .\qforge_optimizer.ps1 -Optimize -Monitor"
Write-Host "  .\qforge_optimizer.ps1 -Status"
