# SKILL: ops-dashboard
## Dynamic Operations Dashboard

Real-time dashboard that spawns sub-agents to collect metrics from every
subsystem, then renders a unified view of Super-Agency operational status.

### Triggers
- Cron: Every 10 minutes (auto-refresh)
- Manual: "dashboard", "system status", "show me everything"
- Event: Any service state change

### What It Does
1. Spawns parallel sub-agent sessions (one per subsystem) via OpenClaw
2. Each sub-agent queries its assigned subsystem:
   - REPO DEPOT → repo health, last sync, build status across 27 repos
   - Memory Doctrine → cache hit rate, storage usage, layer health
   - Matrix Monitor → agent performance scores, flywheel metrics
   - NCC → command queue depth, execution success rate
   - NCL → knowledge base size, recent ingestions, search quality
   - QForge → optimization queue, completed builds
   - QUSAR → query performance, cache status
   - Conductor → orchestration state, active workflows
3. Results merged into unified dashboard payload
4. Dashboard rendered as Markdown table or served via HTTP endpoint
5. Anomalies highlighted with color coding

### Sub-Agent Spawning Pattern
```
Dashboard Controller (parent session)
  ├── spawn → REPO DEPOT Collector
  ├── spawn → Memory Collector
  ├── spawn → Matrix Collector
  ├── spawn → NCC Collector
  ├── spawn → NCL Collector
  ├── spawn → QForge Collector
  ├── spawn → QUSAR Collector
  └── spawn → Conductor Collector

All collectors run in parallel → results merged → dashboard rendered
```

### Dashboard Sections
| Section | Metrics | Source |
|---|---|---|
| System Health | CPU, RAM, Disk, Network | OS metrics |
| Agent Status | 47+ Inner Council active/idle | Matrix Monitor |
| Repo Health | 27 repos: last commit, CI status | REPO DEPOT |
| Memory Stats | Ephemeral/Session/Persistent usage | Memory Doctrine |
| Build Pipeline | Queue depth, success rate | QForge |
| Knowledge Base | Docs indexed, recent additions | NCL |
| Department Status | 5 departments operational state | Department configs |
| Active Tasks | Current backlog, priority items | Backlog system |

### Output Format
```
╔══════════════════════════════════════════════════════╗
║            SUPER-AGENCY OPERATIONS DASHBOARD         ║
║                  [timestamp] — Auto-refresh: 10min   ║
╠══════════════════════════════════════════════════════╣

SYSTEM HEALTH          CPU: 34%  RAM: 62%  Disk: 71%
OVERALL STATUS         ███████████░░ 85% OPERATIONAL

DEPARTMENTS
  Executive Council    ██████████████ ACTIVE   — 3 tasks running
  Intelligence Ops     ██████████████ ACTIVE   — digest in progress
  Operations Command   ██████████████ ACTIVE   — monitoring
  Tech Infrastructure  █████████████░ STANDBY  — no builds queued
  Financial Ops        ██████████████ ACTIVE   — market scan running

REPO DEPOT             27/27 repos synced — last: 4min ago
MEMORY DOCTRINE        Ephemeral: 2.1K/4K — Session: 31K/64K
MATRIX MONITOR         47 agents tracked — 44 healthy, 3 idle
NCC                    Queue: 0 — Last command: 2min ago
NCL                    1,247 documents indexed — 12 added today
```

### Dependencies
- dynamic-dashboard skill (clawhub install dynamic-dashboard)
- Matrix Monitor API
- REPO DEPOT status.json
- Memory Doctrine health endpoint
- OpenClaw session spawning (for parallel sub-agents)
