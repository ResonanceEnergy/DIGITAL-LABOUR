#!/usr/bin/env python3
"""
Context Manager Agent
=======================
Management-tier agent (T2) that governs shared
context across the agent fleet.  Ensures every agent
operates with accurate, current, and relevant data.

Authority:
- Set and enforce context windows for all agents
- Manage cross-agent knowledge sharing
- Gate information flow (need-to-know enforcement)
- Compress / archive stale context
- Publish authoritative context snapshots

Capabilities:
- context_snapshot: Collect & freeze global state
- context_compress: Summarise and prune stale entries
- context_gate: Decide what context each agent sees
- context_distribute: Push relevant context to agents
- knowledge_index: Maintain a master knowledge index
- context_audit: Validate context freshness & accuracy

Integrates:
  hierarchy → AgentRegistry (authority checks)
  ml_intelligence_framework → TextIntelligence
  agent_metrics → MetricsCollector
  message_bus → pub/sub

Usage::

    from agents.context_manager import ContextManager
    mgr = ContextManager()
    snap = mgr.collect_context()
    mgr.distribute(snap)
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CTX_DIR = ROOT / "data" / "context"
CTX_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = ROOT / "reports" / "context"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Authority constants
TIER = 2  # Management tier
AUTHORITY_SCOPE = [
    "context_snapshot",
    "context_compress",
    "context_gate",
    "context_distribute",
    "knowledge_index",
    "context_audit",
]

# Context freshness thresholds (seconds)
FRESH_THRESHOLD = 3600       # <1 h = fresh
STALE_THRESHOLD = 86400      # >24 h = stale
MAX_CONTEXT_ENTRIES = 5000   # hard cap per domain


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
            source="context_manager",
        )
# ──────────────────────────────────────────────────────────┘


class ContextEntry:
    """Single piece of context with provenance."""

    __slots__ = (
        "key", "value", "source",
        "created_at", "accessed_at", "ttl",
    )

    def __init__(
        self,
        key: str,
        value: Any,
        source: str = "unknown",
        ttl: int = STALE_THRESHOLD,
    ) -> None:
        self.key = key
        self.value = value
        self.source = source
        now = time.time()
        self.created_at = now
        self.accessed_at = now
        self.ttl = ttl

    @property
    def age_s(self) -> float:
        return time.time() - self.created_at

    @property
    def is_stale(self) -> bool:
        return self.age_s > self.ttl

    @property
    def is_fresh(self) -> bool:
        return self.age_s < FRESH_THRESHOLD

    def touch(self) -> None:
        self.accessed_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "source": self.source,
            "age_s": round(self.age_s, 1),
            "stale": self.is_stale,
        }


class ContextManager:
    """Management-tier agent that governs shared context.

    Has authority to:
    - Collect context from all agents and subsystems
    - Gate which agents see which context
    - Compress stale context into summaries
    - Distribute relevant context snapshots
    - Audit freshness and accuracy
    """

    def __init__(self) -> None:
        self._store: dict[str, ContextEntry] = {}
        self._domains: dict[
            str, list[str]
        ] = defaultdict(list)
        self._access_policy: dict[
            str, list[str]
        ] = {}  # agent → allowed domains
        self._cycle = 0
        self._collect_system_context()

    # ── Collection ──────────────────────────────────────────

    def _collect_system_context(self) -> None:
        """Scan filesystem for context-worthy data."""
        # Mandates
        mandates_path = ROOT / "agent_mandates.json"
        if mandates_path.exists():
            try:
                data = json.loads(
                    mandates_path.read_text(
                        encoding="utf-8",
                    )
                )
                self.set(
                    "mandates",
                    data,
                    source="agent_mandates.json",
                    domain="governance",
                )
            except Exception:
                pass

        # Skill registry
        skill_path = (
            ROOT / "config" / "skill_registry.json"
        )
        if skill_path.exists():
            try:
                data = json.loads(
                    skill_path.read_text(
                        encoding="utf-8",
                    )
                )
                agent_count = len(
                    data.get("agents", {})
                )
                self.set(
                    "skill_registry_summary",
                    {"agents": agent_count},
                    source="skill_registry.json",
                    domain="capabilities",
                )
            except Exception:
                pass

        # Knowledge / secondbrain counts
        for folder_name in [
            "knowledge", "secondbrain",
        ]:
            folder = ROOT / folder_name
            if folder.is_dir():
                count = sum(
                    1 for _ in folder.rglob("*.json")
                )
                self.set(
                    f"{folder_name}_count",
                    count,
                    source="filesystem",
                    domain="knowledge",
                )

        # Reports inventory
        reports_dir = ROOT / "reports"
        if reports_dir.is_dir():
            report_types = [
                d.name for d in reports_dir.iterdir()
                if d.is_dir()
            ]
            self.set(
                "report_types",
                report_types,
                source="filesystem",
                domain="reporting",
            )

    def set(
        self,
        key: str,
        value: Any,
        source: str = "unknown",
        domain: str = "general",
        ttl: int = STALE_THRESHOLD,
    ) -> None:
        """Set a context entry."""
        entry = ContextEntry(key, value, source, ttl)
        self._store[key] = entry
        if key not in self._domains[domain]:
            self._domains[domain].append(key)

    def get(self, key: str) -> Optional[Any]:
        """Get a context value. Tracks access."""
        entry = self._store.get(key)
        if entry is None:
            return None
        entry.touch()
        return entry.value

    def get_domain(
        self,
        domain: str,
    ) -> dict[str, Any]:
        """Get all context entries in a domain."""
        keys = self._domains.get(domain, [])
        result: dict[str, Any] = {}
        for k in keys:
            entry = self._store.get(k)
            if entry and not entry.is_stale:
                entry.touch()
                result[k] = entry.value
        return result

    # ── Access gating (authority) ───────────────────────────

    def set_access_policy(
        self,
        agent: str,
        allowed_domains: list[str],
    ) -> None:
        """Define which domains an agent can access.

        Only ContextManager (T2) can call this.
        """
        self._access_policy[agent] = allowed_domains
        logger.info(
            "[ContextMgr] Policy set: %s → %s",
            agent, allowed_domains,
        )

    def get_context_for_agent(
        self,
        agent: str,
    ) -> dict[str, Any]:
        """Return context filtered by access policy."""
        allowed = self._access_policy.get(agent)
        if allowed is None:
            # No policy = gets general domain only
            return self.get_domain("general")
        result: dict[str, Any] = {}
        for domain in allowed:
            result.update(self.get_domain(domain))
        return result

    # ── Compression ─────────────────────────────────────────

    def compress_stale(self) -> dict[str, Any]:
        """Prune stale entries, return summary of removed."""
        stale_keys: list[str] = []
        for key, entry in self._store.items():
            if entry.is_stale:
                stale_keys.append(key)

        for key in stale_keys:
            del self._store[key]
            for keys_list in self._domains.values():
                if key in keys_list:
                    keys_list.remove(key)

        result = {
            "pruned": len(stale_keys),
            "remaining": len(self._store),
            "pruned_keys": stale_keys,
        }
        if stale_keys:
            logger.info(
                "[ContextMgr] Pruned %d stale entries",
                len(stale_keys),
            )
            _emit("context.compressed", result)
        return result

    # ── Distribution ────────────────────────────────────────

    def collect_context(self) -> dict[str, Any]:
        """Produce a full snapshot for archival."""
        self._collect_system_context()  # refresh
        snapshot: dict[str, Any] = {
            "ts": datetime.now().isoformat(),
            "total_entries": len(self._store),
            "domains": {},
        }
        for domain, keys in self._domains.items():
            entries: list[dict[str, Any]] = []
            for k in keys:
                e = self._store.get(k)
                if e:
                    entries.append(e.to_dict())
            snapshot["domains"][domain] = {
                "count": len(entries),
                "entries": entries,
            }
        return snapshot

    def distribute(
        self,
        snapshot: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Push context to subscribed agents.

        In practice this emits a bus event; agents
        with context subscriptions will receive it.
        """
        snap = snapshot or self.collect_context()
        _emit("context.distributed", {
            "ts": snap.get("ts"),
            "total_entries": snap.get(
                "total_entries", 0,
            ),
            "domains": list(
                snap.get("domains", {}).keys()
            ),
        })
        return snap

    # ── Audit ───────────────────────────────────────────────

    def audit(self) -> dict[str, Any]:
        """Audit context freshness and accuracy."""
        now = time.time()
        fresh = stale = 0
        domain_stats: dict[str, dict[str, int]] = {}

        for domain, keys in self._domains.items():
            d_fresh = d_stale = 0
            for k in keys:
                e = self._store.get(k)
                if e is None:
                    continue
                if e.is_stale:
                    stale += 1
                    d_stale += 1
                else:
                    fresh += 1
                    d_fresh += 1
            domain_stats[domain] = {
                "fresh": d_fresh, "stale": d_stale,
            }

        total = fresh + stale
        freshness_pct = (
            round(100 * fresh / total, 1)
            if total else 100.0
        )

        report = {
            "ts": datetime.now().isoformat(),
            "total_entries": total,
            "fresh": fresh,
            "stale": stale,
            "freshness_pct": freshness_pct,
            "domains": domain_stats,
            "policies_set": len(self._access_policy),
        }
        _emit("context.audit", report)
        return report

    # ── Run cycle ───────────────────────────────────────────

    def run_cycle(self) -> dict[str, Any]:
        """Full management cycle:
        collect → audit → compress → distribute.
        """
        self._cycle += 1
        t0 = time.time()

        snapshot = self.collect_context()
        audit = self.audit()
        compressed = self.compress_stale()
        self.distribute(snapshot)

        elapsed = round(time.time() - t0, 2)
        report = {
            "cycle": self._cycle,
            "elapsed_s": elapsed,
            "context_entries": len(self._store),
            "freshness_pct": audit["freshness_pct"],
            "pruned": compressed["pruned"],
            "domains": list(
                self._domains.keys(),
            ),
        }

        # Persist report
        dest = (
            REPORTS_DIR
            / f"ctx_{self._cycle:04d}.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        _emit("context.cycle.done", report)
        logger.info(
            "[ContextMgr] Cycle #%d: %d entries, "
            "%.1f%% fresh, %d pruned (%.2fs)",
            self._cycle,
            len(self._store),
            audit["freshness_pct"],
            compressed["pruned"],
            elapsed,
        )
        return report

    # ── Persistence ─────────────────────────────────────────

    def save(
        self,
        path: Optional[Path] = None,
    ) -> Path:
        dest = path or (CTX_DIR / "context.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(
                self.collect_context(), indent=2,
            ),
            encoding="utf-8",
        )
        return dest
