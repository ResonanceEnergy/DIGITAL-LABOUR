#!/usr/bin/env python3
"""
Bit Rage Labour Integration Bridge
===================================
Connects BIT RAGE LABOUR infrastructure to Bit Rage Labour operations.
DL is the primary mission — this bridge ensures SA's hierarchy,
bus, orchestrator, and memory doctrine all serve DL objectives.

Runs as an orchestrator stage (first in pipeline) and also
provides an API for DL's resonance layer to push events into
SA's message bus.

Integration points:
  - Pulls DL health/KPIs and publishes to SA bus
  - Reads DL task queue status for orchestrator awareness
  - Caches DL fleet status in memory doctrine
  - Provides methods DL's resonance/sync.py calls into

Usage:
    # As orchestrator stage:
    python agents/dl_bridge.py

    # Programmatic sync:
    from agents.dl_bridge import DLBridge
    bridge = DLBridge()
    bridge.sync()
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DL_ROOT = Path(
    os.getenv(
        "DIGITAL_LABOUR_ROOT",
        r"C:\Dev\BIT RAGE LABOUR\BIT RAGE LABOUR",
    )
)

# SA message bus (best-effort)
_bus: Any = None
try:
    from agents.message_bus import bus
    _bus = bus
except Exception:
    pass

# DL status cache
_CACHE_DIR = ROOT / "data" / "dl_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _emit(
    topic: str,
    payload: Optional[dict] = None,
) -> None:
    """Publish event to SA message bus."""
    if _bus:
        _bus.publish(
            topic, payload or {},
            source="dl_bridge",
        )


class DLBridge:
    """Bridge between BIT RAGE LABOUR infrastructure and
    Bit Rage Labour operations.

    Designed to be called from:
    1. SA orchestrator (as first pipeline stage)
    2. DL resonance/sync.py (to push events into SA bus)
    3. SA monitoring dashboards (for DL status)
    """

    def __init__(self, dl_root: Optional[Path] = None):
        self.dl_root = dl_root or DL_ROOT
        self.data_dir = self.dl_root / "data"
        self.agents_dir = self.dl_root / "agents"

    @property
    def available(self) -> bool:
        """Check if DL repo is accessible."""
        return self.dl_root.exists()

    # ── Status Queries ──────────────────────────────────────

    def fleet_status(self) -> dict:
        """Count DL agents and get basic fleet info."""
        if not self.agents_dir.exists():
            return {"status": "offline", "agents": 0}

        agent_dirs = [
            d.name for d in self.agents_dir.iterdir()
            if d.is_dir()
            and (d / "runner.py").exists()
        ]
        return {
            "status": "online",
            "agent_count": len(agent_dirs),
            "agents": agent_dirs,
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    def queue_status(self) -> dict:
        """Read DL task queue stats from its SQLite DB."""
        queue_db = self.data_dir / "task_queue.db"
        if not queue_db.exists():
            return {"status": "no_queue_db"}

        try:
            import sqlite3
            conn = sqlite3.connect(str(queue_db))
            cur = conn.cursor()

            counts = {}
            for status_val in (
                "queued", "running", "completed", "failed",
            ):
                cur.execute(
                    "SELECT COUNT(*) FROM tasks "
                    "WHERE status = ?",
                    (status_val,),
                )
                row = cur.fetchone()
                counts[status_val] = row[0] if row else 0

            conn.close()
            counts["status"] = "online"
            counts["ts"] = datetime.now(
                timezone.utc,
            ).isoformat()
            return counts
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
            }

    def kpi_summary(self) -> dict:
        """Read DL KPI summary from its data stores."""
        kpi_db = self.data_dir / "kpi.db"
        if not kpi_db.exists():
            return {"status": "no_kpi_db"}

        try:
            import sqlite3
            conn = sqlite3.connect(str(kpi_db))
            cur = conn.cursor()

            # Count recent events
            cur.execute(
                "SELECT COUNT(*) FROM events "
                "WHERE timestamp > "
                "datetime('now', '-7 days')"
            )
            row = cur.fetchone()
            total_7d = row[0] if row else 0

            conn.close()
            return {
                "status": "online",
                "tasks_7d": total_7d,
                "ts": datetime.now(
                    timezone.utc,
                ).isoformat(),
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
            }

    def revenue_snapshot(self) -> dict:
        """Read DL revenue from billing DB."""
        billing_db = self.data_dir / "billing.db"
        if not billing_db.exists():
            return {"status": "no_billing_db"}

        try:
            import sqlite3
            conn = sqlite3.connect(str(billing_db))
            cur = conn.cursor()

            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) "
                "FROM invoices "
                "WHERE created_at > "
                "datetime('now', '-30 days')"
            )
            row = cur.fetchone()
            rev_30d = row[0] if row else 0

            conn.close()
            return {
                "status": "online",
                "revenue_30d": rev_30d,
                "ts": datetime.now(
                    timezone.utc,
                ).isoformat(),
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
            }

    # ── Event Publishing (DL → SA bus) ──────────────────────

    def publish_task_event(self, event: dict) -> None:
        """Publish a DL task event to SA bus."""
        status = event.get("status", "completed")
        topic = (
            "bit_rage_labour.task.completed"
            if status == "completed"
            else "bit_rage_labour.task.failed"
        )
        _emit(topic, event)

    def publish_revenue_event(
        self, amount: float, client_id: str, **kw,
    ) -> None:
        """Publish revenue event to SA bus."""
        _emit("bit_rage_labour.revenue.received", {
            "amount": amount,
            "client_id": client_id,
            **kw,
        })

    def publish_fleet_update(self) -> None:
        """Publish current fleet status to SA bus."""
        status = self.fleet_status()
        _emit("bit_rage_labour.fleet.status", status)

    def publish_nerve_phase(
        self, phase: str, details: Optional[dict] = None,
    ) -> None:
        """Publish NERVE cycle phase to SA bus."""
        _emit(f"bit_rage_labour.nerve.{phase}", {
            "phase": phase,
            **(details or {}),
        })

    def publish_csuite_report(
        self, board_data: dict,
    ) -> None:
        """Publish C-Suite board report to SA bus."""
        _emit(
            "bit_rage_labour.csuite.report",
            board_data,
        )

    def publish_qa_alert(
        self, agent: str, pass_rate: float,
    ) -> None:
        """Publish QA alert to SA bus for escalation."""
        _emit("bit_rage_labour.qa.alert", {
            "agent": agent,
            "pass_rate": pass_rate,
        })

    def publish_client_event(
        self, event: str, client_id: str, **kw,
    ) -> None:
        """Publish client lifecycle event to SA bus."""
        _emit(f"bit_rage_labour.client.{event}", {
            "event": event,
            "client_id": client_id,
            **kw,
        })

    # ── Cache (for SA dashboards/orchestrator) ──────────────

    def _cache(self, name: str, data: dict) -> None:
        """Write data to DL cache for SA consumption."""
        path = _CACHE_DIR / f"{name}.json"
        path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )

    def _read_cache(self, name: str) -> Optional[dict]:
        """Read cached DL data."""
        path = _CACHE_DIR / f"{name}.json"
        if path.exists():
            return json.loads(
                path.read_text(encoding="utf-8"),
            )
        return None

    # ── Full Sync (orchestrator stage) ──────────────────────

    def sync(self) -> dict:
        """Run full DL sync — called as orchestrator stage.

        Pulls status from DL, publishes to SA bus,
        caches for dashboards.
        """
        result = {
            "ts": datetime.now(
                timezone.utc,
            ).isoformat(),
            "dl_available": self.available,
        }

        if not self.available:
            logger.warning(
                "[DL Bridge] Bit Rage Labour repo not "
                "found at %s",
                self.dl_root,
            )
            _emit("bit_rage_labour.sync.offline", {
                "dl_root": str(self.dl_root),
            })
            result["status"] = "offline"
            return result

        # Fleet status
        fleet = self.fleet_status()
        self._cache("fleet_status", fleet)
        self.publish_fleet_update()
        result["fleet"] = fleet

        # Queue status
        queue = self.queue_status()
        self._cache("queue_status", queue)
        result["queue"] = queue

        # KPIs
        kpis = self.kpi_summary()
        self._cache("kpi_summary", kpis)
        result["kpis"] = kpis

        # Revenue
        revenue = self.revenue_snapshot()
        self._cache("revenue", revenue)
        result["revenue"] = revenue

        _emit("bit_rage_labour.sync.complete", result)
        logger.info(
            "[DL Bridge] Sync complete — "
            "%d agents, queue=%s",
            fleet.get("agent_count", 0),
            queue.get("status", "?"),
        )
        result["status"] = "synced"
        return result


def main():
    """Run DL bridge sync as orchestrator stage."""
    logging.basicConfig(level=logging.INFO)
    bridge = DLBridge()
    result = bridge.sync()
    status = result.get("status", "unknown")
    agents = result.get("fleet", {}).get(
        "agent_count", 0,
    )
    print(
        f"[DL Bridge] Status: {status} "
        f"| Agents: {agents}"
    )


if __name__ == "__main__":
    main()
