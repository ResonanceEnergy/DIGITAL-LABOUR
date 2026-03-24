# DIGITAL LABOUR MATRIX MONITOR — Audit, Roadmap & Task List

> Generated 2026-03-16 | Commit baseline: `f687d92` (watchdog + startup)

---

## 1. SYSTEM AUDIT

### 1.1 Architecture Overview

```
                    ┌───────────────────────────┐
                    │     MATRIX DASHBOARD       │
                    │  (PWA — mobile C2 panel)   │
                    │   api/matrix_dashboard.html│
                    └────────────┬──────────────┘
                                 │ fetch /matrix/sitrep
                                 │ POST  /matrix/command
                    ┌────────────▼──────────────┐
                    │    MATRIX MONITOR API      │
                    │   api/matrix_monitor.py    │
                    │   24 C2 commands (v2)      │
                    │   /matrix/sitrep + /command│
                    └────────────┬──────────────┘
          ┌──────────┬───────────┼───────────┬──────────┐
          │          │           │           │          │
    ┌─────▼────┐ ┌───▼───┐ ┌────▼────┐ ┌────▼───┐ ┌───▼────┐
    │ WATCHDOG │ │ NERVE │ │OPENCLAW │ │C-SUITE │ │ AGENTS │
    │ 24/7     │ │14-phase│ │freelance│ │AXIOM   │ │ 24x    │
    │ guardian │ │daemon  │ │engine   │ │VECTIS  │ │runners │
    │          │ │        │ │         │ │LEDGR   │ │        │
    └──────────┘ └───────┘ └─────────┘ └────────┘ └────────┘
```

### 1.2 Command Inventory (All CLI + API)

| # | Command | Module | Matrix C2? | Status |
|---|---------|--------|------------|--------|
| 1 | `python launch.py` | launch.py | `restart_daemons` | ✅ |
| 2 | `python launch.py --status` | launch.py | `full_status` | ✅ NEW |
| 3 | `python launch.py --kill` | launch.py | `kill_daemons` | ✅ |
| 4 | `python launch.py --checks` | launch.py | `system_check` | ✅ |
| 5 | `python -m automation.nerve --daemon` | nerve.py | via watchdog | ✅ |
| 6 | `python -m automation.nerve --status` | nerve.py | `nerve_status` | ✅ NEW |
| 7 | `python -m automation.nerve --decisions` | nerve.py | in sitrep | ✅ |
| 8 | `python -m automation.watchdog` | watchdog.py | `watchdog_start` | ✅ NEW |
| 9 | `python -m automation.watchdog --status` | watchdog.py | `watchdog_status` | ✅ NEW |
| 10 | `python -m automation.watchdog --stop` | watchdog.py | `watchdog_stop` | ✅ NEW |
| 11 | `python -m automation.orchestrator --daily` | orchestrator.py | `daily_cycle` | ✅ NEW |
| 12 | `python -m automation.orchestrator --status` | orchestrator.py | `full_status` | ✅ |
| 13 | `python -m automation.revenue_daemon --summary` | revenue_daemon.py | `revenue_summary` | ✅ NEW |
| 14 | `python -m automation.outreach --followups` | outreach.py | `send_followups` | ✅ |
| 15 | `python -m automation.outreach_push` | outreach_push.py | `outreach_push` | ✅ NEW |
| 16 | `python -m automation.inbox_reader --process` | inbox_reader.py | `check_inbox` | ✅ |
| 17 | `python -m automation.upwork_jobhunt --search` | upwork_jobhunt.py | `upwork_hunt` | ✅ NEW |
| 18 | `python -m openclaw.engine` | engine.py | `openclaw_cycle` | ✅ NEW |
| 19 | `python -m openclaw.engine --scan-only` | engine.py | `openclaw_scan` | ✅ NEW |
| 20 | `python -m openclaw.inbox_agent --check` | inbox_agent.py | `openclaw_inbox` | ✅ NEW |
| 21 | `python c_suite/boardroom.py --quick` | boardroom.py | `boardroom_quick` | ✅ NEW |
| 22 | `python -m kpi.unit_economics` | unit_economics.py | `unit_economics` | ✅ NEW |
| 23 | `python -m automation.gen_proposals` | gen_proposals.py | `run_proposals` | ✅ |
| 24 | `python dashboard/health.py` | health.py | in sitrep | ✅ |

**Pre-integration: 10 C2 commands, 4 dashboard buttons**
**Post-integration: 24 C2 commands, 16 dashboard buttons**

### 1.3 Sitrep Payload (v2)

