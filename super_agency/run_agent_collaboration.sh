#!/bin/bash
# Bit Rage Systems OPTIMUS + GASKET Agent Collaboration Runner
# Runs production agent collaboration every 15 minutes

cd "$HOME/repos/SuperAgency-Shared"

# Run production cycle for 14 minutes (leaves buffer before next run)
PRODUCTION_HOURS=0.23 python3 production_agent_collaboration.py >> gasket_logs/production.log 2>&1

# Keep log trimmed (last 5000 lines)
if [ -f gasket_logs/production.log ]; then
    tail -5000 gasket_logs/production.log > gasket_logs/production.log.tmp
    mv gasket_logs/production.log.tmp gasket_logs/production.log
fi
