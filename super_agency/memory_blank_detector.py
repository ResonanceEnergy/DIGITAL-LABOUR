#!/usr/bin/env python3
"""
Memory Blank Detector — scans memory layers for gaps, corruption, or missing
snapshots and reports health status.
"""
import json
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / "memory_backups"
MEMORY_DIR = ROOT / "memory"


def detect_blanks() -> dict:
    """Scan memory state and return a health report.

    Returns dict with keys:
      healthy: bool, score: int (0-100), issues: list[str],
      last_backup: str|None, backup_count: int, memory_files: int
    """
    issues = []
    score = 100

    # 1. Check backup directory
    backup_count = 0
    last_backup_ts = None
    if BACKUP_DIR.exists():
        snapshots = sorted(BACKUP_DIR.glob("memory_snapshot_*"), reverse=True)
        backup_count = len(snapshots)
        if backup_count == 0:
            issues.append("No memory backup snapshots found")
            score -= 30
        else:
            # Check recency
            latest = snapshots[0]
            try:
                # Parse timestamp from directory name: memory_snapshot_YYYYMMDD_HHMMSS
                ts_str = latest.name.replace("memory_snapshot_", "")
                last_backup_ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                age = datetime.now() - last_backup_ts
                if age > timedelta(hours=2):
                    issues.append(
                        f"Last backup is {age.total_seconds() / 3600:.1f}h old")
                    score -= 15
            except (ValueError, IndexError):
                last_backup_ts = None
    else:
        issues.append("Memory backup directory missing")
        score -= 30

    # 2. Check memory files
    memory_files = 0
    if MEMORY_DIR.exists():
        memory_files = len(list(MEMORY_DIR.glob("*.json"))) + \
                           len(list(MEMORY_DIR.glob("*.md")))
        if memory_files == 0:
            issues.append("No memory files found in memory/")
            score -= 20
    else:
        issues.append("memory/ directory missing")
        score -= 20

    # 3. Check memory system state files
    state_dir = ROOT / "state"
    if state_dir.exists():
        state_files = list(state_dir.rglob("*.json"))
        if not state_files:
            issues.append("No state files found")
            score -= 10
    else:
        issues.append("state/ directory missing")
        score -= 10

    # 4. Check for memory doctrine system
    doctrine_ok = False
    try:
        from unified_memory_doctrine_system import get_unified_memory_system
        mem = get_unified_memory_system()
        if hasattr(mem, "layers") and len(mem.layers) > 0:
            doctrine_ok = True
        else:
            issues.append("Memory doctrine has no layers")
            score -= 15
    except ImportError:
        try:
            from memory_doctrine_system import get_memory_system
            doctrine_ok = True
        except ImportError:
            issues.append("No memory doctrine system importable")
            score -= 15

    score = max(0, score)
    return {
        "healthy": score >= 70,
        "score": score,
        "issues": issues,
        "last_backup": last_backup_ts.isoformat() if last_backup_ts else None,
        "backup_count": backup_count,
        "memory_files": memory_files,
        "doctrine_loaded": doctrine_ok,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


if __name__ == "__main__":
    report = detect_blanks()
    print(json.dumps(report, indent=2))
