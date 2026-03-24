# MATRIX MAXIMIZER — REBUILD PLAN
## From Fake Dashboard to Real Command Center

**Date:** 2026-02-25
**Author:** GitHub Copilot (audit-driven)
**Status:** APPROVED FOR IMPLEMENTATION

---

## EXECUTIVE SUMMARY

The current Matrix Maximizer is **95% fake**. The only real data it shows is CPU/memory/disk/network from `psutil`. Everything else — portfolio values, agent statuses, device metrics, intelligence insights, predictions, alerts, and all intervention buttons — returns hardcoded placeholder values. Meanwhile, the workspace contains **15+ rich, real data sources** that are completely ignored.

The JavaScript frontend has a **critical bug**: the API returns data in a different structure than the JS expects, so after the initial page load, every 5-second refresh overwrites all values with hardcoded fallbacks embedded in `||` operators.

Every "intervention" button (`Optimize`, `Backup`, `Restart`, `Emergency Shutdown`) does nothing — they call `time.sleep()` and return canned success messages.

---

## WHAT THE BEST DASHBOARDS DO (Lessons from Netdata, Grafana, Uptime Kuma)

### Netdata (77.9K stars)
- **Per-second real metrics** — no faking, no averaging
- **Zero-config auto-discovery** — finds what to monitor automatically
- **ML-powered anomaly detection** — trained at the edge per metric
- **Tiered storage** — ~0.5 bytes per sample for long-term retention
- **800+ integrations** — everything from hardware sensors to cloud APIs

### Grafana (72.4K stars)
- **Mixed data sources** in same dashboard — query different backends per panel
- **Dynamic dashboards** with template variables (dropdowns to filter)
- **Ad-hoc exploration** — drill down without predefined views
- **Visual alert rules** — configure thresholds visually, get Slack/Discord/email notifications
- **Time range picker** — look at any historical window

### Uptime Kuma (83.3K stars)
- **WebSocket real-time updates** (not polling)
- **20-second monitoring intervals** with ping charts
- **90+ notification providers** (Telegram, Discord, Slack, email...)
- **Status pages** — public-facing health pages
- **Certificate monitoring** — TLS expiry alerts
- **PWA support** — installable on mobile as native app

### What ALL three share:
1. **Every single number on screen comes from a real source**
2. **Historical data** — not just current snapshot, but trends over time
3. **Alerting that actually works** — thresholds → notifications → escalation
4. **Mobile-first responsive design** with touch targets
5. **WebSocket or SSE** for instant updates (not polling with stale fallbacks)

---

## WHAT'S REAL VS FAKE IN CURRENT MATRIX MAXIMIZER

### REAL (keep and enhance):
| Source | What it provides |
|--------|-----------------|
| `psutil` | CPU%, memory%, disk%, network bytes, boot time, uptime |

### FAKE (must replace with real data):
| Fake Value | Hardcoded As | Real Source Available |
|-----------|-------------|---------------------|
| Portfolio $127,459 | Static number | `REPO_INDEX.json` has real GitHub repo data (stars, forks, size, language) |
| 23 positions | Static | `portfolio.json` has 27 repos with tier/risk |
| Agent health 95-100% | Oscillating fake | `production_state.json` has real agent task lists |
| 47 repos monitored | Static | `portfolio.json` + `repos/` directory = 27-28 real repos |
| 156 changes detected | Static | Real git log available per repo |
| Intelligence insights | 2 canned strings | `NCL/events.ndjson` has real event data |
| Predictions | 2 canned strings | `continuous_orchestration_log_ultra_high.csv` has 482 real cycles |
| Alerts | 2 canned alerts | Can compute from real thresholds on psutil + file ages |
| iPhone battery 87% | Static | Cannot get real iPhone data (acknowledge this honestly) |
| iPad battery 89% | Static | Cannot get real iPad data (acknowledge this honestly) |
| Security threats | Static | `oversight_logs/security.log` has real events |
| QUASMEM 172MB/256MB | Static | `memory_snapshot_20260220.json` + live `psutil.Process` |
| All intervention buttons | `time.sleep()` + fake | Can wire to real subprocess calls |

