#!/usr/bin/env python3
"""
QA Manager Agent — DIGITAL LABOUR
=====================================
T2 Management agent responsible for quality assurance
across the entire agent fleet. Validates outputs,
enforces standards, runs regression checks, and
tracks quality metrics over time.

Authority:
- Can reject/flag agent outputs that fail QA gates
- Enforces code quality, report quality, data integrity
- Owns the qa.* bus namespace
- Triggers re-runs when quality drops below threshold

Reports to: CTO (T1)
Manages: self_check_validator (T3), gap_analyzer (T3)
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
QA_DIR = ROOT / "data" / "qa_manager"
QA_DIR.mkdir(parents=True, exist_ok=True)

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
            source="qa_manager",
        )


class QAManagerAgent:
    """Quality assurance gate for agent fleet outputs."""

    QUALITY_THRESHOLD = 0.80  # 80% pass rate

    def __init__(self) -> None:
        self._cycle = 0
        self._history: list[dict[str, Any]] = []
        self._load_state()

    # ── Persistence ────────────────────────────
    def _state_path(self) -> Path:
        return QA_DIR / "qa_state.json"

    def _load_state(self) -> None:
        p = self._state_path()
        if p.exists():
            try:
                data = json.loads(
                    p.read_text(encoding="utf-8"),
                )
                self._cycle = data.get("cycle", 0)
                self._history = data.get(
                    "history", [],
                )[-50:]
            except (json.JSONDecodeError, OSError):
                pass

    def _save_state(self) -> None:
        self._state_path().write_text(
            json.dumps(
                {
                    "cycle": self._cycle,
                    "history": self._history[-50:],
                    "saved_at": datetime.now().isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # ── QA Checks ──────────────────────────────
    def _check_report_quality(self) -> dict[str, Any]:
        """Validate freshness and completeness of
        generated reports."""
        reports_dir = ROOT / "reports"
        if not reports_dir.is_dir():
            return {"status": "no_reports_dir"}

        total = 0
        fresh = 0
        empty = 0
        now_ts = time.time()
        cutoff = 86400 * 7  # 7 days

        for f in reports_dir.rglob("*.json"):
            total += 1
            try:
                size = f.stat().st_size
                age = now_ts - f.stat().st_mtime
                if size < 10:
                    empty += 1
                elif age < cutoff:
                    fresh += 1
            except OSError:
                continue

        return {
            "total_reports": total,
            "fresh_7d": fresh,
            "empty": empty,
            "freshness_pct": round(
                fresh / max(total, 1) * 100, 1,
            ),
        }

    def _check_test_health(self) -> dict[str, Any]:
        """Check test file presence and rough health."""
        test_dir = ROOT / "tests"
        if not test_dir.is_dir():
            return {"status": "no_tests_dir"}

        test_files = list(test_dir.glob("test_*.py"))
        total_lines = 0
        for f in test_files:
            try:
                total_lines += len(
                    f.read_text(encoding="utf-8")
                    .splitlines()
                )
            except OSError:
                continue

        return {
            "test_files": len(test_files),
            "total_lines": total_lines,
            "avg_lines": round(
                total_lines / max(len(test_files), 1),
            ),
        }

    def _check_config_integrity(self) -> dict[str, Any]:
        """Validate JSON configs parse correctly."""
        configs = [
            ROOT / "agent_mandates.json",
            ROOT / "agent_protocols.json",
            ROOT / "organization_structure.json",
            ROOT / "config" / "skill_registry.json",
            ROOT / "portfolio.json",
        ]
        results: dict[str, str] = {}
        for cfg in configs:
            name = cfg.name
            if not cfg.exists():
                results[name] = "missing"
                continue
            try:
                json.loads(
                    cfg.read_text(encoding="utf-8"),
                )
                results[name] = "valid"
            except json.JSONDecodeError:
                results[name] = "invalid_json"
            except OSError:
                results[name] = "read_error"

        valid = sum(
            1 for v in results.values() if v == "valid"
        )
        return {
            "configs_checked": len(configs),
            "valid": valid,
            "results": results,
        }

    def _check_log_errors(self) -> dict[str, Any]:
        """Scan recent logs for error patterns."""
        log_dir = ROOT / "logs"
        if not log_dir.is_dir():
            return {"status": "no_logs_dir"}

        error_count = 0
        warning_count = 0
        files_scanned = 0

        for log_file in log_dir.glob("*.log"):
            files_scanned += 1
            try:
                text = log_file.read_text(
                    encoding="utf-8", errors="ignore",
                )
                for line in text.splitlines()[-500:]:
                    upper = line.upper()
                    if "ERROR" in upper:
                        error_count += 1
                    elif "WARNING" in upper:
                        warning_count += 1
            except OSError:
                continue

        return {
            "files_scanned": files_scanned,
            "recent_errors": error_count,
            "recent_warnings": warning_count,
        }

    # ── Main Cycle ─────────────────────────────
    def run_cycle(self) -> dict[str, Any]:
        """Run a full QA assessment cycle."""
        self._cycle += 1
        t0 = time.monotonic()

        reports = self._check_report_quality()
        tests = self._check_test_health()
        configs = self._check_config_integrity()
        logs = self._check_log_errors()

        # Calculate overall quality score
        scores: list[float] = []
        if reports.get("total_reports", 0) > 0:
            scores.append(
                reports["freshness_pct"] / 100.0
            )
        if configs.get("configs_checked", 0) > 0:
            scores.append(
                configs["valid"]
                / configs["configs_checked"]
            )

        quality_score = round(
            sum(scores) / max(len(scores), 1), 3,
        )
        passed = quality_score >= self.QUALITY_THRESHOLD

        elapsed = round(time.monotonic() - t0, 3)

        report = {
            "cycle": self._cycle,
            "timestamp": datetime.now().isoformat(),
            "quality_score": quality_score,
            "passed": passed,
            "reports": reports,
            "tests": tests,
            "configs": configs,
            "logs": logs,
            "elapsed_s": elapsed,
        }

        self._history.append({
            "cycle": self._cycle,
            "score": quality_score,
            "passed": passed,
            "ts": datetime.now().isoformat(),
        })
        self._save_state()

        _emit("qa.cycle.complete", {
            "cycle": self._cycle,
            "score": quality_score,
            "passed": passed,
        })

        if not passed:
            _emit("qa.quality.below_threshold", {
                "score": quality_score,
                "threshold": self.QUALITY_THRESHOLD,
            })
            logger.warning(
                "[QA_MGR] Quality below threshold: "
                "%.1f%% < %.1f%%",
                quality_score * 100,
                self.QUALITY_THRESHOLD * 100,
            )

        logger.info(
            "[QA_MGR] Cycle %d — score %.1f%% %s "
            "(%.3fs)",
            self._cycle,
            quality_score * 100,
            "PASS" if passed else "FAIL",
            elapsed,
        )

        return report
