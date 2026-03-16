#!/usr/bin/env python3
"""
OpenClaw Skill Registration Pipeline.

Agents declare their capabilities. Each agent can call
``register(name, description, capabilities)`` at init.
The registry is persisted to ``config/skill_registry.json``
and can be published to the OpenClaw gateway when available.

Usage from any agent::

    from tools.skill_registry import register, get_registry

    register(
        "repo_sentry",
        "Repository monitoring",
        ["scan", "delta_plan", "health_check"],
    )
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "config" / "skill_registry.json"


def _load() -> dict[str, Any]:
    if REGISTRY_PATH.exists():
        try:
            return json.loads(
                REGISTRY_PATH.read_text(encoding="utf-8"),
            )
        except (json.JSONDecodeError, OSError):
            pass
    return {"agents": {}, "updated_at": None}


def _save(registry: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = datetime.now().isoformat()
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def register(
    agent_name: str,
    description: str,
    capabilities: list[str],
) -> dict[str, Any]:
    """Register an agent's capabilities."""
    reg = _load()
    reg["agents"][agent_name] = {
        "description": description,
        "capabilities": capabilities,
        "registered_at": datetime.now().isoformat(),
    }
    _save(reg)
    return reg["agents"][agent_name]


def unregister(agent_name: str) -> bool:
    """Remove an agent from the registry."""
    reg = _load()
    if agent_name in reg["agents"]:
        del reg["agents"][agent_name]
        _save(reg)
        return True
    return False


def get_registry() -> dict[str, Any]:
    """Return the full skill registry."""
    return _load()


def find_capability(capability: str) -> list[dict[str, Any]]:
    """Find agents that offer a given capability."""
    reg = _load()
    results = []
    cap_lower = capability.lower()
    for name, info in reg.get("agents", {}).items():
        if any(cap_lower in c.lower() for c in info.get("capabilities", [])):
            results.append({"agent": name, **info})
    return results


# ── Default registrations (core agents) ─────────────────────────────────

_CORE_AGENTS = {
    "repo_sentry": {
        "description": "Repository health monitoring",
        "capabilities": [
            "scan", "delta_plan",
            "health_check", "branch_audit",
        ],
    },
    "daily_brief": {
        "description": "Daily operational briefings",
        "capabilities": [
            "brief_generation",
            "intelligence_digest",
            "error_summary",
        ],
    },
    "council": {
        "description": "Executive council decisions",
        "capabilities": [
            "proposal_vote",
            "risk_assessment",
            "graduation_decision",
        ],
    },
    "portfolio_autotier": {
        "description": "Portfolio classification",
        "capabilities": [
            "tier_assignment",
            "risk_scoring",
            "autonomy_graduation",
        ],
    },
    "portfolio_selfheal": {
        "description": "Self-healing portfolio maintenance",
        "capabilities": [
            "ci_fix", "dependency_check",
            "license_audit", "fix_proposal",
        ],
    },
    "gasket": {
        "description": "QUSAR and OpenClaw bridge",
        "capabilities": [
            "gateway_bridge",
            "memory_doctrine",
            "cpu_optimization",
        ],
    },
    "intelligence_scheduler": {
        "description": "YouTube watchlist scheduler",
        "capabilities": [
            "youtube_ingest",
            "watchlist_scan",
            "queue_management",
        ],
    },
    "memory_backup": {
        "description": "Memory backup and health monitoring",
        "capabilities": [
            "backup", "blank_detection",
            "consolidation",
        ],
    },
}


def bootstrap_core() -> int:
    """Register all core agents. Returns count."""
    for name, info in _CORE_AGENTS.items():
        register(
            name,
            str(info["description"]),
            list(info["capabilities"]),
        )
    return len(_CORE_AGENTS)


if __name__ == "__main__":
    n = bootstrap_core()
    reg = get_registry()
    print(f"Registered {n} core agents ({reg['updated_at']})")
    for name, info in reg["agents"].items():
        print(f"  {name}: {', '.join(info['capabilities'])}")
