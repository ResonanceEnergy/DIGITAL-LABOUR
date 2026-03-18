#!/bin/bash
###############################################################################
# Digital-Labour Service Watchdog — 24/7/365 Failsafe Health Monitor
# Runs every 15 minutes via com.BIT RAGE LABOUR.watchdog launchd plist
#
# Monitors:
#   1. OpenClaw Gateway    — http://127.0.0.1:18789  (ai.openclaw.gateway)
#   2. Matrix Monitor V3   — http://127.0.0.1:3000   (com.BIT RAGE LABOUR.matrixmonitor)
#
# Actions:
#   - Check HTTP health of each service
#   - If down → restart via launchctl
#   - If still down after restart → escalate via Telegram bot alert
#   - Logs everything to /tmp/BIT RAGE LABOUR_watchdog.log
###############################################################################

# ─── Configuration ───────────────────────────────────────────────────────────
OPENCLAW_URL="http://127.0.0.1:18789"
OPENCLAW_LABEL="ai.openclaw.gateway"

MATRIX_URL="http://127.0.0.1:3000"
MATRIX_LABEL="com.BIT RAGE LABOUR.matrixmonitor"

DASHBOARDS_LABEL="com.BIT RAGE LABOUR.dashboards"

LOG_FILE="/tmp/BIT RAGE LABOUR_watchdog.log"
STATE_FILE="/tmp/BIT RAGE LABOUR_watchdog_state.json"
MAX_LOG_LINES=5000

TELEGRAM_BOT_TOKEN="8766824944:AAGsZtV_AlqzX6LokmffiNwYlkcz77bq7jE"
TELEGRAM_CHAT_ID="8253467085"

OPENCLAW_BIN="/Users/gripandripphdd/.nvm/versions/node/v25.6.1/bin/openclaw"
LAUNCHCTL="/bin/launchctl"
UID_NUM=$(id -u)

CURL="/usr/bin/curl"
PGREP="/usr/bin/pgrep"

# Max consecutive failures before Telegram alert
ALERT_THRESHOLD=2
# Max consecutive failures before hard reboot attempt
HARD_REBOOT_THRESHOLD=4

# ─── Logging ─────────────────────────────────────────────────────────────────
log() {
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$ts] $1" >> "$LOG_FILE"
}

log_rotate() {
    if [[ -f "$LOG_FILE" ]]; then
        local lines
        lines=$(wc -l < "$LOG_FILE" 2>/dev/null || echo "0")
        if (( lines > MAX_LOG_LINES )); then
            tail -n "$((MAX_LOG_LINES / 2))" "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
            log "LOG ROTATED (was $lines lines)"
        fi
    fi
}

