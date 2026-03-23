# OPTIMUS OPENCLAW DEPOT ENGINE - Architecture & Integration Guide

## Overview

The **OPTIMUS OPENCLAW DEPOT ENGINE** is the unified orchestration engine for the DIGITAL LABOUR platform. It consolidates 9 internal subsystems into a single process with cross-platform communication (macOS QUSAR ↔ Windows x64 QFORGE).

## Architecture

```
╔══════════════════════════════════════════════════════════════════════════╗
║  OPTIMUS OPENCLAW DEPOT ENGINE v1.0                                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         ║
║  │ 1. PingChat      │  │ 2. SharedFile    │  │ 3. TaskExecutor │         ║
║  │    Protocol      │──│    Manager       │  │  (QFORGE-style) │         ║
║  │  :8890/:8891     │  │  git sync       │  │  async queue    │         ║
║  └────────┬─────────┘  └─────────────────┘  └────────┬────────┘         ║
║           │                                           │                  ║
║  ┌────────┴─────────┐  ┌─────────────────┐  ┌────────┴────────┐         ║
║  │ 4. GASKET Agent  │  │ 5. OpenClaw     │  │ 6. RepoDepot   │         ║
║  │  implementation  │──│    Bridge       │  │    Flywheel    │         ║
║  │  testing, deploy │  │  :18789 gateway │  │  27 repos      │         ║
║  └──────────────────┘  └─────────────────┘  └────────────────┘         ║
║                                                                          ║
║  ┌─────────────────┐                                                     ║
║  │ 7. SyncEngine   │    ┌─────────────────────────────────────┐         ║
║  │  60s intervals   │    │ 8. MATRIX MONITOR (Internal)        │         ║
║  │  QUSAR↔QFORGE    │    │    CPU/RAM telemetry (5s)           │         ║
║  └──────────────────┘    │    Process detection (10s)          │         ║
║                          │    Device sync Pulsar/Titan (30s)   │         ║
║                          │    → feeds :8501 dashboard          │         ║
║                          └─────────────────────────────────────┘         ║
║                          ┌─────────────────────────────────────┐         ║
║                          │ 9. MATRIX MAXIMIZER (Internal)      │         ║
║                          │    Zero-Data-Loss persistence       │         ║
║                          │    Comprehensive agent metrics      │         ║
║                          │    Matrix visualization (11 nodes)  │         ║
║                          │    Intervention system              │         ║
║                          │    Alerts & predictions             │         ║
║                          │    Inner Council (20 agents)        │         ║
║                          │    → feeds :8080 dashboard          │         ║
║                          └─────────────────────────────────────┘         ║
║                                                                          ║
║  ╔═══════════════════════════════════════════════════════════════╗       ║
║  ║ 10. ORCHESTRATOR - Main Loop (2s cycle)                       ║       ║
║  ║     Ping peer → Process tasks → Sync → Scaffold → Write state║       ║
║  ╚═══════════════════════════════════════════════════════════════╝       ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## Subsystems Detail

### 1. PingChatProtocol (`:8890` ping, `:8891` chat)
- **Ping**: TCP heartbeat with HMAC-SHA256 signed messages
- **Chat**: Structured message exchange (chat, file sync, insights, task dispatch, status)
- **Stats**: Tracks pings/pongs/chats/syncs/latency

### 2. SharedFileManager
- Uses git as transport layer, protocol messages as signal layer
- Cross-platform file sharing (macOS ↔ Windows)
- Insight storage and retrieval
- File change detection via SHA-256 hashing

### 3. InternalTaskExecutor
- QFORGE-style async task queue
- Handles: architecture review, planning, implementation, testing, scaffolding
- Per-task metrics and completion tracking

### 4. GASKET Agent
- Implementation, testing, integration, deployment
- Communicates through OpenClaw gateway
- Accepts tasks from the executor pipeline

### 5. OpenClaw Bridge
- Multi-channel AI gateway (Telegram, Discord, WhatsApp, etc.)
- Gateway at `http://127.0.0.1:18789`
- Registers OPTIMUS DEPOT as an OpenClaw skill
- Auto-discovers OpenClaw binary

