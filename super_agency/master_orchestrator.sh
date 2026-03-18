#!/bin/bash
# Bit Rage Labour Master Orchestrator
# Consolidates all scheduled tasks into one service
# Runs every 15 minutes via launchd

set -eu

WORKSPACE="$HOME/repos/BIT RAGE LABOUR-Shared"
LOG_DIR="$WORKSPACE/orchestrator_logs"
LOG_FILE="$LOG_DIR/master_$(date +%Y%m%d).log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

run_task() {
    local task_name="$1"
    local script="$2"

    log "▶️ Starting: $task_name"

    if [ -f "$WORKSPACE/$script" ]; then
        cd "$WORKSPACE"
        if python3 "$script" >> "$LOG_FILE" 2>&1; then
            log "✅ Completed: $task_name"
        else
            log "❌ Failed: $task_name (exit: $?)"
        fi
    else
        log "⚠️ Script not found: $script"
    fi
}

# Header
log "═══════════════════════════════════════════════════════"
log "🚀 Bit Rage Labour MASTER ORCHESTRATOR"
log "═══════════════════════════════════════════════════════"

# Task 1: Cross-platform refresh
run_task "Cross-Platform Refresh" "cross_platform_refresh.py"

# Task 2: Auto system audit
run_task "Auto System Audit" "auto_system_audit.py"

# Task 3: Repo backup
run_task "Repository Backup" "repo_backup_system.py"

# Task 4: Council meeting (if available)
if [ -f "$WORKSPACE/agent_council_meeting.py" ]; then
    run_task "Agent Council Meeting" "agent_council_meeting.py"
fi

# Task 5: OPTIMUS + GASKET Agent Collaboration (REAL EXECUTOR)
# DISABLED: production_agent_collaboration.py was simulation-only
# REPLACED with real task executor
if [ -f "$WORKSPACE/repo_depot/core/task_executor.py" ]; then
    run_task "REAL Task Executor" "repo_depot/core/task_executor.py"
fi

# Task 6: Doctrine Preservation System
if [ -f "$WORKSPACE/doctrine_preservation_system.py" ]; then
    run_task "Doctrine Preservation" "doctrine_preservation_system.py"
fi

# Task 7: Memory Doctrine System
if [ -f "$WORKSPACE/memory_doctrine_system.py" ]; then
    run_task "Memory Doctrine" "memory_doctrine_system.py"
fi

# Task 8: Backlog Intelligence
if [ -f "$WORKSPACE/backlog_intelligence_system.py" ]; then
    run_task "Backlog Intelligence" "backlog_intelligence_system.py"
fi

# Task 9: GitHub Integration
if [ -f "$WORKSPACE/github_integration/github_integration_system.py" ]; then
    run_task "GitHub Integration" "github_integration/github_integration_system.py"
fi

# Summary
log "═══════════════════════════════════════════════════════"
log "🏁 ORCHESTRATION COMPLETE"
log "═══════════════════════════════════════════════════════"

# Rotate logs (keep last 7 days)
find "$LOG_DIR" -name "master_*.log" -mtime +7 -delete 2>/dev/null || true
