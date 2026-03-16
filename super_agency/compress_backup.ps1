# Compress Digital Labour Backup
Write-Host "🗜️ Compressing Digital Labour Backup..." -ForegroundColor Cyan

$timestamp = "20260220_180000"
$backupDir = "backups\memory_doctrine_logs_$timestamp"
$archiveName = "digital_labour_backup_$timestamp.zip"

if (Test-Path $backupDir) {
    Compress-Archive -Path $backupDir -DestinationPath $archiveName -Force
    Write-Host "✅ Backup compressed successfully!" -ForegroundColor Green
    Write-Host "📦 Archive: $archiveName" -ForegroundColor Cyan

    # Get archive size
    $size = (Get-Item $archiveName).Length / 1MB
    Write-Host "📊 Size: $([math]::Round($size, 2)) MB" -ForegroundColor Yellow

    Write-Host ""
    Write-Host "🧠 Memory, Doctrine, and Logs Backup Complete!" -ForegroundColor Green
    Write-Host "🔄 System ready for continued operations" -ForegroundColor Cyan
} else {
    Write-Host "❌ Backup directory not found: $backupDir" -ForegroundColor Red
}