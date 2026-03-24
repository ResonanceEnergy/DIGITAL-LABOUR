#!/usr/bin/env python3
"""
Agent Hierarchy & Delegation Framework
========================================
Defines the formal agent hierarchy, capability registry,
and task routing for the Bit Rage Systems multi-agent system.

Hierarchy tiers:
  T0 — Strategic: CEO, Inner Council
  T1 — Executive: CTO, CFO, CMO, CIO
  T2 — Management: Orchestrator, Scheduler, Brain
  T3 — Operational: Sentry, Intel, Metrics, Validators
  T4 — Support: Bus, Backup, Cost Tracker

Provides:
- Hierarchical task delegation with authority checks
- Capability-based agent discovery and routing
- Load-aware task assignment
- Chain-of-command escalation
- Agent lifecycle management (register, deregister, status)

Usage::

    from agents.hierarchy import (
        AgentRegistry, TaskRouter, Hierarchy,
    )
    registry = AgentRegistry()
    registry.register("repo_sentry", tier=3,
                       capabilities=["scan", "delta"])
    router = TaskRouter(registry)
    agent = router.route("scan", priority=2)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
HIERARCHY_DIR = ROOT / "data" / "hierarchy"
HIERARCHY_DIR.mkdir(parents=True, exist_ok=True)


# ── Message bus (best-effort) ──────────────────────────────┐
_bus: Any = None
try:
    from agents.message_bus import bus
    _bus = bus
except Exception:
    pass


def _emit(
    topic: str,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    if _bus:
        _bus.publish(  # type: ignore[union-attr]
            topic,
            payload or {},
            source="hierarchy",
        )
# ──────────────────────────────────────────────────────────┘


# ═══════════════════════════════════════════════════════════════
#  TIER DEFINITIONS
# ═══════════════════════════════════════════════════════════════

TIER_NAMES: dict[int, str] = {
    0: "Strategic",
    1: "Executive",
    2: "Management",
    3: "Operational",
    4: "Support",
}

# Default agent-to-tier mapping
DEFAULT_ASSIGNMENTS: dict[str, int] = {
    # T0 — Strategic
    "ceo": 0,
    "inner_council": 0,
    # T1 — Executive (includes DL CEO)
    "cto": 1,
    "cfo": 1,
    "cmo": 1,
    "cio": 1,
    "axiom_ceo": 1,  # DL CEO — Strategic Growth
    # T2 — Management (includes DL COO/CFO + Dispatcher)
    "orchestrator": 2,
    "research_scheduler": 2,
    "autonomous_brain": 2,
    "research_intelligence": 2,
    "alignment_monitor": 2,
    "learning_agent": 2,
    "context_manager_agent": 2,
    "qa_manager": 2,
    "production_manager": 2,
    "automation_manager": 2,
    "vectis_coo": 2,  # DL COO — Ops & Quality
    "ledgr_cfo": 2,  # DL CFO — Revenue & Margins
    "dl_dispatcher": 2,  # DL task routing + budget
    # T3 — Operational (includes DL worker agents + NERVE)
    "repo_sentry": 3,
    "portfolio_intel": 3,
    "research_metrics": 3,
    "gap_analyzer": 3,
    "self_check_validator": 3,
    "idea_engine": 3,
    "topic_index": 3,
    "intelligence_products": 3,
    "dl_nerve": 3,  # DL autonomous daemon
    # DL worker agents (all T3 — revenue producers)
    "dl_sales_ops": 3,
    "dl_support": 3,
    "dl_content_repurpose": 3,
    "dl_doc_extract": 3,
    "dl_ad_copy": 3,
    "dl_email_marketing": 3,
    "dl_seo_content": 3,
    "dl_social_media": 3,
    "dl_lead_gen": 3,
    "dl_web_scraper": 3,
    "dl_market_research": 3,
    "dl_press_release": 3,
    "dl_product_desc": 3,
    "dl_proposal_writer": 3,
    "dl_resume_writer": 3,
    "dl_tech_docs": 3,
    "dl_freelancer_work": 3,
    "dl_crm_ops": 3,
    "dl_bookkeeping": 3,
    "dl_data_entry": 3,
    "dl_business_plan": 3,
    # T4 — Support (includes DL intake API)
    "bus_subscribers": 4,
    "memory_backup": 4,
    "api_cost_tracker": 4,
    "skill_registry": 4,
    "dl_intake_api": 4,  # DL client-facing webhook
}


# ═══════════════════════════════════════════════════════════════
#  AGENT REGISTRATION
# ═══════════════════════════════════════════════════════════════

@dataclass
class AgentRecord:
    name: str
    tier: int
    capabilities: list[str] = field(
        default_factory=list,
    )
    status: str = "active"
    registered_at: str = field(
        default_factory=lambda: datetime.now().isoformat(),
    )
    last_heartbeat: Optional[str] = None
    load: float = 0.0  # 0.0 = idle, 1.0 = fully loaded
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tier": self.tier,
            "tier_name": TIER_NAMES.get(
                self.tier, "Unknown",
            ),
            "capabilities": self.capabilities,
            "status": self.status,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "load": self.load,
            "metadata": self.metadata,
        }


class AgentRegistry:
    """Central registry of all agents in the system."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentRecord] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        for name, tier in DEFAULT_ASSIGNMENTS.items():
            self._agents[name] = AgentRecord(
                name=name, tier=tier,
            )

    def register(
        self,
        name: str,
        tier: int = 3,
        capabilities: Optional[list[str]] = None,
        **meta: Any,
    ) -> None:
        self._agents[name] = AgentRecord(
            name=name,
            tier=tier,
            capabilities=capabilities or [],
            metadata=dict(meta),
        )
        _emit("hierarchy.agent.registered", {
            "agent": name, "tier": tier,
        })
        logger.info(
            "[Hierarchy] Registered %s at tier %d",
            name, tier,
        )

    def deregister(self, name: str) -> None:
        if name in self._agents:
            del self._agents[name]
            _emit("hierarchy.agent.deregistered", {
                "agent": name,
            })

    def heartbeat(self, name: str, load: float = 0.0) -> None:
        if name in self._agents:
            rec = self._agents[name]
            rec.last_heartbeat = (
                datetime.now().isoformat()
            )
            rec.load = max(0.0, min(1.0, load))

    def get(self, name: str) -> Optional[AgentRecord]:
        return self._agents.get(name)

    def by_tier(self, tier: int) -> list[AgentRecord]:
        return [
            a for a in self._agents.values()
            if a.tier == tier and a.status == "active"
        ]

    def by_capability(
        self,
        capability: str,
    ) -> list[AgentRecord]:
        return [
            a for a in self._agents.values()
            if capability in a.capabilities
            and a.status == "active"
        ]

    def all_agents(self) -> list[AgentRecord]:
        return list(self._agents.values())

    def snapshot(self) -> dict[str, Any]:
        tiers: dict[str, list[str]] = {}
        for tier_id, tier_name in TIER_NAMES.items():
            tiers[tier_name] = [
                a.name for a in self.by_tier(tier_id)
            ]
        return {
            "ts": datetime.now().isoformat(),
            "total_agents": len(self._agents),
            "tiers": tiers,
            "agents": {
                n: a.to_dict()
                for n, a in self._agents.items()
            },
        }

    def save(
        self,
        path: Optional[Path] = None,
    ) -> Path:
        dest = path or (
            HIERARCHY_DIR / "registry.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(self.snapshot(), indent=2),
            encoding="utf-8",
        )
        return dest


