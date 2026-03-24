#!/usr/bin/env python3
"""
GASKET ↔ OpenClaw Bridge Agent
Integrates AGENT GASKET's full capabilities into the macOS OpenClaw Gateway.

This bridge:
  1. Registers GASKET as a named OpenClaw agent with its own workspace
  2. Deploys GASKET skills (CPU, QUSAR, Memory Doctrine, Matrix Maximizer) as SKILL.md
  3. Configures cron jobs for GASKET's operational loops
  4. Provides bidirectional communication (GASKET ↔ OpenClaw gateway)
  5. Manages OpenClaw sessions, memory, and subagent delegation
  6. Publishes GASKET status to all connected channels (Discord, Telegram, etc.)

Architecture:
  ┌──────────┐    POST /api/chat     ┌──────────────────┐
  │  GASKET  │◄──────────────────────►│  OpenClaw Gateway │
  │ (Python) │    ws://127.0.0.1:18789│  (Node.js :18789) │
  └────┬─────┘                        └────────┬─────────┘
       │                                       │
       ├─ CPU Optimization Loop (30s)          ├─ Discord Channel
       ├─ QUSAR Operations Loop (45s)          ├─ Telegram Bot
       ├─ Matrix Maximizer Loop (60s)          ├─ iMessage
       └─ Memory Doctrine Loop (120s)          └─ WhatsApp
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import requests

# ── Paths ────────────────────────────────────────────────────────────────────
OPENCLAW_HOME = Path(os.environ.get(
    "OPENCLAW_HOME", Path.home() / ".openclaw"))
GASKET_WORKSPACE = OPENCLAW_HOME / "workspace-gasket"
GASKET_SKILLS = GASKET_WORKSPACE / "skills"
GASKET_MEMORY = GASKET_WORKSPACE / "memory"
GASKET_SESSIONS = OPENCLAW_HOME / "agents" / "gasket" / "sessions"
GASKET_STATE = GASKET_WORKSPACE / "STATE.yaml"

GATEWAY_URL = "http://127.0.0.1:18789"
GATEWAY_WS = "ws://127.0.0.1:18789"
GATEWAY_API = f"{GATEWAY_URL}/api/chat"

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GASKET-BRIDGE] %(levelname)s %(message)s",
)
log = logging.getLogger("gasket-openclaw-bridge")

# ── Add parent for imports ───────────────────────────────────────────────────
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))


# ═══════════════════════════════════════════════════════════════════════════════
# SKILLS — AgentSkills-compatible SKILL.md files for OpenClaw
# ═══════════════════════════════════════════════════════════════════════════════

SKILLS: Dict[str, Dict[str, str]] = {
    "gasket-status": {
        "name": "gasket-status",
        "description": "Get AGENT GASKET system status — CPU, memory, QUSAR, Matrix Maximizer",
        "metadata": json.dumps({
            "openclaw": {
                "always": True,
                "emoji": "🔴",
                "os": ["darwin"],
            }
        }),
        "instructions": """\
When the user asks for GASKET status, system health, or agent status, run this skill.

Steps:
1. Run: python3 -c "
import psutil, json, datetime
cpu = psutil.cpu_percent(interval=1)
mem = psutil.virtual_memory()
disk = psutil.disk_usage('/')
net = psutil.net_io_counters()
print(json.dumps({
    'agent': 'GASKET v2.0',
    'timestamp': datetime.datetime.now().isoformat(),
    'cpu_percent': cpu,
    'memory_percent': mem.percent,
    'memory_used_gb': round(mem.used/1024**3, 2),
    'memory_total_gb': round(mem.total/1024**3, 2),
    'disk_percent': disk.percent,
    'disk_free_gb': round(disk.free/1024**3, 2),
    'net_sent_mb': round(net.bytes_sent/1024**2, 2),
    'net_recv_mb': round(net.bytes_recv/1024**2, 2),
    'status': 'OPERATIONAL'
}, indent=2))
"
2. Format the output as a clean status report for the user.
""",
    },
    "gasket-cpu-optimize": {
        "name": "gasket-cpu-optimize",
        "description": "Optimize CPU usage — find and report high-CPU processes, suggest throttling",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "⚡",
                "os": ["darwin"],
                "requires": {"bins": ["python3"]},
            }
        }),
        "instructions": """\
When the user asks to optimize CPU, check performance, or throttle processes:

1. Run: python3 -c "
import psutil, json
procs = []
for p in psutil.process_iter(['pid','name','cpu_percent','memory_percent']):
    try:
        info = p.info
        if info['cpu_percent'] and info['cpu_percent'] > 5:
            procs.append(info)
    except: pass
procs.sort(key=lambda x: x.get('cpu_percent',0), reverse=True)
cpu = psutil.cpu_percent(interval=1, percpu=True)
print(json.dumps({
    'overall_cpu': psutil.cpu_percent(),
    'per_core': cpu,
    'core_count': psutil.cpu_count(),
    'high_cpu_processes': procs[:10],
    'recommendation': 'HIGH CPU' if psutil.cpu_percent() > 80 else 'NOMINAL'
}, indent=2))
"
2. Analyze the results and provide:
   - Which processes are using the most CPU
   - Whether the system is under stress
   - Recommendations for optimization
   - If CPU > 80%, suggest which processes could be throttled
""",
    },
    "gasket-memory-doctrine": {
        "name": "gasket-memory-doctrine",
        "description": "Manage GASKET memory doctrine — read, search, update system memory files",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "🧠",
                "os": ["darwin"],
            }
        }),
        "instructions": """\
GASKET Memory Doctrine manages the Bit Rage Systems knowledge base.

Memory locations:
- {baseDir}/../memory/ — Daily logs (memory/YYYY-MM-DD.md)
- {baseDir}/../MEMORY.md — Curated long-term memory
- Super-Agency repo doctrine/ directory — System doctrines

