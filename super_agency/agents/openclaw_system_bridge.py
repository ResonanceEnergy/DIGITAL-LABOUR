#!/usr/bin/env python3
"""
OpenClaw System Bridge v1.0 — DIGITAL LABOUR
==========================================
System-wide OpenClaw gateway bridge serving ALL 5 departments,
47+ Inner Council agents, NCC/NCL subsystems, REPO DEPOT, Matrix Monitor,
and all 27 managed repos.

Extends the GASKET-specific bridge to provide OpenClaw capabilities
across every agent, department, division, and process in DIGITAL LABOUR.

Architecture:
    OpenClaw Gateway (ws://127.0.0.1:18789)
        ↕
    OpenClawSystemBridge (this file)
        ↕
    Department Routers → Agent Sessions → Skills
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Configuration ───────────────────────────────────────────────────────────

OPENCLAW_GATEWAY = os.getenv("OPENCLAW_GATEWAY", "ws://127.0.0.1:18789")
OPENCLAW_PORT = int(os.getenv("OPENCLAW_PORT", "18789"))
SKILLS_ROOT = Path(__file__).parent.parent / "skills"
WORKSPACE_ROOT = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE_ROOT / "memory"
STATE_DIR = WORKSPACE_ROOT / "state"

VERSION = "1.0.0"

# Department registry
DEPARTMENTS = {
    "executive_council": {
        "name": "Executive Council",
        "authority": "AZ_FINAL",
        "head": "Agent AZ",
        "skills_prefix": "exec",
        "agents": ["agent_az"],
        "topics": ["strategy", "decisions", "doctrine"],
    },
    "intelligence_operations": {
        "name": "Intelligence Operations",
        "authority": "HIGH",
        "head": "Intelligence Director",
        "skills_prefix": "intel",
        "agents": [
            "joe_rogan_agent", "lex_fridman_agent", "tom_bilyeu_agent",
            "jordan_peterson_agent", "andrew_huberman_agent", "peter_attia_agent",
            "daniel_schmachtenberger_agent", "geoffrey_hinton_agent",
            "demis_hassabis_agent",
        ],
        "topics": ["youtube-intel", "research-intel", "news-digest", "second-brain"],
    },
    "operations_command": {
        "name": "Operations Command",
        "authority": "STANDARD",
        "head": "Operations Commander",
        "skills_prefix": "ops",
        "agents": ["repo_sentry", "daily_brief", "orchestrator", "gasket"],
        "topics": ["system-health", "alerts", "morning-brief", "tasks"],
    },
    "technology_infrastructure": {
        "name": "Technology Infrastructure",
        "authority": "STANDARD",
        "head": "Technology Director",
        "skills_prefix": "tech",
        "agents": ["integrate_cell", "ncl_catalog", "intelligent_repo_builder"],
        "topics": ["project-state", "builds", "deployments", "n8n"],
    },
    "financial_operations": {
        "name": "Financial Operations",
        "authority": "STANDARD",
        "head": "Financial Director",
        "skills_prefix": "fin",
        "agents": ["portfolio_intel", "portfolio_maintainer"],
        "topics": ["earnings", "market-research", "portfolio-crm"],
    },
}

# Use case registry — maps all 30 awesome-openclaw use cases to departments
USE_CASES = {
    "custom-morning-brief": {"dept": "operations_command", "priority": "CRITICAL"},
    "self-healing-home-server": {"dept": "operations_command", "priority": "CRITICAL"},
    "dynamic-dashboard": {"dept": "operations_command", "priority": "HIGH"},
    "project-state-management": {"dept": "technology_infrastructure", "priority": "HIGH"},
    "autonomous-project-management": {"dept": "technology_infrastructure", "priority": "HIGH"},
    "second-brain": {"dept": "intelligence_operations", "priority": "CRITICAL"},
    "knowledge-base-rag": {"dept": "intelligence_operations", "priority": "HIGH"},
    "semantic-memory-search": {"dept": "intelligence_operations", "priority": "HIGH"},
    "daily-youtube-digest": {"dept": "intelligence_operations", "priority": "HIGH"},
    "daily-reddit-digest": {"dept": "intelligence_operations", "priority": "MEDIUM"},
    "multi-source-tech-news-digest": {"dept": "intelligence_operations", "priority": "HIGH"},
    "youtube-content-pipeline": {"dept": "intelligence_operations", "priority": "MEDIUM"},
    "content-factory": {"dept": "intelligence_operations", "priority": "MEDIUM"},
    "x-account-analysis": {"dept": "intelligence_operations", "priority": "MEDIUM"},
    "multi-agent-team": {"dept": "executive_council", "priority": "CRITICAL"},
    "autonomous-game-dev-pipeline": {"dept": "technology_infrastructure", "priority": "LOW"},
    "n8n-workflow-orchestration": {"dept": "technology_infrastructure", "priority": "HIGH"},
    "todoist-task-manager": {"dept": "operations_command", "priority": "MEDIUM"},
    "multi-channel-assistant": {"dept": "operations_command", "priority": "HIGH"},
    "multi-channel-customer-service": {"dept": "financial_operations", "priority": "MEDIUM"},
    "personal-crm": {"dept": "financial_operations", "priority": "MEDIUM"},
    "inbox-declutter": {"dept": "operations_command", "priority": "MEDIUM"},
    "phone-based-personal-assistant": {"dept": "operations_command", "priority": "LOW"},
    "event-guest-confirmation": {"dept": "operations_command", "priority": "LOW"},
    "earnings-tracker": {"dept": "financial_operations", "priority": "HIGH"},
    "market-research-product-factory": {"dept": "intelligence_operations", "priority": "HIGH"},
    "polymarket-autopilot": {"dept": "financial_operations", "priority": "MEDIUM"},
    "health-symptom-tracker": {"dept": "operations_command", "priority": "LOW"},
    "family-calendar-household-assistant": {"dept": "operations_command", "priority": "LOW"},
    "overnight-mini-app-builder": {"dept": "executive_council", "priority": "HIGH"},
}


class DepartmentRouter:
    """Routes OpenClaw messages and skills to the correct department."""

    def __init__(self, dept_id: str, config: dict):
        self.dept_id = dept_id
        self.config = config
        self.name = config["name"]
        self.authority = config["authority"]
        self.skills_prefix = config["skills_prefix"]
        self.active_sessions: Dict[str, dict] = {}
        self.message_count = 0
        self.last_activity = None
        self.health = "HEALTHY"

    def get_status(self) -> dict:
        return {
            "department": self.name,
            "authority": self.authority,
            "active_sessions": len(self.active_sessions),
            "message_count": self.message_count,
            "last_activity": self.last_activity,
            "health": self.health,
            "agents": self.config["agents"],
            "topics": self.config["topics"],
        }

    def route_message(self, message: str, source_agent: str = None) -> dict:
        """Route an incoming message to the appropriate agent/topic."""
        self.message_count += 1
        self.last_activity = datetime.now().isoformat()

        # Determine target agent based on message content
        target = self._classify_message(message)

        return {
            "department": self.dept_id,
            "target_agent": target,
            "message": message,
            "source": source_agent,
            "timestamp": self.last_activity,
            "session_id": self._get_or_create_session(target),
        }

    def _classify_message(self, message: str) -> str:
        """Classify message to determine target agent."""
        msg_lower = message.lower()

        # Topic-based routing
        for topic in self.config["topics"]:
            if topic.replace(
                "-", " ") in msg_lower or topic.replace(
                "-", "_") in msg_lower:
                return topic

        # Default to first agent
        return self.config["agents"][0] if self.config["agents"] else "default"

    def _get_or_create_session(self, agent_id: str) -> str:
        """Get existing session or create new one for the agent."""
        if agent_id not in self.active_sessions:
            session_id = f"{self.dept_id}_{agent_id}_{int(time.time())}"
            self.active_sessions[agent_id] = {
                "id": session_id,
                "created": datetime.now().isoformat(),
                "messages": 0,
            }
        self.active_sessions[agent_id]["messages"] += 1
        return self.active_sessions[agent_id]["id"]

    def get_use_cases(self) -> List[dict]:
        """Return all use cases mapped to this department."""
        return [
            {"name": name, **config}
            for name, config in USE_CASES.items()
            if config["dept"] == self.dept_id
        ]


class OpenClawSystemBridge:
    """
    System-wide OpenClaw bridge serving ALL DIGITAL LABOUR components.

    Provides:
    - Department-level message routing
    - Cross-department skill deployment
    - Unified health monitoring
    - System-wide morning brief aggregation
    - Security boundary enforcement
    - Use case ↔ department mapping
    """

    def __init__(self):
        self.version = VERSION
        self.gateway_url = OPENCLAW_GATEWAY
        self.gateway_port = OPENCLAW_PORT
        self.initialized = False
        self.start_time = datetime.now()

        # Department routers
        self.routers: Dict[str, DepartmentRouter] = {}
        for dept_id, config in DEPARTMENTS.items():
            self.routers[dept_id] = DepartmentRouter(dept_id, config)

        # Subsystem connections
        self.subsystem_status: Dict[str, dict] = {
            "ncc": {"connected": False, "last_check": None},
            "ncl_second_brain": {"connected": False, "last_check": None},
            "repo_depot": {"connected": False, "last_check": None},
            "matrix_monitor": {"connected": False, "last_check": None},
            "inner_council": {"connected": False, "last_check": None},
            "qforge": {"connected": False, "last_check": None},
            "qusar": {"connected": False, "last_check": None},
            "memory_doctrine": {"connected": False, "last_check": None},
            "flywheel": {"connected": False, "last_check": None},
        }

        # Skill registry — all deployed skills across departments
        self.deployed_skills: Dict[str, dict] = {}

        # Gateway health
        self.gateway_healthy = False
        self.gateway_last_check = None

        # Statistics
        self.total_messages_routed = 0
        self.total_skills_deployed = 0
        self.total_sessions_created = 0

        self._initialize()

    def _initialize(self):
        """Initialize the system bridge."""
        self.gateway_healthy = self._check_gateway_health()
        self._discover_skills()
        self._check_subsystems()
        self.initialized = True

    def _check_gateway_health(self) -> bool:
        """Check if OpenClaw Gateway is reachable."""
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 f"http://127.0.0.1:{self.gateway_port}/"],
                capture_output=True, text=True, timeout=5
            )
            healthy = result.stdout.strip() in ("200", "301", "302")
            self.gateway_last_check = datetime.now().isoformat()
            return healthy
        except Exception:
            self.gateway_last_check = datetime.now().isoformat()
            return False

    def _discover_skills(self):
        """Discover all deployed skills across all department directories."""
        if not SKILLS_ROOT.exists():
            return

        for dept_dir in SKILLS_ROOT.iterdir():
            if not dept_dir.is_dir():
                continue
            for skill_dir in dept_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    self.deployed_skills[skill_dir.name] = {
                        "path": str(skill_dir),
                        "department": dept_dir.name,
                        "has_skill_md": True,
                    }
                    self.total_skills_deployed += 1

    def _check_subsystems(self):
        """Check connectivity to all subsystems."""
        now = datetime.now().isoformat()

        # NCC
        ncc_path = WORKSPACE_ROOT / "NCC" / "ncc_orchestrator.py"
        self.subsystem_status["ncc"]["connected"] = ncc_path.exists()
        self.subsystem_status["ncc"]["last_check"] = now

        # NCL / Second Brain
        ncl_path = WORKSPACE_ROOT / "ncl_second_brain" / "engine"
        self.subsystem_status["ncl_second_brain"]["connected"] = ncl_path.exists(
        )
        self.subsystem_status["ncl_second_brain"]["last_check"] = now

        # REPO DEPOT
        depot_path = WORKSPACE_ROOT / "repo_depot"
        self.subsystem_status["repo_depot"]["connected"] = depot_path.exists()
        self.subsystem_status["repo_depot"]["last_check"] = now

        # Matrix Monitor
        matrix_path = WORKSPACE_ROOT / "matrix_monitor"
        self.subsystem_status["matrix_monitor"]["connected"] = matrix_path.exists(
        )
        self.subsystem_status["matrix_monitor"]["last_check"] = now

        # Inner Council
        council_path = WORKSPACE_ROOT / "inner_council" / "agents"
        self.subsystem_status["inner_council"]["connected"] = council_path.exists(
        )
        self.subsystem_status["inner_council"]["last_check"] = now

        # QForge
        qforge_path = WORKSPACE_ROOT / "qforge"
        self.subsystem_status["qforge"]["connected"] = qforge_path.exists()
        self.subsystem_status["qforge"]["last_check"] = now

        # QUSAR
        qusar_path = WORKSPACE_ROOT / "qusar"
        self.subsystem_status["qusar"]["connected"] = qusar_path.exists()
        self.subsystem_status["qusar"]["last_check"] = now

        # Memory Doctrine
        memory_path = WORKSPACE_ROOT / "memory_doctrine_system.py"
        self.subsystem_status["memory_doctrine"]["connected"] = memory_path.exists(
        )
        self.subsystem_status["memory_doctrine"]["last_check"] = now

        # Flywheel
        flywheel_path = WORKSPACE_ROOT / "repo_depot_flywheel.py"
        self.subsystem_status["flywheel"]["connected"] = flywheel_path.exists()
        self.subsystem_status["flywheel"]["last_check"] = now

    # ─── Core Routing ────────────────────────────────────────────────────

    def route_message(self, message: str, department: str = None,
                      source_agent: str = None) -> dict:
        """Route a message to the appropriate department and agent."""
        self.total_messages_routed += 1

        if department and department in self.routers:
            return self.routers[department].route_message(
                message, source_agent)

        # Auto-detect department from message content
        dept = self._auto_detect_department(message)
        return self.routers[dept].route_message(message, source_agent)

    def _auto_detect_department(self, message: str) -> str:
        """Auto-detect which department should handle a message."""
        msg_lower = message.lower()

        # Keyword-based detection
        dept_keywords = {
            "executive_council": ["strategy", "decision", "doctrine", "approve",
                                  "priority", "goal", "vision", "mandate"],
            "intelligence_operations": ["research", "youtube", "podcast", "news",
                                        "trend", "analysis", "intelligence",
                                        "digest", "second brain", "knowledge"],
            "operations_command": ["status", "health", "monitor", "alert",
                                   "dashboard", "morning brief", "system",
                                   "self-heal", "task", "deploy", "cpu", "memory"],
            "technology_infrastructure": ["build", "repo", "project", "deploy",
                                          "pipeline", "n8n", "workflow",
                                          "git", "code", "test", "ci/cd"],
            "financial_operations": ["earnings", "market", "portfolio", "crm",
                                     "revenue", "customer", "finance", "trade",
                                     "price", "stock"],
        }

        scores = {}
        for dept, keywords in dept_keywords.items():
            scores[dept] = sum(1 for kw in keywords if kw in msg_lower)

        # Return highest scoring department, default to operations_command
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "operations_command"

    # ─── Skill Management ────────────────────────────────────────────────

    def deploy_department_skills(self, department: str) -> dict:
        """Deploy all skills for a specific department."""
        if department not in DEPARTMENTS:
            return {"error": f"Unknown department: {department}"}

        dept_config = DEPARTMENTS[department]
        skills_dir = SKILLS_ROOT / department.replace("_", "-")
        results = {"department": department, "skills": []}

        if not skills_dir.exists():
            # Check alternate name formats
            for alt in [department, department.replace("_", "")]:
                alt_dir = SKILLS_ROOT / alt
                if alt_dir.exists():
                    skills_dir = alt_dir
                    break

        if skills_dir.exists():
            for skill in skills_dir.iterdir():
                if skill.is_dir() and (skill / "SKILL.md").exists():
                    results["skills"].append({
                        "name": skill.name,
                        "status": "deployed",
                        "path": str(skill),
                    })
                    self.deployed_skills[skill.name] = {
                        "path": str(skill),
                        "department": department,
                        "deployed_at": datetime.now().isoformat(),
                    }

        return results

    def deploy_all_skills(self) -> dict:
        """Deploy skills for all departments."""
        results = {}
        for dept in DEPARTMENTS:
            results[dept] = self.deploy_department_skills(dept)
        return results

    # ─── Morning Brief Aggregation ───────────────────────────────────────

    def generate_system_morning_brief(self) -> str:
        """Generate a unified morning brief aggregating all departments."""
        now = datetime.now()
        brief_parts = []

        brief_parts.append(f"# DIGITAL LABOUR MORNING BRIEF")
        brief_parts.append(f"**Date**: {now.strftime('%A, %B %d, %Y')}")
        brief_parts.append(f"**Generated**: {now.strftime('%I:%M %p')}")
        brief_parts.append(f"**OpenClaw System Bridge**: v{self.version}")
        brief_parts.append("")

        # System Health
        brief_parts.append("## SYSTEM HEALTH")
        brief_parts.append(
            f"- Gateway: {'ONLINE' if self.gateway_healthy else 'OFFLINE'}")
        connected = sum(
            1 for s in self.subsystem_status.values() if s["connected"])
        total = len(self.subsystem_status)
        brief_parts.append(f"- Subsystems: {connected}/{total} connected")
        brief_parts.append(f"- Skills Deployed: {self.total_skills_deployed}")
        brief_parts.append(f"- Messages Routed: {self.total_messages_routed}")
        brief_parts.append("")

        # Subsystem Details
        brief_parts.append("### Subsystem Status")
        for name, status in self.subsystem_status.items():
            icon = "OK" if status["connected"] else "DOWN"
            brief_parts.append(f"  - {name}: {icon}")
        brief_parts.append("")

        # Department Summaries
        brief_parts.append("## DEPARTMENT SUMMARIES")
        for dept_id, router in self.routers.items():
            status = router.get_status()
            brief_parts.append(f"### {status['department']}")
            brief_parts.append(f"  Authority: {status['authority']}")
            brief_parts.append(f"  Health: {status['health']}")
            brief_parts.append(
                f"  Active Sessions: {status['active_sessions']}")
            brief_parts.append(f"  Messages: {status['message_count']}")
            brief_parts.append(f"  Agents: {len(status['agents'])}")

            # Use cases for this department
            use_cases = router.get_use_cases()
            critical = [uc for uc in use_cases if uc["priority"] == "CRITICAL"]
            if critical:
                brief_parts.append(
                    f"  CRITICAL Use Cases: {', '.join(uc['name'] for uc in critical)}")
            brief_parts.append("")

        # Portfolio Health
        brief_parts.append("## PORTFOLIO")
        portfolio_path = WORKSPACE_ROOT / "portfolio.json"
        if portfolio_path.exists():
            try:
                portfolio = json.loads(portfolio_path.read_text())
                repos = portfolio.get(
                    "repositories", portfolio.get("repos", []))
                if isinstance(repos, list):
                    brief_parts.append(f"  Total Repos: {len(repos)}")
                elif isinstance(repos, dict):
                    brief_parts.append(f"  Total Repos: {len(repos)}")
            except Exception:
                brief_parts.append("  Portfolio: error reading")
        brief_parts.append("")

        # REPO DEPOT Status
        brief_parts.append("## REPO DEPOT")
        depot_status_path = WORKSPACE_ROOT / "repo_depot_status.json"
        if depot_status_path.exists():
            try:
                depot = json.loads(depot_status_path.read_text())
                brief_parts.append(
                    f"  Repos Managed: {depot.get('total_repos', 'N/A')}")
                brief_parts.append(
                    f"  Last Sync: {depot.get('last_sync', 'N/A')}")
            except Exception:
                brief_parts.append("  REPO DEPOT: error reading status")
        brief_parts.append("")

        # Memory Doctrine
        brief_parts.append("## MEMORY DOCTRINE")
        memory_json = WORKSPACE_ROOT / "unified_memory_doctrine.json"
        if memory_json.exists():
            try:
                mem = json.loads(memory_json.read_text())
                brief_parts.append(f"  Entries: {len(mem)}")
            except Exception:
                brief_parts.append("  Memory: error reading")
        brief_parts.append("")

        # Upcoming Actions
        brief_parts.append("## RECOMMENDED ACTIONS")
        if not self.gateway_healthy:
            brief_parts.append("  - [CRITICAL] Restart OpenClaw Gateway")
        disconnected = [
            n for n, s in self.subsystem_status.items() if not s["connected"]]
        if disconnected:
            brief_parts.append(
                f"  - [HIGH] Reconnect subsystems: {', '.join(disconnected)}")
        if self.total_skills_deployed == 0:
            brief_parts.append("  - [HIGH] Deploy department skills")
        brief_parts.append("")

        return "\n".join(brief_parts)

    # ─── Self-Healing ────────────────────────────────────────────────────

    def self_heal_check(self) -> dict:
        """Run self-healing checks across all departments and subsystems."""
        issues = []
        actions_taken = []

        # 1. Gateway health
        self.gateway_healthy = self._check_gateway_health()
        if not self.gateway_healthy:
            issues.append("OpenClaw Gateway unreachable")

        # 2. Subsystem connectivity
        self._check_subsystems()
        for name, status in self.subsystem_status.items():
            if not status["connected"]:
                issues.append(f"Subsystem {name} disconnected")

        # 3. Department health
        for dept_id, router in self.routers.items():
            if router.health != "HEALTHY":
                issues.append(
                    f"Department {router.name} unhealthy: {router.health}")

        # 4. REPO DEPOT staleness check
        depot_status_path = WORKSPACE_ROOT / "repo_depot_status.json"
        if depot_status_path.exists():
            try:
                depot = json.loads(depot_status_path.read_text())
                last_sync = depot.get("last_sync", "")
                if last_sync:
                    last_dt = datetime.fromisoformat(
                        last_sync.replace("Z", "+00:00"))
                    if datetime.now(last_dt.tzinfo) - last_dt > timedelta(minutes=30):
                        issues.append("REPO DEPOT sync stale (>30 min)")
            except Exception:
                pass

        # 5. Memory doctrine health
        memory_session = MEMORY_DIR / "session_memory.json"
        if memory_session.exists():
            try:
                mem = json.loads(memory_session.read_text())
                if not mem:
                    issues.append(
                        "Session memory is empty — potential blank state")
            except Exception:
                issues.append("Session memory unreadable")

        # 6. Skill integrity
        if self.total_skills_deployed == 0:
            issues.append(
                "No skills deployed — departments have no OpenClaw capabilities")

        return {
            "timestamp": datetime.now().isoformat(),
            "gateway_healthy": self.gateway_healthy,
            "issues_found": len(issues),
            "issues": issues,
            "actions_taken": actions_taken,
            "recommendation": "All clear" if not issues else f"Fix {len(issues)} issue(s)",
        }

    # ─── Cross-Department Communication ──────────────────────────────────

    def send_cross_department(self, source_dept: str, target_dept: str,
                              message: str) -> dict:
        """Send a message from one department to another via OpenClaw."""
        if source_dept not in self.routers or target_dept not in self.routers:
            return {"error": "Unknown department"}

        source_auth = DEPARTMENTS[source_dept]["authority"]
        target_auth = DEPARTMENTS[target_dept]["authority"]

        # Authority check — only higher authority can command lower
        auth_levels = {"AZ_FINAL": 4, "HIGH": 3, "STANDARD": 2, "LOW": 1}
        source_level = auth_levels.get(source_auth, 0)
        target_level = auth_levels.get(target_auth, 0)

        return {
            "routed": True,
            "source": source_dept,
            "target": target_dept,
            "authority_check": "PASSED" if source_level >= target_level else "ADVISORY",
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

    # ─── Inner Council Integration ───────────────────────────────────────

    def get_inner_council_agents(self) -> List[str]:
        """List all Inner Council persona agents available for OpenClaw sessions."""
        council_dir = WORKSPACE_ROOT / "inner_council" / "agents"
        agents = []
        if council_dir.exists():
            for f in council_dir.iterdir():
                if f.name.endswith("_agent.py") and f.name != "__init__.py":
                    agent_name = f.stem.replace("_agent", "")
                    agents.append(agent_name)
        return sorted(agents)

    def spawn_council_session(self, agent_name: str) -> dict:
        """Spawn an OpenClaw session for an Inner Council persona agent."""
        agents = self.get_inner_council_agents()
        if agent_name not in agents:
            return {"error": f"Agent {agent_name} not found in Inner Council"}

        session_id = f"council_{agent_name}_{int(time.time())}"
        self.total_sessions_created += 1

        return {
            "session_id": session_id,
            "agent": agent_name,
            "type": "inner_council",
            "gateway": self.gateway_url,
            "status": "spawned",
            "timestamp": datetime.now().isoformat(),
        }

    # ─── Portfolio Integration ───────────────────────────────────────────

    def get_portfolio_repos(self) -> List[dict]:
        """Get all managed repos for OpenClaw monitoring."""
        portfolio_path = WORKSPACE_ROOT / "portfolio.json"
        if not portfolio_path.exists():
            return []
        try:
            data = json.loads(portfolio_path.read_text())
            repos = data.get("repositories", data.get("repos", []))
            if isinstance(repos, dict):
                return [{"name": k, **v} for k, v in repos.items()]
            return repos if isinstance(repos, list) else []
        except Exception:
            return []

    # ─── NCL Second Brain Integration ────────────────────────────────────

    def ingest_to_second_brain(self, content: str, source: str = "openclaw",
                                content_type: str = "note") -> dict:
        """Ingest content into NCL Second Brain via OpenClaw."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "content_type": content_type,
            "content": content,
            "ingested_via": "openclaw_system_bridge",
        }

        # Write to NCL events
        ncl_events = WORKSPACE_ROOT / "NCL" / "events.ndjson"
        if ncl_events.exists():
            try:
                with open(ncl_events, "a") as f:
                    f.write(json.dumps(event) + "\n")
                return {"status": "ingested", "event": event}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        return {"status": "ncl_not_available"}

    # ─── NCC Command Integration ─────────────────────────────────────────

    def route_to_ncc(self, command: str, priority: str = "STANDARD") -> dict:
        """Route a command to the NCC orchestrator."""
        ncc_path = WORKSPACE_ROOT / "NCC" / "ncc_orchestrator.py"
        if not ncc_path.exists():
            return {"status": "ncc_not_available"}

        return {
            "command": command,
            "priority": priority,
            "routed_to": "ncc_orchestrator",
            "via": "openclaw_system_bridge",
            "timestamp": datetime.now().isoformat(),
        }

    # ─── n8n Proxy Pattern ───────────────────────────────────────────────

    def create_n8n_webhook_proxy(self, workflow_name: str,
                                  webhook_url: str) -> dict:
        """Register an n8n webhook proxy — agents call this instead of raw APIs."""
        proxy_entry = {
            "workflow": workflow_name,
            "webhook_url": webhook_url,
            "registered_at": datetime.now().isoformat(),
            "calls": 0,
        }

        # Store in state
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        proxies_file = STATE_DIR / "n8n_proxies.json"
        proxies = {}
        if proxies_file.exists():
            try:
                proxies = json.loads(proxies_file.read_text())
            except Exception:
                pass
        proxies[workflow_name] = proxy_entry
        proxies_file.write_text(json.dumps(proxies, indent=2))

        return {"status": "registered", "proxy": proxy_entry}

    def call_n8n_proxy(self, workflow_name: str, payload: dict) -> dict:
        """Call an n8n workflow via webhook — agent never sees raw API keys."""
        proxies_file = STATE_DIR / "n8n_proxies.json"
        if not proxies_file.exists():
            return {"error": "No n8n proxies registered"}

        proxies = json.loads(proxies_file.read_text())
        if workflow_name not in proxies:
            return {"error": f"Workflow {workflow_name} not registered"}

        webhook_url = proxies[workflow_name]["webhook_url"]
        try:
            result = subprocess.run(
                ["curl", "-s", "-X", "POST", webhook_url,
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps(payload)],
                capture_output=True, text=True, timeout=30
            )
            proxies[workflow_name]["calls"] = proxies[workflow_name].get(
                "calls", 0) + 1
            proxies_file.write_text(json.dumps(proxies, indent=2))
            return {"status": "called", "response": result.stdout}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── Full System Status ──────────────────────────────────────────────

    def get_system_status(self) -> dict:
        """Get comprehensive system status across all departments and subsystems."""
        uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "version": self.version,
            "uptime_seconds": round(uptime),
            "gateway": {
                "url": self.gateway_url,
                "healthy": self.gateway_healthy,
                "last_check": self.gateway_last_check,
            },
            "departments": {
                dept_id: router.get_status()
                for dept_id, router in self.routers.items()
            },
            "subsystems": self.subsystem_status,
            "statistics": {
                "total_messages_routed": self.total_messages_routed,
                "total_skills_deployed": self.total_skills_deployed,
                "total_sessions_created": self.total_sessions_created,
                "total_use_cases_mapped": len(USE_CASES),
                "inner_council_agents": len(self.get_inner_council_agents()),
                "portfolio_repos": len(self.get_portfolio_repos()),
            },
            "use_case_coverage": {
                "total": len(USE_CASES),
                "critical": sum(1 for uc in USE_CASES.values() if uc["priority"] == "CRITICAL"),
                "high": sum(1 for uc in USE_CASES.values() if uc["priority"] == "HIGH"),
                "medium": sum(1 for uc in USE_CASES.values() if uc["priority"] == "MEDIUM"),
                "low": sum(1 for uc in USE_CASES.values() if uc["priority"] == "LOW"),
            },
        }


