# Digital Labour Autonomous Operations
# Automated GitHub integration and portfolio management

Write-Host "🤖 Digital Labour Autonomous Operations" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Yellow

$rootDir = Split-Path -Parent $PSScriptRoot
$githubOrchestrator = Join-Path $rootDir "github_orchestrator.py"

Write-Host "📍 Root directory: $rootDir" -ForegroundColor Blue
Write-Host "🎯 Running GitHub orchestrator..." -ForegroundColor Green

try {
    # Run the GitHub orchestrator
    & python $githubOrchestrator

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Autonomous operations completed successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Autonomous operations failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error running autonomous operations: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n📊 Check logs in the 'logs' directory for detailed results" -ForegroundColor Cyan
Write-Host "🔄 Next run: Scheduled for daily execution" -ForegroundColor Gray