```json
{
  "status": "GREEN|AMBER|RED",
  "daemons": [...],
  "health": {...},
  "queue": {...},
  "kpi_7d": {...},
  "revenue": {...},
  "outreach": {...},
  "inbox": {...},
  "fleet": [...],
  "watchdog": {                    // ← NEW
    "running": true,
    "nerve_alive": true,
    "nerve_cycles": 42,
    "nerve_last_cycle_min": 12.5,
    "restarts_last_hour": 0,
    "uptime_hours": 48.2
  },
  "openclaw": {                    // ← NEW
    "active": true,
    "cycles": 8,
    "upwork_jobs": 3,
    "fiverr_orders": 1
  },
  "csuite": {                      // ← NEW
    "last_meeting": "...",
    "executives": [
      {"name": "AXIOM", "verdict": "...", "last_run": "..."},
      {"name": "VECTIS", ...},
      {"name": "LEDGR", ...}
    ]
  },
  "recent_decisions": [...],
  "nerve_decisions": [...],
  "alerts_pending": [...]
}
```

### 1.4 Dashboard Sections (v2)

| Section | Status | Data Source |
|---------|--------|-------------|
| Quick Metrics (Revenue, Tasks, Pass%, Emails, Inbox, Agents) | ✅ Live | sitrep |
| Daemons (alive/dead indicators) | ✅ Live | daemon_pids.json |
| Outreach (sent, F/U due, scheduled, prospects) | ✅ Live | sent_log + followups + prospects.csv |
| **Watchdog & NERVE** (status, cycles, staleness, restarts) | ✅ **NEW** | watchdog_status.json + nerve_state.json |
| **OpenClaw** (cycles, upwork/fiverr/freelancer counts) | ✅ **NEW** | openclaws_state.json |
| **C-Suite** (AXIOM/VECTIS/LEDGR verdicts + last run) | ✅ **NEW** | csuite_schedule.json |
| Agent Fleet (24 agents ready/offline) | ✅ Live | agents/ directory |
| Queue (queued, running, done, failed) | ✅ Live | task_queue.db |
| Decision Log (C2 audit trail) | ✅ Live | matrix_decisions.json |
| System Health (env, LLMs, DBs, dirs) | ✅ Live | health.py |

---

## 2. ROADMAP

### Phase 1: FOUNDATION (Done)
- [x] 14-phase NERVE daemon with autonomous decision loop
- [x] 24 billing-tier agents with QA gates
- [x] FastAPI intake + monitoring endpoints
- [x] Stripe billing integration
- [x] Matrix Monitor v1 (10 C2 commands, 4 buttons)
- [x] OpenClaw unified freelance engine
- [x] C-Suite executives (AXIOM, VECTIS, LEDGR)
- [x] Watchdog + Windows Task Scheduler startup

### Phase 2: MATRIX INTEGRATION (Current — March 2026)
- [x] Integrate all 24 commands into Matrix C2
- [x] Add Watchdog/NERVE status to sitrep
- [x] Add OpenClaw status to sitrep
- [x] Add C-Suite status to sitrep
- [x] Expand dashboard to 16-button command grid
- [x] Add Watchdog, OpenClaw, C-Suite sections to dashboard
- [ ] Add command output modal (show full text results in popup)
- [ ] Add Telegram alert integration for watchdog restarts
- [ ] Add confirmation dialog for destructive commands (kill, outreach_push)

### Phase 3: REVENUE ENGINE (April 2026)
- [ ] Stripe webhook → auto-provision client in scheduler
- [ ] Client portal (login, view deliverables, request support)
- [ ] Automated invoice generation with PDF export
- [ ] Revenue goal tracker on dashboard (target vs actual)
- [ ] Per-client margin tracking in unit economics
- [ ] Auto-scale: add agents for high-demand service types

### Phase 4: PLATFORM DOMINANCE (April–May 2026)
- [ ] Upwork Connect management (budget auto-allocation)
- [ ] Fiverr gig optimization (title/description A/B testing)
- [ ] Freelancer.com bid automation (ranked by win probability)
- [ ] PeoplePerHour + Guru cross-listing
- [ ] Client review/rating request automation
- [ ] Portfolio showcase generator (from delivery history)

### Phase 5: INTELLIGENCE LAYER (May–June 2026)
- [ ] LLM cost optimizer (auto-route to cheapest capable provider)
- [ ] A/B testing for outreach templates (metrics → auto-select winner)
- [ ] Lead scoring model (train on conversion history)
- [ ] Competitor analysis agent (monitor marketplace competitors)
- [ ] Sentiment tracker on client communications
- [ ] Predictive revenue forecasting (project next 30/60/90 days)

### Phase 6: SCALE & RESILIENCE (June–July 2026)
- [ ] Multi-machine deployment (Railway + local watchdog)
- [ ] Database migration: SQLite → PostgreSQL for concurrent access
- [ ] Redis queue for task distribution
- [ ] Horizontal agent scaling (multiple instances per agent type)
- [ ] Playwright browser pool (shared headless instances)
- [ ] Automated backup: state files → encrypted S3/B2

