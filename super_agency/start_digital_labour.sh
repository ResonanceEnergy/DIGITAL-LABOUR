#!/usr/bin/env bash
# Automated launcher for the Bit Rage Labour runtime
# - installs dependencies
# - verifies AAC UI assets directory
# - starts run_bit_rage_labour.py

set -e

echo "[1/3] Installing Python dependencies..."
pip install -r requirements.txt

# check for AAC UI stub or assets
if [ -f "apps/monitor/matrix_monitor/monitoring/aac_matrix_monitor_enhanced.py" ]; then
    echo "AAC monitor module detected. UI will use enhanced version."
else
    echo "No AAC monitor module present; using simple console UI."
fi

echo "[2/3] Starting Bit Rage Labour in run mode..."
python run_bit_rage_labour.py
