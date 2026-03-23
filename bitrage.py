"""DIGITAL LABOUR — Master Launcher & Control Panel.

Consolidates: launch.py, matrix_boot.py, setup_keys.py, watchdog,
              dashboard/health.py, and all daemon management.
Integrates:   NCC (governance), NCL (brain), AAC (bank) via resonance bridges.

This is the ONE command to rule them all.

Usage:
    python bitrage.py                    # Interactive menu
    python bitrage.py start              # Start server + all daemons
    python bitrage.py stop               # Stop everything
    python bitrage.py status             # Full system status
    python bitrage.py daemons            # Start daemons only (no server)
    python bitrage.py server             # Start API server only
    python bitrage.py health             # Health dashboard
    python bitrage.py setup              # Interactive .env key setup
    python bitrage.py checks             # Run one-shot system checks
    python bitrage.py monitor            # Launch Matrix Monitor (separate exe)
    python bitrage.py sync               # Run NCC/NCL/AAC resonance sync
    python bitrage.py preflight          # Pre-launch readiness check

Build:  pyinstaller bitrage.spec
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── UTF-8 stdout fix for Windows ───────────────────────────────
import io
if sys.stdout and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Project Setup ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
# pythonw.exe = windowless Python — no console host for background daemons
VENV_PYTHONW = PROJECT_ROOT / ".venv" / "Scripts" / "pythonw.exe"
PYTHONW = str(VENV_PYTHONW) if VENV_PYTHONW.exists() else PYTHON
DAEMON_PID_FILE = PROJECT_ROOT / "data" / "daemon_pids.json"
LOG_DIR = PROJECT_ROOT / "data"
LOG_DIR.mkdir(parents=True, exist_ok=True)

VERSION = "2.0.0"
BANNER = f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗ ██╗████████╗    ██████╗  █████╗  ██████╗ ███████╗   ║
║   ██╔══██╗██║╚══██╔══╝    ██╔══██╗██╔══██╗██╔════╝ ██╔════╝   ║
║   ██████╔╝██║   ██║       ██████╔╝███████║██║  ███╗█████╗     ║
║   ██╔══██╗██║   ██║       ██╔══██╗██╔══██║██║   ██║██╔══╝     ║
║   ██████╔╝██║   ██║       ██║  ██║██║  ██║╚██████╔╝███████╗   ║
║   ╚═════╝ ╚═╝   ╚═╝       ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ║
║                                                               ║
║   DIGITAL LABOUR — Master Control v{VERSION:<25}          ║
║   24 AI Agents • NERVE • C-Suite • NCC/NCL/AAC               ║
╚═══════════════════════════════════════════════════════════════╝
"""

# ── Required / Recommended Keys ───────────────────────────────
REQUIRED_KEYS = {
    "core": ["MATRIX_AUTH_TOKEN"],
    "email": ["SMTP_HOST", "SMTP_USER", "SMTP_PASS"],
    "billing": ["STRIPE_API_KEY"],
    "llm": ["OPENAI_API_KEY"],
}

RECOMMENDED_KEYS = {
    "social": ["X_BEARER_TOKEN"],
    "llm_backup": ["ANTHROPIC_API_KEY", "GEMINI_API_KEY"],
}


# ═══════════════════════════════════════════════════════════════
# PID MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def _save_pids(pids: dict):
    DAEMON_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    DAEMON_PID_FILE.write_text(json.dumps(pids, indent=2), encoding="utf-8")


def _load_pids() -> dict:
    if DAEMON_PID_FILE.exists():
        try:
            return json.loads(DAEMON_PID_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _is_running(pid: int) -> bool:
    if not pid:
        return False
    try:
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x100000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, PermissionError):
        return False


def _clean_stale_pids():
    pids = _load_pids()
    stale = [name for name, info in pids.items() if not _is_running(info.get("pid", 0))]
    for name in stale:
        del pids[name]
    if stale:
        _save_pids(pids)
    return stale