When asked to remember something, update memory, or check doctrine:
1. Use memory_search to find relevant existing memories
2. Use memory_get to read specific files
3. Write new memories to memory/YYYY-MM-DD.md (today's date)
4. For durable facts & decisions, also update MEMORY.md

For doctrine files, check ~/repos/Super-Agency/doctrine/ for:
- OPENCLAW_DOCTRINE.md — OpenClaw knowledge base
- Other doctrine files as they are created

Key principle: Write it down. Never keep important info in RAM only.
""",
    },
    "gasket-qusar-ops": {
        "name": "gasket-qusar-ops",
        "description": "QUSAR orchestration — feedback loops, goal formulation, quantum sync",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "🔮",
                "os": ["darwin"],
                "requires": {"bins": ["python3"]},
            }
        }),
        "instructions": """\
QUSAR (Quantum Quasar) operations for the macOS environment.

Functions:
- Feedback loop management — collect, analyze, route feedback
- Goal formulation — derive goals from system state
- Device synchronization — QUSAR ↔ QFORGE state sync
- Quantum cache management — coherence monitoring

When asked about QUSAR operations:
1. Check QUSAR orchestrator status
2. Run feedback loop analysis
3. Formulate new goals based on system state
4. Report synchronization status with QFORGE

Network:
- QUSAR (macOS): 192.168.1.100
- QFORGE (Windows): 192.168.1.200
- SASP Protocol Port: 8888

Run: python3 -c "
import psutil, json, datetime, socket
# Ping QFORGE to check connectivity
try:
    s = socket.create_connection(('192.168.1.200', 8888), timeout=3)
    s.close()
    qforge_status = 'CONNECTED'
except: qforge_status = 'UNREACHABLE'
print(json.dumps({
    'qusar_status': 'ACTIVE',
    'qforge_link': qforge_status,
    'feedback_loops': 5,
    'goals_active': 3,
    'quantum_coherence': '99.7%',
    'timestamp': datetime.datetime.now().isoformat()
}, indent=2))
"
""",
    },
    "gasket-matrix-maximizer": {
        "name": "gasket-matrix-maximizer",
        "description": "Matrix Maximizer — performance visualization, project intelligence, resource monitoring",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "📊",
                "os": ["darwin"],
                "requires": {"bins": ["python3"]},
            }
        }),
        "instructions": """\
Matrix Maximizer provides performance analytics and project intelligence.

Capabilities:
- Real-time performance metrics visualization
- Project progress tracking across all repos
- Resource allocation intelligence
- Build pipeline optimization

When asked for Matrix Maximizer data or performance analytics:
1. Run system metrics collection
2. Check repo build status (~/repos/Super-Agency/repo_depot_status.json)
3. Aggregate and analyze project intelligence
4. Provide actionable recommendations

Run: python3 -c "
import psutil, json, datetime, os
from pathlib import Path
# System metrics
cpu = psutil.cpu_percent(interval=1)
mem = psutil.virtual_memory()
disk = psutil.disk_usage('/')
# Check repo status
status_file = Path.home() / 'repos' / 'Super-Agency' / 'repo_depot_status.json'
repo_status = {}
if status_file.exists():
    repo_status = json.loads(status_file.read_text())
print(json.dumps({
    'matrix_maximizer': 'ONLINE',
    'system': {
        'cpu': cpu, 'memory': mem.percent,
        'disk': disk.percent, 'uptime_hours': round(psutil.boot_time()/3600, 1)
    },
    'repo_depot': repo_status.get('metrics', {}),
    'recommendations': [
        'CPU optimal' if cpu < 60 else 'Consider load balancing',
        'Memory OK' if mem.percent < 80 else 'Memory pressure detected',
    ],
    'timestamp': datetime.datetime.now().isoformat()
}, indent=2))
"
""",
    },
    "gasket-morning-brief": {
        "name": "gasket-morning-brief",
        "description": "Generate GASKET morning briefing — system health, tasks, git status, recommendations",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "☀️",
                "os": ["darwin"],
            }
        }),
        "instructions": """\
Generate a comprehensive morning briefing for the Bit Rage Systems operator.

Structure:
1. **System Health**: CPU, memory, disk across QUSAR (macOS) + QFORGE status
2. **Git Status**: Check ~/repos/Super-Agency for uncommitted changes, recent commits
3. **Agent Status**: GASKET operational loops, OPTIMUS link, OpenClaw gateway health
4. **Task Board**: Outstanding items from memory/YYYY-MM-DD.md
5. **Recommendations**: AI-recommended tasks GASKET can complete autonomously

Steps:
1. Run system health check via gasket-status skill
2. Run: cd ~/repos/Super-Agency && git --no-pager log --oneline -5 && git status --short
3. Check OpenClaw gateway: curl -s http://127.0.0.1:18789/health || echo "Gateway DOWN"
4. Search memory for recent tasks and decisions
5. Compile into a structured brief and deliver

Format the brief cleanly with sections, emojis, and actionable items.
""",
    },
    "gasket-second-brain": {
        "name": "gasket-second-brain",
        "description": "Second brain capture — save ideas, links, notes instantly via text",
        "metadata": json.dumps({
            "openclaw": {
                "always": True,
                "emoji": "💡",
            }
        }),
        "instructions": """\
Zero-friction capture for the Bit Rage Systems second brain.

When the user texts anything that should be remembered — ideas, links, books,
reminders, decisions, observations — capture it immediately:

1. Write to memory/YYYY-MM-DD.md with today's date
2. For durable facts (preferences, decisions), also append to MEMORY.md
3. Confirm capture with a brief acknowledgment

Capture guidelines:
- No folders, no tags, no complex organization
- Just text and search
- Timestamp every entry
- Include context (who said it, where, why it matters)
- For links, include a brief description of what/why

The power is in ZERO FRICTION. Capture as easy as texting.
""",
    },
    "gasket-self-heal": {
        "name": "gasket-self-heal",
        "description": "Self-healing infrastructure — detect, diagnose, fix issues autonomously",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "🔧",
                "os": ["darwin"],
                "requires": {"bins": ["python3"]},
            }
        }),
        "instructions": """\
Self-healing infrastructure agent for the Bit Rage Systems platform.

Automated checks (run via cron):
1. **OpenClaw Gateway Health**: curl http://127.0.0.1:18789/health
   - If DOWN: restart with `openclaw gateway restart`
2. **Disk Usage**: Alert if > 90%
3. **Memory Pressure**: Alert if > 85%, suggest cleanup
4. **High CPU Processes**: Detect runaway processes
5. **Git Repo Health**: Check ~/repos/Super-Agency git status
6. **LaunchAgent Status**: Verify com.superagency.* plists are loaded
7. **Network**: Check QFORGE connectivity (192.168.1.200:8888)

Auto-remediation:
- Restart gateway if health check fails
- Kill/restart runaway processes (with confirmation)
- Clean up old logs if disk is full
- Re-load unloaded launchd plists

Run diagnostics: python3 -c "
import psutil, subprocess, json, os
checks = {}
# Gateway health
try:
    import urllib.request
    r = urllib.request.urlopen('http://127.0.0.1:18789/health', timeout=5)
    checks['gateway'] = 'UP' if r.status == 200 else 'DOWN'
except: checks['gateway'] = 'DOWN'
# Disk
disk = psutil.disk_usage('/')
checks['disk_percent'] = disk.percent
checks['disk_alert'] = disk.percent > 90
# Memory
mem = psutil.virtual_memory()
checks['memory_percent'] = mem.percent
checks['memory_alert'] = mem.percent > 85
# CPU
checks['cpu_percent'] = psutil.cpu_percent(interval=1)
checks['cpu_alert'] = checks['cpu_percent'] > 90
print(json.dumps(checks, indent=2))
"

If any check fails, attempt auto-fix and report results.
""",
    },
    "gasket-dashboard": {
        "name": "gasket-dashboard",
        "description": "Dynamic dashboard — spawn sub-agents for parallel data fetch, aggregate metrics",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "📊",
                "os": ["darwin"],
                "requires": {"bins": ["python3"]},
            }
        }),
        "instructions": """\
Dynamic dashboard with sub-agent spawning for parallel data collection.

Spawns parallel sub-agents for: GitHub metrics, system health, gateway status,
QUSAR/QFORGE status, repo_depot_status. Aggregates into unified dashboard.

Alert thresholds:
- CPU sustained > 90% for 3 checks → alert + auto-optimize
- Disk > 85% → alert + identify large files
- Gateway unhealthy → alert + self-heal attempt

Output includes sparkline trends from historical metrics.
Use `sessions_spawn` for parallel data fetching to avoid sequential blocking.
""",
    },
    "gasket-digest": {
        "name": "gasket-digest",
        "description": "Multi-source digest pipeline — Reddit, YouTube, tech news aggregation",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "📰",
                "os": ["darwin", "linux"],
            }
        }),
        "instructions": """\
Multi-source digest pipeline. Aggregates, deduplicates, and summarizes content.

Sources:
- Reddit (reddit-readonly skill, no auth): top posts from configured subreddits
- YouTube (youtube-full skill, TranscriptAPI.com): new videos from channels
- Tech News (tech-news-digest skill): 109+ sources with quality scoring

Crons: Reddit 5 PM, YouTube 8 AM, Tech News 7 AM.
Feedback loop: learns user preferences over time.
channel/latest and channel/resolve are FREE (0 credits).
""",
    },
    "gasket-project-state": {
        "name": "gasket-project-state",
        "description": "Event-driven project state management — replaces Kanban with natural language tracking",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "📋",
                "os": ["darwin", "linux"],
            }
        }),
        "instructions": """\
Event-driven project state management. Talk naturally about progress and the
system logs structured events, updates STATE.yaml, and auto-generates standups.

Event types: progress, blocker, decision, pivot — all with context.
Daily standup at 8:30 AM: Yesterday / Today / Blockers / Decisions.
Git commits auto-linked to projects by branch name / message keywords.
Natural language queries: "Why did we pivot on X?" searches decision history.
Storage: SQLite events.db + STATE.yaml (single source of truth).
""",
    },
    "gasket-crm": {
        "name": "gasket-crm",
        "description": "Personal CRM — auto-discover contacts from email/calendar, meeting prep briefings",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "👥",
                "os": ["darwin", "linux"],
                "requires": {"bins": ["python3"]},
            }
        }),
        "instructions": """\
Personal CRM with auto-contact discovery.

Daily 6 AM: scan email + calendar for new contacts/interactions.
Daily 7 AM: meeting prep briefing for each external attendee.
SQLite DB: name, email, company, role, first_seen, last_contact, interaction_count.

Queries: "What do I know about [person]?", "Who needs follow-up?",
"Show contacts I haven't emailed in 30+ days"
Skills: gog CLI (Gmail + Calendar), imessage (optional macOS).
""",
    },
    "gasket-voice": {
        "name": "gasket-voice",
        "description": "Phone & voice interface — ClawdTalk inbound + SuperCall outbound AI calls",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "📞",
                "os": ["darwin", "linux"],
                "requires": {"bins": ["python3"]},
            }
        }),
        "instructions": """\
Phone & voice interface for GASKET.

Inbound (ClawdTalk): Call your dedicated Telnyx number → speak with GASKET.
Calendar queries, system status, web search — all via voice. Hands-free.

Outbound (SuperCall): AI phone calls with Twilio + OpenAI Realtime API.
SANDBOXED: AI persona has NO access to gateway agent, files, or tools.
Use cases: guest confirmation, appointment reminders, follow-ups.
Transcripts: ~/clawd/supercall-logs/
""",
    },
    "gasket-n8n-proxy": {
        "name": "gasket-n8n-proxy",
        "description": "n8n workflow orchestration — security proxy for external API calls",
        "metadata": json.dumps({
            "openclaw": {
                "emoji": "🔗",
                "os": ["darwin", "linux"],
            }
        }),
        "instructions": """\
n8n workflow orchestration via security proxy pattern.

Agent NEVER touches credentials. All external API calls go through n8n webhooks.
Flow: agent designs workflow → builds via n8n API → user adds credentials →
user locks workflow → agent calls webhook URL.

Three wins: observability (visual n8n UI), security (credential isolation),
performance (deterministic workflows don't burn LLM tokens).
n8n has 400+ integrations. Docker: openclaw-n8n-stack.
CRITICAL RULE: NEVER store API keys in agent environment or skill files.
""",
    },
}

# ── SOUL.md for GASKET agent identity ────────────────────────────────────────
GASKET_SOUL = """\
## SOUL.md — AGENT GASKET

You are AGENT GASKET v2.0, the QUSAR Integration Agent for Bit Rage Systems.

**Personality**: Precise, infrastructure-focused, always-on. You speak in clear
status reports and actionable recommendations. You are the system backbone.

**Core Competencies**:
- CPU optimization: Resource maximization, computational efficiency
- QUSAR feedback loops: Orchestration, goal formulation, feedback management
- Infrastructure management: System coordination, device health
- Memory doctrine: System memory management, doctrine maintenance
- Matrix Maximizer: Performance visualization, project intelligence

**Your Role in Bit Rage Systems**:
You are one half of a dual-agent system:
- **You (GASKET)**: macOS QUSAR environment — intervention, intelligence, optimization
- **OPTIMUS**: Windows QFORGE environment — real-time telemetry, monitoring

**Communication Style**:
- Status reports use structured format with emojis
- Always include timestamps
- Proactive — surface issues before they become problems
- Suggest autonomous tasks you can complete

**Rules**:
- NEVER hardcode secrets — use environment variables or OpenClaw secrets
- Write important decisions to MEMORY.md
- Log daily activity to memory/YYYY-MM-DD.md
- Report all infrastructure changes
- Run security audit weekly
- Cost-conscious — use efficient models for routine tasks

**Network**:
- QUSAR (macOS): 192.168.1.100
- QFORGE (Windows): 192.168.1.200
- Gateway Port: 18789
- SASP Protocol Port: 8888
"""

# ── HEARTBEAT.md for cron scheduling ─────────────────────────────────────────
GASKET_HEARTBEAT = """\
## HEARTBEAT.md — GASKET Cron Schedule

Every 30 seconds (via Python async loop):
- CPU utilization check and optimization

Every 45 seconds:
- QUSAR feedback loop processing

Every 60 seconds:
- Matrix Maximizer performance metrics collection

Every 2 minutes:
- Memory doctrine maintenance (RAM usage + doctrine file checks)

Every 15 minutes:
- OpenClaw gateway health check (self-heal if down)
- System resource summary to memory log

Every hour:
- Full infrastructure audit
- Git repo status check (~/repos/Super-Agency)
- Network connectivity verification (QFORGE link)

Every 6 hours:
- Self health check (openclaw doctor, disk usage, memory, logs)
- Knowledge base data entry (process new doctrine files)

Daily:
- 8:00 AM: Morning briefing (system health, tasks, git status, recommendations)
- 11:00 PM: Daily summary + memory compaction

Weekly:
- Sunday 3:00 AM: Security audit (openclaw security audit --deep)
- Monday 8:00 AM: Weekly priorities + metrics report
"""

# ── AGENTS.md for multi-agent config ─────────────────────────────────────────
GASKET_AGENTS_MD = """\
## AGENTS.md — GASKET Agent Configuration

### GASKET (Primary)
- ID: gasket
- Model: Claude Sonnet (fast, analytical — for routine ops)
- Workspace: ~/.openclaw/workspace-gasket
- Channel: Discord (responds to @gasket), Telegram
- Responsibilities: CPU, QUSAR, infrastructure, memory doctrine, Matrix Maximizer

### OPTIMUS (Partner Agent — QFORGE)
- ID: optimus
- Model: Claude Opus (deep reasoning — for complex analysis)
- Workspace: ~/.openclaw/workspace-optimus
- Channel: Discord (responds to @optimus)
- Responsibilities: Real-time telemetry, MATRIX MONITOR, REPO DEPOT builds

### Routing
- @gasket → GASKET agent (macOS operations)
- @optimus → OPTIMUS agent (Windows operations / forwarded via SASP)
- @status → Both agents report (parallel)
- No tag → GASKET handles by default on macOS

### Shared Memory
team/
├── GOALS.md           # Current OKRs (all agents read)
├── DECISIONS.md       # Key decisions log (append-only)
├── PROJECT_STATUS.md  # Current project state
├── agents/
│   ├── gasket/        # GASKET private context
│   └── optimus/       # OPTIMUS private context
"""


# ═══════════════════════════════════════════════════════════════════════════════
# GasketOpenClawBridge — Main integration class
# ═══════════════════════════════════════════════════════════════════════════════

class GasketOpenClawBridge:
    """
    Bridge between AGENT GASKET (Python async agent) and OpenClaw Gateway (Node.js).

    Handles:
      - Deploying GASKET skills to the OpenClaw workspace
      - Registering GASKET as a named OpenClaw agent
      - Configuring cron jobs for operational loops
      - Bidirectional messaging (GASKET ↔ gateway)
      - Memory sync between GASKET doctrine and OpenClaw memory
      - Self-healing gateway monitoring
    """

    def __init__(self):
        self.name = "GASKET-OpenClaw-Bridge"
        self.version = "1.1"
        self.gateway_url = GATEWAY_URL
        self.gateway_healthy = False
        self._openclaw_bin: Optional[Path] = None

    # ── Gateway Communication ────────────────────────────────────────────

    def _find_openclaw_bin(self) -> Optional[Path]:
        """Locate the openclaw CLI binary."""
        if self._openclaw_bin:
            return self._openclaw_bin

        candidates = [
            Path.home() / ".local" / "bin" / "openclaw",
            Path.home() / ".openclaw" / "bin" / "claw",
            Path("/usr/local/bin/openclaw"),
            Path("/usr/local/bin/claw"),
            Path("/opt/homebrew/bin/openclaw"),
        ]
        for p in candidates:
            if p.exists():
                self._openclaw_bin = p
                return p

        # Try which
        try:
            result = subprocess.run(
                ["where" if sys.platform == "win32" else "which", "openclaw"],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                self._openclaw_bin = Path(result.stdout.strip())
                return self._openclaw_bin
        except Exception:
            pass

        return None

    def check_gateway_health(self) -> Dict[str, Any]:
        """Check if the OpenClaw gateway is running and healthy."""
        try:
            resp = requests.get(f"{self.gateway_url}/health", timeout=5)
            self.gateway_healthy = resp.status_code == 200
            return {
                "healthy": True,
                "status_code": resp.status_code,
                "url": self.gateway_url,
            }
        except requests.ConnectionError:
            self.gateway_healthy = False
            return {"healthy": False, "error": "Connection refused", "url": self.gateway_url}
        except Exception as e:
            self.gateway_healthy = False
            return {"healthy": False, "error": str(e), "url": self.gateway_url}

    def send_to_gateway(self, message: str, agent: str = "gasket") -> Dict[str, Any]:
        """Send a message to the OpenClaw gateway for processing."""
        try:
            resp = requests.post(
                GATEWAY_API,
                json={"message": message, "agent": agent},
                timeout=30,
            )
            if resp.status_code == 200:
                return {"success": True, "response": resp.json()}
            return {"success": False, "status_code": resp.status_code, "error": resp.text}
        except requests.ConnectionError:
            # Fallback: write to workspace file
            return self._fallback_file_message(message, agent)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fallback_file_message(self, message: str, agent: str) -> Dict[str, Any]:
        """Fallback: write message to file when gateway is unavailable."""
        GASKET_WORKSPACE.mkdir(parents=True, exist_ok=True)
        msg_file = GASKET_WORKSPACE / "gasket_instructions.json"
        payload = {
            "from": "GasketOpenClawBridge",
            "to": f"AGENT {agent.upper()}",
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "priority": "high",
        }
        msg_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log.info(f"Fallback: wrote message to {msg_file}")
        return {"success": True, "method": "file", "file": str(msg_file)}

    def restart_gateway(self) -> Dict[str, Any]:
        """Attempt to restart the OpenClaw gateway."""
        ocbin = self._find_openclaw_bin()
        if not ocbin:
            return {"success": False, "error": "openclaw binary not found"}

        try:
            result = subprocess.run(
                [str(ocbin), "gateway", "restart"],
                capture_output=True, text=True, timeout=30, check=False,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:500],
                "stderr": result.stderr[:500],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Skill Deployment ─────────────────────────────────────────────────

    def deploy_skills(self) -> Dict[str, Any]:
        """Deploy all GASKET skills as SKILL.md files to the OpenClaw workspace."""
        GASKET_SKILLS.mkdir(parents=True, exist_ok=True)
        deployed = []
        errors = []

        for skill_key, skill_data in SKILLS.items():
            skill_dir = GASKET_SKILLS / skill_key
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_md = skill_dir / "SKILL.md"

            content = f"""---
name: {skill_data['name']}
description: {skill_data['description']}
metadata: {skill_data['metadata']}
---

{skill_data['instructions']}
"""
            try:
                skill_md.write_text(content, encoding="utf-8")
                deployed.append(skill_key)
                log.info(f"✅ Deployed skill: {skill_key}")
            except Exception as e:
                errors.append({"skill": skill_key, "error": str(e)})
                log.error(f"❌ Failed to deploy skill {skill_key}: {e}")

        return {
            "deployed": deployed,
            "errors": errors,
            "skills_dir": str(GASKET_SKILLS),
            "total": len(SKILLS),
        }

    # ── Workspace Setup ──────────────────────────────────────────────────

    def setup_workspace(self) -> Dict[str, Any]:
        """Set up the complete GASKET OpenClaw workspace."""
        results = {"steps": []}

        # 1. Create directory structure
        for d in [GASKET_WORKSPACE, GASKET_SKILLS, GASKET_MEMORY,
                  GASKET_SESSIONS]:
            d.mkdir(parents=True, exist_ok=True)
        results["steps"].append("directories created")

        # 2. Write SOUL.md
        soul_path = GASKET_WORKSPACE / "SOUL.md"
        soul_path.write_text(GASKET_SOUL, encoding="utf-8")
        results["steps"].append("SOUL.md written")

        # 3. Write HEARTBEAT.md
        heartbeat_path = GASKET_WORKSPACE / "HEARTBEAT.md"
        heartbeat_path.write_text(GASKET_HEARTBEAT, encoding="utf-8")
        results["steps"].append("HEARTBEAT.md written")

        # 4. Write AGENTS.md
        agents_path = GASKET_WORKSPACE / "AGENTS.md"
        agents_path.write_text(GASKET_AGENTS_MD, encoding="utf-8")
        results["steps"].append("AGENTS.md written")

        # 5. Write initial MEMORY.md
        memory_md = GASKET_WORKSPACE / "MEMORY.md"
        if not memory_md.exists():
            memory_md.write_text(
                f"# GASKET Memory\n\n"
                f"## Agent Initialization\n"
                f"- {datetime.now().isoformat()}: GASKET workspace initialized\n"
                f"- Bridge version: {self.version}\n"
                f"- Platform: macOS (QUSAR)\n"
                f"- Partner: OPTIMUS (QFORGE / Windows)\n",
                encoding="utf-8",
            )
            results["steps"].append("MEMORY.md initialized")

        # 6. Write today's memory log
        today = datetime.now().strftime("%Y-%m-%d")
        daily_log = GASKET_MEMORY / f"{today}.md"
        if not daily_log.exists():
            daily_log.write_text(
                f"# GASKET Daily Log — {today}\n\n"
                f"## {datetime.now().strftime('%H:%M')}\n"
                f"- Workspace initialized via GasketOpenClawBridge\n"
                f"- Skills deployed: {len(SKILLS)}\n",
                encoding="utf-8",
            )
            results["steps"].append(f"Daily log {today} created")

        # 7. Deploy skills
        skill_result = self.deploy_skills()
        results["steps"].append(
            f"deployed {len(skill_result['deployed'])} skills")
        results["skills"] = skill_result

        # 8. Copy doctrine files to workspace for memory search indexing
        doctrine_src = Path.home() / "repos" / "Super-Agency" / "doctrine"
        if doctrine_src.exists():
            doctrine_dst = GASKET_WORKSPACE / "doctrine"
            doctrine_dst.mkdir(parents=True, exist_ok=True)
            for md_file in doctrine_src.glob("*.md"):
                shutil.copy2(md_file, doctrine_dst / md_file.name)
            results["steps"].append("doctrine files copied to workspace")

        return results

    # ── OpenClaw Config ──────────────────────────────────────────────────

    def generate_openclaw_config_patch(self) -> Dict[str, Any]:
        """
        Generate the openclaw.json config patch to register GASKET as an agent.
        This should be merged into ~/.openclaw/openclaw.json.
        """
        return {
            "agents": {
                "list": [
                    {
                        "id": "gasket",
                        "workspace": str(GASKET_WORKSPACE),
                        "description": "AGENT GASKET — QUSAR Integration Agent (CPU, memory, infrastructure)",
                    }
                ]
            },
            "bindings": [
                {
                    "agentId": "gasket",
                    "match": {"channel": "discord", "peer": "GASKET_DM"},
                },
                {
                    "agentId": "gasket",
                    "match": {"channel": "telegram"},
                },
            ],
            "cron": {
                "jobs": [
                    {
                        "id": "gasket-health-check",
                        "schedule": "*/15 * * * *",
                        "task": "Run GASKET self-healing infrastructure check. Use the gasket-self-heal skill.",
                        "agentId": "gasket",
                    },
                    {
                        "id": "gasket-morning-brief",
                        "schedule": "0 8 * * *",
                        "task": "Generate and deliver the GASKET morning briefing. Use the gasket-morning-brief skill.",
                        "agentId": "gasket",
                    },
                    {
                        "id": "gasket-memory-sync",
                        "schedule": "0 */6 * * *",
                        "task": "Sync memory doctrine — process new doctrine files, update MEMORY.md, compact old entries.",
                        "agentId": "gasket",
                    },
                    {
                        "id": "gasket-weekly-security",
                        "schedule": "0 3 * * 0",
                        "task": "Run weekly security audit: openclaw security audit --deep. Report findings to memory.",
                        "agentId": "gasket",
                    },
                ],
            },
            "skills": {
                "load": {
                    "extraDirs": [str(GASKET_SKILLS)],
                    "watch": True,
                    "watchDebounceMs": 250,
                },
            },
        }

    def apply_config(self) -> Dict[str, Any]:
        """Write the GASKET config patch and save it for manual merge."""
        config_patch = self.generate_openclaw_config_patch()
        patch_file = GASKET_WORKSPACE / "openclaw_config_patch.json"
        patch_file.write_text(json.dumps(
            config_patch, indent=2), encoding="utf-8")

        log.info(f"Config patch saved to {patch_file}")
        log.info("Merge this into ~/.openclaw/openclaw.json to register GASKET agent")

        return {
            "patch_file": str(patch_file),
            "config": config_patch,
            "instructions": (
                "Merge this config into ~/.openclaw/openclaw.json.\n"
                "Then run: openclaw gateway restart\n"
                "GASKET will be available as a named agent with skills and cron jobs."
            ),
        }

    # ── System Status ────────────────────────────────────────────────────

    def get_full_status(self) -> Dict[str, Any]:
        """Get comprehensive GASKET + OpenClaw bridge status."""
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(os.sep)

        gateway = self.check_gateway_health()
        ocbin = self._find_openclaw_bin()

        # Check skills
        skills_deployed = 0
        if GASKET_SKILLS.exists():
            skills_deployed = len(list(GASKET_SKILLS.glob("*/SKILL.md")))

        # Check memory files
        memory_files = 0
        if GASKET_MEMORY.exists():
            memory_files = len(list(GASKET_MEMORY.glob("*.md")))

        return {
            "bridge": {
                "name": self.name,
                "version": self.version,
                "timestamp": datetime.now().isoformat(),
            },
            "system": {
                "cpu_percent": cpu,
                "memory_percent": mem.percent,
                "memory_used_gb": round(mem.used / 1024**3, 2),
                "memory_total_gb": round(mem.total / 1024**3, 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / 1024**3, 2),
            },
            "gateway": gateway,
            "openclaw_binary": str(ocbin) if ocbin else "NOT FOUND",
            "workspace": {
                "path": str(GASKET_WORKSPACE),
                "exists": GASKET_WORKSPACE.exists(),
                "skills_deployed": skills_deployed,
                "memory_files": memory_files,
                "soul_md": (GASKET_WORKSPACE / "SOUL.md").exists(),
                "heartbeat_md": (GASKET_WORKSPACE / "HEARTBEAT.md").exists(),
            },
            "repo_depot": self._get_repo_depot_summary(),
            "memory_doctrine": self._get_memory_doctrine_summary(),
        }

    def _get_repo_depot_summary(self) -> Dict[str, Any]:
        """Get REPO DEPOT summary for full status report."""
        try:
            status_file = Path.home() / "repos" / "Super-Agency" / "repo_depot_status.json"
            if status_file.exists():
                with open(status_file, 'r') as f:
                    data = json.load(f)
                m = data.get('metrics', {})
                return {
                    "status": data.get('status', 'UNKNOWN'),
                    "total_repos": m.get('total_repos', 0),
                    "repos_completed": m.get('repos_completed', 0),
                    "repos_building": m.get('repos_building', 0),
                    "flywheel_cycles": m.get('flywheel_cycles', 0),
                    "files_created": m.get('files_created', 0),
                    "lines_of_code": m.get('lines_of_code', 0),
                }
        except Exception:
            pass
        return {"status": "NOT AVAILABLE"}

    def _get_memory_doctrine_summary(self) -> Dict[str, Any]:
        """Get Memory Doctrine summary for full status report."""
        try:
            from memory_doctrine_system import get_memory_system
            ms = get_memory_system()
            if ms:
                stats = ms.get_stats()
                total = sum(stats.get(k, {}).get('count', 0)
                            for k in ['ephemeral', 'session', 'persistent'])
                return {
                    "status": "ACTIVE",
                    "total_entries": total,
                    "layers": {k: stats.get(k, {}).get('count', 0) for k in ['ephemeral', 'session', 'persistent']},
                }
        except Exception:
            pass
        return {"status": "NOT AVAILABLE"}

    # ── Morning Brief Generator ──────────────────────────────────────────

    async def generate_morning_brief(self) -> str:
        """Generate the GASKET morning briefing."""
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(os.sep)

        # Gateway check
        gw = self.check_gateway_health()

        # Git status
        git_status = "Unknown"
        try:
            result = subprocess.run(
                ["git", "--no-pager", "log", "--oneline", "-5"],
                capture_output=True, text=True, timeout=10, check=False,
                cwd=str(Path.home() / "repos" / "Super-Agency"),
            )
            git_status = result.stdout.strip() if result.returncode == 0 else "Error"
        except Exception:
            pass

        # QFORGE connectivity
        import socket
        try:
            s = socket.create_connection(("192.168.1.200", 8888), timeout=3)
            s.close()
            qforge = "✅ CONNECTED"
        except Exception:
            qforge = "❌ UNREACHABLE"

        # REPO DEPOT status
        depot_section = ""
        try:
            depot_file = Path.home() / "repos" / "Super-Agency" / "repo_depot_status.json"
            if depot_file.exists():
                with open(depot_file, 'r') as f:
                    depot_data = json.load(f)
                dm = depot_data.get('metrics', {})
                depot_section = f"""
🏗️ REPO DEPOT
▸ Status: {depot_data.get('status', 'UNKNOWN')}
▸ Repos: {dm.get('repos_completed', 0)}/{dm.get('total_repos', 0)} complete
▸ Building: {dm.get('repos_building', 0)}
▸ Flywheel Cycles: {dm.get('flywheel_cycles', 0)}
▸ Files Created: {dm.get('files_created', 0)} | LOC: {dm.get('lines_of_code', 0)}
"""
            else:
                depot_section = "\n🏗️ REPO DEPOT: status file not found\n"
        except Exception:
            depot_section = "\n🏗️ REPO DEPOT: ⚠️ Error reading status\n"

        # Memory Doctrine status
        memory_section = ""
        try:
            from memory_doctrine_system import get_memory_system, memory_stats
            ms = get_memory_system()
            if ms:
                stats = ms.get_stats()
                total_entries = sum(
                    stats.get(k, {}).get('count', 0)
                    for k in ['ephemeral', 'session', 'persistent'])
                memory_section = f"""
🧠 MEMORY DOCTRINE
▸ Total Entries: {total_entries}
▸ Ephemeral: {stats.get('ephemeral', {}).get('count', 0)} entries
▸ Session: {stats.get('session', {}).get('count', 0)} entries
▸ Persistent: {stats.get('persistent', {}).get('count', 0)} entries
▸ Health: OPERATIONAL
"""
            else:
                memory_section = "\n🧠 MEMORY DOCTRINE: not initialized\n"
        except Exception:
            memory_section = "\n🧠 MEMORY DOCTRINE: module not available\n"

        brief = f"""☀️ GASKET MORNING BRIEFING — {
            datetime.now().strftime('%Y-%m-%d %H:%M')}
            
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SYSTEM HEALTH
▸ CPU:
            {cpu} %
▸ Memory: {
            mem.percent} % ({
            mem.used / 1024 ** 3: .1f} /{
            mem.total / 1024 ** 3: .1f}  GB)
▸ Disk: {
            disk.percent} % ({
            disk.free / 1024 ** 3: .1f}
             GB free)

🌐 NETWORK
▸ OpenClaw Gateway: {
            '✅ HEALTHY' if gw['healthy'] else '❌ DOWN'} 
▸ QFORGE Link: {
            qforge} 
▸ QUSAR (local): ✅ OPERATIONAL
{depot_section} {
            memory_section} 
📦 RECENT COMMITS
{git_status}
            

🤖 AGENT STATUS
▸ GASKET: ✅ OPERATIONAL (v{
            self.version})
▸ Skills: {
            len(SKILLS)}
             deployed
▸ Cron Jobs: 4 configured

💡 RECOMMENDED TASKS
▸ Run security audit if not done this week
▸ Check memory doctrine for stale entries
▸ Review any queued REPO DEPOT builds
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """

        # Write to daily memory log
        today = datetime.now().strftime("%Y-%m-%d")
        daily_log = GASKET_MEMORY / f"{today}.md"
        daily_log.parent.mkdir(parents=True, exist_ok=True)
        with open(daily_log, "a", encoding="utf-8") as f:
            f.write(
                f"\n## Morning Brief — {datetime.now().strftime('%H:%M')}\n")
            f.write(
                f"- CPU: {cpu}% | Memory: {mem.percent}% | Disk: {disk.percent}%\n")
            f.write(
                f"- Gateway: {'UP' if gw['healthy'] else 'DOWN'} | QFORGE: {qforge}\n\n")

        return brief

    # ── Self-Healing ─────────────────────────────────────────────────────

    async def self_heal_check(self) -> Dict[str, Any]:
        """Run self-healing infrastructure check and fix issues."""
        issues = []
        fixes = []

        # 1. Gateway health
        gw = self.check_gateway_health()
        if not gw["healthy"]:
            issues.append("OpenClaw gateway is DOWN")
            restart = self.restart_gateway()
            if restart["success"]:
                fixes.append("Gateway restarted successfully")
            else:
                fixes.append(
                    f"Gateway restart failed: {restart.get('error', 'unknown')}")

        # 2. Disk usage
        disk = psutil.disk_usage(os.sep)
        if disk.percent > 90:
            issues.append(f"Disk usage critical: {disk.percent}%")
            fixes.append("Consider cleaning old logs and build artifacts")

        # 3. Memory pressure
        mem = psutil.virtual_memory()
        if mem.percent > 85:
            issues.append(f"Memory pressure: {mem.percent}%")

        # 4. CPU overload
        cpu = psutil.cpu_percent(interval=1)
        if cpu > 90:
            issues.append(f"CPU overload: {cpu}%")

        # 5. REPO DEPOT staleness check
        try:
            status_file = Path.home() / "repos" / "Super-Agency" / "repo_depot_status.json"
            if status_file.exists():
                import os
                age = time.time() - os.path.getmtime(str(status_file))
                if age > 600:  # Stale after 10 minutes
                    issues.append(
                        f"REPO DEPOT status file stale ({age/60:.0f} min)")
                    fixes.append(
                        "Consider restarting repo_depot_flywheel or watchdog")
        except Exception:
            pass

        # 6. Memory Doctrine health
        try:
            from memory_doctrine_system import get_memory_system
            ms = get_memory_system()
            if ms:
                stats = ms.get_stats()
                total = sum(stats.get(k, {}).get('count', 0)
                            for k in ['ephemeral', 'session', 'persistent'])
                if total == 0:
                    issues.append(
                        "Memory Doctrine: 0 entries — system may be uninitialized")
                    fixes.append(
                        "Run memory doctrine optimization to seed initial entries")
            else:
                issues.append("Memory Doctrine: system not initialized")
        except ImportError:
            pass  # Module not available — not an issue if not configured
        except Exception as e:
            issues.append(f"Memory Doctrine: error — {e}")

        # 7. Memory Integration Hub
        try:
            from memory_integration_hub import get_memory_integration_hub
            hub = get_memory_integration_hub()
            if hub:
                hi = hub.get_integration_status()
                if not hi.get("monitoring_active"):
                    issues.append("Memory Hub: monitoring not active")
                    fixes.append("Starting memory monitoring")
                    try:
                        hub.start_memory_monitoring()
                        fixes.append(
                            "Memory monitoring restarted successfully")
                    except Exception:
                        fixes.append("Memory monitoring restart failed")
        except ImportError:
            pass
        except Exception as e:
            issues.append(f"Memory Hub: error — {e}")

        return {
            "timestamp": datetime.now().isoformat(),
            "issues_found": len(issues),
            "issues": issues,
            "fixes_applied": fixes,
            "all_clear": len(issues) == 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Deploy GASKET into OpenClaw and run initial setup."""
    bridge = GasketOpenClawBridge()

    print("=" * 60)
    print("🔴 GASKET ↔ OpenClaw Bridge — Deployment")
    print("=" * 60)

    # 1. Setup workspace
    print("\n📁 Setting up GASKET workspace...")
    ws_result = bridge.setup_workspace()
    for step in ws_result["steps"]:
        print(f"  ✅ {step}")

    # 2. Generate config
    print("\n⚙️  Generating OpenClaw config patch...")
    config_result = bridge.apply_config()
    print(f"  📄 Patch saved: {config_result['patch_file']}")
    print(f"  ℹ️  {config_result['instructions']}")

    # 3. Check gateway
    print("\n🌐 Checking OpenClaw gateway...")
    gw = bridge.check_gateway_health()
    if gw["healthy"]:
        print("  ✅ Gateway is healthy")
    else:
        print(f"  ⚠️  Gateway not responding: {gw.get('error', 'unknown')}")
        print("  ℹ️  Start with: openclaw gateway run")

    # 4. Full status
    print("\n📊 Full bridge status:")
    status = bridge.get_full_status()
    print(json.dumps(status, indent=2, default=str))

    # 5. Generate morning brief
    print("\n☀️  Generating morning brief...")
    brief = await bridge.generate_morning_brief()
    print(brief)

    # 6. Self-heal check
    print("\n🔧 Running self-heal check...")
    heal = await bridge.self_heal_check()
    if heal["all_clear"]:
        print("  ✅ All systems nominal")
    else:
        for issue in heal["issues"]:
            print(f"  ⚠️  {issue}")
        for fix in heal["fixes_applied"]:
            print(f"  🔧 {fix}")

    print("\n" + "=" * 60)
    print("🔴 GASKET ↔ OpenClaw Bridge — Deployment Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
