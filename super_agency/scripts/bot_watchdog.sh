#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# bot_watchdog.sh — Failsafe for OPTIMUS (and GASKET) Discord bots
# Runs every 15 minutes via launchd. If a bot is not running,
# tries launchctl first, then falls back to direct launch.
# ─────────────────────────────────────────────────────────────────
LOG_DIR="/tmp/superagency"
LOG="$LOG_DIR/bot_watchdog.log"
mkdir -p "$LOG_DIR"

PYTHON="/Users/gripandripphdd/botenv/bin/python"
ENV_FILE="$HOME/repos/SuperAgency-Shared/.env.optimus"

# Load token/guild env vars
if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

NOW=$(date '+%Y-%m-%d %H:%M:%S')

# ── Function: ensure a bot is running ─────────────────────────────
ensure_running() {
    local label="$1"        # launchd label
    local script="$2"       # python script path
    local name="$3"         # friendly name for logs

    if pgrep -f "$(basename "$script")" > /dev/null 2>&1; then
        echo "$NOW [$name] RUNNING ✓" >> "$LOG"
        return 0
    fi

    echo "$NOW [$name] NOT RUNNING — attempting restart..." >> "$LOG"

    # Attempt 1: launchctl kickstart (preferred — launchd manages it)
    if launchctl list "$label" > /dev/null 2>&1; then
        launchctl kickstart -k "gui/$(id -u)/$label" >> "$LOG" 2>&1 \
            && echo "$NOW [$name] Restarted via launchctl ✓" >> "$LOG" \
            && return 0
    fi

    # Attempt 2: direct nohup launch (fallback if launchd not loaded)
    echo "$NOW [$name] launchctl failed — launching directly..." >> "$LOG"
    OPTIMUS_DISCORD_BOT_TOKEN="${OPTIMUS_DISCORD_BOT_TOKEN:-}" \
    DISCORD_GUILD_ID="${DISCORD_GUILD_ID:-}" \
    SUPER_AGENCY_REPO="/Users/gripandripphdd/repos/Super-Agency" \
    nohup "$PYTHON" "$script" >> "$LOG_DIR/${name,,}_bot.log" 2>&1 &

    sleep 3
    if pgrep -f "$(basename "$script")" > /dev/null 2>&1; then
        echo "$NOW [$name] Direct launch succeeded ✓ (PID $!)" >> "$LOG"
    else
        echo "$NOW [$name] FAILED TO START — manual intervention needed ✗" >> "$LOG"
    fi
}

# ── Watch OPTIMUS ──────────────────────────────────────────────────
ensure_running \
    "com.superagency.optimusbot" \
    "$HOME/repos/SuperAgency-Shared/scripts/optimus_discord_bot.py" \
    "OPTIMUS"

# ── Watch GASKET (uncomment when GASKET bot is deployed) ──────────
# ensure_running \
#     "com.superagency.gasketbot" \
#     "$HOME/repos/SuperAgency-Shared/scripts/gasket_discord_bot.py" \
#     "GASKET"

# ── Trim log to last 500 lines ────────────────────────────────────
if [[ -f "$LOG" ]]; then
    tail -500 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi
