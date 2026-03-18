#!/bin/bash
# Bit Rage Labour Auto Repo Backup Runner
# Triggered every 15 minutes by launchd

cd "$HOME/repos/BIT RAGE LABOUR-Shared"

# Run the backup
python3 auto_repo_backup.py >> backup_logs/scheduler.log 2>&1

# Keep scheduler log trimmed (last 2000 lines)
if [ -f backup_logs/scheduler.log ]; then
    tail -2000 backup_logs/scheduler.log > backup_logs/scheduler.log.tmp
    mv backup_logs/scheduler.log.tmp backup_logs/scheduler.log
fi
