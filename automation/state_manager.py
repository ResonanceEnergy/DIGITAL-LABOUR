"""State Manager — Unified state persistence layer for BIT RAGE SYSTEMS.

Provides a single interface for reading/writing all JSON state files
across the system. Prevents state corruption with atomic writes and
provides state snapshots for the C-Suite and NERVE.

Usage:
    python -m automation.state_manager --snapshot     # Dump all state to stdout
    python -m automation.state_manager --health       # Check all state files
    python -m automation.state_manager --export FILE  # Export full snapshot to file
    python -m automation.state_manager --reset MODULE # Reset a module's state
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"

# Registry of all state files in the system
STATE_REGISTRY = {
    "nerve": DATA_DIR / "nerve_state.json",
    "revenue": DATA_DIR / "revenue_state.json",
    "schedule": DATA_DIR / "schedule_state.json",
    "resonance_sync": DATA_DIR / "resonance_sync_state.json",
    "income": DATA_DIR / "income_tracker.json",
    "kpi": DATA_DIR / "kpi_data.json",
    "registration": DATA_DIR / "registration_log.json",
    "daemon_pids": DATA_DIR / "daemon_pids.json",
    "csuite_schedule": DATA_DIR / "csuite_schedule.json",
    "x_poster": DATA_DIR / "x_poster_state.json",
    "linkedin_poster": DATA_DIR / "linkedin_poster_state.json",
    "lead_scores": DATA_DIR / "lead_scores.json",
    "email_tracker": DATA_DIR / "email_tracker_state.json",
    "cold_email": DATA_DIR / "cold_email_state.json",
    "upwork_apply": DATA_DIR / "upwork_apply_state.json",
    "lead_magnet": DATA_DIR / "lead_magnet_state.json",
    "board_dispatch": DATA_DIR / "board_dispatch_state.json",
    "board_executor": DATA_DIR / "board_executor_state.json",
    "autobidder": DATA_DIR / "autobidder" / "autobidder_state.json",
}


def read_state(module: str) -> dict | list | None:
    """Read a module's state file. Returns None if not found."""
    path = STATE_REGISTRY.get(module)
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_state(module: str, data: dict | list):
    """Atomically write state for a module. Uses temp-file + rename to prevent corruption."""
    path = STATE_REGISTRY.get(module)
    if not path:
        raise KeyError(f"Unknown module: {module}. Available: {list(STATE_REGISTRY.keys())}")

    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, default=str)

    # Atomic write: write to temp file in same directory, then rename
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        # On Windows, must remove target first if it exists
        if path.exists():
            path.unlink()
        os.rename(tmp_path, str(path))
    except Exception:
        os.close(fd) if not os.get_inheritable(fd) else None
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def update_state(module: str, updates: dict):
    """Merge updates into existing state (dict only)."""
    current = read_state(module)
    if current is None:
        current = {}
    if not isinstance(current, dict):
        raise TypeError(f"State for {module} is {type(current).__name__}, not dict — cannot merge")
    current.update(updates)
    write_state(module, current)


def get_snapshot() -> dict:
    """Get a complete snapshot of all state across the system."""
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modules": {},
    }
    for module, path in STATE_REGISTRY.items():
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                snapshot["modules"][module] = {
                    "status": "ok",
                    "size_bytes": path.stat().st_size,
                    "modified": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
                    "data": data,
                }
            except (json.JSONDecodeError, OSError) as e:
                snapshot["modules"][module] = {"status": "error", "error": str(e)}
        else:
            snapshot["modules"][module] = {"status": "missing"}

    return snapshot


def health_check() -> dict:
    """Check health of all state files."""
    results = {"healthy": 0, "missing": 0, "corrupt": 0, "details": {}}
    for module, path in STATE_REGISTRY.items():
        if not path.exists():
            results["missing"] += 1
            results["details"][module] = "missing"
        else:
            try:
                json.loads(path.read_text(encoding="utf-8"))
                results["healthy"] += 1
                results["details"][module] = "ok"
            except json.JSONDecodeError:
                results["corrupt"] += 1
                results["details"][module] = "corrupt"
            except OSError as e:
                results["corrupt"] += 1
                results["details"][module] = f"read_error: {e}"

    results["total"] = len(STATE_REGISTRY)
    return results


def reset_state(module: str):
    """Reset a module's state to empty dict."""
    write_state(module, {})


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="State Manager — Unified state persistence")
    parser.add_argument("--snapshot", action="store_true", help="Dump all state")
    parser.add_argument("--health", action="store_true", help="Check all state files")
    parser.add_argument("--export", metavar="FILE", help="Export snapshot to JSON file")
    parser.add_argument("--reset", metavar="MODULE", help="Reset a module's state")
    parser.add_argument("--list", action="store_true", help="List registered state modules")
    args = parser.parse_args()

    if args.health:
        result = health_check()
        print(f"\n  State Health Check:")
        print(f"    Total:   {result['total']}")
        print(f"    Healthy: {result['healthy']}")
        print(f"    Missing: {result['missing']}")
        print(f"    Corrupt: {result['corrupt']}")
        for module, status in result["details"].items():
            icon = {"ok": "+", "missing": "-", "corrupt": "!"}
            print(f"    [{icon.get(status, '?')}] {module:25s} {status}")
    elif args.snapshot:
        snap = get_snapshot()
        for module, info in snap["modules"].items():
            status = info.get("status", "?")
            size = info.get("size_bytes", 0)
            print(f"  [{status:7s}] {module:25s} ({size:>8,} bytes)")
    elif args.export:
        snap = get_snapshot()
        Path(args.export).write_text(json.dumps(snap, indent=2, default=str), encoding="utf-8")
        print(f"  Exported snapshot to {args.export}")
    elif args.reset:
        if args.reset not in STATE_REGISTRY:
            print(f"  Unknown module: {args.reset}")
            print(f"  Available: {', '.join(STATE_REGISTRY.keys())}")
        else:
            reset_state(args.reset)
            print(f"  Reset {args.reset} state")
    elif args.list:
        print(f"\n  Registered State Modules ({len(STATE_REGISTRY)}):")
        for module, path in STATE_REGISTRY.items():
            exists = "+" if path.exists() else "-"
            print(f"    [{exists}] {module:25s} {path.name}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
