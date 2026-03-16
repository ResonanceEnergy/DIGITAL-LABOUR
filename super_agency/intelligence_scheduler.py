#!/usr/bin/env python3
"""
Intelligence Scheduler — runs weekly YouTube watchlist scans and queues
ingested content into the Second Brain pipeline for the daily brief.

Watchlist is stored in config/intelligence_watchlist.json.
Add a new orchestrator stage or run standalone.
"""
import json, sys, logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
WATCHLIST_FILE = ROOT / "config" / "intelligence_watchlist.json"
STATE_FILE = ROOT / "logs" / "intelligence_scheduler_state.json"
SECONDBRAIN_QUEUE = ROOT / "knowledge" / "secondbrain" / "pending.json"

DEFAULT_WATCHLIST = {
    "description": "YouTube channels and playlists for weekly intelligence scans",
    "scan_interval_days": 7,
    "sources": []
}


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_run": None, "runs": 0, "urls_queued": 0}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _load_watchlist() -> dict:
    if WATCHLIST_FILE.exists():
        return json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
    # Create default watchlist config
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_FILE.write_text(json.dumps(
        DEFAULT_WATCHLIST, indent=2), encoding="utf-8")
    logger.info(f"Created default watchlist at {WATCHLIST_FILE}")
    return DEFAULT_WATCHLIST


def should_run() -> bool:
    """Check if a weekly intelligence scan is due."""
    state = _load_state()
    watchlist = _load_watchlist()
    interval = watchlist.get("scan_interval_days", 7)

    if state["last_run"] is None:
        return True

    try:
        last = datetime.fromisoformat(state["last_run"])
        return datetime.now() - last > timedelta(days=interval)
    except (ValueError, TypeError):
        return True


def run_intelligence_scan():
    """Process all watchlist sources through Second Brain pipeline."""
    watchlist = _load_watchlist()
    sources = watchlist.get("sources", [])
    state = _load_state()

    if not sources:
        logger.info(
            "[INTEL] No sources in watchlist — add URLs to config/intelligence_watchlist.json")
        state["last_run"] = datetime.now().isoformat(timespec="seconds")
        _save_state(state)
        return {"queued": 0, "sources": 0}

    # Queue URLs into Second Brain pending queue
    SECONDBRAIN_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    try:
        pending = json.loads(SECONDBRAIN_QUEUE.read_text(
            encoding="utf-8")) if SECONDBRAIN_QUEUE.exists() else []
    except (json.JSONDecodeError, OSError):
        pending = []

    existing_urls = {item.get("url") for item in pending}
    queued = 0

    for source in sources:
        url = source if isinstance(source, str) else source.get("url", "")
        if not url or url in existing_urls:
            continue
        pending.append({
            "url": url,
            "queued_at": datetime.now().isoformat(timespec="seconds"),
            "source": "intelligence_scheduler",
        })
        existing_urls.add(url)
        queued += 1

    SECONDBRAIN_QUEUE.write_text(json.dumps(
        pending, indent=2), encoding="utf-8")

    state["last_run"] = datetime.now().isoformat(timespec="seconds")
    state["runs"] = state.get("runs", 0) + 1
    state["urls_queued"] = state.get("urls_queued", 0) + queued
    _save_state(state)

    logger.info(f"[INTEL] Queued {queued} URLs from {len(sources)} sources")
    return {"queued": queued, "sources": len(sources)}


def main():
    """Run weekly intelligence scan if due."""
    logging.basicConfig(level=logging.INFO)
    if should_run():
        result = run_intelligence_scan()
        print(f"[OK] Intelligence scan complete: {result}")
    else:
        state = _load_state()
        print(
            f"[SKIP] Not due yet — last run: {state.get('last_run', 'never')}")


if __name__ == "__main__":
    main()
