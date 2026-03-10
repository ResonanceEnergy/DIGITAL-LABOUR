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

    print(f"\n{'='*60}")
    print(f"  DAILY AUTOMATION CYCLE — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    results = {"run_id": run_id, "started": now.isoformat(), "steps": {}}

    # Step 1: Generate leads
    print(f"\n[STEP 1] Generating {lead_count} outreach leads...")
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
        print(f"  -> {passed}/{len(gen_results)} passed QA")
    except Exception as e:
        results["steps"]["generate"] = {"status": "error", "error": str(e)}
        print(f"  -> ERROR: {e}")

    # Step 2: Send approved outreach
    print(f"\n[STEP 2] Sending approved outreach (auto_approve={auto_approve})...")
    try:
        sent = send_approved(auto_approve=auto_approve)
        results["steps"]["send"] = {"status": "ok", "count": len(sent)}
        print(f"  -> {len(sent)} emails processed")
    except Exception as e:
        results["steps"]["send"] = {"status": "error", "error": str(e)}
        print(f"  -> ERROR: {e}")

    # Step 3: Follow-ups
    print(f"\n[STEP 3] Processing follow-ups...")
    try:
        followups = send_followups()
        results["steps"]["followups"] = {"status": "ok", "count": len(followups)}
        print(f"  -> {len(followups)} follow-ups sent")
    except Exception as e:
        results["steps"]["followups"] = {"status": "error", "error": str(e)}
        print(f"  -> ERROR: {e}")

    # Step 4: Health check
    print(f"\n[STEP 4] Running health check...")
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
        print(f"  -> {providers_up}/4 LLM providers up")
        print(f"  -> Queue: {dashboard.get('queue', {})}")
    except Exception as e:
        results["steps"]["health"] = {"status": "error", "error": str(e)}
        print(f"  -> Health check error: {e}")

    # Step 5: Pipeline status
    print(f"\n[STEP 5] Pipeline status:")
    show_status()

    # Save log
    results["finished"] = datetime.now(timezone.utc).isoformat()
    log_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n[LOG] Saved to {log_file.name}")

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
    print(f"\n{'='*60}")
    print("  LAUNCHING DIGITAL LABOUR SERVICES")
    print(f"{'='*60}")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    for svc in SERVICES:
        print(f"\n  Starting {svc['name']}...")
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
            print(f"    PID {proc.pid} — {svc['name']} started")
        except Exception as e:
            print(f"    FAILED: {e}")

    print(f"\n{'='*60}")
    print(f"  {len(_running_procs)} services running")
    print(f"  API: http://localhost:8000")
    print(f"  Press Ctrl+C to stop all")
    print(f"{'='*60}")


def wait_for_services():
    """Block until Ctrl+C, then clean up."""
    try:
        while True:
            # Check if any service died
            for i, proc in enumerate(_running_procs):
                rc = proc.poll()
                if rc is not None:
                    print(f"  [WARN] {SERVICES[i]['name']} exited with code {rc}")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Stopping all services...")
        for proc in _running_procs:
            proc.terminate()
        for proc in _running_procs:
            proc.wait(timeout=5)
        print("[SHUTDOWN] All services stopped.")


# ── Operational Status ─────────────────────────────────────────

def show_full_status():
    """Show comprehensive operational status."""
    from automation.outreach import show_status as outreach_status

    print(f"\n{'='*60}")
    print("  DIGITAL LABOUR — OPERATIONAL STATUS")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    # SMTP status
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_user = os.getenv("SMTP_USER", "")
    print(f"\n  SMTP: {'CONFIGURED' if smtp_pass else 'NOT CONFIGURED (file mode)'}")
    print(f"  SMTP User: {smtp_user or 'not set'}")

    # LLM providers
    providers = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROK_API_KEY"]
    active = sum(1 for p in providers if os.getenv(p, ""))
    print(f"  LLM Providers: {active}/4 configured")

    # Stripe
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    print(f"  Stripe: {'CONFIGURED' if stripe_key else 'NOT SET'}")
    if stripe_key and stripe_key.startswith("sk_test_"):
        print(f"           (TEST MODE)")

    # Client profiles
    clients_dir = PROJECT_ROOT / "clients"
    client_count = 0
    if clients_dir.exists():
        client_count = len(list(clients_dir.glob("*.json")))
    print(f"  Client Profiles: {client_count}")

    # Recent orchestrator logs
    if LOG_DIR.exists():
        logs = sorted(LOG_DIR.glob("daily_*.json"), reverse=True)
        if logs:
            last = json.loads(logs[0].read_text(encoding="utf-8"))
            print(f"\n  Last Daily Run: {last.get('started', 'unknown')}")
            for step, data in last.get("steps", {}).items():
                status = data.get("status", "?")
                print(f"    {step}: {status}")

    # Outreach pipeline
    outreach_status()

    # Queue depth
    try:
        from dispatcher.queue import TaskQueue
        q = TaskQueue()
        stats = q.stats()
        print(f"  Task Queue: {stats.get('pending', 0)} pending, "
              f"{stats.get('completed', 0)} completed, "
              f"{stats.get('failed', 0)} failed")
    except Exception:
        print(f"  Task Queue: unable to read")


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
