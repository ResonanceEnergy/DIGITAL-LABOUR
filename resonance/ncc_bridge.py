"""NCC Relay Bridge — Publishes sync events to NCC governance hub.

Sends ncl.sync.v1 events to the NCC Relay Server (port 8787).
Events are queued locally if the relay is unreachable, then flushed on reconnect.

Usage:
    from resonance.ncc_bridge import ncc

    # Publish a task completion event
    ncc.publish_task_event(event_dict)

    # Publish daily ops summary
    ncc.publish_daily_summary()

    # Manual flush of queued events
    ncc.flush()
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RELAY_URL = os.getenv("NCC_RELAY_URL", "http://127.0.0.1:8787")
SOURCE = "Digital-Labour"
PILLAR = "AGENCY"

OUTBOX_DIR = PROJECT_ROOT / "data" / "ncc_outbox"
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)


class NCCBridge:
    """Connector to NCC Relay Server for cross-pillar sync events."""

    def __init__(self, relay_url: str = RELAY_URL):
        self.relay_url = relay_url.rstrip("/")
        self._last_flush_attempt = None

    # ── Event Construction ──────────────────────────────────────

    def _make_sync_event(self, event_type: str, data: dict) -> dict:
        """Build an ncl.sync.v1 event conforming to the NCC schema."""
        return {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": SOURCE,
            "pillar": PILLAR,
            "data": data,
        }

    # ── Publishing ──────────────────────────────────────────────

    def _post(self, event: dict) -> bool:
        """POST event to NCC relay. Returns True if accepted."""
        try:
            import requests
            r = requests.post(
                f"{self.relay_url}/event",
                json=event,
                timeout=5,
            )
            return r.status_code in (200, 202)
        except Exception:
            return False

    def _queue(self, event: dict):
        """Queue event locally if relay is unreachable."""
        outbox_file = OUTBOX_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.ndjson"
        with open(outbox_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def publish(self, event_type: str, data: dict) -> bool:
        """Build and publish a sync event. Queues locally on failure.
        Auto-flushes stale outbox every 10 minutes on successful publish."""
        event = self._make_sync_event(event_type, data)
        if self._post(event):
            # Opportunistic auto-flush: if outbox has queued events, try flushing
            self._auto_flush()
            return True
        self._queue(event)
        return False

    def _auto_flush(self):
        """Flush outbox if enough time has passed since last attempt."""
        now = datetime.now(timezone.utc)
        if self._last_flush_attempt and (now - self._last_flush_attempt) < timedelta(minutes=10):
            return
        self._last_flush_attempt = now
        # Only flush if there are queued files
        if any(OUTBOX_DIR.glob("*.ndjson")):
            self.flush()

    def flush(self) -> dict:
        """Flush all queued outbox events to relay. Returns counts."""
        sent, failed = 0, 0
        for outbox_file in sorted(OUTBOX_DIR.glob("*.ndjson")):
            lines = outbox_file.read_text(encoding="utf-8").strip().splitlines()
            remaining = []
            for line in lines:
                event = json.loads(line)
                if self._post(event):
                    sent += 1
                else:
                    remaining.append(line)
                    failed += 1
            if remaining:
                outbox_file.write_text("\n".join(remaining) + "\n", encoding="utf-8")
            else:
                outbox_file.unlink()
        return {"sent": sent, "failed": failed}

    def relay_health(self) -> dict | None:
        """Check NCC relay health. Returns None if unreachable."""
        try:
            import requests
            r = requests.get(f"{self.relay_url}/health", timeout=3)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    # ── ALOPS Event Types ───────────────────────────────────────

    def publish_task_event(self, event: dict):
        """Publish a task completion/failure event to NCC."""
        self.publish("ncl.sync.v1.alops.task_completed", {
            "event_id": event.get("event_id", ""),
            "task_type": event.get("task_type", ""),
            "client_id": event.get("client_id", ""),
            "qa_status": event.get("qa", {}).get("status", ""),
            "latency_ms": event.get("metrics", {}).get("latency_ms", 0),
            "cost_usd": event.get("metrics", {}).get("cost_estimate", 0),
        })

    def publish_daily_summary(self):
        """Publish daily ALOPS operations summary to NCC."""
        from dashboard.health import queue_status, kpi_summary, revenue_summary, client_count

        kpi = kpi_summary()
        rev = revenue_summary()
        queue = queue_status()

        self.publish("ncl.sync.v1.alops.daily_summary", {
            "tasks_7d": kpi.get("total_tasks", 0),
            "pass_rate": kpi.get("pass_rate", "N/A"),
            "avg_duration_s": kpi.get("avg_duration_s", 0),
            "revenue_30d": rev.get("total_revenue", 0),
            "cost_30d": rev.get("total_cost", 0),
            "margin_30d": rev.get("gross_margin", 0),
            "queue_depth": queue.get("queued", 0),
            "queue_running": queue.get("running", 0),
            "active_clients": client_count(),
            "agents": ["sales_ops", "support", "content_repurpose", "doc_extract"],
        })

    def publish_csuite_report(self, board_data: dict):
        """Publish C-Suite board meeting results to NCC."""
        self.publish("ncl.sync.v1.alops.board_report", {
            "overall_status": board_data.get("overall_status", ""),
            "board_verdict": (board_data.get("board_verdict") or "")[:500],
            "execution_queue_count": len(board_data.get("execution_queue", [])),
            "conflicts_resolved": len(board_data.get("conflicts_resolved", [])),
            "risk_count": len(board_data.get("risk_register", [])),
        })

    def publish_fleet_status(self):
        """Publish agent fleet status for NCC ops monitoring."""
        agents_dir = PROJECT_ROOT / "agents"
        agent_count = sum(1 for d in agents_dir.iterdir() if d.is_dir() and (d / "runner.py").exists()) if agents_dir.exists() else 0

        from dashboard.health import queue_status
        queue = queue_status()

        self.publish("ncl.sync.v1.ops.fleet_status", {
            "division": "ALOPS",
            "agent_count": agent_count,
            "active_tasks": queue.get("running", 0),
            "queued_tasks": queue.get("queued", 0),
            "completed_today": queue.get("completed", 0),
            "errors": queue.get("failed", 0),
        })


# Module-level singleton
ncc = NCCBridge()
