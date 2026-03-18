# BIT RAGE LABOUR

Bit Rage Labour autonomous multi-agent operations platform. Departmental matrix
structure with three web servers, an 8-stage orchestrator, Inner Council
decision-making, 3-layer SQLite memory, continuous backup, auto-restart
watchdog, and four management-tier agents (Context, QA, Production, Automation).

**Status:** Fully operational — DL v2.0.0 — Bit Rage Labour integration complete.

---

## Quick Start

```bash
# 1. Clone & enter
git clone https://github.com/ResonanceEnergy/Digital-Labour.git
cd Digital-Labour

# 2. Create virtual environment
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY and GITHUB_TOKEN

# 5. Launch
python start.py
```

`start.py` runs pre-flight checks (Python >= 3.10, required keys, dependencies)
then calls `run_bit_rage_labour.main()` which boots all servers and daemons.

### Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Yes | LLM API access |
| `GITHUB_TOKEN` | Yes | GitHub API / portfolio ops |
| `ANTHROPIC_API_KEY` | No | Anthropic models |
| `YOUTUBE_API_KEY` | No | YouTube Intelligence division |
| `AZURE_OPENAI_ENDPOINT` | No | Azure OpenAI |
| `AZURE_OPENAI_KEY` | No | Azure OpenAI |

See `.env.example` for the full list.

---

## Architecture

### Servers (boot automatically via `run_bit_rage_labour.py`)

| Service | Port | Framework | Purpose |
|---|---|---|---|
| Matrix Maximizer | 8080 | Flask | Main dashboard & agent coordination |
| Mobile Command Center | 8081 | Flask | Lightweight mobile-friendly interface |
| Operations API | 5001 | Quart/Hypercorn | Async REST API for status, health, metrics |

### Core Systems

- **8-Stage Orchestrator** (`agents/orchestrator.py`) — runs portfolio scan,
  daily brief, council meeting, memory consolidation, self-heal, intelligence
  scheduling, research management, and audit in sequence.
- **Inner Council** (`agent_council_meeting.py`) — multi-agent decision-making
  with voting, escalation, and mandate tracking.
- **3-Layer Memory** (`memory_doctrine_system.py`) — ephemeral / session /
  persistent SQLite layers with blank prevention.
- **Continuous Backup** (`continuous_memory_backup.py`) — daemon thread backs
  up memory every 10 minutes, keeps last 10 snapshots.
- **Auto-Restart Watchdog** — monitors all daemon threads, restarts crashed
  services up to 5 times, checks port liveness every 5 minutes.
- **Message Bus** (`agents/message_bus.py`) — publish/subscribe event bus for
  inter-agent communication.
- **Autonomy Mode** (`autonomy_mode.py`) — graduated autonomy levels
  (observer → supervised → autonomous → full) with action allowlists.

### Departments

```
departments/
├── executive_council/           # AZ_FINAL authority, doctrine enforcement
├── intelligence_operations/     # YouTube, research, strategic intel
├── operations_command/          # Monitoring, daily brief, orchestration
├── financial_operations/        # AAC, compliance, forecasting
└── technology_infrastructure/   # DevOps, NCL integration, scaling
```

---

## Docker

```bash
# Build and run
docker compose up --build -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

The `Dockerfile` uses a multi-stage build with a non-root user. The
`docker-compose.yml` mounts `./memory` for persistent data and sets resource
limits.

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v --tb=short

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

111 tests passing, 1 xfailed, 0 failures.

---

## Key Files

| File | Purpose |
|---|---|
| `start.py` | Entry point — env loading, pre-flight checks |
| `run_bit_rage_labour.py` | Runtime — boots servers, orchestrator, watchdog |
| `departmental_agent_manager.py` | Manages agent lifecycle across departments |
| `matrix_maximizer.py` | Flask dashboard server (:8080) |
| `mobile_command_center_simple.py` | Flask mobile server (:8081) |
| `operations_api.py` | Quart async API (:5001) |
| `agents/orchestrator.py` | 8-stage pipeline scheduler |
| `agent_council_meeting.py` | Inner Council voting & decisions |
| `memory_doctrine_system.py` | 3-layer SQLite memory |
| `memory_integration_hub.py` | Cross-system memory sync |
| `continuous_memory_backup.py` | Backup daemon |
| `autonomy_mode.py` | Graduated autonomy control |
| `emergency_stop_cli.py` | Emergency shutdown CLI |
| `intelligence_scheduler.py` | Scheduled intel gathering |
| `tools/api_cost_tracker.py` | Per-agent LLM cost tracking |

---

## Operations

```bash
# Emergency stop
python emergency_stop_cli.py

# Check portfolio status
python departments/operations_command/system_monitoring/portfolio_autotier.py

# Generate daily brief manually
python departments/operations_command/system_monitoring/daily_brief.py

# Run council meeting
python agent_council_meeting.py

# Second Brain ingestion (VS Code task or manual)
make -C tools all URL=https://youtube.com/watch?v=...
```

---

## Documentation

- [ROADMAP.md](ROADMAP.md) — Phase progress and feature checklist
- [CHANGELOG.md](CHANGELOG.md) — Release history
- [NORTH_STAR.md](NORTH_STAR.md) — Strategic vision
- `.env.example` — Environment variable reference
- `LEGACY.md` — Legacy/deprecated component reference

---

## ⚖️ LEGAL & COMPLIANCE

- **Financial Compliance**: AAC system maintains full regulatory compliance
- **Data Privacy**: All operations follow privacy protection protocols
- **Security**: Multi-layer security with continuous monitoring
- **Audit Trail**: Complete transaction and decision logging

---

**BIT RAGE LABOUR is fully operational and ready for maximum computational output.**

*See [DL_DOCTRINE_MEMORY.md](DL_DOCTRINE_MEMORY.md) for complete operational doctrine and procedures.*

---
*Generated by BIT RAGE LABOUR — Bit Rage Labour Platform v2.0*

Generated: 2026-02-27T22:36:38.632085