### 6. RepoDepot Flywheel
- Scaffolds all 27 repos from `portfolio.json`
- Creates: README.md, src/__init__.py, src/main.py, tests/, docs/, config/
- Auto-detects new repos and scaffolds them

### 7. SyncEngine
- Regular 60-second sync cycles between QUSAR and QFORGE
- Ping → Scan changes → Share files → Get peer insights → Request status
- State persistence to `optimus_state/sync_state.json`

### 8. InternalMatrixMonitor (internal, feeds `:8501`)
- **CPU/RAM telemetry**: 5-second intervals, 60-point history (5 min window)
- **Process detection**: Every 10s, scans for qforge, qusar, watchdog, openclaw, gasket, repo_depot, matrix_maximizer, optimus_depot
- **Device sync**: Every 30s, checks Pulsar (iPhone 192.168.1.101) and Titan (iPad 192.168.1.102)
- **Activity log**: 200-entry rolling buffer
- **State output**: `optimus_state/matrix_monitor_state.json`

### 9. InternalMatrixMaximizer (internal, feeds `:8080`)
- **Zero-Data-Loss**: Auto-save every 60s, checkpoint system (keeps 10), restore on startup
- **Agent metrics**: 9 core agents + 20 Inner Council members
- **Matrix visualization**: 11 nodes (Quantum Quasar, Pocket Pulsar, Tablet Titan, OPTIMUS DEPOT, SASP, REPODEPOT, OpenClaw, Council, QUASMEM, Finance, + dynamic)
- **Intervention**: restart_agent, optimize_system, update_configuration
- **Alerts**: Dynamic based on CPU/RAM thresholds and agent status
- **Predictions**: System load, portfolio growth, repo completion
- **State output**: `optimus_state/matrix_maximizer_state.json`

## State Files

All state is written to `optimus_state/` directory:

| File | Writer | Consumers |
|------|--------|-----------|
| `optimus_depot_state.json` | Orchestrator | Matrix Monitor v4, Matrix Maximizer |
| `production_state.json` | Orchestrator | Legacy systems |
| `matrix_monitor_state.json` | Internal Monitor | Matrix Monitor v4 dashboard |
| `matrix_maximizer_state.json` | Internal Maximizer | Matrix Maximizer dashboard |
| `sync_state.json` | SyncEngine | Status queries |
| `zdl/maximizer_state.json` | ZDL persistence | Internal Maximizer (restore) |
| `zdl/checkpoints/` | ZDL persistence | Backup/recovery |

## API Endpoints

### Matrix Monitor v4 (`:8501`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v4/status` | GET | Full system status (all agents, repos, devices) |
| `/api/v4/optimus-depot` | GET | **NEW** - OPTIMUS DEPOT unified state |
| `/api/v4/matrix-nodes` | GET | **NEW** - Matrix visualization nodes |
| `/api/v4/alerts` | GET | **NEW** - Alerts & predictions from Maximizer |
| `/api/v4/devices` | GET | Pulsar/Titan device sync status |
| `/api/v4/devices/sync` | POST | Record device sync event |
| `/api/v4/control/start-depot` | POST | Start Repo Depot launcher |
| `/api/v4/control/stop-depot` | POST | Stop Repo Depot launcher |
| `/api/health` | GET | Health check |
| `/docs` | GET | API documentation |

### Matrix Maximizer (`:8080`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/matrix` | GET | Matrix visualization (11 nodes + OPTIMUS DEPOT) |
| `/api/agents` | GET | All agent metrics (enriched with depot data) |
| `/api/system` | GET | System health and performance |
| `/api/portfolio` | GET | Portfolio performance data |
| `/api/intelligence` | GET | Intelligence and prediction data |
| `/api/security` | GET | Security status and threat data |
| `/api/intervene` | POST | Execute intervention commands |
| `/api/alerts` | GET | Active alerts |
| `/api/predictions` | GET | System predictions |
| `/api/optimize` | POST | Trigger system-wide optimization |
| `/api/backup` | POST | Create ZDL checkpoint backup |
| `/api/restart/<component>` | POST | Restart specific component |
| `/api/repodepot/*` | GET | REPODEPOT specific routes |

