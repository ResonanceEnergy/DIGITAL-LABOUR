#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# launch_optimus.sh — Manual launch / restart for OPTIMUS Discord bot
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

PYTHON="/Users/gripandripphdd/botenv/bin/python"
BOT="$HOME/repos/DIGITAL LABOUR-Shared/scripts/optimus_discord_bot.py"
LOG_DIR="/tmp/DIGITAL LABOUR"
LOG="$LOG_DIR/optimus_bot.log"

# Load env file if it exists
ENV_FILE="$HOME/repos/DIGITAL LABOUR-Shared/.env.optimus"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

mkdir -p "$LOG_DIR"

# Kill any existing instance
if pgrep -f "optimus_discord_bot.py" > /dev/null 2>&1; then
    echo "$(date): Stopping existing OPTIMUS instance..." | tee -a "$LOG"
    pkill -f "optimus_discord_bot.py" || true
    sleep 2
fi

echo "$(date): Starting OPTIMUS Discord bot..." | tee -a "$LOG"
OPTIMUS_DISCORD_BOT_TOKEN="${OPTIMUS_DISCORD_BOT_TOKEN}" \
DISCORD_GUILD_ID="${DISCORD_GUILD_ID:-}" \
DL_REPO="/Users/gripandripphdd/repos/Digital-Labour" \
nohup "$PYTHON" "$BOT" >> "$LOG" 2>&1 &

echo "$(date): OPTIMUS launched (PID $!). Log: $LOG"
