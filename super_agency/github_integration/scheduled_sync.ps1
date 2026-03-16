# Digital Labour Scheduled GitHub Sync
# Run this with Task Scheduler for daily automated updates

param(
    [switch]$Daily,
    [switch]$Weekly,
    [switch]$Force
)

$integrationPath = "C:\Dev\DIGITAL LABOUR-Shared\github_integration"
$logFile = "$integrationPath\scheduled_sync_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Start logging
Start-Transcript -Path $logFile -Append

Write-Host "🤖 Digital Labour Scheduled GitHub Sync" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Yellow
Write-Host "Timestamp: $(Get-Date)" -ForegroundColor Gray

try {
    # Navigate to integration directory
    Set-Location $integrationPath

    # Check if we should run today
    if ($Daily -or $Force) {
        Write-Host "📅 Running daily sync..." -ForegroundColor Green

        # Run the sync
        & ".\run_github_integration.bat" sync

        Write-Host "✅ Daily sync completed successfully!" -ForegroundColor Green
    } elseif ($Weekly) {
        Write-Host "📆 Running weekly maintenance sync..." -ForegroundColor Blue

        # Run full maintenance sync
        & ".\run_github_integration.bat" sync

        Write-Host "✅ Weekly maintenance sync completed!" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  No sync type specified. Use -Daily, -Weekly, or -Force" -ForegroundColor Yellow
    }

} catch {
    Write-Host "❌ Error during sync: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    Stop-Transcript
    Write-Host "📊 Log saved to: $logFile" -ForegroundColor Gray
}