# ─── State Tracking ─────────────────────────────────────────────────────────
# Simple JSON state file to track consecutive failures per service
read_fail_count() {
    local svc="$1"
    if [[ -f "$STATE_FILE" ]]; then
        /usr/bin/python3 -c "
import json, sys
try:
    with open('$STATE_FILE') as f:
        d = json.load(f)
    print(d.get('$svc', 0))
except:
    print(0)
" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

write_fail_count() {
    local svc="$1"
    local count="$2"
    /usr/bin/python3 -c "
import json, os
state_file = '$STATE_FILE'
try:
    with open(state_file) as f:
        d = json.load(f)
except:
    d = {}
d['$svc'] = $count
with open(state_file, 'w') as f:
    json.dump(d, f)
" 2>/dev/null
}

reset_fail_count() {
    write_fail_count "$1" 0
}

# ─── Telegram Alerting ──────────────────────────────────────────────────────
send_telegram_alert() {
    local message="$1"
    local encoded
    encoded=$(echo -n "$message" | /usr/bin/python3 -c "import sys,urllib.parse; print(urllib.parse.quote(sys.stdin.read()))" 2>/dev/null)
    
    $CURL -s -o /dev/null --max-time 10 \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage?chat_id=${TELEGRAM_CHAT_ID}&text=${encoded}&parse_mode=Markdown" \
        2>/dev/null
    
    local rc=$?
    if [[ $rc -eq 0 ]]; then
        log "TELEGRAM ALERT SENT: $message"
    else
        log "TELEGRAM ALERT FAILED (curl exit $rc)"
    fi
}

# ─── Health Check ────────────────────────────────────────────────────────────
check_service_http() {
    local url="$1"
    local name="$2"
    
    local http_code
    http_code=$($CURL -s -o /dev/null -w "%{http_code}" --max-time 8 "$url" 2>/dev/null)
    
    if [[ "$http_code" =~ ^(200|301|302|304)$ ]]; then
        return 0
    else
        log "HEALTH FAIL: $name returned HTTP $http_code (expected 200)"
        return 1
    fi
}

check_process_running() {
    local label="$1"
    $LAUNCHCTL list "$label" >/dev/null 2>&1
    return $?
}

# ─── Service Restart ─────────────────────────────────────────────────────────
restart_service() {
    local label="$1"
    local name="$2"
    
    log "RESTARTING $name ($label)..."
    
    # Try kickstart -k (kill and restart) first
    $LAUNCHCTL kickstart -k "gui/${UID_NUM}/${label}" 2>/dev/null
    local rc=$?
    
    if [[ $rc -ne 0 ]]; then
        log "kickstart failed for $label, trying unload/load..."
        $LAUNCHCTL bootout "gui/${UID_NUM}/${label}" 2>/dev/null
        sleep 2
        $LAUNCHCTL bootstrap "gui/${UID_NUM}" ~/Library/LaunchAgents/${label}.plist 2>/dev/null
        rc=$?
    fi
    
    if [[ $rc -eq 0 ]]; then
        log "RESTART ISSUED for $name"
    else
        log "RESTART FAILED for $name (exit $rc)"
    fi
    
    return $rc
}

hard_reboot_service() {
    local label="$1"
    local name="$2"
    
    log "HARD REBOOT: $name ($label) — killing all processes and reloading..."
    
    # Kill any lingering processes
    case "$label" in
        ai.openclaw.gateway)
            pkill -9 -f 'openclaw' 2>/dev/null
            pkill -9 -f 'openclaw-gateway' 2>/dev/null
            ;;
        com.BIT RAGE LABOUR.matrixmonitor)
            pkill -9 -f 'matrix_maximizer_v3' 2>/dev/null
            # Also kill anything on port 3000
            lsof -ti :3000 2>/dev/null | xargs kill -9 2>/dev/null
            ;;
    esac
    
    sleep 3
    
    # Unload then reload
    $LAUNCHCTL bootout "gui/${UID_NUM}/${label}" 2>/dev/null
    sleep 2
    
    if [[ "$label" == "ai.openclaw.gateway" ]]; then
        $LAUNCHCTL bootstrap "gui/${UID_NUM}" ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null
    else
        $LAUNCHCTL bootstrap "gui/${UID_NUM}" ~/Library/LaunchAgents/${label}.plist 2>/dev/null
    fi
    
    log "HARD REBOOT COMPLETE for $name — waiting for startup..."
    sleep 10
}

