#!/bin/bash
# Bit Rage Systems Auto Audit Runner
# Triggered every 15 minutes by launchd

cd "$HOME/repos/SuperAgency-Shared"

# Run the audit
python3 auto_system_audit.py >> audit_logs/scheduler.log 2>&1

# Keep scheduler log trimmed (last 1000 lines)
if [ -f audit_logs/scheduler.log ]; then
    tail -1000 audit_logs/scheduler.log > audit_logs/scheduler.log.tmp
    mv audit_logs/scheduler.log.tmp audit_logs/scheduler.log
fi