### BROKEN (must fix):
| Bug | Impact |
|-----|--------|
| JS reads `matrixData.system.health_score` but API returns `system_health` at top level | All metrics revert to fallback values after first refresh |
| JS reads `matrixData.portfolio.total_value` but no `portfolio` key in API response | Portfolio always shows fallback |
| `updateAlerts()` reads `matrixData.alerts` but API response has no `alerts` key | Alerts section always empty |
| Mobile device metrics are hardcoded HTML — no Jinja/JS updates | Never change |

---

## THE PLAN: 3 PHASES

### PHASE 1: MAKE IT REAL (Kill All Fakes)
**Goal:** Every number on the dashboard comes from a real, auditable source. If we can't get real data for something, we show "N/A" or "Unavailable" — never a fake number.

#### 1.1 Backend — Wire Real Data Sources

**New module: `data_collector.py`** — Single source of truth for all metrics

```
data_collector.py
├── SystemCollector       ← psutil (already working)
├── PortfolioCollector    ← portfolio.json + REPO_INDEX.json + git stats
├── AgentCollector        ← production_state.json + GASKET_STATUS.md + agent_mandates.json
├── IntelligenceCollector ← NCL/events.ndjson + inner_council/config/settings.json
├── SecurityCollector     ← oversight_logs/*.log + oversight_logs/*.jsonl
├── HealthCollector       ← reports/health_status_*.json + integration_test_report.json
├── OrchestrationCollector← continuous_orchestration_log_ultra_high.csv
├── BackupCollector       ← backups/ directory age + manifest files
├── GitCollector          ← subprocess git calls per repo
└── DeviceCollector       ← real Mac metrics + honest "unknown" for mobile
```

**Each collector:**
- Reads real files/runs real commands
- Caches results with configurable TTL (e.g., git stats = 60s, psutil = 5s)
- Returns typed dict with `last_updated` timestamp
- Logs errors instead of returning fake fallbacks

#### 1.2 API — Fix Response Structure

**Current broken structure:**
```json
{"matrix": [...], "system_health": 76.5, "total_nodes": 9}
```

**New consistent structure:**
```json
{
  "timestamp": "ISO8601",
  "system": {
    "cpu_percent": 23.6,
    "memory_percent": 82.7,
    "disk_percent": 45.2,
    "uptime_hours": 120.7,
    "health_score": 76.5
  },
  "portfolio": {
    "total_repos": 27,
    "repos": [...],
    "by_tier": {"S": 14, "M": 7, "L": 6},
    "by_risk": {"LOW": 18, "MEDIUM": 7, "HIGH": 2}
  },
  "agents": {
    "optimus": {"status": "...", "tasks_completed": 5, "current_task": "..."},
    "gasket": {"status": "...", "tasks_completed": 3, "current_task": "..."},
    "az": {"last_meeting": 10}
  },
  "devices": {
    "quantum_quasar": {"status": "online", "cpu": 23.6, "memory": 82.7},
    "pocket_pulsar": {"status": "unknown", "note": "No direct connection"},
    "tablet_titan": {"status": "unknown", "note": "No direct connection"}
  },
  "intelligence": {
    "recent_events": [...],
    "council_members_active": 28,
    "channels_monitored": 28
  },
  "alerts": [...],
  "health": {
    "last_backup_age_hours": 12,
    "integration_tests": {"passed": 7, "total": 7},
    "orchestration_cycles": 482,
    "last_cycle_duration": "3.05s"
  }
}
```

#### 1.3 Frontend — Fix JS Data Paths + Remove Fake Fallbacks

- Match JS property paths to actual API response structure
- Remove ALL `|| hardcodedValue` fallbacks — show "—" if data missing
- Add `data-source` attributes to every metric element for auditability
- Show "Last updated: Xs ago" per data section

#### 1.4 Intervention Buttons — Wire to Real Actions