# ─── Monitor Single Service ─────────────────────────────────────────────────
monitor_service() {
    local url="$1"
    local label="$2"
    local name="$3"
    
    local fail_count
    fail_count=$(read_fail_count "$label")
    
    if check_service_http "$url" "$name"; then
        # Service is healthy
        if [[ "$fail_count" -gt 0 ]]; then
            log "RECOVERED: $name is back online after $fail_count failure(s)"
            if [[ "$fail_count" -ge "$ALERT_THRESHOLD" ]]; then
                send_telegram_alert "✅ *RECOVERED*: $name is back online after ${fail_count} check failure(s)."
            fi
            reset_fail_count "$label"
        fi
        log "OK: $name — HTTP 200"
        return 0
    fi
    
    # Service is DOWN
    fail_count=$((fail_count + 1))
    write_fail_count "$label" "$fail_count"
    
    log "DOWN: $name — failure #${fail_count}"
    
    if [[ "$fail_count" -ge "$HARD_REBOOT_THRESHOLD" ]]; then
        # Hard reboot
        log "ESCALATION: $name has failed $fail_count consecutive checks — HARD REBOOT"
        send_telegram_alert "🔴 *CRITICAL*: $name has been DOWN for $fail_count checks (~$((fail_count * 15)) min). Performing HARD REBOOT."
        hard_reboot_service "$label" "$name"
        
        # Check if hard reboot worked
        sleep 5
        if check_service_http "$url" "$name"; then
            log "HARD REBOOT SUCCESS: $name is back online"
            send_telegram_alert "✅ *HARD REBOOT SUCCESS*: $name is back online."
            reset_fail_count "$label"
        else
            log "HARD REBOOT FAILED: $name still down"
            send_telegram_alert "🚨 *HARD REBOOT FAILED*: $name is STILL DOWN after hard reboot. Manual intervention may be required."
        fi
        
    elif [[ "$fail_count" -ge "$ALERT_THRESHOLD" ]]; then
        # Alert + normal restart
        send_telegram_alert "⚠️ *WARNING*: $name is DOWN (failure #${fail_count}, ~$((fail_count * 15)) min). Attempting restart..."
        restart_service "$label" "$name"
        
        # Wait and re-check
        sleep 15
        if check_service_http "$url" "$name"; then
            log "RESTART SUCCESS: $name is back online"
            send_telegram_alert "✅ *RESTART SUCCESS*: $name recovered after restart."
            reset_fail_count "$label"
        else
            log "RESTART FAILED: $name still down — will escalate next cycle"
        fi
        
    else
        # First failure — try quiet restart, no alert yet
        log "FIRST FAILURE: $name — attempting quiet restart"
        restart_service "$label" "$name"
        
        sleep 15
        if check_service_http "$url" "$name"; then
            log "QUIET RESTART SUCCESS: $name recovered"
            reset_fail_count "$label"
        else
            log "QUIET RESTART FAILED: $name — will alert on next check"
        fi
    fi
}

# ─── OpenClaw Telegram Channel Check ────────────────────────────────────────
check_telegram_channel() {
    # Verify the Telegram bot is actually polling
    local bot_info
    bot_info=$($CURL -s --max-time 8 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" 2>/dev/null)
    
    if echo "$bot_info" | grep -q '"ok":true'; then
        log "OK: Telegram bot API reachable"
    else
        log "WARN: Telegram bot API unreachable — bot may be offline"
    fi
}

# ─── Dashboard Browser Check ────────────────────────────────────────────────
ensure_dashboards_plist() {
    if ! $LAUNCHCTL list "$DASHBOARDS_LABEL" >/dev/null 2>&1; then
        log "WARN: Dashboards plist not loaded — loading..."
        $LAUNCHCTL load ~/Library/LaunchAgents/com.BIT RAGE LABOUR.dashboards.plist 2>/dev/null
    fi
}

# ─── Main ────────────────────────────────────────────────────────────────────
main() {
    log "=========================================="
    log "WATCHDOG RUN START"
    log "=========================================="
    
    # Rotate log if needed
    log_rotate
    
    # Check each service
    monitor_service "$OPENCLAW_URL"  "$OPENCLAW_LABEL"  "OpenClaw Gateway"
    monitor_service "$MATRIX_URL"    "$MATRIX_LABEL"    "Matrix Monitor V3"
    
    # Verify Telegram channel is alive
    check_telegram_channel
    
    # Ensure dashboards plist is loaded
    ensure_dashboards_plist
    
    log "WATCHDOG RUN COMPLETE"
    log ""
}

main "$@"
