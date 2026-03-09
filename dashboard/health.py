"""Health Dashboard — real-time system status and KPI overview.

Usage:
    python dashboard/health.py              # Full dashboard
    python dashboard/health.py --json       # JSON output
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def system_health() -> dict:
    """Check system component health."""
    checks = {}

    # Check .env
    env_file = PROJECT_ROOT / ".env"
    checks["env_file"] = env_file.exists()

    # Check LLM providers
    try:
        from utils.llm_client import list_available_providers
        providers = list_available_providers()
        checks["llm_providers"] = providers
        checks["providers_ok"] = len(providers) > 0
    except Exception as e:
        checks["llm_providers"] = []
        checks["providers_ok"] = False
        checks["provider_error"] = str(e)

    # Check SQLite databases
    data_dir = PROJECT_ROOT / "data"
    for db_name in ["task_queue.db", "kpi.db", "billing.db"]:
        checks[db_name] = (data_dir / db_name).exists()

    # Check agent modules
    for agent in ["sales_ops", "support", "content_repurpose", "doc_extract"]:
        runner = PROJECT_ROOT / "agents" / agent / "runner.py"
        checks[f"agent_{agent}"] = runner.exists()

    # Check key directories
    for d in ["output", "kpi/logs", "clients"]:
        checks[f"dir_{d.replace('/', '_')}"] = (PROJECT_ROOT / d).exists()

    return checks


def queue_status() -> dict:
    """Get task queue stats."""
    try:
        from dispatcher.queue import TaskQueue
        q = TaskQueue()
        return q.stats()
    except Exception:
        return {"queued": 0, "running": 0, "completed": 0, "failed": 0, "total": 0}


def kpi_summary() -> dict:
    """Get KPI summary."""
    try:
        from kpi.logger import summary
        return summary(days=7)
    except Exception:
        return {}


def revenue_summary() -> dict:
    """Get revenue snapshot."""
    try:
        from billing.tracker import BillingTracker
        bt = BillingTracker()
        return bt.revenue_report(days=30)
    except Exception:
        return {}


def client_count() -> int:
    """Count active clients."""
    clients_dir = PROJECT_ROOT / "clients"
    if not clients_dir.exists():
        return 0
    return sum(1 for f in clients_dir.glob("*.json"))


def full_dashboard() -> dict:
    """Generate full dashboard data."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "health": system_health(),
        "queue": queue_status(),
        "kpi_7d": kpi_summary(),
        "revenue_30d": revenue_summary(),
        "active_clients": client_count(),
    }


def print_dashboard():
    """Print formatted dashboard to terminal."""
    data = full_dashboard()
    h = data["health"]
    q = data["queue"]
    kpi = data["kpi_7d"]
    rev = data["revenue_30d"]

    print("\n" + "=" * 60)
    print("  DIGITAL LABOUR — System Dashboard")
    print("=" * 60)
    print(f"  Timestamp: {data['timestamp']}")

    # System Health
    print("\n── System Health ──")
    providers = h.get("llm_providers", [])
    print(f"  LLM Providers: {', '.join(providers) if providers else 'NONE'}")
    for agent in ["sales_ops", "support", "content_repurpose", "doc_extract"]:
        status = "✓" if h.get(f"agent_{agent}") else "✗"
        print(f"  Agent {agent}: {status}")
    for db in ["task_queue.db", "kpi.db", "billing.db"]:
        status = "✓" if h.get(db) else "—"
        print(f"  DB {db}: {status}")

    # Queue
    print("\n── Task Queue ──")
    print(f"  Queued: {q.get('queued', 0)} | Running: {q.get('running', 0)} | "
          f"Completed: {q.get('completed', 0)} | Failed: {q.get('failed', 0)}")

    # KPI
    print("\n── KPI (7 days) ──")
    if kpi:
        print(f"  Total tasks: {kpi.get('total_tasks', 0)}")
        print(f"  Pass rate: {kpi.get('pass_rate', 'N/A')}")
        print(f"  Avg duration: {kpi.get('avg_duration_s', 0)}s")
        print(f"  Total cost: ${kpi.get('total_cost_usd', 0):.4f}")
    else:
        print("  No data yet.")

    # Revenue
    print("\n── Revenue (30 days) ──")
    if rev:
        print(f"  Revenue: ${rev.get('total_revenue', 0):.2f}")
        print(f"  LLM Cost: ${rev.get('total_cost', 0):.4f}")
        print(f"  Gross Margin: ${rev.get('gross_margin', 0):.2f}")
        print(f"  Tasks: {rev.get('total_tasks', 0)}")
    else:
        print("  No revenue data yet.")

    print(f"\n  Active clients: {data['active_clients']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Digital Labour Health Dashboard")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.json:
        print(json.dumps(full_dashboard(), indent=2))
    else:
        print_dashboard()