## Running

### Full Engine Mode
```bash
python optimus_openclaw_depot.py --peer 192.168.1.100
```

### One-Shot Commands
```bash
# Ping peer
python optimus_openclaw_depot.py --ping 192.168.1.100

# Send chat
python optimus_openclaw_depot.py --chat 192.168.1.100 "Hello from QFORGE"

# Request status
python optimus_openclaw_depot.py --status 192.168.1.100

# Single sync cycle
python optimus_openclaw_depot.py --sync 192.168.1.100
```

### Dashboards
```bash
# Matrix Monitor v4 (port 8501)
python matrix_monitor_v4.py

# Matrix Maximizer (port 8080)
python matrix_maximizer.py
```

## Data Flow

```
OPTIMUS DEPOT ENGINE (optimus_openclaw_depot.py)
    │
    ├── InternalMatrixMonitor (5s collection)
    │   └── writes → optimus_state/matrix_monitor_state.json
    │           │
    │           └── read by → matrix_monitor_v4.py (:8501)
    │                          └── /api/v4/optimus-depot
    │                          └── /api/v4/matrix-nodes
    │                          └── /api/v4/alerts
    │
    ├── InternalMatrixMaximizer (30s collection)
    │   └── writes → optimus_state/matrix_maximizer_state.json
    │           │
    │           └── read by → matrix_maximizer.py (:8080)
    │                          └── /api/matrix (OPTIMUS DEPOT node)
    │                          └── /api/agents (enriched with depot data)
    │
    └── Orchestrator (10-cycle state writes)
        └── writes → optimus_state/optimus_depot_state.json
                │
                └── read by → both dashboards
```

## Network Configuration

| System | Host | Ports | Platform |
|--------|------|-------|----------|
| QFORGE | 192.168.1.200 | 8888, 8890, 8891 | Windows x64 |
| QUSAR | 192.168.1.100 | 8888, 8890, 8891 | macOS arm64 |
| Pulsar | 192.168.1.101 | 8080 | iPhone 15 |
| Titan | 192.168.1.102 | 8080 | iPad Pro |
| Matrix Monitor | localhost | 8501 | Any |
| Matrix Maximizer | localhost | 8080 | Any |
| OpenClaw | localhost | 18789 | Any |

## Inner Council Agents (20)

Andrew Huberman, Balaji Srinivasan, Chamath Palihapitiya, David Goggins, Elon Musk, Gary Vaynerchuk, Lex Fridman, Marc Andreessen, Naval Ravikant, Paul Graham, Peter Thiel, Ray Dalio, Reid Hoffman, Sam Altman, Satya Nadella, Steve Jobs, Sundar Pichai, Tim Ferriss, Vitalik Buterin, Warren Buffett

## Matrix Visualization Nodes (11)

1. **Quantum Quasar** - Mac Workstation (CPU/MEM metrics)
2. **Pocket Pulsar** - iPhone 15 (battery/network)
3. **Tablet Titan** - iPad Pro (battery)
4. **OPTIMUS DEPOT** - Unified Engine (subsystems/repos/tasks)
5. **SASP Protocol** - Network Protocol (connections/latency)
6. **REPODEPOT** - Portfolio Engine (repos/files)
7. **OpenClaw** - AI Gateway (channels/gateway port)
8. **Inner Council** - Agent Collective (members/decisions/autonomy)
9. **QUASMEM** - Memory Pool (pool/used/efficiency)
10. **Finance** - Financial System (value/score/positions)
11. **Dynamic** - REPODEPOT integration node (from repo_depot module)

---
*Generated by OPTIMUS OPENCLAW DEPOT ENGINE*
*Last updated: 2026*
