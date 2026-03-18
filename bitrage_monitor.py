"""BIT RAGE MATRIX MONITOR — Live Console Dashboard & C2 Interface.

Consolidates: api/matrix_monitor.py (C2), c_suite/exec_dashboard.py,
              dashboard/health.py, and all monitoring/display capabilities
              into a single live-updating console application.

Integrates:   NCC/NCL/AAC resonance status panel + 5 resonance C2 commands.

Usage:
    python bitrage_monitor.py                # Live dashboard (auto-refresh)
    python bitrage_monitor.py --once         # Print once and exit
    python bitrage_monitor.py --command CMD  # Execute C2 command directly
    python bitrage_monitor.py --commands     # List all C2 commands
    python bitrage_monitor.py --json         # JSON dump of full status
    python bitrage_monitor.py --exec         # Executive C-Suite dashboard

Build:  pyinstaller bitrage_monitor.spec
"""

import argparse
import json
import os
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

DAEMON_PID_FILE = PROJECT_ROOT / "data" / "daemon_pids.json"
VERSION = "2.0.0"

# ── ANSI Colors ────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
DIM = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"

MONITOR_BANNER = f"""{CYAN}
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   ███╗   ███╗ █████╗ ████████╗██████╗ ██╗██╗  ██╗                     ║
║   ████╗ ████║██╔══██╗╚══██╔══╝██╔══██╗██║╚██╗██╔╝                     ║
║   ██╔████╔██║███████║   ██║   ██████╔╝██║ ╚███╔╝                      ║
║   ██║╚██╔╝██║██╔══██║   ██║   ██╔══██╗██║ ██╔██╗                      ║
║   ██║ ╚═╝ ██║██║  ██║   ██║   ██║  ██║██║██╔╝ ██╗                     ║
║   ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝                  ║
║                                                                       ║
║   {WHITE}BIT RAGE MATRIX MONITOR{CYAN} — Live C2 v{VERSION:<21}{CYAN}    ║
║   {DIM}33 C2 Commands • NERVE • C-Suite • Revenue • Fleet • Resonance{CYAN}      ║
╚═══════════════════════════════════════════════════════════════════════╝{RESET}
"""

# All 28 C2 commands
C2_COMMANDS = {
    "restart_daemons": "Restart all background daemons",
    "kill_daemons": "Kill all background daemons",
    "pause_agent": "Pause a specific agent (target=agent_name)",
    "resume_agent": "Resume a paused agent (target=agent_name)",
    "approve_task": "Approve a queued task (target=task_id)",
    "reject_task": "Reject a queued task (target=task_id)",
    "send_followups": "Send all pending follow-up emails",
    "check_inbox": "Process inbound email inbox",
    "run_proposals": "Generate proposals for open leads",
    "system_check": "Run full system diagnostics + auto-heal",
    "watchdog_status": "Get NERVE watchdog status",
    "watchdog_stop": "Stop the NERVE watchdog",
    "watchdog_start": "Start the NERVE watchdog",
    "nerve_status": "Get NERVE daemon status + cycle info",
    "revenue_summary": "Get revenue snapshot from Stripe",
    "daily_cycle": "Run full daily orchestrator cycle",
    "openclaw_cycle": "Run OpenClaw automation cycle",
    "openclaw_scan": "Scan for OpenClaw tasks",
    "openclaw_inbox": "Process OpenClaw inbox",
    "fiverr_setup": "Deploy top-4 Fiverr gigs via OpenClaw platform_setup",
    "fiverr_deploy_all": "Deploy all 20 Fiverr gigs via browser automation",
    "fiverr_deploy_top4": "Deploy gigs 1,2,3,4 (Sales/Support/Content/Docs) via browser",
    "boardroom_quick": "Run quick C-Suite standup",
    "outreach_push": "Push outreach batch to prospects",
    "upwork_hunt": "Run Upwork job hunt scanner",
    "unit_economics": "Calculate unit economics (CAC, LTV)",
    "full_status": "Get comprehensive system status",
    "x_post": "Post next tweet from queue",
    "x_status": "Get X/Twitter posting status",
    "lead_scores": "Score all prospects by ICP fit",
    "email_funnel": "Get email outreach funnel metrics",
    "ncc_status": "Check NCC relay health + outbox depth",
    "ncl_brief": "Pull latest NCL intelligence brief",
    "aac_snapshot": "Pull AAC BANK financial snapshot",
    "resonance_sync": "Run all resonance sync jobs now",
    "resonance_status": "Show resonance sync health",
}