### Phase 7: RESONANCE CONVERGENCE (Q3 2026)
- [ ] NCC integration: receive directives from Natrix Command
- [ ] NCL brain sync: share learnings across the quad
- [ ] AAC bank sync: crypto earnings → unified P&L
- [ ] Unified KPI dashboard across all pillars
- [ ] Cross-pillar resource allocation (VECTIS orchestrates)
- [ ] Full autonomy: 0 human touches for standard task delivery

---

## 3. TASK LIST — Immediate Priorities

### Critical (This Week)

| # | Task | Owner | Status | ETA |
|---|------|-------|--------|-----|
| 1 | Run `startup_install.ps1` as Admin — register watchdog in Task Scheduler | Operator | TODO | 10 min |
| 2 | Set `MATRIX_AUTH_TOKEN` in .env for production security | Operator | TODO | 5 min |
| 3 | Configure Telegram alerts (Bot token + chat ID via /matrix/alerts/config) | Operator | TODO | 15 min |
| 4 | Verify all 16 C2 buttons work from mobile dashboard | Operator | TODO | 30 min |
| 5 | Load first real client into `clients/` directory | Operator | TODO | 1 hr |
| 6 | Load real prospects into `automation/prospects.csv` (50+ targets) | Operator | TODO | 1 hr |

### High (Next 2 Weeks)

| # | Task | Status |
|---|------|--------|
| 7 | Add command output modal to dashboard (full-text results) | TODO |
| 8 | Add confirmation dialogs for destructive C2 commands | TODO |
| 9 | Wire Stripe webhook → auto-provision client pipeline | TODO |
| 10 | Set up Upwork API credentials + test autobidder | TODO |
| 11 | Set up Fiverr account + deploy first 3 gigs | TODO |
| 12 | Run first outreach push (50 targets) and measure open rate | TODO |
| 13 | Run first C-Suite board meeting and review directives | TODO |

### Medium (Month 2)

| # | Task | Status |
|---|------|--------|
| 14 | Build client portal (login + deliverable viewer) | TODO |
| 15 | Implement LLM cost optimizer (route by cheapest capable) | TODO |
| 16 | Add A/B testing for outreach subject lines | TODO |
| 17 | Set up automated daily backup schedule | TODO |
| 18 | Create custom Telegram bot with inline keyboards for C2 | TODO |
| 19 | Add WebSocket live-update to dashboard (replace polling) | TODO |
| 20 | Revenue forecasting model (train on 30 days of data) | TODO |

---

## 4. FILE MANIFEST

### Files Modified (This Commit)

| File | Changes |
|------|---------|
| [api/matrix_monitor.py](../api/matrix_monitor.py) | +14 C2 command handlers, +3 sitrep sections (watchdog, openclaw, csuite), expanded actions dict |
| [api/matrix_dashboard.html](../api/matrix_dashboard.html) | +12 C2 buttons (16 total), +3 dashboard sections (Watchdog, OpenClaw, C-Suite), output in toasts |

### Files Created (Previous Commit)

| File | Purpose |
|------|---------|
| [automation/watchdog.py](../automation/watchdog.py) | NERVE process guardian — spawns, monitors, restarts |
| [scripts/health_check.ps1](../scripts/health_check.ps1) | 5-min Task Scheduler job — ensures watchdog itself is alive |
| [scripts/startup_install.ps1](../scripts/startup_install.ps1) | Registers both tasks in Windows Task Scheduler |

### Key State Files

| File | Used By | Purpose |
|------|---------|---------|
| data/nerve_state.json | NERVE, Watchdog, Matrix | Cycle count + last_cycle timestamp |
| data/watchdog_status.json | Watchdog, Matrix | PID + alive + restarts + uptime |
| data/daemon_pids.json | launch.py, Matrix | All daemon PIDs |
| data/matrix_decisions.json | Matrix | C2 audit trail (last 500) |
| data/matrix_alerts.json | Matrix | Telegram bot config |
| data/openclaws_state.json | OpenClaw, Matrix | Engine cycle state |
| data/csuite_schedule.json | C-Suite, Matrix | Meeting schedule + verdicts |

---

## 5. QUICK REFERENCE

### Start Everything
```bash
python launch.py                          # All daemons + checks
# OR via watchdog (recommended):
python -m automation.watchdog             # Watchdog → NERVE → auto-restart
```

### Access Dashboards
```
http://localhost:8000/matrix              # Mobile C2 (PWA)
http://localhost:8000/ops                 # Ops dashboard
http://localhost:8000/monitor/overview    # Full API overview
```

### C2 from CLI
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/matrix/sitrep
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"nerve_status"}' http://localhost:8000/matrix/command
```

### 24 Available C2 Commands
```
restart_daemons    kill_daemons       pause_agent        resume_agent
approve_task       reject_task        send_followups     check_inbox
run_proposals      system_check       watchdog_status    watchdog_stop
watchdog_start     nerve_status       revenue_summary    daily_cycle
openclaw_cycle     openclaw_scan      openclaw_inbox     boardroom_quick
outreach_push      upwork_hunt        unit_economics     full_status
```
