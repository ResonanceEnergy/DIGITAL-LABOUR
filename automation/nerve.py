"""NERVE — Nexus Engine for Resilient Vigilant Execution.

The autonomous 24/7 daemon that runs DIGITAL LABOUR without human intervention.
Self-checking, self-healing, self-motivated. Only escalates truly critical issues.

NERVE wraps the existing orchestrator, outreach pipeline, C-Suite scheduler,
and health systems into a single relentless daemon that:
  1. Runs self-check every cycle (gaps, health, opportunities)
  2. Auto-heals what it can (follow-ups, prospect replenishment, queue)
  3. Executes outreach cycles when prospects are available
  4. Runs C-Suite executive cadence on schedule
  5. Logs every decision to an immutable audit trail
  6. Escalates only truly critical failures to the human operator

Usage:
    python -m automation.nerve                    # Run one full cycle
    python -m automation.nerve --daemon           # Run 24/7 daemon
    python -m automation.nerve --status           # Show NERVE status
    python -m automation.nerve --decisions        # Show recent decisions
"""

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from automation.decision_log import log_decision, log_escalation, decision_summary, get_decisions, get_escalations
from automation.self_check import run_full_check, find_gaps, heal_issues

STATE_FILE = PROJECT_ROOT / "data" / "nerve_state.json"
LOG_DIR = PROJECT_ROOT / "data" / "nerve_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Cycle timing ───────────────────────────────────────────────
CYCLE_INTERVAL_MINUTES = 60      # Full cycle every hour
OUTREACH_BATCH_SIZE = 5          # Leads per outreach cycle
MIN_PROSPECTS_THRESHOLD = 10     # Replenish below this


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"cycles_run": 0, "started_at": None, "last_cycle": None}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Single NERVE Cycle ─────────────────────────────────────────

