#!/bin/bash
# Bit Rage Systems ULTIMATE FAIL-SAFE STARTUP SCRIPT
# Launches the watchdog service for 24/7/365 operation
# This script ensures the entire agency remains online forever

echo
echo "==============================================="
echo " 🚀 Bit Rage Systems ULTIMATE FAIL-SAFE STARTUP"
echo "==============================================="
echo

# Change to the script directory
cd "$(dirname "$0")"

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ ERROR: Python is not installed or not in PATH"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# Check if watchdog service is already running
if pgrep -f "watchdog_service.py" > /dev/null; then
    echo "⚠️ WARNING: Watchdog service appears to be already running"
    echo "If you're sure it's not running, you can kill existing Python processes"
    echo
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

echo "🐕 Starting Watchdog Service..."
echo "This will launch the fail-safe orchestrator and ensure 24/7 operation"
echo

# Start the watchdog service
nohup $PYTHON_CMD watchdog_service.py > watchdog_startup.log 2>&1 &
WATCHDOG_PID=$!

# Wait a moment for startup
sleep 3

if kill -0 $WATCHDOG_PID 2>/dev/null; then
    echo "✅ Watchdog service started! (PID: $WATCHDOG_PID)"
    echo
    echo "🛡️ SYSTEM STATUS:"
    echo "  • Watchdog Service: ACTIVE (monitoring fail-safe orchestrator)"
    echo "  • Fail-Safe Orchestrator: Starting... (will be monitored by watchdog)"
    echo "  • All Agency Components: Will be started by orchestrator"
    echo
    echo "📊 To monitor the system:"
    echo "  • Check watchdog_service.log for watchdog activity"
    echo "  • Check fail_safe_orchestrator.log for orchestrator activity"
    echo "  • Check alerts.log for any system alerts"
    echo
    echo "🔄 The system will now run continuously in the background."
    echo "Run 'pkill -f watchdog_service.py' to stop everything."
    echo
else
    echo "❌ Failed to start watchdog service"
    echo "Check watchdog_startup.log for details"
    exit 1
fi
