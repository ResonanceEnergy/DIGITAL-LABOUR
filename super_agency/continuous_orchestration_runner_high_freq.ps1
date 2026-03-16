# Digital Labour High-Frequency Orchestration Runner
# Runs orchestration cycles every 5 minutes for rapid monitoring

param(
    [int]$IntervalMinutes = 5,
    [switch]$TestMode,
    [switch]$SafeMode
)

$IntervalSeconds = $IntervalMinutes * 60
$CycleCount = 0

Write-Host "⚡ Digital Labour HIGH-FREQUENCY Orchestration Runner" -ForegroundColor Yellow
Write-Host "Interval: $IntervalMinutes minutes ($IntervalSeconds seconds)" -ForegroundColor Cyan
Write-Host "⚠️  HIGH FREQUENCY MODE - Monitor resource usage closely!" -ForegroundColor Red
Write-Host "Press Ctrl+C to stop"
Write-Host ""

# Safety check for high frequency
if ($IntervalMinutes -lt 5 -and -not $TestMode) {
    Write-Host "❌ ERROR: Minimum safe interval is 5 minutes for production use" -ForegroundColor Red
    Write-Host "💡 Use -TestMode for faster testing" -ForegroundColor Yellow
    exit 1
}

while ($true) {
    $CycleCount++
    $StartTime = Get-Date

    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Starting HIGH-FREQ Cycle #$CycleCount" -ForegroundColor Green

    try {
        # Ensure API key is set from environment
        if (-not $env:OPENAI_API_KEY) {
            Write-Host "ERROR: OPENAI_API_KEY environment variable not set" -ForegroundColor Red
            return
        }

        # Run the orchestration cycle
        & python -c "import asyncio; from conductor_agent import ConductorAgent; asyncio.run(ConductorAgent().orchestrate_cycle())"

        $EndTime = Get-Date
        $Duration = ($EndTime - $StartTime).TotalSeconds

        Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - HIGH-FREQ Cycle #$CycleCount completed in $([math]::Round($Duration, 2)) seconds" -ForegroundColor Green

        # Log to file (high-frequency log)
        $LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),HIGH_FREQ_Cycle_$CycleCount,$([math]::Round($Duration, 2))s"
        Add-Content -Path "continuous_orchestration_log_high_freq.csv" -Value $LogEntry

        # Safety check - monitor system resources
        if ($SafeMode) {
            $cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 1).CounterSamples.CookedValue
            $memory = (Get-Counter '\Memory\% Committed Bytes In Use' -SampleInterval 1 -MaxSamples 1).CounterSamples.CookedValue

            if ($cpu -gt 80) {
                Write-Host "⚠️  HIGH CPU USAGE: $([math]::Round($cpu, 1))% - Consider slowing down" -ForegroundColor Yellow
            }
            if ($memory -gt 90) {
                Write-Host "⚠️  HIGH MEMORY USAGE: $([math]::Round($memory, 1))% - Consider slowing down" -ForegroundColor Yellow
            }
        }

    }
    catch {
        Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - ERROR in HIGH-FREQ Cycle #$CycleCount : $($_.Exception.Message)" -ForegroundColor Red
        $LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),HIGH_FREQ_Cycle_$CycleCount,ERROR:$($_.Exception.Message)"
        Add-Content -Path "continuous_orchestration_log_high_freq.csv" -Value $LogEntry
    }

    # Wait for next cycle (unless in test mode)
    if (-not $TestMode) {
        Write-Host "⏱️  Waiting $IntervalMinutes minutes until next high-frequency cycle..." -ForegroundColor Gray
        Start-Sleep -Seconds $IntervalSeconds
    }
    else {
        # In test mode, just wait a few seconds
        Write-Host "🧪 Test mode: waiting 10 seconds..." -ForegroundColor Blue
        Start-Sleep -Seconds 10
    }
}
