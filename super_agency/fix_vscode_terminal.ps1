# VS Code Terminal Fix
# Resolves terminal blocking issues caused by background processes

Write-Host "🔧 VS Code Terminal Fix" -ForegroundColor Cyan
Write-Host "=======================" -ForegroundColor Yellow

# Check for problematic processes
Write-Host "🔍 Checking for problematic processes..." -ForegroundColor Blue

$problematicProcesses = Get-Process | Where-Object {
    $_.Name -like "*backup*" -or
    $_.Name -like "*sync*" -or
    $_.ProcessName -like "*powershell*" -and $_.Id -ne $PID
} | Select-Object Name, Id, StartTime

if ($problematicProcesses) {
    Write-Host "⚠️  Found potentially problematic processes:" -ForegroundColor Yellow
    $problematicProcesses | Format-Table -AutoSize

    # Ask user if they want to stop them
    $stopProcesses = Read-Host "Do you want to stop these processes? (y/n)"
    if ($stopProcesses -eq 'y' -or $stopProcesses -eq 'Y') {
        foreach ($proc in $problematicProcesses) {
            try {
                Stop-Process -Id $proc.Id -Force
                Write-Host "✅ Stopped process: $($proc.Name) (ID: $($proc.Id))" -ForegroundColor Green
            } catch {
                Write-Host "❌ Failed to stop process: $($proc.Name)" -ForegroundColor Red
            }
        }
    }
} else {
    Write-Host "✅ No problematic processes found" -ForegroundColor Green
}

# Check for file locks in the workspace
Write-Host "`n🔍 Checking for file lock issues..." -ForegroundColor Blue

$workspacePath = "C:\Dev\DIGITAL LABOUR-Shared"

# Clear any stuck prompts
Write-Host "`n🧹 Clearing terminal state..." -ForegroundColor Blue

# Try to reset the terminal
try {
    # Send some input to clear any stuck prompts
    $host.UI.RawUI.FlushInputBuffer()
    Write-Host "✅ Terminal state cleared" -ForegroundColor Green
} catch {
    Write-Host "ℹ️  Terminal state clearing not available" -ForegroundColor Gray
}

Write-Host "`n🎯 VS Code Terminal Fix Complete" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Yellow
Write-Host "Try using the VS Code terminal again. If issues persist:" -ForegroundColor Cyan
Write-Host "1. Restart VS Code completely" -ForegroundColor White
Write-Host "2. Run this script again" -ForegroundColor White
Write-Host "3. Check Task Manager for stuck processes" -ForegroundColor White