def run_cycle() -> dict:
    """Execute one full NERVE autonomous cycle."""
    state = _load_state()
    cycle_num = state.get("cycles_run", 0) + 1
    now = datetime.now(timezone.utc)

    print(f"\n{'='*70}")
    print(f"  NERVE CYCLE #{cycle_num} — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}")

    cycle_report = {
        "cycle": cycle_num,
        "started": now.isoformat(),
        "phases": {},
        "decisions_made": 0,
        "issues_healed": 0,
        "escalations": 0,
    }

    # ── Phase 1: Self-Check ────────────────────────────────────
    print(f"\n[PHASE 1] Deep Self-Check...")
    try:
        check_report = run_full_check()
        status = check_report["status"]
        issue_count = check_report["metrics"]["issue_count"]
        opp_count = check_report["metrics"]["opportunity_count"]
        print(f"  System: {status} | Issues: {issue_count} | Opportunities: {opp_count}")
        cycle_report["phases"]["self_check"] = {"status": status, "issues": issue_count}

        log_decision(
            actor="NERVE",
            action="self_check",
            reasoning=f"Cycle #{cycle_num} self-check",
            outcome=f"System {status}, {issue_count} issues found",
        )
    except Exception as e:
        print(f"  [ERROR] Self-check failed: {e}")
        check_report = {"checks": {}, "issues": [], "status": "UNKNOWN"}
        cycle_report["phases"]["self_check"] = {"status": "error", "error": str(e)}

    # ── Phase 2: Gap Analysis & Auto-Heal ──────────────────────
    print(f"\n[PHASE 2] Gap Analysis & Auto-Heal...")
    try:
        gaps = find_gaps(check_report)
        if gaps:
            print(f"  Found {len(gaps)} gaps:")
            for g in gaps:
                print(f"    [{g['severity']}] {g['description']}")

            heal_results = heal_issues(gaps)
            healed = sum(1 for r in heal_results if r.get("success"))
            escalated = sum(1 for r in heal_results if r.get("action") == "escalated")
            cycle_report["phases"]["healing"] = {
                "gaps_found": len(gaps),
                "healed": healed,
                "escalated": escalated,
            }
            cycle_report["issues_healed"] = healed
            cycle_report["escalations"] = escalated
            print(f"  Healed: {healed} | Escalated: {escalated}")
        else:
            print(f"  No gaps found — system healthy.")
            cycle_report["phases"]["healing"] = {"gaps_found": 0}
    except Exception as e:
        print(f"  [ERROR] Healing failed: {e}")
        cycle_report["phases"]["healing"] = {"error": str(e)}

    # ── Phase 3: Prospect Replenishment ────────────────────────
    print(f"\n[PHASE 3] Prospect Pipeline...")
    try:
        from automation.outreach import load_prospects
        remaining = len(load_prospects())
        print(f"  Prospects remaining: {remaining}")

        if remaining < MIN_PROSPECTS_THRESHOLD:
            print(f"  Below threshold ({MIN_PROSPECTS_THRESHOLD}). Replenishing...")
            from automation.prospect_engine import generate_prospects
            added = generate_prospects(count=25)
            remaining += added
            log_decision(
                actor="NERVE",
                action="replenish_prospects",
                reasoning=f"Prospects below {MIN_PROSPECTS_THRESHOLD} threshold",
                outcome=f"Added {added} new prospects, now {remaining} available",
            )
            cycle_report["decisions_made"] += 1

        cycle_report["phases"]["prospects"] = {"remaining": remaining}
    except Exception as e:
        print(f"  [ERROR] Prospect check failed: {e}")
        cycle_report["phases"]["prospects"] = {"error": str(e)}

    # ── Phase 4: Outreach Execution ────────────────────────────
    print(f"\n[PHASE 4] Outreach Execution...")
    try:
        from automation.outreach import load_prospects, generate_batch, send_approved, send_followups

        prospects = load_prospects()
        if prospects:
            print(f"  Running outreach batch ({OUTREACH_BATCH_SIZE} leads)...")
            gen_results = generate_batch(count=OUTREACH_BATCH_SIZE, priority="high")
            if not gen_results:
                gen_results = generate_batch(count=OUTREACH_BATCH_SIZE, priority="all")

            passed = sum(1 for r in gen_results if r.get("qa_status") == "PASS")

            # Auto-approve and send
            sent = send_approved(auto_approve=True)

            log_decision(
                actor="NERVE",
                action="outreach_cycle",
                reasoning=f"Cycle #{cycle_num} — {len(prospects)} prospects available",
                outcome=f"Generated {len(gen_results)} ({passed} passed QA), sent {len(sent)}",
            )
            cycle_report["decisions_made"] += 1
            cycle_report["phases"]["outreach"] = {
                "generated": len(gen_results),
                "qa_passed": passed,
                "sent": len(sent),
            }
        else:
            print(f"  No prospects available. Skipping outreach.")
            cycle_report["phases"]["outreach"] = {"status": "no_prospects"}

        # Follow-ups always
        followups = send_followups()
        cycle_report["phases"]["followups"] = {"sent": len(followups)}
        if followups:
            print(f"  Sent {len(followups)} follow-ups")
    except Exception as e:
        print(f"  [ERROR] Outreach failed: {e}")
        cycle_report["phases"]["outreach"] = {"error": str(e)}

    # ── Phase 5: C-Suite Executive Cadence ─────────────────────
    print(f"\n[PHASE 5] C-Suite Cadence...")
    try:
        from c_suite.scheduler import run_due_actions
        actions = run_due_actions()
        if actions:
            print(f"  Ran: {', '.join(actions)}")
            log_decision(
                actor="NERVE",
                action="csuite_cadence",
                reasoning=f"Scheduled C-Suite actions due",
                outcome=f"Completed: {', '.join(actions)}",
            )
            cycle_report["decisions_made"] += 1
        else:
            print(f"  No C-Suite actions due.")
        cycle_report["phases"]["csuite"] = {"actions": actions}
    except Exception as e:
        print(f"  [ERROR] C-Suite cadence failed: {e}")
        cycle_report["phases"]["csuite"] = {"error": str(e)}

    # ── Phase 6: Health Snapshot ───────────────────────────────
    print(f"\n[PHASE 6] Health Snapshot...")
    try:
        from dashboard.health import full_dashboard
        dashboard = full_dashboard()
        providers = dashboard.get("health", {}).get("llm_providers", [])
        queue = dashboard.get("queue", {})
        print(f"  Providers: {', '.join(providers) if providers else 'NONE'}")
        print(f"  Queue: {queue}")
        print(f"  Clients: {dashboard.get('active_clients', 0)}")
        cycle_report["phases"]["health"] = {
            "providers_up": len(providers),
            "queue": queue,
        }
    except Exception as e:
        print(f"  [ERROR] Health snapshot failed: {e}")

    # ── Phase 7: Revenue Check ─────────────────────────────────
    print(f"\n[PHASE 7] Revenue Check...")
    try:
        from automation.revenue_daemon import check_stripe_revenue
        rev = check_stripe_revenue()
        new_charges = rev.get("new_charges", 0)
        total = rev.get("total", 0)
        print(f"  Stripe total: ${total:.2f} | New charges: {new_charges}")
        if new_charges > 0:
            log_decision(
                actor="NERVE",
                action="revenue_detected",
                reasoning=f"Cycle #{cycle_num} — {new_charges} new Stripe charges",
                outcome=f"${total:.2f} total revenue logged",
            )
            cycle_report["decisions_made"] += 1
        cycle_report["phases"]["revenue"] = {"total": total, "new": new_charges}
    except Exception as e:
        print(f"  [ERROR] Revenue check failed: {e}")
        cycle_report["phases"]["revenue"] = {"error": str(e)}

    # ── Phase 8: Freelancing Job Hunt (every 3 cycles) ────────
    if cycle_num % 3 == 0:
        print(f"\n[PHASE 8] Freelancing Job Hunt Cycle...")
        try:
            from automation.job_aggregator import aggregate, export_feed
            feed = aggregate(max_age_hours=24)
            unbid = [j for j in feed if not j.get("already_bid") and j.get("rank_score", 0) >= 0.25]
            print(f"  Aggregated {len(feed)} jobs, {len(unbid)} unbid opportunities")
            export_feed(feed, "")
            log_decision(
                actor="NERVE",
                action="job_hunt_aggregate",
                reasoning=f"Cycle #{cycle_num} — periodic job aggregation",
                outcome=f"{len(feed)} total, {len(unbid)} actionable opportunities",
            )
            cycle_report["decisions_made"] += 1
            cycle_report["phases"]["job_hunt"] = {
                "total": len(feed),
                "unbid": len(unbid),
                "top_platforms": list(set(j["platform"] for j in feed[:10])),
            }
        except Exception as e:
            print(f"  [ERROR] Job hunt aggregation failed: {e}")
            cycle_report["phases"]["job_hunt"] = {"error": str(e)}

    # ── Phase 9: Autobidder Scan (every 2 cycles) ─────────────
    if cycle_num % 2 == 0:
        print(f"\n[PHASE 9] Autobidder Scan...")
        try:
            from automation.autobidder import run_scan
            scan_result = run_scan()
            bids_made = scan_result.get("bids_queued", 0) if isinstance(scan_result, dict) else 0
            print(f"  Autobidder: {bids_made} bids queued")
            log_decision(
                actor="NERVE",
                action="autobidder_scan",
                reasoning=f"Cycle #{cycle_num} — automated bid scanning",
                outcome=f"{bids_made} bids queued for review",
            )
            cycle_report["decisions_made"] += 1
            cycle_report["phases"]["autobidder"] = {"bids_queued": bids_made}
        except Exception as e:
            print(f"  [ERROR] Autobidder scan failed: {e}")
            cycle_report["phases"]["autobidder"] = {"error": str(e)}

    # ── Phase 10: Delivery Check (every 4 cycles) ─────────────
    if cycle_num % 4 == 0:
        print(f"\n[PHASE 10] Cross-Platform Delivery Check...")
        delivery_summary = {}
        # Check Fiverr orders
        try:
            from automation.fiverr_orders import show_status as fiverr_status
            fiverr_status()
            delivery_summary["fiverr"] = "checked"
        except Exception as e:
            delivery_summary["fiverr"] = f"error: {e}"
        # Log
        log_decision(
            actor="NERVE",
            action="delivery_check",
            reasoning=f"Cycle #{cycle_num} — periodic delivery pipeline check",
            outcome=f"Platforms checked: {list(delivery_summary.keys())}",
        )
        cycle_report["decisions_made"] += 1
        cycle_report["phases"]["delivery_check"] = delivery_summary

    # ── Phase 11: FAIL Reprocessing (every 6 cycles) ───────────
    if cycle_num % 6 == 0:
        print(f"\n[PHASE 11] FAIL Reprocessing...")
        try:
            from automation.reprocess import find_fail_files, reprocess
            fails = find_fail_files()
            if fails:
                print(f"  Found {len(fails)} FAIL files. Reprocessing up to 5...")
                result = reprocess(count=5)
                log_decision(
                    actor="NERVE",
                    action="reprocess_fails",
                    reasoning=f"Cycle #{cycle_num} — periodic FAIL reprocessing",
                    outcome=f"{result.get('success', 0)} fixed, {result.get('still_fail', 0)} still failing",
                )
                cycle_report["decisions_made"] += 1
                cycle_report["phases"]["reprocess"] = result
            else:
                print(f"  No FAIL files to reprocess.")
                cycle_report["phases"]["reprocess"] = {"status": "none_found"}
        except Exception as e:
            print(f"  [ERROR] Reprocessing failed: {e}")
            cycle_report["phases"]["reprocess"] = {"error": str(e)}

    # ── Finalize ───────────────────────────────────────────────
    cycle_report["finished"] = datetime.now(timezone.utc).isoformat()
    elapsed = (datetime.now(timezone.utc) - now).total_seconds()
    cycle_report["elapsed_seconds"] = round(elapsed, 1)

    # Save cycle log
    log_file = LOG_DIR / f"nerve_cycle_{cycle_num:04d}.json"
    log_file.write_text(json.dumps(cycle_report, indent=2), encoding="utf-8")

    # Update state
    state["cycles_run"] = cycle_num
    state["last_cycle"] = now.isoformat()
    state["last_status"] = check_report.get("status", "UNKNOWN")
    if not state.get("started_at"):
        state["started_at"] = now.isoformat()
    _save_state(state)

    print(f"\n{'='*70}")
    print(f"  NERVE CYCLE #{cycle_num} COMPLETE — {elapsed:.1f}s")
    print(f"  Decisions: {cycle_report['decisions_made']} | Healed: {cycle_report['issues_healed']} | Escalations: {cycle_report['escalations']}")
    print(f"{'='*70}")

    return cycle_report


