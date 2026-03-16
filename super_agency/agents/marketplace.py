#!/usr/bin/env python3
"""
Agent Marketplace — plugin-based agent discovery and registration system.

New agents can be added by:
1. Creating a Python file in agents/plugins/
2. Implementing the AgentPlugin interface (execute, name, description)
3. The marketplace auto-discovers and registers them at startup

Usage::

    python agents/marketplace.py list           # list available agents
    python agents/marketplace.py run <agent>    # run a specific agent
    python agents/marketplace.py info <agent>   # show agent details
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.common import Log, ensure_dir, now_iso  # noqa: E402

PLUGINS_DIR = Path(__file__).resolve().parent / "plugins"
REGISTRY_FILE = ROOT / "config" / "agent_registry.json"
ensure_dir(PLUGINS_DIR)
ensure_dir(REGISTRY_FILE.parent)


# ── Plugin Interface ─────────────────────────────────────────────────────

class AgentPlugin(ABC):
    """Base class for marketplace agent plugins.

    To create a new agent:
    1. Create a file in agents/plugins/ (e.g., my_agent.py)
    2. Define a class that inherits from AgentPlugin
    3. Implement name, description, and execute()
    4. The marketplace will auto-discover it
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique agent name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of what this agent does."""

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        """List of capability tags (e.g., 'analysis', 'monitoring')."""
        return []

    @abstractmethod
    def execute(
        self, task: str, context: dict | None = None,
    ) -> dict[str, Any]:
        """Execute a task and return results.

        Returns:
            Standard result dict: {task, result, agent, timestamp, status}
        """

    def health_check(self) -> bool:
        """Optional health check. Override if your agent has dependencies."""
        return True


# ── Plugin Discovery ─────────────────────────────────────────────────────

_registry: dict[str, AgentPlugin] = {}
_discovery_done = False


def _discover_plugins() -> dict[str, AgentPlugin]:
    """Scan agents/plugins/ for AgentPlugin subclasses."""
    global _discovery_done
    if _discovery_done:
        return _registry

    if not PLUGINS_DIR.is_dir():
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        # Create example plugin
        _create_example_plugin()
        _discovery_done = True
        return _registry

    for py_file in sorted(PLUGINS_DIR.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                f"agents.plugins.{py_file.stem}", str(py_file),
            )
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Find AgentPlugin subclasses
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, AgentPlugin)
                    and attr is not AgentPlugin
                ):
                    try:
                        instance = attr()
                        _registry[instance.name] = instance
                        Log.info(
                            f"[Marketplace] Registered: "
                            f"{instance.name} v{instance.version}"
                        )
                    except Exception as exc:
                        Log.error(
                            f"[Marketplace] Failed to "
                            f"instantiate {attr_name}: {exc}"
                        )
        except Exception as exc:
            Log.error(f"[Marketplace] Failed to load {py_file.name}: {exc}")

    _discovery_done = True
    _save_registry()
    return _registry


def _save_registry():
    """Persist the registry to disk for status endpoints."""
    data = {
        "agents": {
            name: {
                "name": agent.name,
                "description": agent.description,
                "version": agent.version,
                "capabilities": agent.capabilities,
                "healthy": agent.health_check(),
            }
            for name, agent in _registry.items()
        },
        "total": len(_registry),
        "updated_at": now_iso(),
    }
    REGISTRY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _create_example_plugin():
    """Create an example plugin as a template."""
    example = PLUGINS_DIR / "example_agent.py"
    if example.exists():
        return
    example.write_text('''#!/usr/bin/env python3
"""Example agent plugin — template for creating new agents."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.marketplace import AgentPlugin
from agents.common import now_iso


class ExampleAgent(AgentPlugin):
    @property
    def name(self) -> str:
        return "example"

    @property
    def description(self) -> str:
        return "Example agent that echoes tasks back — use as a template"

    @property
    def capabilities(self) -> list[str]:
        return ["echo", "testing"]

    def execute(self, task: str, context: dict | None = None) -> dict:
        return {
            "task": task,
            "result": f"Echo: {task}",
            "agent": self.name,
            "timestamp": now_iso(),
            "status": "success",
        }
''', encoding="utf-8")
    Log.info("[Marketplace] Created example plugin template")


# ── Public API ───────────────────────────────────────────────────────────

def list_agents() -> list[dict]:
    """List all registered agents."""
    agents = _discover_plugins()
    return [
        {
            "name": a.name,
            "description": a.description,
            "version": a.version,
            "capabilities": a.capabilities,
            "healthy": a.health_check(),
        }
        for a in agents.values()
    ]


def get_agent(name: str) -> AgentPlugin | None:
    """Get a registered agent by name."""
    agents = _discover_plugins()
    return agents.get(name)


def run_agent(
    name: str, task: str, context: dict | None = None,
) -> dict[str, Any]:
    """Run a registered agent by name."""
    agent = get_agent(name)
    if agent is None:
        return {
            "task": task, "status": "error",
            "result": f"Agent '{name}' not found",
            "agent": name, "timestamp": now_iso(),
        }

    if not agent.health_check():
        return {
            "task": task, "status": "error",
            "result": (
                f"Agent '{name}' health check failed"
            ),
            "agent": name, "timestamp": now_iso(),
        }

    try:
        return agent.execute(task, context)
    except Exception as exc:
        return {"task": task, "status": "error", "result": str(exc),
                "agent": name, "timestamp": now_iso()}


def register_agent(agent: AgentPlugin):
    """Manually register an agent plugin."""
    _registry[agent.name] = agent
    _save_registry()
    Log.info(f"[Marketplace] Manually registered: {agent.name}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

    if cmd == "list":
        agents = list_agents()
        print(f"\nAgent Marketplace: {len(agents)} agents registered\n")
        for a in agents:
            health = "OK" if a["healthy"] else "UNHEALTHY"
            print(f"  {a['name']} v{a['version']} [{health}]")
            print(f"    {a['description']}")
            if a["capabilities"]:
                print(f"    Capabilities: {', '.join(a['capabilities'])}")
            print()

    elif cmd == "run" and len(sys.argv) > 2:
        agent_name = sys.argv[2]
        task = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "default task"
        result = run_agent(agent_name, task)
        print(json.dumps(result, indent=2))

    elif cmd == "info" and len(sys.argv) > 2:
        agent = get_agent(sys.argv[2])
        if agent:
            print(f"Name: {agent.name}")
            print(f"Version: {agent.version}")
            print(f"Description: {agent.description}")
            print(f"Capabilities: {', '.join(agent.capabilities)}")
            print(f"Healthy: {agent.health_check()}")
        else:
            print(f"Agent '{sys.argv[2]}' not found")

    else:
        print("Usage: marketplace.py [list|run <agent> [task]|info <agent>]")
