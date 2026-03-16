"""Master Orchestrator — single command to run the full DIGITAL LABOUR operation.

Runs the daily sales + ops automation loop and optionally starts all background
services (API, scheduler, C-Suite, alerts, resonance sync).

Usage:
    python -m automation.orchestrator --daily           # Run daily outreach cycle
    python -m automation.orchestrator --launch-all      # Start all background services
    python -m automation.orchestrator --full             # Daily cycle + launch services
    python -m automation.orchestrator --status           # Full operational status
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

LOG_DIR = PROJECT_ROOT / "output" / "orchestrator_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Structured logging ─────────────────────────────────────────────────────
_LOG_FMT = logging.Formatter("%(asctime)s [%(levelname)s] orchestrator — %(message)s")
logger = logging.getLogger("orchestrator")
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setFormatter(_LOG_FMT)
    logger.addHandler(_sh)
    _fh = logging.FileHandler(LOG_DIR / "orchestrator.log", encoding="utf-8")
    _fh.setFormatter(_LOG_FMT)
    logger.addHandler(_fh)
    logger.setLevel(logging.INFO)
logger.propagate = False


# ── Daily Outreach Cycle ───────────────────────────────────────

def run_daily_cycle(lead_count: int = 5, auto_approve: bool = True):
    """Execute the full daily sales automation cycle.

    1. Generate leads from prospects.csv
    2. Auto-approve PASS results
    3. Send approved outreach (or queue to ready_to_send/)
    4. Process due follow-ups
    5. Run health check
    6. Log results
    """
    from automation.outreach import generate_batch, send_approved, send_followups, show_status

    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"daily_{run_id}.json"

    logger.info(f"\n{'='*60}")
    logger.info(f"  DAILY AUTOMATION CYCLE — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"{'='*60}")

    results = {"run_id": run_id, "started": now.isoformat(), "steps": {}}

    # Step 1: Generate leads
    logger.info(f"\n[STEP 1] Generating {lead_count} outreach leads...")
    try:
        gen_results = generate_batch(count=lead_count, priority="high")
        if not gen_results:
            gen_results = generate_batch(count=lead_count, priority="all")
        passed = sum(1 for r in gen_results if r.get("qa_status") == "PASS")
        results["steps"]["generate"] = {
            "status": "ok",
            "total": len(gen_results),
            "passed": passed,
        }
        logger.info(f"  -> {passed}/{len(gen_results)} passed QA")
    except Exception as e:
        results["steps"]["generate"] = {"status": "error", "error": str(e)}
        logger.info(f"  -> ERROR: {e}")

    # Step 2: Send approved outreach
    logger.info(f"\n[STEP 2] Sending approved outreach (auto_approve={auto_approve})...")
    try:
        sent = send_approved(auto_approve=auto_approve)
        results["steps"]["send"] = {"status": "ok", "count": len(sent)}
        logger.info(f"  -> {len(sent)} emails processed")
    except Exception as e:
        results["steps"]["send"] = {"status": "error", "error": str(e)}
        logger.info(f"  -> ERROR: {e}")

    # Step 3: Follow-ups
    logger.info(f"\n[STEP 3] Processing follow-ups...")
    try:
        followups = send_followups()
        results["steps"]["followups"] = {"status": "ok", "count": len(followups)}
        logger.info(f"  -> {len(followups)} follow-ups sent")
    except Exception as e:
        results["steps"]["followups"] = {"status": "error", "error": str(e)}
        logger.info(f"  -> ERROR: {e}")

    # Step 4: Health check
    logger.info(f"\n[STEP 4] Running health check...")
    try:
        from dashboard.health import full_dashboard
        dashboard = full_dashboard()
        health = dashboard.get("system", {})
        providers_up = sum(1 for v in health.get("llm_providers", {}).values() if v)
        results["steps"]["health"] = {
            "status": "ok",
            "providers_up": providers_up,
            "queue": dashboard.get("queue", {}),
        }
        logger.info(f"  -> {providers_up}/4 LLM providers up")
        logger.info(f"  -> Queue: {dashboard.get('queue', {})}")
    except Exception as e:
        results["steps"]["health"] = {"status": "error", "error": str(e)}
        logger.info(f"  -> Health check error: {e}")

    # Step 5: Pipeline status
    logger.info(f"\n[STEP 5] Pipeline status:")
    show_status()

    # Save log
    results["finished"] = datetime.now(timezone.utc).isoformat()
    log_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info(f"\n[LOG] Saved to {log_file.name}")

    return results


# ── Service Launcher ───────────────────────────────────────────

SERVICES = [
    {
        "name": "API Server",
        "cmd": [sys.executable, "-m", "uvicorn", "api.intake:app",
                "--host", "0.0.0.0", "--port", "8000"],
        "cwd": str(PROJECT_ROOT),
    },
    {
        "name": "Retainer Scheduler",
        "cmd": [sys.executable, "scheduler/runner.py", "--daemon"],
        "cwd": str(PROJECT_ROOT),
    },
    {
        "name": "C-Suite Scheduler",
        "cmd": [sys.executable, "c_suite/scheduler.py", "--daemon"],
        "cwd": str(PROJECT_ROOT),
    },
    {
        "name": "Resonance Sync",
        "cmd": [sys.executable, "-m", "resonance.sync", "--daemon"],
        "cwd": str(PROJECT_ROOT),
    },
]

_running_procs: list[subprocess.Popen] = []


def launch_all_services():
    """Start all background services as subprocesses."""
    logger.info(f"\n{'='*60}")
    logger.info("  LAUNCHING DIGITAL LABOUR SERVICES")
    logger.info(f"{'='*60}")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    for svc in SERVICES:
        logger.info(f"\n  Starting {svc['name']}...")
        try:
            proc = subprocess.Popen(
                svc["cmd"],
                cwd=svc["cwd"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            _running_procs.append(proc)
            logger.info(f"    PID {proc.pid} — {svc['name']} started")
        except Exception as e:
            logger.info(f"    FAILED: {e}")

    logger.info(f"\n{'='*60}")
    logger.info(f"  {len(_running_procs)} services running")
    logger.info(f"  API: http://localhost:8000")
    logger.info(f"  Press Ctrl+C to stop all")
    logger.info(f"{'='*60}")


def wait_for_services():
    """Block until Ctrl+C, then clean up."""
    try:
        while True:
            # Check if any service died
            for i, proc in enumerate(_running_procs):
                rc = proc.poll()
                if rc is not None:
                    logger.warning(f"  [WARN] {SERVICES[i]['name']} exited with code {rc}")
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("\n\n[SHUTDOWN] Stopping all services...")
        for proc in _running_procs:
            proc.terminate()
        for proc in _running_procs:
            proc.wait(timeout=5)
        logger.info("[SHUTDOWN] All services stopped.")


# ── Operational Status ─────────────────────────────────────────

def show_full_status():
    """Show comprehensive operational status."""
    from automation.outreach import show_status as outreach_status

    logger.info(f"\n{'='*60}")
    logger.info("  DIGITAL LABOUR — OPERATIONAL STATUS")
    logger.info(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"{'='*60}")

    # SMTP status
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_user = os.getenv("SMTP_USER", "")
    logger.info(f"\n  SMTP: {'CONFIGURED' if smtp_pass else 'NOT CONFIGURED (file mode)'}")
    logger.info(f"  SMTP User: {smtp_user or 'not set'}")

    # LLM providers
    providers = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROK_API_KEY"]
    active = sum(1 for p in providers if os.getenv(p, ""))
    logger.info(f"  LLM Providers: {active}/4 configured")

    # Stripe
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    logger.info(f"  Stripe: {'CONFIGURED' if stripe_key else 'NOT SET'}")
    if stripe_key and stripe_key.startswith("sk_test_"):
        logger.info(f"           (TEST MODE)")

    # Client profiles
    clients_dir = PROJECT_ROOT / "clients"
    client_count = 0
    if clients_dir.exists():
        client_count = len(list(clients_dir.glob("*.json")))
    logger.info(f"  Client Profiles: {client_count}")

    # Recent orchestrator logs
    if LOG_DIR.exists():
        logs = sorted(LOG_DIR.glob("daily_*.json"), reverse=True)
        if logs:
            last = json.loads(logs[0].read_text(encoding="utf-8"))
            logger.info(f"\n  Last Daily Run: {last.get('started', 'unknown')}")
            for step, data in last.get("steps", {}).items():
                status = data.get("status", "?")
                logger.info(f"    {step}: {status}")

    # Outreach pipeline
    outreach_status()

    # Inbox status
    try:
        from automation.inbox_reader import _load_inbox_log, INBOX_DIR
        inbox_log = _load_inbox_log()
        leads_count = len(list(INBOX_DIR.glob("lead_*.json"))) if INBOX_DIR.exists() else 0
        cats = {}
        for entry in inbox_log:
            cat = entry.get("category", "unknown")
            cats[cat] = cats.get(cat, 0) + 1
        logger.info(f"\n  Inbox: {len(inbox_log)} processed | {leads_count} leads saved | "
              f"{cats.get('reply', 0)} replies | {cats.get('spam', 0)} spam")
    except Exception:
        logger.info(f"\n  Inbox: not yet checked (run: python -m automation.inbox_reader --status)")

    # Registration progress
    try:
        from income.tracker import _load_tracker
        tracker_data = _load_tracker()
        src = tracker_data["sources"]
        reg_done = sum(1 for s in src.values() if s["status"] in ("registered", "configured", "active", "earning"))
        reg_total = len(src)
        earning = sum(1 for s in src.values() if s["status"] == "earning")
        logger.info(f"\n  Platforms: {reg_done}/{reg_total} registered | {earning} earning | ${tracker_data.get('total_revenue', 0):,.2f} revenue")
    except Exception:
        logger.info(f"\n  Platforms: unable to read tracker")

    # Queue depth
    try:
        from dispatcher.queue import TaskQueue
        q = TaskQueue()
        stats = q.stats()
        logger.info(f"  Task Queue: {stats.get('pending', 0)} pending, "
              f"{stats.get('completed', 0)} completed, "
              f"{stats.get('failed', 0)} failed")
    except Exception:
        logger.info(f"  Task Queue: unable to read")


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DIGITAL LABOUR — Master Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m automation.orchestrator --daily              # Run daily lead gen + send
    python -m automation.orchestrator --daily --leads 10   # Generate 10 leads
    python -m automation.orchestrator --launch-all         # Start all services
    python -m automation.orchestrator --full               # Daily cycle + services
    python -m automation.orchestrator --status             # Show operational status
""",
    )
    parser.add_argument("--daily", action="store_true", help="Run daily outreach cycle")
    parser.add_argument("--leads", type=int, default=5, help="Number of leads to generate (default: 5)")
    parser.add_argument("--no-approve", action="store_true", help="Don't auto-approve PASS leads")
    parser.add_argument("--launch-all", action="store_true", help="Start all background services")
    parser.add_argument("--full", action="store_true", help="Daily cycle + launch all services")
    parser.add_argument("--status", action="store_true", help="Show full operational status")

    args = parser.parse_args()

    if args.status:
        show_full_status()
    elif args.daily:
        run_daily_cycle(lead_count=args.leads, auto_approve=not args.no_approve)
    elif args.launch_all:
        launch_all_services()
        wait_for_services()
    elif args.full:
        run_daily_cycle(lead_count=args.leads, auto_approve=not args.no_approve)
        launch_all_services()
        wait_for_services()
    else:
        parser.print_help()
