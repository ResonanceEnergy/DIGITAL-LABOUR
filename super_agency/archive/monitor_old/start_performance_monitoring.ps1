# Digital Labour Performance Monitoring Launcher
# Runs 24-hour performance monitoring in background

Write-Host "🚀 Starting Digital Labour Performance Monitoring (24 hours)" -ForegroundColor Green
Write-Host "📊 This will run in the background and collect metrics every 15 minutes" -ForegroundColor Cyan
Write-Host "📁 Results will be saved to performance_monitoring\ directory" -ForegroundColor Cyan

Set-Location "C:\Dev\DIGITAL LABOUR-Shared"

# Start monitoring in background (24 hours = 1440 minutes)
$job = Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    & python performance_monitor.py --hours 24 --interval 15
} -ArgumentList (Get-Location)

Write-Host "✅ Performance monitoring started successfully (Job ID: $($job.Id))" -ForegroundColor Green
Write-Host "⏰ Monitoring will run for 24 hours" -ForegroundColor Yellow
Write-Host "📋 Check performance_monitoring\ directory for results" -ForegroundColor Cyan
Write-Host "🛑 To stop monitoring early: Stop-Job -Id $($job.Id); Remove-Job -Id $($job.Id)" -ForegroundColor Red

Read-Host "Press Enter to continue"
