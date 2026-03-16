# Digital Labour Memory Doctrine Logs Backup System
# Saves current state, doctrine updates, and log backups

param(
    [switch]$Compress,
    [switch]$NoCompress,
    [string]$CustomPath
)

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = if ($CustomPath) { "$CustomPath\memory_doctrine_logs_$Timestamp" } else { "backups\memory_doctrine_logs_$Timestamp" }
$LogFile = if ($CustomPath) { "$CustomPath\backup_log_$Timestamp.txt" } else { "backups\backup_log_$Timestamp.txt" }

# Colors for PowerShell
$Colors = @{
    Red = [ConsoleColor]::Red
    Green = [ConsoleColor]::Green
    Yellow = [ConsoleColor]::Yellow
    Blue = [ConsoleColor]::Blue
    White = [ConsoleColor]::White
}

function Write-Log {
    param([string]$Message)
    $LogMessage = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
    Add-Content -Path $LogFile -Value $LogMessage
}

function Write-Info {
    param([string]$Message)
    Write-Log "INFO: $Message"
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] INFO: $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Log "SUCCESS: $Message"
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] SUCCESS: $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Log "WARNING: $Message"
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] WARNING: $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Log "ERROR: $Message"
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] ERROR: $Message" -ForegroundColor Red
}

# Create backup directory
function New-BackupDirectory {
    Write-Info "Creating backup directory: $BackupDir"

    $Directories = @(
        $BackupDir,
        "$BackupDir\doctrine",
        "$BackupDir\memory",
        "$BackupDir\logs",
        "$BackupDir\config",
        "$BackupDir\state"
    )

    foreach ($Dir in $Directories) {
        if (!(Test-Path $Dir)) {
            New-Item -ItemType Directory -Path $Dir -Force | Out-Null
        }
    }

    Write-Success "Backup directories created"
}

# Save current memory state
function Save-Memory {
    Write-Info "Saving current memory state..."

    # Session memory capture
    if (Test-Path "SESSION_MEMORY_CAPTURE.md") {
        Copy-Item "SESSION_MEMORY_CAPTURE.md" "$BackupDir\memory\session_memory_$Timestamp.md"
        Write-Success "Session memory captured"
    }

    # Inner council intelligence
    if (Test-Path "inner_council_intelligence.log") {
        Copy-Item "inner_council_intelligence.log" "$BackupDir\memory\inner_council_intelligence_$Timestamp.log"
        Write-Success "Inner council intelligence saved"
    }

    # YouTube intelligence data
    if (Test-Path "youtube_intelligence_data") {
        Copy-Item -Recurse "youtube_intelligence_data" "$BackupDir\memory\youtube_intelligence_data_$Timestamp"
        Write-Success "YouTube intelligence data saved"
    }

    # Current operations state
    if (Test-Path "operations_command_interface.py") {
        # Capture current running processes
        Get-Process | Where-Object { $_.ProcessName -match "(python|node)" } |
            Select-Object ProcessName, Id, CPU, WorkingSet |
            Out-File "$BackupDir\state\processes_$Timestamp.txt"
        Write-Success "Current process state captured"
    }

    Write-Success "Memory state saved"
}

# Save doctrine files
function Save-Doctrine {
    Write-Info "Saving doctrine files..."

    $DoctrineFiles = @(
        "DOCTRINE_NCL_SECOND_BRAIN.md",
        "DOCTRINE_COUNCIL_52.md",
        "DL_DOCTRINE_MEMORY.md",
        "NORTH_STAR.md",
        "ROADMAP.md"
    )

    foreach ($File in $DoctrineFiles) {
        if (Test-Path $File) {
            $NewName = [System.IO.Path]::GetFileNameWithoutExtension($File) + "_$Timestamp.md"
            Copy-Item $File "$BackupDir\doctrine\$NewName"
            Write-Success "Doctrine saved: $File"
        } else {
            Write-Warning "Doctrine file not found: $File"
        }
    }

    # NCL Second Brain doctrine
    if (Test-Path "ncl_second_brain") {
        if (Test-Path "ncl_second_brain\contracts") {
            Copy-Item -Recurse "ncl_second_brain\contracts" "$BackupDir\doctrine\ncl_contracts_$Timestamp"
        }
        if (Test-Path "ncl_second_brain\engine") {
            Copy-Item -Recurse "ncl_second_brain\engine" "$BackupDir\doctrine\ncl_engine_$Timestamp"
        }
        Write-Success "NCL Second Brain doctrine saved"
    }

    Write-Success "All doctrine files saved"
}

# Backup logs
function Backup-Logs {
    Write-Info "Backing up log files..."

    # Main logs directory
    if (Test-Path "logs") {
        Copy-Item -Recurse "logs" "$BackupDir\logs\main_logs_$Timestamp"
        Write-Success "Main logs backed up"
    }

    # NCC logs
    if (Test-Path "ncc_logs") {
        Copy-Item -Recurse "ncc_logs" "$BackupDir\logs\ncc_logs_$Timestamp"
        Write-Success "NCC logs backed up"
    }

    # Oversight logs
    if (Test-Path "oversight_logs") {
        Copy-Item -Recurse "oversight_logs" "$BackupDir\logs\oversight_logs_$Timestamp"
        Write-Success "Oversight logs backed up"
    }

    # Inner council logs
    if (Test-Path "inner_council_intelligence.log") {
        Copy-Item "inner_council_intelligence.log" "$BackupDir\logs\inner_council_$Timestamp.log"
        Write-Success "Inner council logs backed up"
    }

    # YouTube intelligence logs
    if (Test-Path "youtube_intelligence.log") {
        Copy-Item "youtube_intelligence.log" "$BackupDir\logs\youtube_intelligence_$Timestamp.log"
        Write-Success "YouTube intelligence logs backed up"
    }

    # Reports directory
    if (Test-Path "reports") {
        Copy-Item -Recurse "reports" "$BackupDir\logs\reports_$Timestamp"
        Write-Success "Reports backed up"
    }

    # Daily reports
    if (Test-Path "reports\daily") {
        Copy-Item -Recurse "reports\daily" "$BackupDir\logs\daily_reports_$Timestamp"
        Write-Success "Daily reports backed up"
    }

    Write-Success "All logs backed up"
}

