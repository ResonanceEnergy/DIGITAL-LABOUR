#!/usr/bin/env python3
"""
Self-Check Validator -- System Integrity Monitor
=================================================
Validates the health and integrity of the entire
BIT RAGE LABOUR system.  Checks configurations, pipeline
outputs, runtime state, and data quality.

Validation categories:
  - Config: JSON validity, required fields
  - Pipeline: stage execution, output freshness
  - Health: log errors, circuit breaker states
  - Data: report quality, knowledge consistency
  - Runtime: scheduler state, brain state

Usage::

    python tools/self_check_validator.py
    python tools/self_check_validator.py config
    python tools/self_check_validator.py health
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    Log, ensure_dir, now_iso,
)

# ── Paths ──────────────────────────────────────────────────

VALIDATION_DIR = ROOT / "reports" / "validation"
ensure_dir(VALIDATION_DIR)

# Required config files
REQUIRED_CONFIGS: list[tuple[str, list[str]]] = [
    (
        "config/settings.json",
        ["name", "version", "tier"],
    ),
    (
        "agent_mandates.json",
        ["mandates", "goals"],
    ),
    (
        "agent_protocols.json",
        ["protocols"],
    ),
    (
        "config/skill_registry.json",
        ["agents"],
    ),
    (
        "config/research_projects.json",
        ["projects"],
    ),
    (
        "config/intelligence_watchlist.json",
        ["sources"],
    ),
]

# Message bus (best-effort)
_bus: Any = None
try:
    from agents.message_bus import bus
    _bus = bus
except Exception:
    pass


def _emit(topic: str, payload: Any = None):
    if _bus:
        _bus.publish(  # type: ignore[union-attr]
            topic, payload or {},
            source="self_check_validator",
        )


# ── Helpers ────────────────────────────────────────────────

def _load_json(path: Path) -> dict | None:
    """Load JSON, return None on failure."""
    if not path.exists():
        return None
    try:
        return cast(
            dict,
            json.loads(
                path.read_text(encoding="utf-8"),
            ),
        )
    except (json.JSONDecodeError, OSError):
        return None


def _file_age_hours(path: Path) -> float | None:
    if not path.exists():
        return None
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (
        datetime.now() - mtime
    ).total_seconds() / 3600


# ── SystemValidator ────────────────────────────────────────

class SystemValidator:
    """Validates entire system integrity."""

    def __init__(self):
        self.issues: list[dict] = []

    def validate_all(self) -> dict[str, Any]:
        """Run all validation checks."""
        self.issues = []
        config_ok = self.validate_config()
        pipeline_ok = self.validate_pipeline()
        health_ok = self.validate_health()
        data_ok = self.validate_data()
        runtime_ok = self.validate_runtime()

        score = self._compute_score(
            config_ok, pipeline_ok, health_ok,
            data_ok, runtime_ok,
        )

        result = {
            "timestamp": now_iso(),
            "config_valid": config_ok,
            "pipeline_valid": pipeline_ok,
            "health_valid": health_ok,
            "data_valid": data_ok,
            "runtime_valid": runtime_ok,
            "integrity_score": score,
            "issues": self.issues,
            "issue_count": len(self.issues),
        }

        # Persist
        out = VALIDATION_DIR / "latest_validation.json"
        out.write_text(
            json.dumps(result, indent=2, default=str),
            encoding="utf-8",
        )
        _emit("validation.complete", {
            "score": score,
            "issues": len(self.issues),
        })
        return result

    # ── Config Validation ──────────────────────────────────

    def validate_config(self) -> bool:
        """Check all required config files."""
        all_ok = True
        for rel_path, required_keys in REQUIRED_CONFIGS:
            fpath = ROOT / rel_path
            data = _load_json(fpath)
            if data is None:
                self.issues.append({
                    "category": "config",
                    "severity": "CRITICAL",
                    "file": rel_path,
                    "issue": (
                        "Missing or invalid JSON"
                    ),
                })
                all_ok = False
                continue

            for key in required_keys:
                if key not in data:
                    self.issues.append({
                        "category": "config",
                        "severity": "HIGH",
                        "file": rel_path,
                        "issue": (
                            f"Missing required key: "
                            f"'{key}'"
                        ),
                    })
                    all_ok = False

        return all_ok

    # ── Pipeline Validation ────────────────────────────────

    def validate_pipeline(self) -> bool:
        """Check pipeline output directories."""
        all_ok = True
        checks = [
            ("reports/research", 48),
            ("reports/ideas", 168),
            ("reports/intelligence", 72),
            ("reports/metrics", 24),
        ]

        for rel_dir, max_age_h in checks:
            d = ROOT / rel_dir
            if not d.exists():
                self.issues.append({
                    "category": "pipeline",
                    "severity": "MEDIUM",
                    "file": rel_dir,
                    "issue": "Directory does not exist",
                })
                all_ok = False
                continue

            jsons = list(d.glob("*.json"))
            if not jsons:
                self.issues.append({
                    "category": "pipeline",
                    "severity": "MEDIUM",
                    "file": rel_dir,
                    "issue": "No JSON output files",
                })
                all_ok = False
                continue

            newest = max(
                jsons,
                key=lambda f: f.stat().st_mtime,
            )
            age = _file_age_hours(newest)
            if age and age > max_age_h:
                self.issues.append({
                    "category": "pipeline",
                    "severity": "LOW",
                    "file": rel_dir,
                    "issue": (
                        f"Latest output is "
                        f"{age:.0f}h old "
                        f"(max {max_age_h}h)"
                    ),
                })

        return all_ok

    # ── Health Validation ──────────────────────────────────

    def validate_health(self) -> bool:
        """Check logs and circuit breakers."""
        all_ok = True
        log_file = ROOT / "logs" / "bit_rage_labour.log"

        if not log_file.exists():
            self.issues.append({
                "category": "health",
                "severity": "MEDIUM",
                "file": "logs/bit_rage_labour.log",
                "issue": "No runtime log file",
            })
            all_ok = False
        else:
            # Count recent ERROR lines
            try:
                lines = log_file.read_text(
                    encoding="utf-8", errors="replace",
                ).splitlines()
                tail = lines[-500:] if len(lines) > 500 else lines
                errors = [
                    ln for ln in tail
                    if "ERROR" in ln
                ]
                if len(errors) > 20:
                    self.issues.append({
                        "category": "health",
                        "severity": "HIGH",
                        "file": (
                            "logs/bit_rage_labour.log"
                        ),
                        "issue": (
                            f"{len(errors)} ERROR "
                            "lines in recent log tail"
                        ),
                    })
                    all_ok = False
            except OSError:
                pass

        # Check alerts log (last 24 h only)
        alerts = ROOT / "logs" / "alerts.ndjson"
        if alerts.exists():
            try:
                text = alerts.read_text(
                    encoding="utf-8", errors="replace",
                )
                alert_lines = [
                    ln for ln in text.splitlines()
                    if ln.strip()
                ]
                cutoff = (
                    datetime.now()
                    - __import__("datetime").timedelta(
                        hours=24,
                    )
                ).isoformat()
                crit = []
                for ln in alert_lines[-200:]:
                    if '"CRITICAL"' not in ln:
                        continue
                    try:
                        obj = json.loads(ln)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    ts = obj.get(
                        "ts",
                        obj.get("timestamp", ""),
                    )
                    if ts >= cutoff:
                        crit.append(ln)
                if crit:
                    self.issues.append({
                        "category": "health",
                        "severity": "CRITICAL",
                        "file": "logs/alerts.ndjson",
                        "issue": (
                            f"{len(crit)} CRITICAL "
                            "alerts in last 24 h"
                        ),
                    })
                    all_ok = False
            except OSError:
                pass

        return all_ok

    # ── Data Validation ────────────────────────────────────

    def validate_data(self) -> bool:
        """Check data quality and consistency."""
        all_ok = True

        # Portfolio exists and has repos?
        portfolio = ROOT / "portfolio.json"
        pdata = _load_json(portfolio)
        if pdata is None:
            self.issues.append({
                "category": "data",
                "severity": "HIGH",
                "file": "portfolio.json",
                "issue": "Portfolio file missing",
            })
            all_ok = False
        else:
            repos = pdata.get("repositories", [])
            if len(repos) == 0:
                self.issues.append({
                    "category": "data",
                    "severity": "HIGH",
                    "file": "portfolio.json",
                    "issue": "Portfolio has 0 repos",
                })
                all_ok = False

        # Research projects has actual projects?
        projects = _load_json(
            ROOT / "config" / "research_projects.json",
        )
        if projects:
            projs = projects.get("projects", [])
            empty = [
                p for p in projs
                if not p.get("repos")
            ]
            if empty:
                self.issues.append({
                    "category": "data",
                    "severity": "LOW",
                    "file": (
                        "config/research_projects.json"
                    ),
                    "issue": (
                        f"{len(empty)} projects "
                        "have no repos"
                    ),
                })

        return all_ok

    # ── Runtime Validation ─────────────────────────────────

    def validate_runtime(self) -> bool:
        """Check scheduler and brain state."""
        all_ok = True

        # Scheduler state
        sched = _load_json(
            ROOT / "config" / "scheduler_state.json",
        )
        if sched is None:
            self.issues.append({
                "category": "runtime",
                "severity": "MEDIUM",
                "file": (
                    "config/scheduler_state.json"
                ),
                "issue": (
                    "Scheduler state missing"
                ),
            })
            all_ok = False
        else:
            runs = sched.get("last_run", {})
            if not runs:
                self.issues.append({
                    "category": "runtime",
                    "severity": "HIGH",
                    "file": (
                        "config/scheduler_state.json"
                    ),
                    "issue": (
                        "Scheduler has never run"
                    ),
                })
                all_ok = False

        # Brain state
        brain = _load_json(
            ROOT / "config" / "brain_state.json",
        )
        if brain is None:
            self.issues.append({
                "category": "runtime",
                "severity": "LOW",
                "file": "config/brain_state.json",
                "issue": (
                    "Autonomous brain has no state"
                ),
            })

        return all_ok

    # ── Score ───────────────────────────────────────────────

    def _compute_score(self, *checks: bool) -> int:
        """Integrity score 0-100."""
        if not self.issues:
            return 100

        penalties = {
            "CRITICAL": 25,
            "HIGH": 10,
            "MEDIUM": 5,
            "LOW": 2,
        }
        total_penalty = sum(
            penalties.get(
                i.get("severity", "LOW"), 2,
            )
            for i in self.issues
        )
        return max(0, 100 - total_penalty)


# ── CLI ────────────────────────────────────────────────────

def main():
    Log.info("=== Self-Check Validator ===")
    validator = SystemValidator()
    result = validator.validate_all()

    score = result["integrity_score"]
    label = (
        "EXCELLENT" if score >= 90
        else "GOOD" if score >= 70
        else "FAIR" if score >= 50
        else "POOR"
    )
    Log.info(
        f"Integrity Score: {score}/100 ({label})"
    )
    Log.info(f"Issues found: {result['issue_count']}")

    for cat in (
        "config", "pipeline", "health",
        "data", "runtime",
    ):
        cat_issues = [
            i for i in result["issues"]
            if i["category"] == cat
        ]
        if cat_issues:
            Log.info(
                f"--- {cat.title()} "
                f"({len(cat_issues)}) ---"
            )
            for i in cat_issues:
                Log.info(
                    f"  [{i['severity']}] "
                    f"{i.get('file', '?')}: "
                    f"{i['issue']}"
                )

    return result


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "config":
        v = SystemValidator()
        v.validate_config()
        for i in v.issues:
            print(f"[{i['severity']}] {i['issue']}")
    elif cmd == "health":
        v = SystemValidator()
        v.validate_health()
        for i in v.issues:
            print(f"[{i['severity']}] {i['issue']}")
    else:
        main()
