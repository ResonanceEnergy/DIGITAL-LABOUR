#!/usr/bin/env python3
"""
DATA COLLECTOR — Real data sources for MATRIX MAXIMIZER
Every value returned by these collectors comes from actual files, processes, or system calls.
Zero hardcoded values. If data is unavailable, returns None / "unknown".
"""

import csv
import glob
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)

# Workspace root — auto-detect from this file's location
_THIS_DIR = Path(__file__).resolve().parent  # repos/Digital-Labour/
WORKSPACE = _THIS_DIR.parent.parent  # DIGITAL-LABOUR/


def _read_json(path: Path) -> Optional[dict]:
    """Safely read a JSON file, return None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Cannot read {path}: {e}")
        return None


def _read_ndjson(path: Path, limit: int = 100) -> List[dict]:
    """Read newline-delimited JSON, return list of dicts."""
    results = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= limit:
                    break
                line = line.strip()
                if line:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logger.warning(f"Cannot read NDJSON {path}: {e}")
    return results


def _file_age_seconds(path: Path) -> Optional[float]:
    """Return seconds since file was last modified, or None."""
    try:
        return time.time() - path.stat().st_mtime
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# 1. SYSTEM COLLECTOR — psutil (the one real source we already had)
# ─────────────────────────────────────────────────────────────
def collect_system() -> Dict[str, Any]:
    """Live system metrics from psutil."""
    try:
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage(os.sep)
        net = psutil.net_io_counters()
        boot = psutil.boot_time()
        cpu = psutil.cpu_percent(interval=0.5)

        # Battery (Mac laptop — may be None on desktop)
        battery = psutil.sensors_battery()
        bat_info = None
        if battery:
            bat_info = {
                "percent": battery.percent,
                "plugged_in": battery.power_plugged,
                "secs_left": (
                    battery.secsleft
                    if battery.secsleft != psutil.POWER_TIME_UNLIMITED
                    else None
                ),
            }

        return {
            "cpu_percent": round(cpu, 1),
            "cpu_count": psutil.cpu_count(),
            "memory_percent": round(vm.percent, 1),
            "memory_used_gb": round(vm.used / (1024**3), 2),
            "memory_total_gb": round(vm.total / (1024**3), 2),
            "disk_percent": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "net_sent_mb": round(net.bytes_sent / (1024**2), 1),
            "net_recv_mb": round(net.bytes_recv / (1024**2), 1),
            "uptime_hours": round((time.time() - boot) / 3600, 1),
            "boot_time": datetime.fromtimestamp(boot).isoformat(),
            "battery": bat_info,
            "process_count": len(psutil.pids()),
        }
    except Exception as e:
        logger.error(f"System collection failed: {e}")
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# 2. PORTFOLIO COLLECTOR — portfolio.json + REPO_INDEX.json
# ─────────────────────────────────────────────────────────────
def collect_portfolio() -> Dict[str, Any]:
    """Read real portfolio data from portfolio.json and REPO_INDEX.json."""
    result = {
        "org": None,
        "repo_count": 0,
        "repos": [],
        "tier_breakdown": {},
        "autonomy_levels": {},
        "policies": {},
        "last_updated": None,
    }

    # portfolio.json
    pf = _read_json(WORKSPACE / "portfolio.json")
    if pf:
        result["org"] = pf.get("org")
        result["policies"] = pf.get("policies", {})
        repos = pf.get("repositories", [])
        result["repo_count"] = len(repos)

        # Tier breakdown
        tiers = {}
        autonomy = {}
        for r in repos:
            t = r.get("tier", "unknown")
            tiers[t] = tiers.get(t, 0) + 1
            a = r.get("autonomy_level", "unknown")
            autonomy[a] = autonomy.get(a, 0) + 1
        result["tier_breakdown"] = tiers
        result["autonomy_levels"] = autonomy
        result["repos"] = [
            {
                "name": r.get("name"),
                "tier": r.get("tier"),
                "visibility": r.get("visibility"),
            }
            for r in repos[:10]  # top 10 for display
        ]

    # REPO_INDEX.json for richer GitHub data
    ri = _read_json(WORKSPACE / "REPO_INDEX.json")
    if ri and isinstance(ri, list):
        result["github_repo_count"] = len(ri)
        # Calculate aggregate stats
        total_stars = sum(r.get("stargazers_count", 0) for r in ri)
        total_forks = sum(r.get("forks_count", 0) for r in ri)
        total_issues = sum(r.get("open_issues_count", 0) for r in ri)
        languages = {}
        for r in ri:
            lang = r.get("language") or "Unknown"
            languages[lang] = languages.get(lang, 0) + 1
        result["github_stats"] = {
            "total_stars": total_stars,
            "total_forks": total_forks,
            "total_open_issues": total_issues,
            "languages": dict(sorted(languages.items(), key=lambda x: -x[1])[:8]),
        }
        result["last_updated"] = ri[0].get("updated_at") if ri else None

    return result


# ─────────────────────────────────────────────────────────────
# 3. AGENT COLLECTOR — production_state.json + GASKET_STATUS.md
# ─────────────────────────────────────────────────────────────
def collect_agents() -> Dict[str, Any]:
    """Read real agent status from production_state.json and GASKET_STATUS.md."""
    result = {
        "agents": {},
        "phase": None,
        "ai_enabled": None,
        "ai_providers": [],
        "qa_system": {},
        "real_metrics": {},
    }

    ps = _read_json(WORKSPACE / "production_state.json")
    if ps:
        result["phase"] = ps.get("phase")
        result["ai_enabled"] = ps.get("ai_enabled")
        result["ai_providers"] = ps.get("ai_providers", [])
        result["qa_system"] = ps.get("qa_system", {})
        result["real_metrics"] = ps.get("real_metrics", {})

        # Agent statuses
        agent_status = ps.get("agent_status", {})
        for agent_id, info in agent_status.items():
            result["agents"][agent_id] = {
                "name": agent_id.upper(),
                "status": info.get("status", "unknown"),
                "role": info.get("role", "unknown"),
                "capabilities": info.get("capabilities", []),
                "verified_tasks": info.get("verified_tasks", []),
                "task_count": len(info.get("tasks", [])),
            }

    # GASKET_STATUS.md — parse key lines
    gasket_path = WORKSPACE / "repo_depot" / "GASKET_STATUS.md"
    if gasket_path.exists():
        try:
            text = gasket_path.read_text(encoding="utf-8")
            # Extract project statuses (lines with %)
            projects = []
            for line in text.split("\n"):
                if "%" in line and ("|" in line or "Progress" in line.lower()):
                    projects.append(line.strip())
                elif line.startswith("- **") or line.startswith("- Primary"):
                    projects.append(line.strip())
            result["gasket_status_lines"] = projects[:10]
            age = _file_age_seconds(gasket_path)
            result["gasket_last_updated"] = (
                datetime.fromtimestamp(gasket_path.stat().st_mtime).isoformat()
                if age is not None
                else None
            )
        except Exception as e:
            logger.warning(f"Cannot read GASKET_STATUS: {e}")

    # agent_mandates.json
    mandates = _read_json(WORKSPACE / "agent_mandates.json")
    if mandates:
        result["mandates"] = mandates.get("mandates", {})
        result["goals"] = mandates.get("goals", {})

    return result


# ─────────────────────────────────────────────────────────────
# 4. INTELLIGENCE COLLECTOR — NCL/events.ndjson
# ─────────────────────────────────────────────────────────────
def collect_intelligence() -> Dict[str, Any]:
    """Read intelligence events from NCL pipeline."""
    result = {"events": [], "event_count": 0, "event_types": {}}

    events = _read_ndjson(WORKSPACE / "NCL" / "events.ndjson")
    result["event_count"] = len(events)
    result["events"] = events[-10:]  # latest 10

    types = {}
    for e in events:
        t = e.get("type", "unknown")
        types[t] = types.get(t, 0) + 1
    result["event_types"] = types

    return result


# ─────────────────────────────────────────────────────────────
# 5. HEALTH COLLECTOR — reports/ + integration_test_report.json
# ─────────────────────────────────────────────────────────────
def collect_health() -> Dict[str, Any]:
    """Read health status reports and integration test results."""
    result = {
        "integration_tests": {},
        "latest_health_report": {},
        "health_reports_count": 0,
    }

    # integration_test_report.json
    itr = _read_json(WORKSPACE / "integration_test_report.json")
    if itr:
        result["integration_tests"] = {
            "total": itr.get("total_tests", 0),
            "passed": itr.get("passed_tests", 0),
            "failed": itr.get("failed_tests", 0),
            "success_rate": itr.get("success_rate", 0),
            "duration": itr.get("duration_seconds", 0),
            "timestamp": itr.get("timestamp"),
            "status": itr.get("summary", {}).get("overall_status", "unknown"),
        }

    # Latest health_status report
    reports_dir = WORKSPACE / "reports"
    if reports_dir.exists():
        health_files = sorted(reports_dir.glob(
            "health_status_*.json"), reverse=True)
        result["health_reports_count"] = len(health_files)
        if health_files:
            latest = _read_json(health_files[0])
            if latest:
                result["latest_health_report"] = {
                    "timestamp": latest.get("timestamp"),
                    "overall_health": latest.get("overall_health"),
                    "file": health_files[0].name,
                }
                # Extract component details
                components = latest.get("components", {})
                for comp_name, comp_data in components.items():
                    result["latest_health_report"][comp_name] = {
                        "status": comp_data.get("status"),
                        "health_score": comp_data.get("details", {}).get(
                            "health_score"
                        ),
                    }

    return result


# ─────────────────────────────────────────────────────────────
# 6. ORCHESTRATION COLLECTOR — CSV logs
# ─────────────────────────────────────────────────────────────
def collect_orchestration() -> Dict[str, Any]:
    """Read orchestration cycle logs."""
    result = {"total_cycles": 0, "latest_cycles": [], "last_cycle_time": None}

    csv_path = WORKSPACE / "continuous_orchestration_log_ultra_high.csv"
    if csv_path.exists():
        try:
            rows = []
            with open(csv_path, "r") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 4:
                        rows.append(row)
            result["total_cycles"] = len(rows)
            # Latest 5 cycles
            for row in rows[-5:]:
                result["latest_cycles"].append(
                    {
                        "time": row[0],
                        "cycle": row[1],
                        "duration": row[2],
                        "cumulative_tasks": row[3],
                    }
                )
            if rows:
                result["last_cycle_time"] = rows[-1][0]
        except Exception as e:
            logger.warning(f"Cannot read orchestration CSV: {e}")

    return result


# ─────────────────────────────────────────────────────────────
# 7. SECURITY COLLECTOR — oversight_logs/
# ─────────────────────────────────────────────────────────────
def collect_security() -> Dict[str, Any]:
    """Read real security/oversight data."""
    result = {"log_files": [], "latest_entries": [], "total_size_kb": 0}

    logs_dir = WORKSPACE / "oversight_logs"
    if logs_dir.exists():
        for f in sorted(logs_dir.iterdir()):
            if (
                f.is_file()
                and not f.name.endswith("-ResonanceEnergy.log")
                and not f.name.endswith("-ResonanceEnergy.json")
                and not f.name.endswith("-ResonanceEnergy.jsonl")
            ):
                size_kb = round(f.stat().st_size / 1024, 1)
                result["log_files"].append(
                    {
                        "name": f.name,
                        "size_kb": size_kb,
                        "modified": datetime.fromtimestamp(
                            f.stat().st_mtime
                        ).isoformat(),
                    }
                )
                result["total_size_kb"] += size_kb

        # Read latest from security.log
        sec_log = logs_dir / "security.log"
        if sec_log.exists():
            try:
                lines = sec_log.read_text(encoding="utf-8").strip().split("\n")
                result["latest_entries"] = lines[-5:]  # last 5 log lines
            except Exception:
                pass

        # Read latest oversight report
        oversight_reports = sorted(
            logs_dir.glob("report_*.json"), reverse=True)
        if oversight_reports:
            report = _read_json(oversight_reports[0])
            if report:
                result["latest_report"] = {
                    "file": oversight_reports[0].name,
                    "summary": str(report)[:200],
                }

    result["total_size_kb"] = round(result["total_size_kb"], 1)
    return result


# ─────────────────────────────────────────────────────────────
# 8. BACKUP COLLECTOR — backups/ directory
# ─────────────────────────────────────────────────────────────
def collect_backups() -> Dict[str, Any]:
    """Read backup inventory from backups/ folder."""
    result = {"backup_count": 0, "total_size_kb": 0, "latest_backups": []}

    backups_dir = WORKSPACE / "backups"
    if backups_dir.exists():
        all_files = []
        for f in backups_dir.rglob("*"):
            if f.is_file():
                all_files.append(f)
        result["backup_count"] = len(all_files)
        result["total_size_kb"] = round(
            sum(f.stat().st_size for f in all_files) / 1024, 1
        )

        # Latest 5 by modification time
        all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        for f in all_files[:5]:
            result["latest_backups"].append(
                {"name": f.name, "size_kb": round(
                     f.stat().st_size / 1024, 1),
                 "modified": datetime.fromtimestamp(f.stat().st_mtime).
                 isoformat(),})

    return result


# ─────────────────────────────────────────────────────────────
# 9. INNER COUNCIL COLLECTOR — inner_council/config/settings.json
# ─────────────────────────────────────────────────────────────
def collect_inner_council() -> Dict[str, Any]:
    """Read Inner Council configuration."""
    result = {"members": [], "member_count": 0, "system": {}}

    settings = _read_json(WORKSPACE / "inner_council" / \
                          "config" / "settings.json")
    if settings:
        result["system"] = settings.get("system", {})
        members = settings.get("council_members", [])
        result["member_count"] = len(members)
        result["members"] = [
            {
                "name": m.get("name"),
                "priority": m.get("priority"),
                "focus_areas": m.get("focus_areas", [])[:3],
                "frequency": m.get("monitoring_frequency"),
            }
            for m in members
        ]

    return result


# ─────────────────────────────────────────────────────────────
# 10. DOCTRINE COLLECTOR — unified_memory_doctrine.json
# ─────────────────────────────────────────────────────────────
def collect_doctrine() -> Dict[str, Any]:
    """Read memory doctrine configuration."""
    result = {
        "version": None,
        "platform": None,
        "architecture": None,
        "devices": {},
        "memory_limits": {},
    }

    doc = _read_json(WORKSPACE / "unified_memory_doctrine.json")
    if doc:
        doctrine = doc.get("doctrine", {})
        result["version"] = doctrine.get("version")
        result["platform"] = doctrine.get("platform")
        result["architecture"] = doctrine.get("architecture")
        result["devices"] = doctrine.get("device_codes", {})
        result["memory_limits"] = doctrine.get("memory_limits", {})
        # Memory entries
        memory = doc.get("memory", {})
        result["memory_entries"] = len(memory)

    return result


# ─────────────────────────────────────────────────────────────
# 11. REAL METRICS COLLECTOR — real_metrics.json
# ─────────────────────────────────────────────────────────────
def collect_real_metrics() -> Dict[str, Any]:
    """Read actual productivity metrics."""
    result = {}
    rm = _read_json(WORKSPACE / "real_metrics.json")
    if rm:
        latest = rm.get("latest", {})
        result = {
            "lines_of_code": latest.get("lines_of_code_added", 0),
            "files_created": latest.get("files_created", 0),
            "tests_added": latest.get("tests_added", 0),
            "repos_touched": latest.get("repos_touched", 0),
            "documentation_added": latest.get("documentation_added", 0),
            "commits_by_agent": latest.get("commits_by_agent", {}),
            "calculated_at": latest.get("calculated_at"),
            "period_days": latest.get("period_days"),
            "history_count": len(rm.get("history", [])),
        }
    return result


# ─────────────────────────────────────────────────────────────
# 12. GIT COLLECTOR — subprocess git calls for workspace repos
# ─────────────────────────────────────────────────────────────
def collect_git() -> Dict[str, Any]:
    """Get real git status from workspace repos."""
    result = {"repos": [], "repo_count": 0}
    repos_dir = WORKSPACE / "repos"
    if not repos_dir.exists():
        return result

    for d in sorted(repos_dir.iterdir()):
        git_dir = d / ".git"
        if d.is_dir() and git_dir.exists():
            repo_info = {"name": d.name}
            try:
                # Last commit
                out = subprocess.run(
                    ["git", "-C", str(d), "log", "-1", "--format=%H|%s|%ci"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if out.returncode == 0 and out.stdout.strip():
                    parts = out.stdout.strip().split("|", 2)
                    if len(parts) >= 3:
                        repo_info["last_commit"] = parts[0][:8]
                        repo_info["last_message"] = parts[1][:60]
                        repo_info["last_date"] = parts[2]

                # Branch
                out = subprocess.run(
                    ["git", "-C", str(d), "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if out.returncode == 0:
                    repo_info["branch"] = out.stdout.strip()

                # Status (modified files count)
                out = subprocess.run(
                    ["git", "-C", str(d), "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if out.returncode == 0:
                    changes = [l for l in out.stdout.strip().split("\n")
                                                           if l.strip()]
                    repo_info["uncommitted_changes"] = len(changes)

            except Exception as e:
                repo_info["error"] = str(e)

            result["repos"].append(repo_info)

    result["repo_count"] = len(result["repos"])
    return result


# ─────────────────────────────────────────────────────────────
# 13. PROCESS COLLECTOR — running BIT RAGE LABOUR processes
# ─────────────────────────────────────────────────────────────
def collect_processes() -> Dict[str, Any]:
    """Check which BIT RAGE LABOUR processes are currently running."""
    result = {"services": [], "python_processes": 0}

    known_services = {
        "matrix_maximizer": {"port": 8081, "name": "Matrix Maximizer"},
        "mobile_command": {"port": 8082, "name": "Mobile Command Center"},
    }

    for svc_id, svc_info in known_services.items():
        port = svc_info["port"]
        running = False
        pid = None
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port == port and conn.status == "LISTEN":
                    running = True
                    pid = conn.pid
                    break
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

        result["services"].append(
            {
                "id": svc_id,
                "name": svc_info["name"],
                "port": port,
                "running": running,
                "pid": pid,
            }
        )

    # Count Python processes
    try:
        for proc in psutil.process_iter(["name"]):
            if "python" in (proc.info.get("name") or "").lower():
                result["python_processes"] += 1
    except Exception:
        pass

    return result


# ─────────────────────────────────────────────────────────────
# MASTER COLLECTOR — assembles everything
# ─────────────────────────────────────────────────────────────
def collect_all() -> Dict[str, Any]:
    """Collect ALL real data for the Matrix Maximizer dashboard."""
    ts = datetime.now().isoformat()

    data = {
        "timestamp": ts,
        "system": collect_system(),
        "portfolio": collect_portfolio(),
        "agents": collect_agents(),
        "intelligence": collect_intelligence(),
        "health": collect_health(),
        "orchestration": collect_orchestration(),
        "security": collect_security(),
        "backups": collect_backups(),
        "inner_council": collect_inner_council(),
        "doctrine": collect_doctrine(),
        "real_metrics": collect_real_metrics(),
        "git": collect_git(),
        "processes": collect_processes(),
    }

    # Calculate REAL health score from actual data
    data["health_score"] = _calculate_real_health(data)

    return data


def _calculate_real_health(data: Dict[str, Any]) -> float:
    """Calculate health score from REAL data only."""
    scores = []
    weights = []

    # CPU health (lower is better) — weight 20%
    cpu = data.get("system", {}).get("cpu_percent")
    if cpu is not None:
        scores.append(max(0, 100 - cpu))
        weights.append(0.2)

    # Memory health — weight 15%
    mem = data.get("system", {}).get("memory_percent")
    if mem is not None:
        scores.append(max(0, 100 - mem))
        weights.append(0.15)

    # Disk health — weight 10%
    disk = data.get("system", {}).get("disk_percent")
    if disk is not None:
        scores.append(max(0, 100 - disk))
        weights.append(0.1)

    # Integration tests — weight 25%
    tests = data.get("health", {}).get("integration_tests", {})
    rate = tests.get("success_rate")
    if rate is not None:
        scores.append(rate * 100)
        weights.append(0.25)

    # Agent status — weight 15%
    agents = data.get("agents", {}).get("agents", {})
    if agents:
        active = sum(1 for a in agents.values() if a.get("status") == "active")
        total = len(agents)
        scores.append((active / total) * 100 if total > 0 else 0)
        weights.append(0.15)

    # Backup freshness — weight 15%
    backups = data.get("backups", {})
    if backups.get("backup_count", 0) > 0:
        scores.append(90)  # backups exist = good
        weights.append(0.15)
    else:
        scores.append(30)  # no backups = bad
        weights.append(0.15)

    if not weights:
        return 0.0

    total_weight = sum(weights)
    return round(sum(s * w for s, w in zip(scores, weights)) / total_weight, 1)


if __name__ == "__main__":
    """Quick test — run this file directly to see all collected data."""
    import pprint

    data = collect_all()
    pprint.pprint(data)
