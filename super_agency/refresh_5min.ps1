# Refresh script to run every 5 minutes
# performs memory/doctrine backup, backlog update and repo sync

# note: this file should be referenced by a Windows scheduled task

Write-Output "[Refresh] $(Get-Date -Format o) - beginning 5‑minute refresh"

# 1. back up memory & doctrine
if (Test-Path .\backup_memory_doctrine_logs.ps1) {
    & .\backup_memory_doctrine_logs.ps1
}
else {
    Write-Warning "backup_memory_doctrine_logs.ps1 not found"
}

# 2. update backlog
if (Test-Path .\backlog_management_system.py) {
    python .\backlog_management_system.py
}
else {
    Write-Warning "backlog_management_system.py not found"
}

# 3. pull latest code
try {
    git -C "${PWD}" pull
}
catch {
    Write-Warning "git pull failed: $_"
}

Write-Output "[Refresh] $(Get-Date -Format o) - finished"