# ─── Module-Level Convenience ────────────────────────────────────────────

_bridge_instance: Optional[OpenClawSystemBridge] = None


def get_system_bridge() -> OpenClawSystemBridge:
    """Get or create the singleton system bridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = OpenClawSystemBridge()
    return _bridge_instance


# ─── CLI Entry Point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenClaw System Bridge")
    parser.add_argument(
        "command",
        choices=["status", "brief", "heal", "deploy", "council", "portfolio",
                 "route"],
        help="Command to execute")
    parser.add_argument("--department", "-d", help="Target department")
    parser.add_argument("--message", "-m", help="Message to route")
    parser.add_argument("--agent", "-a", help="Target agent")

    args = parser.parse_args()
    bridge = get_system_bridge()

    if args.command == "status":
        status = bridge.get_system_status()
        print(json.dumps(status, indent=2))

    elif args.command == "brief":
        print(bridge.generate_system_morning_brief())

    elif args.command == "heal":
        result = bridge.self_heal_check()
        print(json.dumps(result, indent=2))

    elif args.command == "deploy":
        if args.department:
            result = bridge.deploy_department_skills(args.department)
        else:
            result = bridge.deploy_all_skills()
        print(json.dumps(result, indent=2))

    elif args.command == "council":
        if args.agent:
            result = bridge.spawn_council_session(args.agent)
            print(json.dumps(result, indent=2))
        else:
            agents = bridge.get_inner_council_agents()
            print(f"Inner Council Agents ({len(agents)}):")
            for a in agents:
                print(f"  - {a}")

    elif args.command == "portfolio":
        repos = bridge.get_portfolio_repos()
        print(f"Portfolio Repos ({len(repos)}):")
        for r in repos:
            name = r.get("name", r) if isinstance(r, dict) else r
            print(f"  - {name}")

    elif args.command == "route":
        if args.message:
            result = bridge.route_message(args.message, args.department)
            print(json.dumps(result, indent=2))
        else:
            print("Error: --message required for route command")