# ═══════════════════════════════════════════════════════════════
# PID HELPERS
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# DATA COLLECTORS
# ═══════════════════════════════════════════════════════════════

def _collect_daemon_status() -> list[dict]:
    pids = _load_pids()
    result = []
    for name, info in pids.items():
        pid = info.get("pid", 0)
        alive = _is_running(pid)
        result.append({
            "name": name,
            "pid": pid,
            "alive": alive,
            "started": info.get("started", "?")[:16],
        })
    return result


def _collect_health() -> dict:
    try:
        from dashboard.health import system_health
        return system_health()
    except Exception:
        return {}


def _collect_queue() -> dict:
    try:
        from dispatcher.queue import TaskQueue
        return TaskQueue().stats()
    except Exception:
        return {"queued": 0, "running": 0, "completed": 0, "failed": 0}


def _collect_revenue() -> dict:
    try:
        from billing.tracker import BillingTracker
        return BillingTracker().revenue_report(days=30)
    except Exception:
        return {}


def _collect_kpi() -> dict:
    try:
        from kpi.logger import summary
        return summary(days=7)
    except Exception:
        return {}


def _collect_nerve() -> dict:
    state_file = PROJECT_ROOT / "data" / "nerve_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _collect_outreach() -> dict:
    result = {"emails_sent": 0, "prospects": 0, "followups_due": 0}
    try:
        sent_file = PROJECT_ROOT / "automation" / "sent_log.json"
        if sent_file.exists():
            sent = json.loads(sent_file.read_text(encoding="utf-8"))
            result["emails_sent"] = len(sent)
    except Exception:
        pass
    try:
        prospects = PROJECT_ROOT / "automation" / "prospects.csv"
        if prospects.exists():
            lines = prospects.read_text(encoding="utf-8").strip().split("\n")
            result["prospects"] = max(0, len(lines) - 1)
    except Exception:
        pass
    try:
        followups_file = PROJECT_ROOT / "automation" / "followups.json"
        if followups_file.exists():
            followups = json.loads(followups_file.read_text(encoding="utf-8"))
            result["followups_due"] = len(followups)
    except Exception:
        pass
    return result


def _collect_csuite() -> dict:
    data = {}
    for exec_name, subfolder in [("AXIOM", "axiom"), ("VECTIS", "vectis"), ("LEDGR", "ledgr")]:
        report_dir = PROJECT_ROOT / "output" / "c_suite" / subfolder
        if report_dir.exists():
            files = sorted(report_dir.glob("*.json"), reverse=True)
            if files:
                try:
                    report = json.loads(files[0].read_text(encoding="utf-8"))
                    if exec_name == "AXIOM":
                        data["axiom"] = report.get("ceo_verdict", "—")[:60]
                    elif exec_name == "VECTIS":
                        data["vectis"] = report.get("coo_verdict", "—")[:60]
                    elif exec_name == "LEDGR":
                        data["ledgr"] = report.get("cfo_verdict", "—")[:60]
                except Exception:
                    pass
    return data


def _collect_decisions(limit=5) -> list[dict]:
    log_file = PROJECT_ROOT / "data" / "matrix_decisions.json"
    if not log_file.exists():
        return []
    try:
        decisions = json.loads(log_file.read_text(encoding="utf-8"))
        return decisions[-limit:]
    except Exception:
        return []


def _collect_nerve_decisions(limit=5) -> list[dict]:
    log_file = PROJECT_ROOT / "data" / "nerve_logs" / "decisions.jsonl"
    if not log_file.exists():
        return []
    try:
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return entries
    except Exception:
        return []


