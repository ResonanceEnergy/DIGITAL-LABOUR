#!/usr/bin/env python3
"""
Context Manager Agent — BIT RAGE LABOUR
=========================================
T2 Management agent responsible for maintaining
operational context across all agent sessions,
memory doctrine enforcement, and cross-agent
context propagation.

Authority:
- Manages shared context windows for all T3/T4 agents
- Enforces context freshness SLAs
- Triggers context compression when limits are hit
- Owns the context bus namespace

Reports to: CTO (T1)
Manages: memory_backup (T4), bus_subscribers (T4)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CTX_DIR = ROOT / "data" / "context_manager"
CTX_DIR.mkdir(parents=True, exist_ok=True)

# ── Message bus (best-effort) ──────────────────
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
            source="context_manager_agent",
        )


class ContextManagerAgent:
    """Manages shared context, freshness, and
    cross-agent context propagation."""

    FRESHNESS_SLA_SECONDS = 3600  # 1 hour
    MAX_CONTEXT_ITEMS = 500

    def __init__(self) -> None:
        self._cycle = 0
        self._contexts: dict[str, dict[str, Any]] = {}
        self._load_state()

    # ── Persistence ────────────────────────────
    def _state_path(self) -> Path:
        return CTX_DIR / "context_state.json"

    def _load_state(self) -> None:
        p = self._state_path()
        if p.exists():
            try:
                data = json.loads(
                    p.read_text(encoding="utf-8"),
                )
                self._contexts = data.get(
                    "contexts", {},
                )
                self._cycle = data.get("cycle", 0)
            except (json.JSONDecodeError, OSError):
                pass

    def _save_state(self) -> None:
        self._state_path().write_text(
            json.dumps(
                {
                    "cycle": self._cycle,
                    "contexts": self._contexts,
                    "saved_at": datetime.now().isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # ── Context Operations ─────────────────────
    def set_context(
        self,
        agent: str,
        key: str,
        value: Any,
    ) -> None:
        """Set a context value for an agent."""
        if agent not in self._contexts:
            self._contexts[agent] = {}
        self._contexts[agent][key] = {
            "value": value,
            "updated_at": datetime.now().isoformat(),
        }

    def get_context(
        self,
        agent: str,
        key: Optional[str] = None,
    ) -> Any:
        """Get context for an agent (all or by key)."""
        ctx = self._contexts.get(agent, {})
        if key:
            entry = ctx.get(key)
            return entry["value"] if entry else None
        return {
            k: v["value"] for k, v in ctx.items()
        }

    def _check_freshness(self) -> dict[str, Any]:
        """Check all contexts for staleness."""
        now = time.time()
        stale: list[str] = []
        fresh = 0
        total = 0

        for agent, items in self._contexts.items():
            for key, entry in items.items():
                total += 1
                try:
                    updated = datetime.fromisoformat(
                        entry["updated_at"],
                    )
                    age = now - updated.timestamp()
                    if age > self.FRESHNESS_SLA_SECONDS:
                        stale.append(f"{agent}.{key}")
                    else:
                        fresh += 1
                except (KeyError, ValueError):
                    stale.append(f"{agent}.{key}")

        return {
            "total": total,
            "fresh": fresh,
            "stale_count": len(stale),
            "stale_keys": stale[:20],
        }

    def _check_memory_doctrine(self) -> dict[str, Any]:
        """Verify memory doctrine files exist and
        are not blank."""
        checks: dict[str, Any] = {}
        doctrine_files = [
            ROOT / "memory_doctrine_system.py",
            ROOT / "unified_memory_doctrine.json",
        ]
        for f in doctrine_files:
            name = f.name
            if not f.exists():
                checks[name] = "missing"
            elif f.stat().st_size < 10:
                checks[name] = "blank"
            else:
                checks[name] = "ok"

        return {
            "files_checked": len(doctrine_files),
            "results": checks,
            "all_ok": all(
                v == "ok" for v in checks.values()
            ),
        }

    def _compress_if_needed(self) -> dict[str, Any]:
        """Compress context if over limit."""
        total = sum(
            len(items)
            for items in self._contexts.values()
        )
        if total <= self.MAX_CONTEXT_ITEMS:
            return {
                "action": "none",
                "items": total,
            }

        # Remove oldest entries first
        entries: list[tuple[str, str, str]] = []
        for agent, items in self._contexts.items():
            for key, entry in items.items():
                entries.append((
                    entry.get("updated_at", ""),
                    agent,
                    key,
                ))
        entries.sort()
        to_remove = total - self.MAX_CONTEXT_ITEMS
        removed = 0
        for _, agent, key in entries[:to_remove]:
            del self._contexts[agent][key]
            removed += 1

        return {
            "action": "compressed",
            "removed": removed,
            "remaining": total - removed,
        }

    # ── Main Cycle ─────────────────────────────
    def run_cycle(self) -> dict[str, Any]:
        """Run a full context management cycle."""
        self._cycle += 1
        t0 = time.monotonic()

        freshness = self._check_freshness()
        doctrine = self._check_memory_doctrine()
        compression = self._compress_if_needed()

        self._save_state()

        elapsed = round(time.monotonic() - t0, 3)
        report = {
            "cycle": self._cycle,
            "timestamp": datetime.now().isoformat(),
            "freshness": freshness,
            "memory_doctrine": doctrine,
            "compression": compression,
            "elapsed_s": elapsed,
        }

        _emit("context.manager.cycle", {
            "cycle": self._cycle,
            "stale": freshness["stale_count"],
            "doctrine_ok": doctrine["all_ok"],
        })

        if freshness["stale_count"] > 0:
            _emit("context.manager.stale_alert", {
                "stale_count": freshness["stale_count"],
            })
            logger.warning(
                "[CTX_MGR] %d stale context entries",
                freshness["stale_count"],
            )

        logger.info(
            "[CTX_MGR] Cycle %d complete "
            "(%.3fs, %d items, %d stale)",
            self._cycle,
            elapsed,
            freshness["total"],
            freshness["stale_count"],
        )

        return report