| Button | Current | Wire To |
|--------|---------|---------|
| Optimize System | `time.sleep(2)` | Run `python3 cleanup_codebase.py` or garbage collect caches |
| Create Backup | Fake path | Run `backup_memory_doctrine_logs.sh` and return real path/size |
| Restart Agents | `time.sleep(1)` | Kill + restart specific Python processes by PID |
| Emergency Shutdown | Returns success | Actually `kill` monitored processes + set flag file |
| Run Integration Tests | NEW | Run `python3 integration_test_suite.py` and stream results |
| Deploy Agents | NEW | Run `agent_specialization.py --repo X --agent both` |

#### 1.5 Honest Device Status

For mobile devices where we **cannot** get real metrics:
```
Pocket Pulsar (iPhone 15)
Status: 📡 Reachable via network  /  ❌ Unreachable
Last seen: Check if device responded to last SASP ping
Note: "Connect via http://192.168.100.133:8081 for mobile view"
```

NO fake battery percentages. NO fake temperatures.

---

### PHASE 2: MAKE IT SMART (Historical Data + Alerts + WebSocket)

#### 2.1 Time-Series Storage
- Store metrics snapshots every 30 seconds to `state/matrix_metrics.jsonl`
- Keep 7 days of data (~20K entries at 30s intervals)
- Enable historical charts: CPU over time, commits per day, backup schedule

#### 2.2 Real Alerting
Threshold-based alerts computed from real data:

| Alert | Condition | Action |
|-------|-----------|--------|
| High CPU | psutil.cpu_percent > 85% for 60s | Notification + dashboard alert |
| Low Disk | psutil.disk_usage.percent > 90% | Critical alert |
| Stale Backup | Last backup file > 48 hours old | Warning alert |
| Test Failure | integration_test_report.json has failures | Critical alert |
| Agent Idle | production_state.json unchanged for 24h+ | Warning alert |
| Memory Pressure | psutil.virtual_memory.percent > 90% | Critical alert with process list |

#### 2.3 WebSocket for Live Updates (Replace Polling)
- Use Flask-SocketIO for push-based updates
- Client connects once, receives metric deltas every 5 seconds
- No more stale fallback values from failed fetches
- Connection status indicator on dashboard

#### 2.4 Historical Charts
Using lightweight Chart.js (no Plotly bloat):
- CPU / Memory trend (last 1h, 6h, 24h, 7d)
- Commits per day per repo
- Orchestration cycle duration trend
- Backup schedule timeline

---

### PHASE 3: MAKE IT MOBILE-NATIVE (PWA + Touch + Offline)

#### 3.1 Progressive Web App
- Service Worker for offline access to last-known metrics
- App manifest for "Add to Home Screen" on iPhone/iPad
- Push notifications for critical alerts (via web push API)
- 60fps smooth scrolling and transitions

#### 3.2 Mobile-Optimized Layout
- Bottom navigation bar (thumb-friendly)
- Swipeable cards between sections
- Pull-to-refresh gesture
- Large touch targets (min 44x44px per Apple HIG)
- Dark/light mode following system preference

#### 3.3 iPhone/iPad Specific
- Safe area insets for notch/Dynamic Island
- Haptic feedback on interactions (where supported)
- Compact mode for iPhone SE / older devices
- Landscape mode for iPad split-view

---

## PRIORITY ORDER (What to build first)

| Priority | Task | Impact | Effort |
|----------|------|--------|--------|
| **P0** | Fix JS data path mismatch (Phase 1.3) | Dashboard currently breaks after first refresh | 1 hour |
| **P0** | Remove all `\|\| fallback` values from JS | Exposes what's actually broken vs faking it | 1 hour |
| **P1** | Create `data_collector.py` with real file readers (Phase 1.1) | Every metric becomes real | 4 hours |
| **P1** | Restructure API response (Phase 1.2) | Frontend can consume clean data | 2 hours |
| **P1** | Wire intervention buttons to real actions (Phase 1.4) | Buttons actually do something | 2 hours |
| **P1** | Honest device status (Phase 1.5) | No more fake iPhone battery | 30 min |
| **P2** | Time-series storage (Phase 2.1) | Enable historical views | 2 hours |
| **P2** | Real threshold-based alerts (Phase 2.2) | Proactive monitoring | 3 hours |
| **P2** | WebSocket live updates (Phase 2.3) | Eliminate polling failures | 3 hours |
| **P2** | Historical Chart.js charts (Phase 2.4) | Visual trends | 3 hours |
| **P3** | PWA manifest + service worker (Phase 3.1) | Installable on iPhone/iPad | 2 hours |
| **P3** | Mobile-first layout overhaul (Phase 3.2) | Professional mobile experience | 4 hours |
| **P3** | iPhone/iPad enhancements (Phase 3.3) | Native-feeling experience | 2 hours |