def _collect_resonance() -> dict:
    """Collect NCC/NCL/AAC integration status."""
    result = {"ncc": "offline", "ncl": "unavailable", "aac": "offline",
              "outbox_depth": 0, "last_sync": "never"}
    try:
        from resonance.ncc_bridge import ncc
        health = ncc.relay_health()
        result["ncc"] = "online" if health else "offline"
    except Exception:
        pass
    try:
        from resonance.ncl_bridge import ncl
        result["ncl"] = "available" if ncl.available else "not found"
    except Exception:
        pass
    try:
        from resonance.aac_bridge import aac
        snap = aac.snapshot()
        result["aac"] = snap.get("status", "offline")
    except Exception:
        pass
    # Outbox depth
    outbox_dir = PROJECT_ROOT / "data" / "ncc_outbox"
    if outbox_dir.exists():
        try:
            result["outbox_depth"] = sum(
                1 for f in outbox_dir.glob("*.ndjson")
                for line in f.read_text(encoding="utf-8").strip().splitlines() if line
            )
        except Exception:
            pass
    # Sync state
    sync_file = PROJECT_ROOT / "data" / "resonance_sync_state.json"
    if sync_file.exists():
        try:
            state = json.loads(sync_file.read_text(encoding="utf-8"))
            result["last_sync"] = state.get("last_check", "never")
        except Exception:
            pass
    return result


