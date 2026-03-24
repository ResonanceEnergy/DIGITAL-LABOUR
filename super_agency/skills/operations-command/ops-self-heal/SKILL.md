# SKILL: ops-self-heal
## Self-Healing Server Pattern

Continuous watchdog that monitors all Super-Agency services, detects failures,
and auto-remediates without human intervention. Covers OpenClaw gateway,
REPO DEPOT agents, Memory Doctrine, Matrix Monitor, and all department services.

### Triggers
- Cron: Every 5 minutes (heartbeat)
- Event: Service health check failure
- Event: GASKET escalation (self-heal request)
- Manual: "heal system", "check services"

### What It Does
1. Polls all registered services (HTTP health endpoints)
2. Checks process status (pm2, systemd, launchd)
3. Validates data freshness (REPO DEPOT status.json < 15 min old)
4. Tests OpenClaw gateway connectivity (port 18789)
5. Verifies Memory Doctrine write/read cycle
6. Checks disk space, CPU, memory thresholds
7. On failure: attempts auto-restart → escalate if 3 retries fail
8. Logs all actions to `logs/self_heal_actions.log`

### Health Check Registry
| Service | Endpoint / Check | Restart Method |
|---|---|---|
| OpenClaw Gateway | `localhost:18789/health` | `pm2 restart openclaw` |
| Matrix Monitor | `localhost:8888/api/status` | `pm2 restart matrix` |
| REPO DEPOT Flywheel | Process check + status.json age | `python repo_depot/flywheel.py` |
| Memory Doctrine | SQLite read/write test | `python memory_doctrine_system.py --repair` |
| NCC Engine | `localhost:9000/health` | `pm2 restart ncc` |
| NCL Second Brain | Process check | `pm2 restart ncl` |
| Daily Brief | Last run time < 24h | Trigger manual run |
| Conductor | Process heartbeat | `pm2 restart conductor` |

### Escalation Path
```
Self-Heal Attempt (3 retries, 30s apart)
  ↓ if fails
GASKET Alert (logged + notification)
  ↓ if critical
OPTIMUS Review (automated analysis)
  ↓ if unresolvable
AZ Prime Decision (human-in-loop optional)
  ↓ if emergency
CEO Notification (SMS/push)
```

### Output Format
```
SELF-HEAL REPORT — [timestamp]
Status: ALL GREEN | DEGRADED | CRITICAL

Services: 8/8 healthy
  ✅ OpenClaw Gateway — 200 OK (12ms)
  ✅ Matrix Monitor — 200 OK (45ms)
  ⚠️ REPO DEPOT — status.json 18min old (threshold: 15min)
       Action: Triggered flywheel refresh → now 2min old
  ✅ Memory Doctrine — write/read OK (3ms)
  ...

Actions Taken: 1
Escalations: 0
```

### Dependencies
- self-healing-server skill (clawhub install self-healing-server)
- pm2 or launchd for process management
- Operations Command → System Monitoring Division agents
- GASKET self-heal module (fallback integration)
