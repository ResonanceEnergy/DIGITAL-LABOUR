# Super Agency Performance Monitoring Dashboard
# Real-time monitoring endpoints for system performance

param(
    [switch]$Continuous,
    [int]$RefreshInterval = 30
)

$DashboardFile = "monitoring_dashboard.html"

function Get-SystemMetrics {
    $cpu = Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average
    $memory = Get-WmiObject -Class Win32_OperatingSystem
    $memoryUsage = [math]::Round(($memory.TotalVisibleMemorySize - $memory.FreePhysicalMemory) / $memory.TotalVisibleMemorySize * 100, 2)

    $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
    $diskUsage = [math]::Round(($disk.Size - $disk.FreeSpace) / $disk.Size * 100, 2)

    return @{
        timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        cpu_percent = $cpu.Average
        memory_percent = $memoryUsage
        disk_percent = $diskUsage
        orchestration_cycles = if (Test-Path "continuous_orchestration_log.csv") {
            (Get-Content "continuous_orchestration_log.csv" | Measure-Object).Count
        } else { 0 }
        last_cycle = if (Test-Path "continuous_orchestration_log.csv") {
            $last = Get-Content "continuous_orchestration_log.csv" | Select-Object -Last 1
            if ($last) { ($last -split ',')[0] } else { "Never" }
        } else { "Never" }
    }
}

function Get-OrchestrationStats {
    if (!(Test-Path "continuous_orchestration_log.csv")) {
        return @{
            total_cycles = 0
            avg_duration = 0
            success_rate = 0
            last_24h_cycles = 0
        }
    }

    $logs = Get-Content "continuous_orchestration_log.csv" | ConvertFrom-Csv
    $total = $logs.Count

    if ($total -eq 0) {
        return @{
            total_cycles = 0
            avg_duration = 0
            success_rate = 0
            last_24h_cycles = 0
        }
    }

    # Calculate average duration (remove 's' suffix)
    $durations = $logs | ForEach-Object {
        try { [double]($_.Duration -replace 's$') } catch { 0 }
    }
    $avgDuration = ($durations | Measure-Object -Average).Average

    # Success rate (cycles without ERROR)
    $errors = ($logs | Where-Object { $_.Duration -like "*ERROR*" }).Count
    $successRate = [math]::Round((($total - $errors) / $total) * 100, 2)

    # Last 24h cycles
    $yesterday = (Get-Date).AddDays(-1)
    $recentCycles = ($logs | Where-Object {
        try { [DateTime]::Parse($_.Timestamp) -gt $yesterday } catch { $false }
    }).Count

    return @{
        total_cycles = $total
        avg_duration = [math]::Round($avgDuration, 2)
        success_rate = $successRate
        last_24h_cycles = $recentCycles
    }
}

function Update-Dashboard {
    $metrics = Get-SystemMetrics
    $stats = Get-OrchestrationStats

    $html = @"
<!DOCTYPE html>
<html>
<head>
    <title>Super Agency Performance Dashboard</title>
    <meta http-equiv="refresh" content="$RefreshInterval">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .metric { background: white; padding: 20px; margin: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric h3 { margin-top: 0; color: #333; }
        .value { font-size: 2em; font-weight: bold; color: #007acc; }
        .status-good { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-error { color: #dc3545; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
    </style>
</head>
<body>
    <h1>🧠 Super Agency Performance Dashboard</h1>
    <p>Last updated: $($metrics.timestamp)</p>

    <div class="grid">
        <div class="metric">
            <h3>System Resources</h3>
            <p>CPU Usage: <span class="value">$($metrics.cpu_percent)%</span></p>
            <p>Memory Usage: <span class="value">$($metrics.memory_percent)%</span></p>
            <p>Disk Usage: <span class="value">$($metrics.disk_percent)%</span></p>
        </div>

        <div class="metric">
            <h3>Orchestration Performance</h3>
            <p>Total Cycles: <span class="value">$($stats.total_cycles)</span></p>
            <p>Average Duration: <span class="value">$($stats.avg_duration)s</span></p>
            <p>Success Rate: <span class="value">$($stats.success_rate)%</span></p>
            <p>Last 24h Cycles: <span class="value">$($stats.last_24h_cycles)</span></p>
        </div>

        <div class="metric">
            <h3>System Status</h3>
            <p>Status: <span class="value status-good">ACTIVE</span></p>
            <p>Last Cycle: $($metrics.last_cycle)</p>
            <p>Platform: QUANTUM FORGE (Windows)</p>
        </div>
    </div>

    <h2>Recent Activity</h2>
    <pre>$(if (Test-Path "continuous_orchestration_log.csv") { Get-Content "continuous_orchestration_log.csv" | Select-Object -Last 10 } else { "No orchestration logs yet" })</pre>
</body>
</html>
"@

    $html | Set-Content -Path $DashboardFile -Encoding UTF8
    Write-Host "Dashboard updated: $DashboardFile"
}

# Main execution
if ($Continuous) {
    Write-Host "Starting continuous monitoring dashboard..."
    Write-Host "Dashboard: $DashboardFile"
    Write-Host "Refresh interval: $RefreshInterval seconds"
    Write-Host "Press Ctrl+C to stop"

    while ($true) {
        Update-Dashboard
        Start-Sleep -Seconds $RefreshInterval
    }
} else {
    Update-Dashboard
    Write-Host "Dashboard generated. Open $DashboardFile in a web browser."
}