# ═══════════════════════════════════════════════════════════════
# ENVIRONMENT VALIDATION
# ═══════════════════════════════════════════════════════════════

def check_env() -> dict:
    report = {"ok": True, "missing_required": [], "missing_recommended": [], "present": []}
    for category, keys in REQUIRED_KEYS.items():
        for key in keys:
            val = os.environ.get(key, "")
            if not val or val.startswith("your_") or val == "changeme":
                report["missing_required"].append(f"{key} ({category})")
                report["ok"] = False
            else:
                report["present"].append(key)
    for category, keys in RECOMMENDED_KEYS.items():
        for key in keys:
            val = os.environ.get(key, "")
            if not val or val.startswith("your_") or val == "changeme":
                report["missing_recommended"].append(f"{key} ({category})")
            else:
                report["present"].append(key)
    return report


def print_env_report():
    report = check_env()
    print(f"\n── Environment Validation ──")
    print(f"  Keys present: {len(report['present'])}")
    if report["missing_required"]:
        print(f"\n  [CRITICAL] Missing REQUIRED keys:")
        for k in report["missing_required"]:
            print(f"    ✗ {k}")
    if report["missing_recommended"]:
        print(f"\n  [WARN] Missing recommended keys:")
        for k in report["missing_recommended"]:
            print(f"    ~ {k}")
    if report["ok"]:
        print(f"\n  [OK] All required keys present.")
    else:
        print(f"\n  [BLOCKED] Fix missing required keys in .env")
    return report


# ═══════════════════════════════════════════════════════════════
# SERVER MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def start_server():
    """Launch FastAPI via uvicorn as a background process."""
    pids = _load_pids()
    existing = pids.get("API Server", {}).get("pid")
    if existing and _is_running(existing):
        print(f"  [SKIP] API Server already running (PID {existing})")
        return existing

    log = open(LOG_DIR / "matrix_server.log", "a", encoding="utf-8")
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(
        [PYTHONW, "-m", "uvicorn", "api.intake:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(PROJECT_ROOT),
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=flags,
    )
    pids["API Server"] = {
        "pid": proc.pid,
        "started": datetime.now(timezone.utc).isoformat(),
        "cmd": f"{PYTHONW} -m uvicorn api.intake:app --host 0.0.0.0 --port 8000",
    }
    _save_pids(pids)
    print(f"  [START] API Server — PID {proc.pid}")
    print(f"          Dashboard: http://localhost:8000/matrix")
    return proc.pid


# ═══════════════════════════════════════════════════════════════
# DAEMON MANAGEMENT
# ═══════════════════════════════════════════════════════════════

DAEMONS = [
    {
        "name": "NERVE",
        "cmd": ["-m", "automation.nerve", "--daemon"],
        "desc": "Nexus Engine — 24/7 autonomous cycles",
    },
    {
        "name": "C-Suite Scheduler",
        "cmd": ["c_suite/scheduler.py", "--daemon"],
        "desc": "Executive cadence — standup, CFO, COO ops",
    },
    {
        "name": "Task Scheduler",
        "cmd": ["scheduler/runner.py", "--daemon"],
        "desc": "Retainer client task runner",
    },
    {
        "name": "Revenue Daemon",
        "cmd": ["-m", "automation.revenue_daemon", "--daemon"],
        "desc": "Stripe polling + income updates",
    },
    {
        "name": "Resonance Sync",
        "cmd": ["-m", "resonance.sync", "--daemon"],
        "desc": "NCC/NCL/AAC cross-pillar sync (30min cadence)",
    },
]


def start_daemons():
    """Start all background daemons."""
    env_report = print_env_report()
    if not env_report["ok"]:
        print("\n  [ABORT] Cannot launch daemons with missing required keys.")
        return

    _clean_stale_pids()
    pids = _load_pids()

    print(f"\n{'='*65}")
    print(f"  DIGITAL LABOUR — DAEMON LAUNCH")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*65}\n")

    for d in DAEMONS:
        name = d["name"]

        existing_pid = pids.get(name, {}).get("pid")
        if existing_pid and _is_running(existing_pid):
            print(f"  [SKIP] {name} already running (PID {existing_pid})")
            continue

        cmd = [PYTHONW] + d["cmd"]
        print(f"  [START] {name} — {d['desc']}")
        try:
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            pids[name] = {
                "pid": proc.pid,
                "started": datetime.now(timezone.utc).isoformat(),
                "cmd": " ".join(cmd),
            }
            print(f"          PID {proc.pid} ✓")
        except Exception as e:
            print(f"          FAILED: {e}")

    _save_pids(pids)
    print(f"\n  All daemons launched. PIDs → data/daemon_pids.json")