# Save configuration
function Save-Config {
    Write-Info "Saving configuration files..."

    # Config directory
    if (Test-Path "config") {
        Copy-Item -Recurse "config" "$BackupDir\config\main_config_$Timestamp"
        Write-Success "Main config saved"
    }

    # Inner council config
    if (Test-Path "inner_council_config.json") {
        Copy-Item "inner_council_config.json" "$BackupDir\config\inner_council_config_$Timestamp.json"
        Write-Success "Inner council config saved"
    }

    # YouTube intelligence config
    if (Test-Path "youtube_intelligence_config.json") {
        Copy-Item "youtube_intelligence_config.json" "$BackupDir\config\youtube_config_$Timestamp.json"
        Write-Success "YouTube config saved"
    }

    # Portfolio files
    if (Test-Path "portfolio.json") {
        Copy-Item "portfolio.json" "$BackupDir\config\portfolio_$Timestamp.json"
        Write-Success "Portfolio config saved"
    }

    if (Test-Path "portfolio.yaml") {
        Copy-Item "portfolio.yaml" "$BackupDir\config\portfolio_$Timestamp.yaml"
        Write-Success "Portfolio YAML saved"
    }

    Write-Success "Configuration saved"
}

# Save current state
function Save-State {
    Write-Info "Saving current system state..."

    # Git status
    if (Test-Path ".git") {
        try {
            git status --porcelain | Out-File "$BackupDir\state\git_status_$Timestamp.txt"
            git log --oneline -10 | Out-File "$BackupDir\state\git_log_$Timestamp.txt"
            Write-Success "Git state saved"
        } catch {
            Write-Warning "Git state capture failed"
        }
    }

    # Running processes related to Digital Labour
    Get-Process | Where-Object { $_.ProcessName -match "(digital.labour|operations|matrix.monitor|ncl|doctrine)" } |
        Select-Object ProcessName, Id, CPU, WorkingSet |
        Out-File "$BackupDir\state\digital_labour_processes_$Timestamp.txt"

    # System information
    Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, Size, FreeSpace |
        Out-File "$BackupDir\state\disk_usage_$Timestamp.txt"

    Write-Success "System state saved"
}

# Create backup manifest
function New-Manifest {
    Write-Info "Creating backup manifest..."

    $Manifest = "$BackupDir\BACKUP_MANIFEST_$Timestamp.txt"

    @"
Digital Labour Memory Doctrine Logs Backup
Timestamp: $Timestamp
Date: $(Get-Date)
==========================================

BACKUP CONTENTS:
===============
"@ | Out-File $Manifest

    Get-ChildItem -Path $BackupDir -Recurse -File | Select-Object FullName | Out-File $Manifest -Append

    @"

BACKUP SUMMARY:
==============
Total files: $((Get-ChildItem -Path $BackupDir -Recurse -File).Count)
Total size: $((Get-ChildItem -Path $BackupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB).ToString("F2")) MB
"@ | Out-File $Manifest -Append

    Write-Success "Backup manifest created: $Manifest"
}

# Compress backup
function Compress-Backup {
    Write-Info "Compressing backup..."

    $ArchiveName = "digital_labour_backup_$Timestamp.zip"

    try {
        Compress-Archive -Path $BackupDir -DestinationPath $ArchiveName -Force
        Write-Success "Backup compressed: $ArchiveName"

        $ArchiveSize = (Get-Item $ArchiveName).Length / 1MB
        Write-Info "Compressed size: $($ArchiveSize.ToString("F2")) MB"

        # Clean up uncompressed backup
        Remove-Item -Recurse -Force $BackupDir
        Write-Success "Uncompressed backup cleaned up"
    } catch {
        Write-Error "Compression failed: $_"
    }
}

# Main execution
function Invoke-Main {
    Write-Host "🧠 Digital Labour Memory Doctrine Logs Backup" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Timestamp: $Timestamp"
    Write-Host ""

    Write-Info "Starting comprehensive backup operation..."

    New-BackupDirectory
    Save-Memory
    Save-Doctrine
    Backup-Logs
    Save-Config
    Save-State
    New-Manifest

    Write-Host ""
    Write-Success "Backup completed successfully!"
    Write-Host "📁 Backup location: $BackupDir"
    Write-Host "📋 Log file: $LogFile"

    # Handle compression
    if ($Compress) {
        Compress-Backup
    } elseif (!$NoCompress) {
        $CompressChoice = Read-Host "Compress backup? (y/n)"
        if ($CompressChoice -eq 'y' -or $CompressChoice -eq 'Y') {
            Compress-Backup
        }
    }

    Write-Host ""
    Write-Success "Memory, doctrine, and logs backup complete!"
    Write-Host "🔄 System ready for continued operations"
}

# Run main function
Invoke-Main