def _collect_all() -> dict:
    """Collect all monitoring data into one dict."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "daemons": _collect_daemon_status(),
        "health": _collect_health(),
        "queue": _collect_queue(),
        "revenue": _collect_revenue(),
        "kpi_7d": _collect_kpi(),
        "nerve": _collect_nerve(),
        "outreach": _collect_outreach(),
        "csuite": _collect_csuite(),
        "decisions": _collect_decisions(),
        "nerve_decisions": _collect_nerve_decisions(),
        "resonance": _collect_resonance(),
    }


# ═══════════════════════════════════════════════════════════════
# DISPLAY RENDERERS
# ═══════════════════════════════════════════════════════════════

def _status_icon(alive: bool) -> str:
    return f"{GREEN}● RUNNING{RESET}" if alive else f"{RED}● DEAD{RESET}"


def _clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def render_dashboard(data: dict):
    """Render the full monitoring dashboard."""
    ts = data.get("timestamp", "?")[:19]

    # ── Header
    print(f"\n{BOLD}{CYAN}═══════════════════════════════════════════════════════════════════{RESET}")
    print(f"  {BOLD}{WHITE}BIT RAGE MATRIX MONITOR{RESET}   {DIM}v{VERSION}{RESET}   {DIM}{ts} UTC{RESET}")
    print(f"{CYAN}═══════════════════════════════════════════════════════════════════{RESET}")

    # ── Daemons
    daemons = data.get("daemons", [])
    alive_count = sum(1 for d in daemons if d["alive"])
    total_count = len(daemons)
    daemon_color = GREEN if alive_count == total_count and total_count > 0 else (YELLOW if alive_count > 0 else RED)
    print(f"\n  {BOLD}DAEMONS{RESET}  {daemon_color}{alive_count}/{total_count}{RESET}")
    print(f"  {'─'*60}")
    if daemons:
        for d in daemons:
            print(f"  {d['name']:25s} PID {d['pid']:>6}  {_status_icon(d['alive'])}  {DIM}{d['started']}{RESET}")
    else:
        print(f"  {DIM}No processes tracked. Run: bitrage start{RESET}")

    # ── Health
    health = data.get("health", {})
    providers = health.get("llm_providers", [])
    print(f"\n  {BOLD}HEALTH{RESET}")
    print(f"  {'─'*60}")
    prov_str = ", ".join(providers) if providers else f"{RED}NONE{RESET}"
    print(f"  LLM Providers: {GREEN}{prov_str}{RESET}")
    for db in ["task_queue.db", "kpi.db", "billing.db"]:
        icon = f"{GREEN}✓{RESET}" if health.get(db) else f"{RED}✗{RESET}"
        print(f"  {db}: {icon}", end="  ")
    print()
    agent_ok = sum(1 for k, v in health.items() if k.startswith("agent_") and v)
    agent_total = sum(1 for k in health if k.startswith("agent_"))
    agent_color = GREEN if agent_ok == agent_total else YELLOW
    print(f"  Agents: {agent_color}{agent_ok}/{agent_total}{RESET} modules")

    # ── Queue
    queue = data.get("queue", {})
    print(f"\n  {BOLD}TASK QUEUE{RESET}")
    print(f"  {'─'*60}")
    queued = queue.get("queued", 0)
    running = queue.get("running", 0)
    completed = queue.get("completed", 0)
    failed = queue.get("failed", 0)
    fail_color = RED if failed > 0 else GREEN
    print(f"  Queued: {CYAN}{queued}{RESET}  Running: {YELLOW}{running}{RESET}  "
          f"Done: {GREEN}{completed}{RESET}  Failed: {fail_color}{failed}{RESET}")

    # ── Revenue
    rev = data.get("revenue", {})
    print(f"\n  {BOLD}REVENUE (30d){RESET}")
    print(f"  {'─'*60}")
    total_rev = rev.get("total_revenue", 0)
    rev_color = GREEN if total_rev > 0 else RED
    print(f"  Revenue: {rev_color}${total_rev:.2f}{RESET}  "
          f"Cost: ${rev.get('total_cost', 0):.4f}  "
          f"Margin: ${rev.get('gross_margin', 0):.2f}")

    # ── NERVE
    nerve = data.get("nerve", {})
    print(f"\n  {BOLD}NERVE ENGINE{RESET}")
    print(f"  {'─'*60}")
    if nerve:
        print(f"  Last cycle: {nerve.get('last_cycle', 'never')}")
        print(f"  Cycles: {nerve.get('cycles_completed', 0)}  Status: {nerve.get('status', 'unknown')}")
    else:
        print(f"  {DIM}No NERVE state{RESET}")

    # ── Outreach
    outreach = data.get("outreach", {})
    print(f"\n  {BOLD}OUTREACH PIPELINE{RESET}")
    print(f"  {'─'*60}")
    print(f"  Emails sent: {outreach.get('emails_sent', 0)}  "
          f"Prospects: {outreach.get('prospects', 0)}  "
          f"Follow-ups due: {outreach.get('followups_due', 0)}")

    # ── C-Suite
    csuite = data.get("csuite", {})
    if csuite:
        print(f"\n  {BOLD}C-SUITE VERDICTS{RESET}")
        print(f"  {'─'*60}")
        if csuite.get("axiom"):
            print(f"  {MAGENTA}AXIOM (CEO):{RESET} {csuite['axiom']}")
        if csuite.get("vectis"):
            print(f"  {CYAN}VECTIS (COO):{RESET} {csuite['vectis']}")
        if csuite.get("ledgr"):
            print(f"  {YELLOW}LEDGR (CFO):{RESET} {csuite['ledgr']}")

    # ── Resonance (NCC/NCL/AAC)
    res = data.get("resonance", {})
    print(f"\n  {BOLD}RESONANCE INTEGRATION{RESET}")
    print(f"  {'─'*60}")
    ncc_s = res.get("ncc", "offline")
    ncl_s = res.get("ncl", "unavailable")
    aac_s = res.get("aac", "offline")
    ncc_color = GREEN if ncc_s == "online" else RED
    ncl_color = GREEN if ncl_s == "available" else YELLOW
    aac_color = GREEN if aac_s == "online" else RED
    print(f"  NCC Relay: {ncc_color}{ncc_s.upper()}{RESET}  "
          f"NCL Brain: {ncl_color}{ncl_s.upper()}{RESET}  "
          f"AAC Bank: {aac_color}{aac_s.upper()}{RESET}")
    outbox = res.get("outbox_depth", 0)
    last_sync = res.get("last_sync", "never")
    if last_sync != "never":
        last_sync = last_sync[:16]
    outbox_color = YELLOW if outbox > 0 else DIM
    print(f"  Outbox: {outbox_color}{outbox} queued{RESET}  Last sync: {DIM}{last_sync}{RESET}")

    # ── Recent Decisions
    nerv_dec = data.get("nerve_decisions", [])
    if nerv_dec:
        print(f"\n  {BOLD}RECENT DECISIONS{RESET}")
        print(f"  {'─'*60}")
        for d in nerv_dec[-5:]:
            ts_short = d.get("timestamp", "?")[:16]
            phase = d.get("phase", "?")
            action = d.get("action", "?")[:50]
            print(f"  {DIM}{ts_short}{RESET} [{phase}] {action}")

    # ── Footer
    print(f"\n{CYAN}═══════════════════════════════════════════════════════════════════{RESET}")
    print(f"  {DIM}C2: bitrage_monitor --command <cmd> | --commands for list{RESET}")
    print(f"  {DIM}Web: http://localhost:8000/matrix{RESET}")
    print(f"{CYAN}═══════════════════════════════════════════════════════════════════{RESET}")


# ═══════════════════════════════════════════════════════════════
# C2 COMMAND EXECUTION (LOCAL — no API needed)
# ═══════════════════════════════════════════════════════════════

def execute_c2(action: str, target: str = "", reason: str = ""):
    """Execute a C2 command locally (same functions as API)."""
    handlers = {
        "restart_daemons": _c2_restart_daemons,
        "kill_daemons": _c2_kill_daemons,
        "send_followups": _c2_send_followups,
        "check_inbox": _c2_check_inbox,
        "system_check": _c2_system_check,
        "nerve_status": _c2_nerve_status,
        "revenue_summary": _c2_revenue_summary,
        "daily_cycle": _c2_daily_cycle,
        "boardroom_quick": _c2_boardroom_quick,
        "outreach_push": _c2_outreach_push,
        "full_status": _c2_full_status,
        "x_post": _c2_x_post,
        "x_status": _c2_x_status,
        "lead_scores": _c2_lead_scores,
        "email_funnel": _c2_email_funnel,
        "unit_economics": _c2_unit_economics,
        "watchdog_status": _c2_watchdog_status,
        "ncc_status": _c2_ncc_status,
        "ncl_brief": _c2_ncl_brief,
        "aac_snapshot": _c2_aac_snapshot,
        "resonance_sync": _c2_resonance_sync,
        "resonance_status": _c2_resonance_status,
        "fiverr_setup": _c2_fiverr_setup,
        "fiverr_deploy_all": _c2_fiverr_deploy_all,
        "fiverr_deploy_top4": _c2_fiverr_deploy_top4,
    }

    handler = handlers.get(action)
    if not handler:
        print(f"  {RED}Unknown command: {action}{RESET}")
        print(f"  Available: {', '.join(sorted(handlers.keys()))}")
        return

    print(f"\n  {BOLD}Executing: {action}{RESET}" + (f" target={target}" if target else ""))
    print(f"  {'─'*50}")
    try:
        result = handler(target)
        if isinstance(result, dict):
            print(json.dumps(result, indent=2, default=str))
        elif result:
            print(f"  {result}")
        print(f"\n  {GREEN}Done.{RESET}")
    except Exception as e:
        print(f"  {RED}Error: {e}{RESET}")


# ── C2 Handlers ───────────────────────────────────────────────

def _c2_restart_daemons(target=""):
    from bitrage import stop_all, start_daemons
    stop_all()
    time.sleep(1)
    start_daemons()
    return {"status": "restarted"}


def _c2_kill_daemons(target=""):
    from bitrage import stop_all
    stop_all()
    return {"status": "killed"}


def _c2_send_followups(target=""):
    from automation.outreach import send_followups
    result = send_followups()
    return {"sent": len(result) if result else 0}


def _c2_check_inbox(target=""):
    from automation.inbox_reader import process_inbox
    result = process_inbox()
    return {"processed": len(result) if result else 0}


def _c2_system_check(target=""):
    from automation.self_check import run_full_check, find_gaps, heal_issues
    check = run_full_check()
    gaps = find_gaps(check)
    healed = heal_issues(gaps)
    return {"check": check, "gaps": gaps, "healed": healed}


def _c2_nerve_status(target=""):
    return _collect_nerve()


def _c2_revenue_summary(target=""):
    return _collect_revenue()


def _c2_daily_cycle(target=""):
    from automation.orchestrator import run_daily
    result = run_daily()
    return {"cycle": "completed", "result": str(result)[:200]}


def _c2_boardroom_quick(target=""):
    from c_suite.boardroom import run_standup
    result = run_standup()
    return {"standup": str(result)[:300]}


def _c2_outreach_push(target=""):
    from automation.outreach import generate_batch, send_approved
    batch = generate_batch(count=5)
    sent = send_approved()
    return {"batch_generated": len(batch) if batch else 0, "sent": len(sent) if sent else 0}


def _c2_full_status(target=""):
    return _collect_all()


def _c2_x_post(target=""):
    from automation.x_poster import post_next
    return post_next()


def _c2_x_status(target=""):
    from automation.x_poster import show_status
    return show_status()


def _c2_lead_scores(target=""):
    from automation.lead_scorer import score_all_prospects, get_top_prospects
    score_all_prospects()
    return {"top_10": get_top_prospects(10)}


def _c2_email_funnel(target=""):
    from automation.email_tracker import build_tracking_report
    return build_tracking_report()


def _c2_unit_economics(target=""):
    try:
        from kpi.unit_economics import calculate_unit_economics
        return calculate_unit_economics()
    except Exception as e:
        return {"error": str(e)}


def _c2_watchdog_status(target=""):
    status_file = PROJECT_ROOT / "data" / "watchdog_status.json"
    if status_file.exists():
        return json.loads(status_file.read_text(encoding="utf-8"))
    return {"status": "no watchdog data"}


def _c2_ncc_status(target=""):
    from resonance.ncc_bridge import ncc
    health = ncc.relay_health()
    outbox = ncc.flush()
    return {"relay": "online" if health else "offline",
            "health": health, "outbox_flushed": outbox}


def _c2_ncl_brief(target=""):
    from resonance.ncl_bridge import ncl
    return {"available": ncl.available,
            "digest": ncl.intelligence_digest() if ncl.available else None,
            "brief": (ncl.latest_daily_brief() or "")[:500] if ncl.available else None}


def _c2_aac_snapshot(target=""):
    from resonance.aac_bridge import aac
    return aac.snapshot()


def _c2_resonance_sync(target=""):
    from resonance.sync import run_all
    run_all()
    return {"status": "sync_complete"}


def _c2_resonance_status(target=""):
    return _collect_resonance()


def _c2_fiverr_setup(target=""):
    """Deploy top-4 Fiverr gigs via OpenClaw engine.platform_setup.

    Equivalent to:
        from openclaw.engine import OpenClawEngine
        OpenClawEngine().platform_setup(platforms=['fiverr'])
    """
    from openclaw.engine import OpenClawEngine
    result = OpenClawEngine().platform_setup(platforms=["fiverr"])
    return result


def _c2_fiverr_deploy_all(target=""):
    """Deploy all 20 Fiverr gigs via browser automation.

    Equivalent to:
        python -m automation.fiverr_automation --deploy
    """
    from automation.fiverr_automation import deploy_all_browser
    deploy_all_browser()
    return {"status": "deploy_all_complete"}


def _c2_fiverr_deploy_top4(target=""):
    """Deploy gigs 1,2,3,4 (Sales Outreach, Support Resolver, Content Repurposer, Doc Extractor).

    Equivalent to:
        python -m automation.fiverr_automation --deploy --gigs 1,2,3,4
    """
    from automation.fiverr_automation import deploy_all_browser
    deploy_all_browser(gig_indices=[1, 2, 3, 4])
    return {"status": "deploy_top4_complete", "gigs": [1, 2, 3, 4]}


# ═══════════════════════════════════════════════════════════════
# EXECUTIVE DASHBOARD
# ═══════════════════════════════════════════════════════════════

def render_exec_dashboard():
    """Render the C-Suite executive dashboard."""
    try:
        from c_suite.exec_dashboard import print_exec_dashboard
        print_exec_dashboard()
    except Exception as e:
        print(f"  {RED}Error loading executive dashboard: {e}{RESET}")


# ═══════════════════════════════════════════════════════════════
# LIVE DASHBOARD LOOP
# ═══════════════════════════════════════════════════════════════

def live_dashboard(interval=30):
    """Live-updating dashboard with auto-refresh."""
    print(MONITOR_BANNER)
    print(f"  {DIM}Live refresh every {interval}s. Press Ctrl+C to exit.{RESET}")
    print(f"  {DIM}Press 'c' + Enter to send a C2 command.{RESET}")

    try:
        while True:
            _clear_screen()
            data = _collect_all()
            render_dashboard(data)
            print(f"\n  {DIM}Refreshing in {interval}s... (Ctrl+C to exit){RESET}")

            # Interruptible sleep
            for _ in range(interval):
                time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n\n  {YELLOW}Monitor stopped.{RESET}\n")


# ═══════════════════════════════════════════════════════════════
# INTERACTIVE MONITOR
# ═══════════════════════════════════════════════════════════════

def interactive_monitor():
    """Interactive monitor with command input."""
    print(MONITOR_BANNER)

    while True:
        # Show dashboard
        data = _collect_all()
        render_dashboard(data)

        print(f"\n  {BOLD}Commands:{RESET}")
        print(f"  {DIM}  r = refresh | c = C2 command | l = list commands{RESET}")
        print(f"  {DIM}  e = exec dashboard | j = json dump | q = quit{RESET}")

        try:
            choice = input(f"\n  {CYAN}>{RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {YELLOW}Goodbye.{RESET}")
            break

        if choice == "r":
            continue
        elif choice == "c":
            cmd = input(f"  Command: ").strip()
            target = input(f"  Target (or Enter): ").strip()
            execute_c2(cmd, target)
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "l":
            print(f"\n  {BOLD}Available C2 Commands:{RESET}")
            for cmd, desc in sorted(C2_COMMANDS.items()):
                print(f"    {CYAN}{cmd:25s}{RESET} {desc}")
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "e":
            render_exec_dashboard()
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "j":
            print(json.dumps(_collect_all(), indent=2, default=str))
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice in ("q", "quit", "exit"):
            print(f"\n  {YELLOW}Goodbye.{RESET}")
            break
        elif choice:
            # Try as direct command
            execute_c2(choice)
            input(f"\n  {DIM}Press Enter to continue...{RESET}")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BIT RAGE MATRIX MONITOR — Live C2 Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--once", action="store_true", help="Print dashboard once and exit")
    parser.add_argument("--live", action="store_true", help="Auto-refreshing dashboard (no input)")
    parser.add_argument("--interval", type=int, default=30, help="Live refresh interval in seconds")
    parser.add_argument("--command", type=str, help="Execute a C2 command directly")
    parser.add_argument("--target", type=str, default="", help="Target for C2 command")
    parser.add_argument("--commands", action="store_true", help="List all C2 commands")
    parser.add_argument("--json", action="store_true", help="JSON dump of full system status")
    parser.add_argument("--exec", action="store_true", help="Show executive C-Suite dashboard")

    args = parser.parse_args()

    if args.commands:
        print(f"\n  {BOLD}BIT RAGE MATRIX — C2 Commands ({len(C2_COMMANDS)}){RESET}\n")
        for cmd, desc in sorted(C2_COMMANDS.items()):
            print(f"  {CYAN}{cmd:25s}{RESET} {desc}")
        print()
    elif args.command:
        execute_c2(args.command, args.target)
    elif args.json:
        print(json.dumps(_collect_all(), indent=2, default=str))
    elif getattr(args, "exec"):
        render_exec_dashboard()
    elif args.once:
        data = _collect_all()
        render_dashboard(data)
    elif args.live:
        live_dashboard(args.interval)
    else:
        interactive_monitor()


if __name__ == "__main__":
    main()
