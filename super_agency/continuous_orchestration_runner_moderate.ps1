# Digital Labour Moderate-Frequency Orchestration Runner
# Runs orchestration cycles every 10 minutes for balanced monitoring

param(
    [int]$IntervalMinutes = 10,
    [switch]$TestMode
)

$IntervalSeconds = $IntervalMinutes * 60
$CycleCount = 0

Write-Host "🔄 Digital Labour MODERATE-FREQUENCY Orchestration Runner" -ForegroundColor Cyan
Write-Host "Interval: $IntervalMinutes minutes ($IntervalSeconds seconds)" -ForegroundColor Green
Write-Host "📊 Balanced monitoring - good for active development" -ForegroundColor Blue
Write-Host "Press Ctrl+C to stop"
Write-Host ""

while ($true) {
    $CycleCount++
    $StartTime = Get-Date

    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Starting MODERATE Cycle #$CycleCount" -ForegroundColor Green

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

        Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - MODERATE Cycle #$CycleCount completed in $([math]::Round($Duration, 2)) seconds" -ForegroundColor Green

        # Log to file (moderate-frequency log)
        $LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),MODERATE_Cycle_$CycleCount,$([math]::Round($Duration, 2))s"
        Add-Content -Path "continuous_orchestration_log_moderate.csv" -Value $LogEntry

    }
    catch {
        Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - ERROR in MODERATE Cycle #$CycleCount : $($_.Exception.Message)" -ForegroundColor Red
        $LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),MODERATE_Cycle_$CycleCount,ERROR:$($_.Exception.Message)"
        Add-Content -Path "continuous_orchestration_log_moderate.csv" -Value $LogEntry
    }

    # Wait for next cycle (unless in test mode)
    if (-not $TestMode) {
        Write-Host "⏱️  Waiting $IntervalMinutes minutes until next moderate cycle..." -ForegroundColor Gray
        Start-Sleep -Seconds $IntervalSeconds
    }
    else {
        # In test mode, just wait a few seconds
        Write-Host "🧪 Test mode: waiting 10 seconds..." -ForegroundColor Blue
        Start-Sleep -Seconds 10
    }
}
