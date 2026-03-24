"""Resonance Sync Runner — Automated cross-pillar sync cadence.

Publishes BIT RAGE SYSTEMS operational data to NCC Relay on a schedule
and pulls intelligence from NCL + financials from AAC for C-Suite.

Cadence:
  - Every 6h:  Fleet status → NCC
  - Daily 06 UTC:  Daily summary → NCC
  - Daily 06 UTC:  Pull NCL brief → cache for AXIOM
  - Daily 06 UTC:  Pull AAC financials → cache for LEDGR
  - On board meeting: Board report → NCC

Usage:
    python -m resonance.sync --daemon          # Continuous 30-min loop
    python -m resonance.sync --run-all         # Run all sync jobs now
    python -m resonance.sync --flush           # Flush NCC outbox
    python -m resonance.sync --status          # Show sync health
"""

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SYNC_STATE_FILE = PROJECT_ROOT / "data" / "resonance_sync_state.json"


def _load_state() -> dict:
    if SYNC_STATE_FILE.exists():
        return json.loads(SYNC_STATE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_state(state: dict):
    SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SYNC_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _hours_since(iso_str: str | None) -> float:
    if not iso_str:
        return 999
    then = datetime.fromisoformat(iso_str)
    return (datetime.now(timezone.utc) - then).total_seconds() / 3600


# ── Sync Jobs ───────────────────────────────────────────────────

def sync_fleet_status():
    """Publish fleet status to NCC relay."""
    from resonance.ncc_bridge import ncc
    try:
        ncc.publish_fleet_status()
        print("[SYNC] Fleet status → NCC")
    except Exception as e:
        print(f"[SYNC] Fleet status failed: {e}")


def sync_daily_summary():
    """Publish daily ops summary to NCC relay."""
    from resonance.ncc_bridge import ncc
    try:
        ncc.publish_daily_summary()
        print("[SYNC] Daily summary → NCC")
    except Exception as e:
        print(f"[SYNC] Daily summary failed: {e}")


def pull_ncl_brief() -> dict | None:
    """Pull latest NCL daily brief for AXIOM."""
    from resonance.ncl_bridge import ncl
    digest = ncl.intelligence_digest()
    # Cache for C-Suite consumption
    cache_dir = PROJECT_ROOT / "data" / "resonance_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "ncl_digest.json"
    cache_file.write_text(json.dumps(digest, indent=2, default=str), encoding="utf-8")
    print(f"[SYNC] NCL digest cached — health={digest.get('trinity_health_score')}")
    return digest


def pull_aac_snapshot() -> dict | None:
    """Pull AAC financial snapshot for LEDGR."""
    from resonance.aac_bridge import aac
    try:
        snapshot = aac.snapshot()
        cache_dir = PROJECT_ROOT / "data" / "resonance_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "aac_snapshot.json"
        cache_file.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")
        print(f"[SYNC] AAC snapshot cached — status={snapshot.get('status')}")
        return snapshot
    except Exception as e:
        print(f"[SYNC] AAC snapshot failed: {e}")
        return None


def flush_outbox() -> dict:
    """Flush any queued NCC outbox events."""
    from resonance.ncc_bridge import ncc
    result = ncc.flush()
    if result["sent"] or result["failed"]:
        print(f"[SYNC] Outbox flush: {result['sent']} sent, {result['failed']} failed")
    return result


# ── Cadence Runner ──────────────────────────────────────────────

def run_due_jobs():
    """Check schedule and run any overdue sync jobs."""
    state = _load_state()
    now = datetime.now(timezone.utc).isoformat()
    ran = []

    # Fleet status every 6h
    if _hours_since(state.get("last_fleet")) >= 6:
        sync_fleet_status()
        state["last_fleet"] = now
        ran.append("fleet_status")

    # Daily summary at 06 UTC
    utc_hour = datetime.now(timezone.utc).hour
    if _hours_since(state.get("last_daily")) >= 20 and 4 <= utc_hour <= 10:
        sync_daily_summary()
        state["last_daily"] = now
        ran.append("daily_summary")

    # NCL brief pull daily
    if _hours_since(state.get("last_ncl_pull")) >= 20 and 4 <= utc_hour <= 10:
        pull_ncl_brief()
        state["last_ncl_pull"] = now
        ran.append("ncl_brief")

    # AAC snapshot daily
    if _hours_since(state.get("last_aac_pull")) >= 20 and 4 <= utc_hour <= 10:
        pull_aac_snapshot()
        state["last_aac_pull"] = now
        ran.append("aac_snapshot")

    # Always try outbox flush
    flush_outbox()

    state["last_check"] = now
    _save_state(state)
    return ran


def run_all():
    """Run all sync jobs immediately regardless of schedule."""
    print("═══ RESONANCE SYNC — FULL RUN ═══")
    sync_fleet_status()
    sync_daily_summary()
    pull_ncl_brief()
    pull_aac_snapshot()
    result = flush_outbox()
    state = _load_state()
    now = datetime.now(timezone.utc).isoformat()
    state.update({
        "last_fleet": now, "last_daily": now,
        "last_ncl_pull": now, "last_aac_pull": now,
        "last_check": now,
    })
    _save_state(state)
    print("═══ SYNC COMPLETE ═══")


def show_status():
    """Print sync health status."""
    state = _load_state()
    print("═══ RESONANCE SYNC STATUS ═══")
    for key, val in state.items():
        age = f"({_hours_since(val):.1f}h ago)" if val and key.startswith("last_") else ""
        print(f"  {key}: {val} {age}")

    # NCC relay health
    from resonance.ncc_bridge import ncc
    health = ncc.relay_health()
    print(f"\n  NCC Relay: {'ONLINE' if health else 'OFFLINE'}")

    # NCL availability
    from resonance.ncl_bridge import ncl
    print(f"  NCL Data:  {'AVAILABLE' if ncl.available else 'NOT FOUND'}")

    # Outbox depth
    outbox = PROJECT_ROOT / "data" / "ncc_outbox"
    queued = sum(1 for f in outbox.glob("*.ndjson") for _ in open(f, encoding="utf-8")) if outbox.exists() else 0
    print(f"  Outbox:    {queued} queued events")
    print("═════════════════════════════")


def daemon_loop(interval_min: int = 30):
    """Continuous sync daemon."""
    print(f"[SYNC DAEMON] Starting — interval {interval_min}min")
    while True:
        try:
            ran = run_due_jobs()
            if ran:
                print(f"[SYNC DAEMON] Ran: {', '.join(ran)}")
        except Exception as e:
            print(f"[SYNC DAEMON] Error: {e}")
        time.sleep(interval_min * 60)


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Resonance Energy Sync Runner")
    parser.add_argument("--daemon", action="store_true", help="Run continuous sync loop")
    parser.add_argument("--run-all", action="store_true", help="Run all sync jobs now")
    parser.add_argument("--flush", action="store_true", help="Flush NCC outbox")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    parser.add_argument("--interval", type=int, default=30, help="Daemon interval in minutes")
    args = parser.parse_args()

    if args.daemon:
        daemon_loop(args.interval)
    elif args.run_all:
        run_all()
    elif args.flush:
        flush_outbox()
    elif args.status:
        show_status()
    else:
        parser.print_help()
