#!/usr/bin/env python3
"""
Emergency Stop CLI — drop all repos to L0 (observe-only) instantly.
Also supports elevating repos back to their computed autonomy level.

Usage:
    python emergency_stop_cli.py stop          # Drop ALL repos to L0
    python emergency_stop_cli.py resume        # Restore computed autonomy levels
    python emergency_stop_cli.py status        # Show current autonomy state
"""
import json, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
PORT = ROOT / "portfolio.json"
LOCK_FILE = ROOT / "logs" / "emergency_stop.lock"
LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_portfolio():
    if PORT.exists():
        return json.loads(PORT.read_text(encoding="utf-8"))
    return {"repositories": []}


def _save_portfolio(data):
    PORT.write_text(json.dumps(data, indent=2), encoding="utf-8")


def emergency_stop():
    """Drop every repo to L0 (observe-only) and persist a lock file."""
    portfolio = _load_portfolio()
    count = 0
    for r in portfolio.get("repositories", []):
        prev = r.get("autonomy_level", "L1")
        r["_prev_autonomy"] = prev
        r["autonomy_level"] = "L0"
        count += 1
    _save_portfolio(portfolio)

    lock = {"activated_at": datetime.now().isoformat(),
                                         "repos_affected": count}
    LOCK_FILE.write_text(json.dumps(lock, indent=2), encoding="utf-8")

    # Emit alert
    try:
        from agents.resilience import _emit_alert
        _emit_alert("emergency_stop", f"All {count} repos dropped to L0 (observe-only)",
                     severity="CRITICAL", component="emergency_stop_cli")
    except Exception:
        pass

    print(
        f"[EMERGENCY STOP] {count} repos dropped to L0. Lock file: {LOCK_FILE}")


def emergency_resume():
    """Restore repos to their previous autonomy level (or recompute)."""
    portfolio = _load_portfolio()
    count = 0
    for r in portfolio.get("repositories", []):
        prev = r.pop("_prev_autonomy", None)
        if prev:
            r["autonomy_level"] = prev
            count += 1
    _save_portfolio(portfolio)

    if LOCK_FILE.exists():
        LOCK_FILE.unlink()

    print(
        f"[RESUME] {count} repos restored to previous autonomy levels. Lock removed.")


def show_status():
    """Show current autonomy distribution and lock state."""
    portfolio = _load_portfolio()
    levels = {}
    for r in portfolio.get("repositories", []):
        lvl = r.get("autonomy_level", "L1")
        levels[lvl] = levels.get(lvl, 0) + 1

    locked = LOCK_FILE.exists()
    lock_info = ""
    if locked:
        try:
            lock_data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            lock_info = f" (since {lock_data.get('activated_at', '?')})"
        except Exception:
            pass

    print(f"Emergency lock: {'ACTIVE' + lock_info if locked else 'inactive'}")
    print(f"Repos by autonomy: {json.dumps(levels, indent=2)}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "stop":
        emergency_stop()
    elif cmd == "resume":
        emergency_resume()
    elif cmd == "status":
        show_status()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
