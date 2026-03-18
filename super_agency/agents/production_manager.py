#!/usr/bin/env python3
"""
Production Manager Agent — BIT RAGE LABOUR
=============================================
T2 Management agent responsible for production
readiness, deployment gates, service health, and
operational excellence across all running services.

Authority:
- Controls production deployment gates
- Monitors service health (ports, threads, memory)
- Can trigger emergency stops via escalation
- Owns the production.* bus namespace

Reports to: CTO (T1)
Manages: gasket (T3), memory_backup (T4)
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
PROD_DIR = ROOT / "data" / "production_manager"
PROD_DIR.mkdir(parents=True, exist_ok=True)

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
            source="production_manager",
        )


class ProductionManagerAgent:
    """Manages production readiness, service health,
    and deployment gates."""

    SERVICE_PORTS = {
        "matrix_maximizer": 8080,
        "mobile_command_center": 8081,
        "operations_api": 5001,
    }

    def __init__(self) -> None:
        self._cycle = 0
        self._incidents: list[dict[str, Any]] = []
        self._load_state()

    # ── Persistence ────────────────────────────
    def _state_path(self) -> Path:
        return PROD_DIR / "production_state.json"

    def _load_state(self) -> None:
        p = self._state_path()
        if p.exists():
            try:
                data = json.loads(
                    p.read_text(encoding="utf-8"),
                )
                self._cycle = data.get("cycle", 0)
                self._incidents = data.get(
                    "incidents", [],
                )[-100:]
            except (json.JSONDecodeError, OSError):
                pass

    def _save_state(self) -> None:
        self._state_path().write_text(
            json.dumps(
                {
                    "cycle": self._cycle,
                    "incidents": self._incidents[-100:],
                    "saved_at": datetime.now().isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # ── Health Checks ──────────────────────────
    def _check_ports(self) -> dict[str, Any]:
        """Check if service ports are responsive."""
        import socket
        results: dict[str, str] = {}
        for name, port in self.SERVICE_PORTS.items():
            try:
                s = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                )
                s.settimeout(2)
                s.connect(("127.0.0.1", port))
                s.close()
                results[name] = "UP"
            except OSError:
                results[name] = "DOWN"

        up = sum(1 for v in results.values() if v == "UP")
        return {
            "services": results,
            "up": up,
            "total": len(results),
            "all_up": up == len(results),
        }

    def _check_disk_usage(self) -> dict[str, Any]:
        """Check disk space for critical directories."""
        checks: dict[str, Any] = {}
        dirs = {
            "logs": ROOT / "logs",
            "memory": ROOT / "memory",
            "reports": ROOT / "reports",
            "data": ROOT / "data",
        }

        total_size = 0
        for name, d in dirs.items():
            if not d.exists():
                checks[name] = {
                    "exists": False, "size_mb": 0,
                }
                continue
            size = sum(
                f.stat().st_size
                for f in d.rglob("*")
                if f.is_file()
            )
            size_mb = round(size / (1024 * 1024), 2)
            checks[name] = {
                "exists": True, "size_mb": size_mb,
            }
            total_size += size_mb

        return {
            "directories": checks,
            "total_mb": round(total_size, 2),
        }

    def _check_pid_files(self) -> dict[str, Any]:
        """Check PID files for running processes."""
        pid_files = list(ROOT.glob(".*pid"))
        results: dict[str, Any] = {}
        for pf in pid_files:
            name = pf.name
            try:
                pid = int(
                    pf.read_text(encoding="utf-8")
                    .strip()
                )
                results[name] = {"pid": pid}
            except (ValueError, OSError):
                results[name] = {"pid": None}

        return {
            "pid_files": len(pid_files),
            "details": results,
        }

    def _check_watchdog_log(self) -> dict[str, Any]:
        """Check for recent watchdog restarts."""
        log_file = ROOT / "logs" / "bit_rage_labour.log"
        restarts = 0
        dead_services: list[str] = []

        if log_file.exists():
            try:
                text = log_file.read_text(
                    encoding="utf-8", errors="ignore",
                )
                for line in text.splitlines()[-200:]:
                    if "WATCHDOG" in line and "DEAD" in line:
                        restarts += 1
                    if "max restarts" in line.lower():
                        dead_services.append(
                            line.strip()[:100]
                        )
            except OSError:
                pass

        return {
            "recent_restarts": restarts,
            "permanently_dead": len(dead_services),
        }

    # ── Main Cycle ─────────────────────────────
    def run_cycle(self) -> dict[str, Any]:
        """Run a full production health cycle."""
        self._cycle += 1
        t0 = time.monotonic()

        ports = self._check_ports()
        disk = self._check_disk_usage()
        pids = self._check_pid_files()
        watchdog = self._check_watchdog_log()

        # Determine overall health
        issues: list[str] = []
        if not ports["all_up"]:
            down = [
                k for k, v in ports["services"].items()
                if v == "DOWN"
            ]
            issues.append(f"services_down: {down}")

        if disk["total_mb"] > 1000:
            issues.append(
                f"disk_high: {disk['total_mb']} MB"
            )

        if watchdog["permanently_dead"] > 0:
            issues.append("dead_services_detected")

        health = "healthy" if not issues else "degraded"

        elapsed = round(time.monotonic() - t0, 3)

        report = {
            "cycle": self._cycle,
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "issues": issues,
            "ports": ports,
            "disk": disk,
            "pid_files": pids,
            "watchdog": watchdog,
            "elapsed_s": elapsed,
        }

        if issues:
            self._incidents.append({
                "cycle": self._cycle,
                "issues": issues,
                "ts": datetime.now().isoformat(),
            })

        self._save_state()

        _emit("production.cycle.complete", {
            "cycle": self._cycle,
            "health": health,
            "issues_count": len(issues),
        })

        if health == "degraded":
            _emit("production.health.degraded", {
                "issues": issues,
            })
            logger.warning(
                "[PROD_MGR] Health DEGRADED: %s",
                "; ".join(issues),
            )

        logger.info(
            "[PROD_MGR] Cycle %d — %s (%.3fs)",
            self._cycle, health, elapsed,
        )

        return report
