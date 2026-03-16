#!/usr/bin/env python3
"""
METRICS STORE — Time-series storage for MATRIX MAXIMIZER Phase 2.
Stores metric snapshots as JSONL, auto-prunes to 7 days.
Provides history retrieval for charts.
"""

import fcntl
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Where metrics are stored
_THIS_DIR = Path(__file__).resolve().parent
STATE_DIR = _THIS_DIR / "state"
METRICS_FILE = STATE_DIR / "matrix_metrics.jsonl"
PRUNE_DAYS = 7
MAX_FILE_SIZE_MB = 50  # Safety limit


def _ensure_state_dir():
    """Create state/ directory if missing."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def record_snapshot(data: Dict[str, Any]) -> bool:
    """
    Append a compact metric snapshot to the JSONL file.
    Extracts only the key numeric metrics to keep file small.
    Returns True on success.
    """
    _ensure_state_dir()

    sys_data = data.get("system", {})
    health = data.get("health", {}).get("integration_tests", {})
    orch = data.get("orchestration", {})
    backups = data.get("backups", {})

    snapshot = {
        "ts": data.get("timestamp", datetime.now().isoformat()),
        "cpu": sys_data.get("cpu_percent"),
        "mem": sys_data.get("memory_percent"),
        "disk": sys_data.get("disk_percent"),
        "net_s": sys_data.get("net_sent_mb"),
        "net_r": sys_data.get("net_recv_mb"),
        "procs": sys_data.get("process_count"),
        "hs": data.get("health_score"),
        "tests_pass": health.get("passed"),
        "tests_fail": health.get("failed"),
        "orch_cycles": orch.get("total_cycles"),
        "bk_count": backups.get("backup_count"),
        "bk_size_kb": backups.get("total_size_kb"),
        "py_procs": data.get("processes", {}).get("python_processes"),
    }

    # Add battery if present
    bat = sys_data.get("battery")
    if bat:
        snapshot["bat"] = bat.get("percent")
        snapshot["bat_plug"] = bat.get("plugged_in")

    try:
        line = json.dumps(snapshot, separators=(",", ":")) + "\n"
        with open(METRICS_FILE, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(line)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return True
    except Exception as e:
        logger.error(f"Failed to record snapshot: {e}")
        return False


def get_history(
    period: str = "1h",
    metric: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve historical metrics for a given time period.

    Args:
        period: One of "1h", "6h", "24h", "7d"
        metric: Optional specific metric key to return (e.g. "cpu", "mem")

    Returns:
        {
            "period": "1h",
            "count": 120,
            "timestamps": [...],
            "cpu": [...],
            "mem": [...],
            ...
        }
    """
    duration_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }
    delta = duration_map.get(period, timedelta(hours=1))
    cutoff = datetime.now() - delta

    result = {
        "period": period,
        "count": 0,
        "timestamps": [],
        "cpu": [],
        "mem": [],
        "disk": [],
        "hs": [],
        "procs": [],
        "net_s": [],
        "net_r": [],
    }

    if not METRICS_FILE.exists():
        return result

    # Downsample target: ~200 points max for charts
    max_points = 200

    try:
        entries = []
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts_str = entry.get("ts", "")
                    ts = datetime.fromisoformat(ts_str)
                    if ts >= cutoff:
                        entries.append(entry)
                except (json.JSONDecodeError, ValueError):
                    continue

        # Downsample if too many points
        if len(entries) > max_points:
            step = len(entries) / max_points
            sampled = []
            i = 0.0
            while int(i) < len(entries):
                sampled.append(entries[int(i)])
                i += step
            entries = sampled

        for entry in entries:
            result["timestamps"].append(entry.get("ts"))
            result["cpu"].append(entry.get("cpu"))
            result["mem"].append(entry.get("mem"))
            result["disk"].append(entry.get("disk"))
            result["hs"].append(entry.get("hs"))
            result["procs"].append(entry.get("procs"))
            result["net_s"].append(entry.get("net_s"))
            result["net_r"].append(entry.get("net_r"))

        result["count"] = len(entries)

    except Exception as e:
        logger.error(f"Failed to read history: {e}")

    # If a specific metric was requested, trim to just that
    if metric and metric in result:
        return {
            "period": period,
            "count": result["count"],
            "timestamps": result["timestamps"],
            metric: result[metric],
        }

    return result


def get_stats(period: str = "1h") -> Dict[str, Any]:
    """
    Get summary statistics for a period (min/max/avg for each metric).
    """
    history = get_history(period)
    stats = {"period": period, "points": history["count"]}

    for key in ("cpu", "mem", "disk", "hs"):
        values = [v for v in history.get(key, []) if v is not None]
        if values:
            stats[key] = {
                "min": round(min(values), 1),
                "max": round(max(values), 1),
                "avg": round(sum(values) / len(values), 1),
                "latest": round(values[-1], 1),
            }
        else:
            stats[key] = {"min": None, "max": None,
                "avg": None, "latest": None}

    return stats


def prune_old_entries():
    """
    Remove entries older than PRUNE_DAYS.
    Also enforces MAX_FILE_SIZE_MB.
    """
    if not METRICS_FILE.exists():
        return

    # Check file size first
    file_size_mb = METRICS_FILE.stat().st_size / (1024 * 1024)
    cutoff = datetime.now() - timedelta(days=PRUNE_DAYS)

    try:
        kept = []
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry.get("ts", ""))
                    if ts >= cutoff:
                        kept.append(line)
                except (json.JSONDecodeError, ValueError):
                    continue

        # If file is oversized, keep only last 50%
        if file_size_mb > MAX_FILE_SIZE_MB:
            kept = kept[len(kept) // 2 :]
            logger.warning(
                f"Metrics file was {file_size_mb:.1f}MB, pruned to {len(kept)} entries"
            )

        # Write back atomically
        tmp_path = METRICS_FILE.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            for line in kept:
                f.write(line + "\n")
        tmp_path.replace(METRICS_FILE)
        logger.info(
            f"Pruned metrics: kept {len(kept)} entries within {PRUNE_DAYS} days"
        )

    except Exception as e:
        logger.error(f"Prune failed: {e}")


def get_file_info() -> Dict[str, Any]:
    """Return info about the metrics store file."""
    if not METRICS_FILE.exists():
        return {"exists": False, "size_kb": 0, "entries": 0}

    try:
        size = METRICS_FILE.stat().st_size
        count = 0
        with open(METRICS_FILE, "r") as f:
            for _ in f:
                count += 1
        return {
            "exists": True,
            "size_kb": round(size / 1024, 1),
            "size_mb": round(size / (1024 * 1024), 2),
            "entries": count,
            "path": str(METRICS_FILE),
        }
    except Exception:
        return {"exists": True, "size_kb": 0, "entries": 0}


if __name__ == "__main__":
    """Quick test."""
    _ensure_state_dir()
    # Test recording
    from data_collector import collect_all

    data = collect_all()
    ok = record_snapshot(data)
    print(f"Record: {'OK' if ok else 'FAIL'}")
    info = get_file_info()
    print(f"Store: {info}")
    stats = get_stats("1h")
    print(f"Stats: {stats}")