# ═══════════════════════════════════════════════════════════════
#  TASK ROUTER  — capability + load-aware routing
# ═══════════════════════════════════════════════════════════════

@dataclass
class TaskAssignment:
    task_type: str
    agent: str
    tier: int
    reason: str
    assigned_at: str = field(
        default_factory=lambda: datetime.now().isoformat(),
    )


class TaskRouter:
    """Routes tasks to the best-suited agent based on
    capability match, tier authority, and current load."""

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry
        self._history: list[TaskAssignment] = []

    def route(
        self,
        task_type: str,
        min_tier: int = 4,
        max_tier: int = 0,
        prefer_idle: bool = True,
    ) -> Optional[TaskAssignment]:
        """Find the best agent for a task.

        Args:
            task_type: capability/task name to match
            min_tier: lowest tier allowed (4=support)
            max_tier: highest tier allowed (0=strategic)
            prefer_idle: prefer agents with lower load
        """
        candidates = self._registry.by_capability(
            task_type,
        )
        # Filter by tier range
        candidates = [
            a for a in candidates
            if max_tier <= a.tier <= min_tier
        ]

        if not candidates:
            # Fallback: find any active agent in tier range
            for tier in range(min_tier, max_tier - 1, -1):
                tier_agents = self._registry.by_tier(tier)
                if tier_agents:
                    candidates = tier_agents[:1]
                    break

        if not candidates:
            return None

        if prefer_idle:
            candidates.sort(key=lambda a: a.load)

        chosen = candidates[0]
        assignment = TaskAssignment(
            task_type=task_type,
            agent=chosen.name,
            tier=chosen.tier,
            reason=(
                f"Matched capability '{task_type}' "
                f"at tier {chosen.tier} "
                f"(load={chosen.load:.1f})"
            ),
        )
        self._history.append(assignment)
        _emit("hierarchy.task.routed", {
            "task": task_type,
            "agent": chosen.name,
            "tier": chosen.tier,
        })
        return assignment

    def escalate(
        self,
        task_type: str,
        from_agent: str,
        reason: str = "",
    ) -> Optional[TaskAssignment]:
        """Escalate a task to a higher-tier agent."""
        current = self._registry.get(from_agent)
        if not current:
            return None
        higher_tier = current.tier - 1
        if higher_tier < 0:
            logger.warning(
                "[Hierarchy] Cannot escalate above T0",
            )
            return None

        return self.route(
            task_type,
            min_tier=higher_tier,
            max_tier=0,
        )

    def recent_assignments(
        self,
        n: int = 20,
    ) -> list[dict[str, Any]]:
        return [
            {
                "task": a.task_type,
                "agent": a.agent,
                "tier": a.tier,
                "reason": a.reason,
                "at": a.assigned_at,
            }
            for a in self._history[-n:]
        ]


# ═══════════════════════════════════════════════════════════════
#  CONVENIENCE — singleton instances
# ═══════════════════════════════════════════════════════════════

_registry: Optional[AgentRegistry] = None
_router: Optional[TaskRouter] = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def get_router() -> TaskRouter:
    global _router
    if _router is None:
        _router = TaskRouter(get_registry())
    return _router
