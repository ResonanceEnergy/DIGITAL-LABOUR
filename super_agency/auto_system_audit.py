#!/usr/bin/env python3
"""
BIT RAGE LABOUR Auto System Audit
Runs every 15 minutes to check system health and fix issues
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import psutil

WORKSPACE = Path(__file__).parent
AUDIT_LOG = WORKSPACE / "audit_logs"
AUDIT_LOG.mkdir(exist_ok=True)


def run_python_audit():
    """Check all Python files for syntax errors"""
    errors = []
    fixed = []

    for py_file in WORKSPACE.glob("*.py"):
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                errors.append(
                    {"file": py_file.name, "error": result.stderr[:200]})
        except Exception as e:
            errors.append({"file": py_file.name, "error": str(e)})

    return {"total_files": len(list(WORKSPACE.glob("*.py"))), "errors": errors}


def check_critical_services():
    """Check if critical services are running"""
    services = {
        "streamlit_dashboard": False,
        "production_state_fresh": False,
        "portfolio_exists": False,
    }

    # Check Streamlit
    for proc in psutil.process_iter(["cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"] or [])
            if "streamlit" in cmdline and "dashboard.py" in cmdline:
                services["streamlit_dashboard"] = True
                break
        except:
            pass

    # Check production state freshness (< 1 hour old)
    state_file = WORKSPACE / "production_state.json"
    if state_file.exists():
        age_seconds = datetime.now().timestamp() - state_file.stat().st_mtime
        services["production_state_fresh"] = age_seconds < 3600

    # Check portfolio
    portfolio_file = WORKSPACE / "portfolio.json"
    services["portfolio_exists"] = portfolio_file.exists()

    return services


def get_system_metrics():
    """Get current system metrics"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage(os.sep).percent,
        "uptime_hours": (datetime.now().timestamp() - psutil.boot_time()) / 3600,
    }


def check_folder_structure():
    """Verify expected folder structure exists"""
    expected_folders = ["MATRIX_MAXIMIZER", "MATRIX_MONITOR", "archive"]
    expected_files = ["portfolio.json", "production_state.json"]

    results = {
        "folders": {f: (WORKSPACE / f).is_dir() for f in expected_folders},
        "files": {f: (WORKSPACE / f).exists() for f in expected_files},
    }
    return results


def run_full_audit():
    """Run complete system audit"""
    timestamp = datetime.now().isoformat()

    audit_result = {
        "timestamp": timestamp,
        "python_audit": run_python_audit(),
        "services": check_critical_services(),
        "system_metrics": get_system_metrics(),
        "structure": check_folder_structure(),
    }

    # Calculate overall health
    issues = []
    if audit_result["python_audit"]["errors"]:
        issues.append(
            f"{len(audit_result['python_audit']['errors'])} Python syntax errors"
        )
    if not audit_result["services"]["streamlit_dashboard"]:
        issues.append("Dashboard not running")
    if not audit_result["services"]["production_state_fresh"]:
        issues.append("Production state stale")
    if audit_result["system_metrics"]["cpu_percent"] > 90:
        issues.append("High CPU usage")
    if audit_result["system_metrics"]["memory_percent"] > 90:
        issues.append("High memory usage")

    audit_result["health_status"] = "HEALTHY" if not issues else "ISSUES_DETECTED"
    audit_result["issues"] = issues

    # Save audit log
    log_file = AUDIT_LOG / \
        f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w") as f:
        json.dump(audit_result, f, indent=2)

    # Keep only last 100 audit logs
    logs = sorted(AUDIT_LOG.glob("audit_*.json"))
    for old_log in logs[:-100]:
        old_log.unlink()

    return audit_result


def print_audit_report(result):
    """Print formatted audit report"""
    print("=" * 60)
    print(f"🔍 BIT RAGE LABOUR AUTO AUDIT - {result['timestamp']}")
    print("=" * 60)

    print(f"\n📊 System Metrics:")
    print(f"   CPU: {result['system_metrics']['cpu_percent']:.1f}%")
    print(f"   Memory: {result['system_metrics']['memory_percent']:.1f}%")
    print(f"   Disk: {result['system_metrics']['disk_percent']:.1f}%")
    print(f"   Uptime: {result['system_metrics']['uptime_hours']:.1f}h")

    print(f"\n🐍 Python Files:")
    print(f"   Total: {result['python_audit']['total_files']}")
    print(f"   Errors: {len(result['python_audit']['errors'])}")

    print(f"\n🔧 Services:")
    for service, status in result["services"].items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {service}")

    print(f"\n📁 Structure:")
    for folder, exists in result["structure"]["folders"].items():
        icon = "✅" if exists else "❌"
        print(f"   {icon} {folder}/")

    print(f"\n🏥 Health Status: {result['health_status']}")
    if result["issues"]:
        print("   Issues:")
        for issue in result["issues"]:
            print(f"   ⚠️  {issue}")

    print("=" * 60)


if __name__ == "__main__":
    result = run_full_audit()
    print_audit_report(result)
