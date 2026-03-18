#!/bin/bash
# Digital-Labour Dashboard Opener
# Opens OpenClaw Control UI and Matrix Monitor in browser on login
# Called by com.BIT RAGE LABOUR.dashboards.plist

OPENCLAW_URL="http://127.0.0.1:18789"
MATRIX_MONITOR_URL="http://127.0.0.1:3000"
MAX_WAIT=60  # seconds to wait for services

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

wait_for_service() {
    local url="$1"
    local name="$2"
    local elapsed=0

    log "Waiting for $name at $url ..."
    while [ $elapsed -lt $MAX_WAIT ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q "200\|301\|302\|304"; then
            log "$name is UP"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    log "WARNING: $name did not respond within ${MAX_WAIT}s — opening anyway"
    return 1
}

log "=== Digital-Labour Dashboard Opener ==="

# Wait for both services to come online
wait_for_service "$OPENCLAW_URL" "OpenClaw Gateway"
wait_for_service "$MATRIX_MONITOR_URL" "Matrix Monitor"

# Open OpenClaw Control UI in browser
log "Opening OpenClaw Control UI..."
open "$OPENCLAW_URL"

# Open Matrix Monitor in browser
log "Opening Matrix Monitor..."
open "$MATRIX_MONITOR_URL"

log "=== Dashboards opened ==="