# ── 24/7 Daemon ────────────────────────────────────────────────

def daemon_loop():
    """Run NERVE continuously — the autonomous heartbeat."""
    print(f"\n{'#'*70}")
    print(f"  NERVE DAEMON ONLINE")
    print(f"  Nexus Engine for Resilient Vigilant Execution")
    print(f"  Cycle interval: {CYCLE_INTERVAL_MINUTES} minutes")
    print(f"  Outreach batch: {OUTREACH_BATCH_SIZE} leads/cycle")
    print(f"  Press Ctrl+C to stop")
    print(f"{'#'*70}")

    log_decision(
        actor="NERVE",
        action="daemon_start",
        reasoning="NERVE daemon initiated",
        outcome="Running 24/7 autonomous mode",
        severity="INFO",
    )

    consecutive_failures = 0
    max_failures = 5

    while True:
        try:
            run_cycle()
            consecutive_failures = 0
        except KeyboardInterrupt:
            print("\n\n[NERVE] Daemon stopped by operator.")
            log_decision(
                actor="NERVE",
                action="daemon_stop",
                reasoning="Operator interrupted",
                outcome="Clean shutdown",
            )
            break
        except Exception as e:
            consecutive_failures += 1
            print(f"\n[NERVE] Cycle failed: {e}")
            traceback.print_exc()

            log_decision(
                actor="NERVE",
                action="cycle_failure",
                reasoning=f"Unhandled exception in cycle",
                outcome=str(e),
                severity="ERROR",
            )

            if consecutive_failures >= max_failures:
                log_escalation(
                    source="NERVE",
                    issue=f"{consecutive_failures} consecutive cycle failures. Last: {e}",
                    severity="CRITICAL",
                    recommended_action="Manual intervention required. Check logs.",
                )
                print(f"\n[NERVE] {consecutive_failures} consecutive failures. Pausing for 10 minutes...")
                time.sleep(600)
                consecutive_failures = 0
            else:
                # Brief pause before retry
                time.sleep(60)
                continue

        # Wait for next cycle
        print(f"\n[NERVE] Next cycle in {CYCLE_INTERVAL_MINUTES} minutes...")
        try:
            time.sleep(CYCLE_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("\n[NERVE] Daemon stopped.")
            break


# ── Status Display ─────────────────────────────────────────────

def show_status():
    """Display NERVE operational status."""
    state = _load_state()
    print(f"\n{'='*60}")
    print(f"  NERVE — Operational Status")
    print(f"{'='*60}")
    print(f"  Cycles run: {state.get('cycles_run', 0)}")
    print(f"  First started: {state.get('started_at', 'never')}")
    print(f"  Last cycle: {state.get('last_cycle', 'never')}")
    print(f"  Last status: {state.get('last_status', 'unknown')}")

    # Recent decisions
    summary = decision_summary(hours=24)
    print(f"\n── Last 24h ──")
    print(f"  Decisions: {summary['total_decisions']}")
    print(f"  By actor: {summary['by_actor']}")
    print(f"  Pending escalations: {summary['escalations_pending']}")

    # Pending escalations
    esc = get_escalations(unacknowledged_only=True)
    if esc:
        print(f"\n── Pending Escalations ──")
        for e in esc[-5:]:
            print(f"  [{e['severity']}] {e['issue']} ({e['timestamp'][:16]})")


def show_decisions(limit: int = 20):
    """Show recent autonomous decisions."""
    decisions = get_decisions(limit=limit)
    print(f"\n{'='*60}")
    print(f"  NERVE — Recent Decisions (last {limit})")
    print(f"{'='*60}")
    for d in decisions:
        ts = d['timestamp'][:16]
        print(f"  [{ts}] {d['actor']}: {d['action']}")
        print(f"           {d['outcome']}")


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NERVE — Autonomous DIGITAL LABOUR daemon")
    parser.add_argument("--daemon", action="store_true", help="Run 24/7 daemon mode")
    parser.add_argument("--status", action="store_true", help="Show NERVE status")
    parser.add_argument("--decisions", action="store_true", help="Show recent decisions")
    parser.add_argument("--cycle", action="store_true", help="Run single cycle")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.decisions:
        show_decisions()
    elif args.daemon:
        daemon_loop()
    else:
        run_cycle()
