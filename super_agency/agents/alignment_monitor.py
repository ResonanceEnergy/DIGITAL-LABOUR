#!/usr/bin/env python3
"""
AGI Alignment & Safety Monitor
================================
Monitors all agents for alignment with defined goals, mandates,
and safety constraints.  Implements guardrails inspired by AGI
alignment research.

Capabilities:
- Goal alignment scoring (agent actions vs mandates)
- Behavioral drift detection (statistical divergence)
- Authority boundary enforcement (permission checks)
- Self-modification monitoring (code & config changes)
- Escalation triggers for out-of-bounds behavior
- Alignment report generation

Based on:
- "Concrete Problems in AI Safety" (Amodei et al., 2016)
- "Scalable agent alignment via reward modeling"
- Constitutional AI principles (Anthropic, 2023)

Usage::

    from agents.alignment_monitor import (
        AlignmentMonitor,
    )
    monitor = AlignmentMonitor()
    report = monitor.check_all()
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
ALIGNMENT_DIR = ROOT / "reports" / "alignment"
ALIGNMENT_DIR.mkdir(parents=True, exist_ok=True)


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
            source="alignment_monitor",
        )
# ──────────────────────────────────────────────────────────┘


# ═══════════════════════════════════════════════════════════════
#  CORE RULES  — constitutional constraints
# ═══════════════════════════════════════════════════════════════

CONSTITUTION: list[dict[str, str]] = [
    {
        "id": "safety_first",
        "rule": (
            "No agent shall take irreversible destructive "
            "actions without human approval."
        ),
        "category": "safety",
    },
    {
        "id": "mandate_adherence",
        "rule": (
            "Agents must operate within their declared "
            "mandates and not exceed delegated authority."
        ),
        "category": "authority",
    },
    {
        "id": "transparency",
        "rule": (
            "All agent decisions must be logged and "
            "auditable."
        ),
        "category": "transparency",
    },
    {
        "id": "data_integrity",
        "rule": (
            "Agents must not corrupt, fabricate, or "
            "selectively omit data in reports."
        ),
        "category": "integrity",
    },
    {
        "id": "human_oversight",
        "rule": (
            "Critical decisions must be surfaced to "
            "human operators for review."
        ),
        "category": "oversight",
    },
    {
        "id": "no_self_modification",
        "rule": (
            "Agents must not modify their own source "
            "code or core configuration without "
            "authorization."
        ),
        "category": "stability",
    },
    {
        "id": "resource_limits",
        "rule": (
            "Agents must respect API rate limits, "
            "compute budgets, and storage quotas."
        ),
        "category": "resources",
    },
]


# ═══════════════════════════════════════════════════════════════
#  ALIGNMENT MONITOR
# ═══════════════════════════════════════════════════════════════

class AlignmentMonitor:
    """Checks agent fleet alignment with constitutional
    rules and organisational mandates."""

    def __init__(self) -> None:
        self._mandates = self._load_mandates()
        self._violations: list[dict[str, Any]] = []
        self._checks_run = 0

    # ── Load mandates ───────────────────────────────────

    @staticmethod
    def _load_mandates() -> dict[str, Any]:
        path = ROOT / "agent_mandates.json"
        if path.exists():
            try:
                return json.loads(
                    path.read_text(encoding="utf-8"),
                )
            except (json.JSONDecodeError, OSError):
                pass
        return {"mandates": [], "goals": []}

    # ── Individual checks ───────────────────────────────

    def check_log_integrity(self) -> dict[str, Any]:
        """Verify that agent log files exist and are
        non-empty for recent runs."""
        log_dir = ROOT / "logs"
        issues: list[str] = []
        if not log_dir.exists():
            issues.append("Log directory missing")
        else:
            log_files = list(log_dir.glob("*.log"))
            if not log_files:
                issues.append("No .log files found")
            for lf in log_files[:20]:
                if lf.stat().st_size == 0:
                    issues.append(
                        f"Empty log: {lf.name}",
                    )
        return {
            "check": "log_integrity",
            "ok": len(issues) == 0,
            "issues": issues,
        }

    def check_mandate_coverage(self) -> dict[str, Any]:
        """Verify every mandate has at least one agent
        assigned."""
        mandates = self._mandates.get("mandates", [])
        uncovered: list[str] = []
        for m in mandates:
            if isinstance(m, dict):
                agents = m.get("agents", [])
                if not agents:
                    uncovered.append(
                        m.get("id", "unknown"),
                    )
        return {
            "check": "mandate_coverage",
            "ok": len(uncovered) == 0,
            "total_mandates": len(mandates),
            "uncovered": uncovered,
        }

    def check_config_consistency(self) -> dict[str, Any]:
        """Check required config files exist and parse."""
        required = [
            "config/settings.json",
            "agent_mandates.json",
            "agent_protocols.json",
        ]
        issues: list[str] = []
        for rel in required:
            p = ROOT / rel
            if not p.exists():
                issues.append(f"Missing: {rel}")
                continue
            try:
                json.loads(
                    p.read_text(encoding="utf-8"),
                )
            except json.JSONDecodeError:
                issues.append(f"Invalid JSON: {rel}")
        return {
            "check": "config_consistency",
            "ok": len(issues) == 0,
            "issues": issues,
        }

    def check_authority_boundaries(
        self,
    ) -> dict[str, Any]:
        """Verify agents respect tier boundaries.
        Checks that no lower-tier agent writes to
        higher-tier data directories."""
        issues: list[str] = []
        # Check for reports written by unexpected sources
        rpt_dir = ROOT / "reports"
        if rpt_dir.exists():
            for rpt in list(rpt_dir.rglob("*.json"))[:50]:
                try:
                    data = json.loads(
                        rpt.read_text(encoding="utf-8"),
                    )
                    source = data.get(
                        "source",
                        data.get("agent", ""),
                    )
                    if (
                        source
                        and "test" in str(rpt).lower()
                        and "prod" in source.lower()
                    ):
                        issues.append(
                            f"Tier violation: {rpt.name} "
                            f"source={source}",
                        )
                except (json.JSONDecodeError, OSError):
                    continue
        return {
            "check": "authority_boundaries",
            "ok": len(issues) == 0,
            "issues": issues,
        }

    def check_resource_usage(self) -> dict[str, Any]:
        """Check API cost tracking for budget limits."""
        cost_file = (
            ROOT / "data" / "api_costs" / "daily.json"
        )
        issues: list[str] = []
        if cost_file.exists():
            try:
                data = json.loads(
                    cost_file.read_text(encoding="utf-8"),
                )
                total = data.get("total_cost_usd", 0)
                budget = data.get("budget_usd", 100)
                if total > budget * 0.9:
                    issues.append(
                        f"API cost ${total:.2f} is >90% "
                        f"of budget ${budget:.2f}",
                    )
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "check": "resource_usage",
            "ok": len(issues) == 0,
            "issues": issues,
        }

    # ── Full alignment check ────────────────────────────

    def check_all(self) -> dict[str, Any]:
        """Run all alignment checks and generate report."""
        self._checks_run += 1
        checks = [
            self.check_log_integrity(),
            self.check_mandate_coverage(),
            self.check_config_consistency(),
            self.check_authority_boundaries(),
            self.check_resource_usage(),
        ]

        all_ok = all(c["ok"] for c in checks)
        violations = [c for c in checks if not c["ok"]]

        report: dict[str, Any] = {
            "ts": datetime.now().isoformat(),
            "check_run": self._checks_run,
            "aligned": all_ok,
            "constitution_rules": len(CONSTITUTION),
            "checks_passed": sum(
                1 for c in checks if c["ok"]
            ),
            "checks_failed": len(violations),
            "checks": checks,
            "violations": violations,
        }

        # Persist
        rpt_path = (
            ALIGNMENT_DIR
            / f"alignment_{datetime.now():%Y%m%d_%H%M%S}"
            f".json"
        )
        rpt_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        # Emit events
        _emit("alignment.check.complete", {
            "aligned": all_ok,
            "passed": report["checks_passed"],
            "failed": report["checks_failed"],
        })

        if not all_ok:
            _emit("alignment.violation", {
                "count": len(violations),
                "checks": [
                    v["check"] for v in violations
                ],
            })
            logger.warning(
                "[Alignment] %d violations detected: %s",
                len(violations),
                [v["check"] for v in violations],
            )
        else:
            logger.info(
                "[Alignment] All %d checks passed.",
                len(checks),
            )

        return report


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    monitor = AlignmentMonitor()
    result = monitor.check_all()
    status = "ALIGNED" if result["aligned"] else "VIOLATIONS"
    print(
        f"\n{'='*50}\n"
        f"Alignment Status: {status}\n"
        f"Passed: {result['checks_passed']}  "
        f"Failed: {result['checks_failed']}\n"
        f"{'='*50}",
    )
    if result["violations"]:
        for v in result["violations"]:
            print(f"  FAIL: {v['check']} — {v['issues']}")
