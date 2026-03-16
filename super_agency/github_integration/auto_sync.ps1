# Digital Labour Autonomous GitHub Integration
# This script runs the full GitHub sync automatically

Write-Host "🤖 Digital Labour Autonomous GitHub Sync" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Yellow

$integrationPath = "C:\Dev\DIGITAL LABOUR-Shared\github_integration"

# Navigate to integration directory
Set-Location $integrationPath

Write-Host "📍 Working directory: $integrationPath" -ForegroundColor Blue

# Run the sync
Write-Host "🚀 Starting autonomous sync..." -ForegroundColor Green
& ".\run_github_integration.bat" sync

Write-Host "✅ Autonomous sync complete!" -ForegroundColor Green
Write-Host "📊 Check https://github.com/ResonanceEnergy for your repositories" -ForegroundColor Cyan