def stop_all():
    """Stop server + all daemons."""
    pids = _load_pids()
    if not pids:
        print("  No tracked processes.")
        return

    print(f"\n{'='*65}")
    print(f"  DIGITAL LABOUR — STOPPING ALL PROCESSES")
    print(f"{'='*65}\n")

    for name, info in list(pids.items()):
        pid = info.get("pid")
        if pid and _is_running(pid):
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                                   capture_output=True, check=False)
                else:
                    os.kill(pid, 15)
                print(f"  [STOP] {name} (PID {pid})")
            except Exception as e:
                print(f"  [WARN] {name} (PID {pid}) — {e}")
        else:
            print(f"  [SKIP] {name} — not running")

    _save_pids({})

    print(f"\n  All processes stopped.")


# ═══════════════════════════════════════════════════════════════
# STATUS & HEALTH
# ═══════════════════════════════════════════════════════════════

def show_status():
    """Comprehensive system status."""
    print(BANNER)
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Daemon status
    pids = _load_pids()
    print(f"\n── Active Processes ──")
    if pids:
        alive_count = 0
        for name, info in pids.items():
            pid = info.get("pid", 0)
            alive = _is_running(pid)
            if alive:
                alive_count += 1
            status = "\033[92mRUNNING\033[0m" if alive else "\033[91mDEAD\033[0m"
            started = info.get("started", "?")[:16]
            print(f"  {name:25s} PID {pid:>6}  {status}  since {started}")
        print(f"\n  {alive_count}/{len(pids)} processes alive")
    else:
        print(f"  No processes tracked. Run: bitrage start")

    # Env check
    print_env_report()

    # Health
    print(f"\n── System Health ──")
    try:
        from dashboard.health import system_health
        h = system_health()
        providers = h.get("llm_providers", [])
        print(f"  LLM Providers: {', '.join(providers) if providers else 'NONE'}")
        for db in ["task_queue.db", "kpi.db", "billing.db"]:
            s = "✓" if h.get(db) else "✗"
            print(f"  DB {db}: {s}")
        agent_count = sum(1 for k, v in h.items() if k.startswith("agent_") and v)
        agent_total = sum(1 for k in h if k.startswith("agent_"))
        print(f"  Agents: {agent_count}/{agent_total} modules found")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # Queue
    print(f"\n── Task Queue ──")
    try:
        from dispatcher.queue import TaskQueue
        q = TaskQueue()
        stats = q.stats()
        print(f"  Queued: {stats.get('queued', 0)} | Running: {stats.get('running', 0)} | "
              f"Done: {stats.get('completed', 0)} | Failed: {stats.get('failed', 0)}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # Revenue
    print(f"\n── Revenue ──")
    try:
        from billing.tracker import BillingTracker
        bt = BillingTracker()
        rev = bt.revenue_report(days=30)
        print(f"  30-day Revenue: ${rev.get('total_revenue', 0):.2f}")
        print(f"  30-day Cost:    ${rev.get('total_cost', 0):.4f}")
        print(f"  Gross Margin:   ${rev.get('gross_margin', 0):.2f}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # NERVE
    print(f"\n── NERVE State ──")
    try:
        state_file = PROJECT_ROOT / "data" / "nerve_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text(encoding="utf-8"))
            print(f"  Last cycle: {state.get('last_cycle', 'never')}")
            print(f"  Total cycles: {state.get('cycles_completed', 0)}")
            print(f"  Status: {state.get('status', 'unknown')}")
        else:
            print(f"  No NERVE state yet.")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # Outreach
    print(f"\n── Outreach ──")
    try:
        sent_file = PROJECT_ROOT / "automation" / "sent_log.json"
        if sent_file.exists():
            sent = json.loads(sent_file.read_text(encoding="utf-8"))
            print(f"  Emails sent: {len(sent)}")
        prospects = PROJECT_ROOT / "automation" / "prospects.csv"
        if prospects.exists():
            lines = prospects.read_text(encoding="utf-8").strip().split("\n")
            print(f"  Prospects: {max(0, len(lines) - 1)}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # Resonance Integration (NCC/NCL/AAC)
    print(f"\n── Resonance Integration ──")
    try:
        from resonance.ncc_bridge import ncc
        ncc_health = ncc.relay_health()
        ncc_status = "ONLINE" if ncc_health else "OFFLINE"
        print(f"  NCC Relay:  {ncc_status}")
    except Exception:
        print(f"  NCC Relay:  UNAVAILABLE")
    try:
        from resonance.ncl_bridge import ncl
        print(f"  NCL Brain:  {'AVAILABLE' if ncl.available else 'NOT FOUND'}")
    except Exception:
        print(f"  NCL Brain:  UNAVAILABLE")
    try:
        from resonance.aac_bridge import aac
        aac_data = aac.snapshot()
        print(f"  AAC Bank:   {aac_data.get('status', 'unknown').upper()}")
    except Exception:
        print(f"  AAC Bank:   UNAVAILABLE")
    # Outbox depth
    outbox_dir = PROJECT_ROOT / "data" / "ncc_outbox"
    if outbox_dir.exists():
        queued = sum(1 for f in outbox_dir.glob("*.ndjson")
                     for _ in f.read_text(encoding="utf-8").strip().splitlines() if _)
        if queued:
            print(f"  NCC Outbox: {queued} queued events")
    # Sync state
    sync_state_file = PROJECT_ROOT / "data" / "resonance_sync_state.json"
    if sync_state_file.exists():
        try:
            sync_state = json.loads(sync_state_file.read_text(encoding="utf-8"))
            last_check = sync_state.get("last_check", "never")
            print(f"  Last Sync:  {last_check[:16] if last_check != 'never' else 'never'}")
        except Exception:
            pass

    print(f"\n{'='*65}")
    print(f"  Commands: bitrage start | stop | status | health | setup | checks | sync")
    print(f"{'='*65}\n")


def show_health():
    """Detailed health dashboard."""
    try:
        from dashboard.health import print_dashboard
        print_dashboard()
    except Exception as e:
        print(f"  [ERROR] Could not load health dashboard: {e}")


# ═══════════════════════════════════════════════════════════════
# SYSTEM CHECKS (one-shot)
# ═══════════════════════════════════════════════════════════════

def run_checks():
    """Run one-shot checks: follow-ups, revenue, outreach, NERVE."""
    print(f"\n{'='*65}")
    print(f"  DIGITAL LABOUR — SYSTEM CHECKS")
    print(f"{'='*65}")

    print(f"\n── Follow-Up Check ──")
    try:
        from automation.outreach import send_followups
        followups = send_followups()
        if followups:
            print(f"  Sent {len(followups)} follow-up(s)")
        else:
            print(f"  No follow-ups due right now")
    except Exception as e:
        print(f"  [ERROR] {e}")

    print(f"\n── Revenue Check ──")
    try:
        from automation.revenue_daemon import check_stripe_revenue
        rev = check_stripe_revenue()
        print(f"  Stripe revenue: ${rev.get('total', 0):.2f}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    print(f"\n── Outreach Status ──")
    try:
        from automation.outreach import show_status as outreach_status
        outreach_status()
    except Exception as e:
        print(f"  [ERROR] {e}")

    print(f"\n── NERVE Status ──")
    try:
        from automation.nerve import show_status as nerve_status
        nerve_status()
    except Exception as e:
        print(f"  [ERROR] {e}")

    print(f"\n── Lead Scores ──")
    try:
        from automation.lead_scorer import show_leaderboard
        show_leaderboard()
    except Exception as e:
        print(f"  [ERROR] {e}")

    print(f"\n── Email Funnel ──")
    try:
        from automation.email_tracker import show_funnel
        show_funnel()
    except Exception as e:
        print(f"  [ERROR] {e}")


# ═══════════════════════════════════════════════════════════════
# SETUP WIZARD
# ═══════════════════════════════════════════════════════════════

def run_setup():
    """Interactive .env setup — wraps setup_keys.py logic."""
    env_path = PROJECT_ROOT / ".env"
    existing = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    print(f"\n{'='*65}")
    print(f"  DIGITAL LABOUR — API Key Setup")
    print(f"  Press Enter to keep existing value, or type new value.")
    print(f"{'='*65}\n")

    all_keys = {}
    for group_name, group_keys in {**REQUIRED_KEYS, **RECOMMENDED_KEYS}.items():
        print(f"\n── {group_name.upper()} ──")
        for key in group_keys:
            current = existing.get(key, "")
            masked = current[:4] + "..." + current[-4:] if len(current) > 12 else current
            prompt_str = f"  {key}"
            if current:
                prompt_str += f" [{masked}]"
            prompt_str += ": "
            new_val = input(prompt_str).strip()
            all_keys[key] = new_val if new_val else current

    # Merge with existing and write
    existing.update({k: v for k, v in all_keys.items() if v})
    lines = [f"{k}={v}" for k, v in existing.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n  [OK] .env updated with {len(existing)} keys.")


# ═══════════════════════════════════════════════════════════════
# FULL START / STOP
# ═══════════════════════════════════════════════════════════════

def cmd_start():
    """Start everything: server + daemons."""
    print(BANNER)
    start_server()
    time.sleep(2)
    start_daemons()
    print(f"\n{'='*65}")
    print(f"  ALL SYSTEMS GO")
    print(f"  Dashboard: http://localhost:8000/matrix")
    print(f"  Use: bitrage status | bitrage stop")
    print(f"{'='*65}\n")


def run_sync():
    """Run NCC/NCL/AAC Resonance sync now."""
    print(f"\n{'='*65}")
    print(f"  DIGITAL LABOUR — RESONANCE SYNC")
    print(f"{'='*65}")
    try:
        from resonance.sync import run_all, show_status as sync_status
        run_all()
        print()
        sync_status()
    except Exception as e:
        print(f"  [ERROR] {e}")


def run_preflight():
    """Pre-launch readiness check — validates everything before going live."""
    print(BANNER)
    print(f"  PRE-FLIGHT CHECK — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*65}")

    checks = []

    # 1. Environment keys
    env = check_env()
    status = "PASS" if env["ok"] else "FAIL"
    checks.append(("ENV Keys", status, f"{len(env['present'])} present, {len(env['missing_required'])} missing"))
    if not env["ok"]:
        for k in env["missing_required"]:
            checks.append(("  Missing", "CRIT", k))

    # 2. Python / venv
    venv_ok = VENV_PYTHON.exists()
    checks.append(("Python venv", "PASS" if venv_ok else "FAIL",
                    str(VENV_PYTHON) if venv_ok else "No .venv found"))

    # 3. Databases
    for db_name in ["data/task_queue.db", "data/kpi.db", "data/billing.db"]:
        db_path = PROJECT_ROOT / db_name
        checks.append((f"DB {db_name.split('/')[-1]}", "PASS" if db_path.exists() else "WARN",
                        f"{'exists' if db_path.exists() else 'missing — will be created on first use'}"))

    # 4. Agent modules
    agents_dir = PROJECT_ROOT / "agents"
    agent_count = sum(1 for d in agents_dir.iterdir()
                      if d.is_dir() and (d / "runner.py").exists()) if agents_dir.exists() else 0
    checks.append(("Agent modules", "PASS" if agent_count > 10 else "WARN",
                    f"{agent_count} agents with runner.py"))

    # 5. LLM providers
    try:
        from dashboard.health import system_health
        h = system_health()
        providers = h.get("llm_providers", [])
        checks.append(("LLM Providers", "PASS" if providers else "FAIL",
                        ", ".join(providers) if providers else "NONE configured"))
    except Exception as e:
        checks.append(("LLM Providers", "FAIL", str(e)))

    # 6. Critical modules import check
    critical_modules = [
        ("automation.nerve", "NERVE daemon"),
        ("automation.orchestrator", "Orchestrator"),
        ("automation.outreach", "Outreach pipeline"),
        ("automation.self_check", "Self-check"),
        ("c_suite.boardroom", "C-Suite boardroom"),
        ("openclaw.engine", "OpenClaw engine"),
        ("resonance.sync", "Resonance sync"),
        ("api.matrix_monitor", "Matrix C2"),
    ]
    for mod_path, mod_name in critical_modules:
        try:
            __import__(mod_path)
            checks.append((mod_name, "PASS", "importable"))
        except Exception as e:
            checks.append((mod_name, "FAIL", str(e)[:60]))

    # 7. Resonance bridges
    try:
        from resonance.ncc_bridge import ncc
        ncc_health = ncc.relay_health()
        checks.append(("NCC Relay", "PASS" if ncc_health else "WARN",
                        "online" if ncc_health else "offline (will queue events)"))
    except Exception as e:
        checks.append(("NCC Relay", "WARN", str(e)[:60]))

    try:
        from resonance.ncl_bridge import ncl
        checks.append(("NCL Brain", "PASS" if ncl.available else "WARN",
                        "data dir found" if ncl.available else "data dir not found"))
    except Exception:
        checks.append(("NCL Brain", "WARN", "bridge unavailable"))

    # 8. Prospects
    prospects_file = PROJECT_ROOT / "automation" / "prospects.csv"
    if prospects_file.exists():
        lines = prospects_file.read_text(encoding="utf-8").strip().split("\n")
        count = max(0, len(lines) - 1)
        checks.append(("Prospects", "PASS" if count > 5 else "WARN",
                        f"{count} loaded"))
    else:
        checks.append(("Prospects", "WARN", "no prospects.csv found"))

    # 9. Outreach content
    content_file = PROJECT_ROOT / "campaign" / "SOCIAL_CONTENT.md"
    checks.append(("Social content", "PASS" if content_file.exists() else "WARN",
                    "SOCIAL_CONTENT.md found" if content_file.exists() else "missing"))

    # Print results
    print()
    pass_count = sum(1 for _, s, _ in checks if s == "PASS")
    warn_count = sum(1 for _, s, _ in checks if s == "WARN")
    fail_count = sum(1 for _, s, _ in checks if s in ("FAIL", "CRIT"))

    for name, status, detail in checks:
        if status == "PASS":
            icon = "\033[92m[PASS]\033[0m"
        elif status == "WARN":
            icon = "\033[93m[WARN]\033[0m"
        elif status == "CRIT":
            icon = "\033[91m[CRIT]\033[0m"
        else:
            icon = "\033[91m[FAIL]\033[0m"
        print(f"  {icon} {name:25s} {detail}")

    print(f"\n{'='*65}")
    verdict = "READY FOR LAUNCH" if fail_count == 0 else "NOT READY — fix FAIL items"
    verdict_color = "\033[92m" if fail_count == 0 else "\033[91m"
    print(f"  {verdict_color}{verdict}\033[0m")
    print(f"  {pass_count} passed  {warn_count} warnings  {fail_count} failures")
    print(f"{'='*65}\n")

    return {"pass": pass_count, "warn": warn_count, "fail": fail_count,
            "ready": fail_count == 0, "checks": checks}


# ═══════════════════════════════════════════════════════════════
# INTERACTIVE MENU
# ═══════════════════════════════════════════════════════════════

def interactive_menu():
    """Full interactive control panel."""
    print(BANNER)

    while True:
        # Count alive
        pids = _load_pids()
        alive = sum(1 for info in pids.values() if _is_running(info.get("pid", 0)))
        total = len(pids)

        print(f"\n  Processes: {alive}/{total} alive")
        print(f"\n  ┌─────────────────────────────────────────┐")
        print(f"  │  1. START    — Server + All Daemons      │")
        print(f"  │  2. STOP     — Kill everything           │")
        print(f"  │  3. STATUS   — Full system report        │")
        print(f"  │  4. HEALTH   — Detailed health check     │")
        print(f"  │  5. CHECKS   — Run one-shot checks       │")
        print(f"  │  6. DAEMONS  — Start daemons only        │")
        print(f"  │  7. SERVER   — Start API server only     │")
        print(f"  │  8. SETUP    — Configure API keys        │")
        print(f"  │  9. MONITOR  — Launch Matrix Monitor     │")
        print(f"  │  S. SYNC     — NCC/NCL/AAC resonance     │")
        print(f"  │  0. EXIT                                 │")
        print(f"  └─────────────────────────────────────────┘")

        try:
            choice = input("\n  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye.")
            break

        if choice == "1":
            cmd_start()
        elif choice == "2":
            stop_all()
        elif choice == "3":
            show_status()
        elif choice == "4":
            show_health()
        elif choice == "5":
            run_checks()
        elif choice == "6":
            start_daemons()
        elif choice == "7":
            start_server()
        elif choice == "8":
            run_setup()
        elif choice == "9":
            # Launch monitor as separate process
            monitor_script = PROJECT_ROOT / "bitrage_monitor.py"
            if monitor_script.exists():
                subprocess.Popen([PYTHON, str(monitor_script)],
                                 cwd=str(PROJECT_ROOT),
                                 creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0)
                print("  [OK] Matrix Monitor launched in new window.")
            else:
                print("  [ERROR] bitrage_monitor.py not found.")
        elif choice.lower() == "s":
            run_sync()
        elif choice == "0":
            print("\n  Goodbye.")
            break
        else:
            print("  Invalid choice.")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="DIGITAL LABOUR — Master Control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run without arguments for interactive menu.",
    )
    parser.add_argument("command", nargs="?", default=None,
                        choices=["start", "stop", "status", "health",
                                 "daemons", "server", "setup", "checks",
                                 "monitor", "sync", "preflight"],
                        help="Command to execute")
    args = parser.parse_args()

    if args.command is None:
        interactive_menu()
    elif args.command == "start":
        cmd_start()
    elif args.command == "stop":
        stop_all()
    elif args.command == "status":
        show_status()
    elif args.command == "health":
        show_health()
    elif args.command == "daemons":
        start_daemons()
    elif args.command == "server":
        start_server()
    elif args.command == "setup":
        run_setup()
    elif args.command == "checks":
        run_checks()
    elif args.command == "monitor":
        monitor_script = PROJECT_ROOT / "bitrage_monitor.py"
        if monitor_script.exists():
            subprocess.Popen([PYTHON, str(monitor_script)],
                             cwd=str(PROJECT_ROOT),
                             creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0)
            print("  Matrix Monitor launched.")
        else:
            print("  bitrage_monitor.py not found.")
    elif args.command == "sync":
        run_sync()
    elif args.command == "preflight":
        run_preflight()


if __name__ == "__main__":
    main()