**Total estimated effort:** ~29 hours across 3 phases

---

## FILES TO CREATE / MODIFY

### New Files:
1. `repos/Super-Agency/data_collector.py` — All real data collectors
2. `repos/Super-Agency/static/js/matrix.js` — Clean JS separated from HTML
3. `repos/Super-Agency/static/css/matrix.css` — Clean CSS separated from HTML
4. `repos/Super-Agency/static/manifest.json` — PWA manifest
5. `repos/Super-Agency/static/sw.js` — Service worker for offline

### Modified Files:
1. `repos/Super-Agency/matrix_maximizer.py` — Replace all hardcoded collectors with `data_collector.py` imports
2. `repos/Super-Agency/templates/matrix_maximizer.html` — Complete rewrite with real data binding
3. `matrix_monitor.sh` (~/matrix_monitor.sh) — Already created for 24/7 uptime

### Files to Read (data sources):
1. `portfolio.json` — Repo inventory
2. `production_state.json` — Agent status + real metrics
3. `real_metrics.json` — Productivity time series
4. `REPO_INDEX.json` — Full GitHub repo data (133KB)
5. `agent_mandates.json` — Goals and mandates
6. `agent_protocols.json` — Operational rules
7. `unified_memory_doctrine.json` — Memory config
8. `memory_snapshot_20260220.json` — Memory actuals
9. `continuous_orchestration_log_ultra_high.csv` — 482 orchestration cycles
10. `NCL/events.ndjson` — Event stream
11. `reports/health_status_*.json` — Health snapshots
12. `oversight_logs/*.jsonl` — Decision audit trail
13. `integration_test_report.json` — Test results
14. `backups/` — Backup health
15. `repo_depot/GASKET_STATUS.md` — Agent progress
16. `inner_council/config/settings.json` — Council config

---

## SUCCESS CRITERIA

When Phase 1 is complete:
- [ ] Every number on the dashboard traces to a real file or system call
- [ ] Zero hardcoded metric values in Python or JavaScript
- [ ] Intervention buttons execute real commands and return real results
- [ ] Mobile devices show honest status ("online"/"unreachable"/"unknown")
- [ ] JS data paths match API response structure — no silent fallbacks
- [ ] Dashboard works on iPhone Safari and iPad Safari without layout issues

When Phase 2 is complete:
- [ ] Historical charts show real trends over 7 days
- [ ] Alerts fire based on real thresholds and appear on dashboard
- [ ] WebSocket eliminates polling — metrics update in <1 second
- [ ] Time-series data persists across server restarts

When Phase 3 is complete:
- [ ] "Add to Home Screen" works on iPhone and iPad
- [ ] Offline mode shows last-known metrics
- [ ] Push notifications for critical alerts
- [ ] Touch interactions feel native (large targets, haptic feedback)
- [ ] Works in iPad split-view and iPhone landscape

---

## COMPARISON: Current vs Target

| Metric | Current | After Phase 1 | After Phase 3 |
|--------|---------|---------------|---------------|
| Real data sources used | 1 (psutil) | 16 | 16 |
| Hardcoded values | 50+ | 0 | 0 |
| Working buttons | 0 | 6 | 6 |
| Mobile optimized | Basic CSS | Responsive | PWA native-feel |
| Update method | Broken polling | Fixed polling | WebSocket |
| Historical data | None | 7-day JSONL | 7-day JSONL + charts |
| Alerting | 2 canned strings | Threshold-based | Threshold + push |
| Offline support | None | None | Service worker |
| iPhone installable | No | No | Yes (PWA) |
| Honest about unknowns | No (fakes data) | Yes | Yes |
