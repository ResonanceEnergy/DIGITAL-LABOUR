"""NERVE — Nexus Engine for Resilient Vigilant Execution.

The autonomous 24/7 daemon that runs BIT RAGE LABOUR without human intervention.
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
import io
import json
import logging
import signal
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── UTF-8 stdout fix for Windows (prevents charmap crashes) ────
if sys.stdout and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from automation.decision_log import log_decision, log_escalation, decision_summary, get_decisions, get_escalations
from automation.self_check import run_full_check, find_gaps, heal_issues

STATE_FILE = PROJECT_ROOT / "data" / "nerve_state.json"
LOG_DIR = PROJECT_ROOT / "data" / "nerve_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Structured logging ─────────────────────────────────────────────────────
_LOG_FMT = logging.Formatter("%(asctime)s [%(levelname)s] nerve — %(message)s")
logger = logging.getLogger("nerve")
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setFormatter(_LOG_FMT)
    logger.addHandler(_sh)
    _fh = logging.FileHandler(LOG_DIR / "nerve.log", encoding="utf-8")
    _fh.setFormatter(_LOG_FMT)
    logger.addHandler(_fh)
    logger.setLevel(logging.INFO)
logger.propagate = False

# ── Cycle timing ───────────────────────────────────────────────
CYCLE_INTERVAL_MINUTES = 60      # Full cycle every hour
OUTREACH_BATCH_SIZE = 5          # Leads per outreach cycle
MIN_PROSPECTS_THRESHOLD = 10     # Replenish below this

# ── Graceful Shutdown ──────────────────────────────────────────
_shutdown_requested = False


def _handle_shutdown(signum, frame):
    """Handle SIGTERM/SIGINT for graceful daemon shutdown."""
    global _shutdown_requested
    sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    logger.info(f"\n[NERVE] Received {sig_name} — finishing current phase then shutting down...")
    _shutdown_requested = True


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"cycles_run": 0, "started_at": None, "last_cycle": None}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _check_smtp_health() -> bool:
    """Quick SMTP auth check — returns True if login succeeds, False otherwise."""
    import os
    import smtplib
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    if not (smtp_host and smtp_user and smtp_pass):
        return False
    try:
        with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587")), timeout=10) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
        return True
    except Exception:
        return False


def _check_imap_health() -> bool:
    """Quick IMAP auth check — returns True if login succeeds."""
    import os
    import imaplib
    host = os.getenv("IMAP_HOST", "")
    user = os.getenv("IMAP_USER", os.getenv("SMTP_USER", ""))
    passwd = os.getenv("IMAP_PASS", os.getenv("SMTP_PASS", ""))
    if not (host and user and passwd):
        return False
    try:
        m = imaplib.IMAP4_SSL(host, timeout=10)
        m.login(user, passwd)
        m.logout()
        return True
    except Exception:
        return False


# ── Single NERVE Cycle ─────────────────────────────────────────

def run_cycle() -> dict:
    """Execute one full NERVE autonomous cycle."""
    state = _load_state()
    cycle_num = state.get("cycles_run", 0) + 1
    now = datetime.now(timezone.utc)

    logger.info(f"\n{'='*70}")
    logger.info(f"  NERVE CYCLE #{cycle_num} — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"{'='*70}")

    cycle_report = {
        "cycle": cycle_num,
        "started": now.isoformat(),
        "phases": {},
        "decisions_made": 0,
        "issues_healed": 0,
        "escalations": 0,
    }

    # ── Phase 1: Self-Check ────────────────────────────────────
    logger.info(f"\n[PHASE 1] Deep Self-Check...")
    try:
        check_report = run_full_check()
        status = check_report["status"]
        issue_count = check_report["metrics"]["issue_count"]
        opp_count = check_report["metrics"]["opportunity_count"]
        logger.info(f"  System: {status} | Issues: {issue_count} | Opportunities: {opp_count}")
        cycle_report["phases"]["self_check"] = {"status": status, "issues": issue_count}

        log_decision(
            actor="NERVE",
            action="self_check",
            reasoning=f"Cycle #{cycle_num} self-check",
            outcome=f"System {status}, {issue_count} issues found",
        )
    except Exception as e:
        logger.error(f"  [ERROR] Self-check failed: {e}")
        check_report = {"checks": {}, "issues": [], "status": "UNKNOWN"}
        cycle_report["phases"]["self_check"] = {"status": "error", "error": str(e)}

    # ── Phase 2: Gap Analysis & Auto-Heal ──────────────────────
    logger.info(f"\n[PHASE 2] Gap Analysis & Auto-Heal...")
    try:
        gaps = find_gaps(check_report)
        if gaps:
            logger.info(f"  Found {len(gaps)} gaps:")
            for g in gaps:
                logger.info(f"    [{g['severity']}] {g['description']}")

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
            logger.info(f"  Healed: {healed} | Escalated: {escalated}")
        else:
            logger.info(f"  No gaps found — system healthy.")
            cycle_report["phases"]["healing"] = {"gaps_found": 0}
    except Exception as e:
        logger.error(f"  [ERROR] Healing failed: {e}")
        cycle_report["phases"]["healing"] = {"error": str(e)}

    # ── Phase 3: Prospect Replenishment ────────────────────────
    logger.info(f"\n[PHASE 3] Prospect Pipeline...")
    try:
        from automation.outreach import load_prospects
        remaining = len(load_prospects())
        logger.info(f"  Prospects remaining: {remaining}")

        if remaining < MIN_PROSPECTS_THRESHOLD:
            logger.info(f"  Below threshold ({MIN_PROSPECTS_THRESHOLD}). Replenishing...")
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
        logger.error(f"  [ERROR] Prospect check failed: {e}")
        cycle_report["phases"]["prospects"] = {"error": str(e)}

    # ── Phase 4: Outreach Execution ────────────────────────────
    logger.info(f"\n[PHASE 4] Outreach Execution...")
    try:
        from automation.outreach import load_prospects, generate_batch, send_approved, send_followups

        # Pre-flight: check SMTP health before spending LLM tokens
        smtp_ok = _check_smtp_health()
        if not smtp_ok:
            logger.warning("  SMTP auth broken — skipping outreach generation (would waste LLM tokens).")
            logger.warning("  Fix: update SMTP_PASS in .env with a valid Zoho app password.")
            cycle_report["phases"]["outreach"] = {"status": "smtp_auth_broken", "skipped": True}
        else:
            prospects = load_prospects()
            if prospects:
                logger.info(f"  Running outreach batch ({OUTREACH_BATCH_SIZE} leads)...")
                gen_results = generate_batch(count=OUTREACH_BATCH_SIZE, priority="high")
                if not gen_results:
                    gen_results = generate_batch(count=OUTREACH_BATCH_SIZE, priority="all")

                passed = sum(1 for r in gen_results if r.get("qa_status") == "PASS")

                # Auto-approve and send
                sent = send_approved(auto_approve=True)

                # Check if sends are all failing (auth dead mid-cycle)
                failed = [s for s in sent if s.get("method") == "failed" and "Authentication" in s.get("error", "")]
                if failed and len(failed) == len(sent):
                    logger.warning(f"  All {len(failed)} sends failed with auth error — SMTP password is dead.")

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
                    "auth_failures": len(failed),
                }
            else:
                logger.info(f"  No prospects available. Skipping outreach.")
                cycle_report["phases"]["outreach"] = {"status": "no_prospects"}

        # Follow-ups always (file-queued, don't need SMTP right now)
        followups = send_followups()
        cycle_report["phases"]["followups"] = {"sent": len(followups)}
        if followups:
            logger.info(f"  Sent {len(followups)} follow-ups")
    except Exception as e:
        logger.error(f"  [ERROR] Outreach failed: {e}")
        cycle_report["phases"]["outreach"] = {"error": str(e)}

    # ── Phase 5: C-Suite Executive Cadence ─────────────────────
    logger.info(f"\n[PHASE 5] C-Suite Cadence...")
    try:
        from c_suite.scheduler import run_due_actions
        actions = run_due_actions()
        if actions:
            logger.info(f"  Ran: {', '.join(actions)}")
            log_decision(
                actor="NERVE",
                action="csuite_cadence",
                reasoning=f"Scheduled C-Suite actions due",
                outcome=f"Completed: {', '.join(actions)}",
            )
            cycle_report["decisions_made"] += 1
        else:
            logger.info(f"  No C-Suite actions due.")
        cycle_report["phases"]["csuite"] = {"actions": actions}
    except Exception as e:
        logger.error(f"  [ERROR] C-Suite cadence failed: {e}")
        cycle_report["phases"]["csuite"] = {"error": str(e)}

    # ── Phase 6: Health Snapshot ───────────────────────────────
    logger.info(f"\n[PHASE 6] Health Snapshot...")
    try:
        from dashboard.health import full_dashboard
        dashboard = full_dashboard()
        providers = dashboard.get("health", {}).get("llm_providers", [])
        queue = dashboard.get("queue", {})
        logger.info(f"  Providers: {', '.join(providers) if providers else 'NONE'}")
        logger.info(f"  Queue: {queue}")
        logger.info(f"  Clients: {dashboard.get('active_clients', 0)}")
        cycle_report["phases"]["health"] = {
            "providers_up": len(providers),
            "queue": queue,
        }
    except Exception as e:
        logger.error(f"  [ERROR] Health snapshot failed: {e}")

    # ── Phase 7: Revenue Check ─────────────────────────────────
    logger.info(f"\n[PHASE 7] Revenue Check...")
    try:
        from automation.revenue_daemon import check_stripe_revenue
        rev = check_stripe_revenue()
        new_charges = rev.get("new_charges", 0)
        total = rev.get("total", 0)
        logger.info(f"  Stripe total: ${total:.2f} | New charges: {new_charges}")
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
        logger.error(f"  [ERROR] Revenue check failed: {e}")
        cycle_report["phases"]["revenue"] = {"error": str(e)}

    # ── Phase 8: Freelancing Job Hunt (every 3 cycles) ────────
    if cycle_num % 3 == 0:
        logger.info(f"\n[PHASE 8] Freelancing Job Hunt Cycle...")
        try:
            from automation.job_aggregator import aggregate, export_feed
            feed = aggregate(max_age_hours=24)
            unbid = [j for j in feed if not j.get("already_bid") and j.get("rank_score", 0) >= 0.25]
            logger.info(f"  Aggregated {len(feed)} jobs, {len(unbid)} unbid opportunities")
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
            logger.error(f"  [ERROR] Job hunt aggregation failed: {e}")
            cycle_report["phases"]["job_hunt"] = {"error": str(e)}

    # ── Phase 9: Autobidder Scan (every 2 cycles) ─────────────
    if cycle_num % 2 == 0:
        logger.info(f"\n[PHASE 9] Autobidder Scan...")
        try:
            from automation.autobidder import run_scan
            scan_result = run_scan()
            bids_made = scan_result.get("bids_queued", 0) if isinstance(scan_result, dict) else 0
            logger.info(f"  Autobidder: {bids_made} bids queued")
            log_decision(
                actor="NERVE",
                action="autobidder_scan",
                reasoning=f"Cycle #{cycle_num} — automated bid scanning",
                outcome=f"{bids_made} bids queued for review",
            )
            cycle_report["decisions_made"] += 1
            cycle_report["phases"]["autobidder"] = {"bids_queued": bids_made}
        except Exception as e:
            logger.error(f"  [ERROR] Autobidder scan failed: {e}")
            cycle_report["phases"]["autobidder"] = {"error": str(e)}

    # ── Phase 10: Delivery Check (every 4 cycles) ─────────────
    if cycle_num % 4 == 0:
        logger.info(f"\n[PHASE 10] Cross-Platform Delivery Check...")
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
        logger.info(f"\n[PHASE 11] FAIL Reprocessing...")
        try:
            from automation.reprocess import find_fail_files, reprocess
            fails = find_fail_files()
            if fails:
                logger.info(f"  Found {len(fails)} FAIL files. Reprocessing up to 5...")
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
                logger.info(f"  No FAIL files to reprocess.")
                cycle_report["phases"]["reprocess"] = {"status": "none_found"}
        except Exception as e:
            logger.error(f"  [ERROR] Reprocessing failed: {e}")
            cycle_report["phases"]["reprocess"] = {"error": str(e)}

    # ── Phase 12: OpenClaw Revenue Reconciliation (every 4 cycles) ──
    if cycle_num % 4 == 0:
        logger.info(f"\n[PHASE 12] OpenClaw Revenue Reconciliation...")
        try:
            from openclaw.engine import OpenClawEngine
            oc = OpenClawEngine()
            rev = oc.reconcile_revenue()
            log_decision(
                actor="NERVE",
                action="openclaw_revenue",
                reasoning=f"Cycle #{cycle_num} — periodic revenue reconciliation",
                outcome=f"Total: ${rev.get('total', 0):.2f} across {len(rev.get('sources', {}))} sources",
            )
            cycle_report["decisions_made"] += 1
            cycle_report["phases"]["openclaw_revenue"] = rev
        except Exception as e:
            logger.error(f"  [ERROR] OpenClaw revenue check failed: {e}")
            cycle_report["phases"]["openclaw_revenue"] = {"error": str(e)}

    # ── Phase 13: Inbox Sales Response (every cycle) ──────────
    logger.info(f"\n[PHASE 13] Inbox Sales Response (sales@bit-rage-labour.com)...")
    if not _check_imap_health():
        logger.warning("  IMAP auth broken — skipping inbox processing.")
        logger.warning("  Fix: update IMAP_PASS / SMTP_PASS in .env with a valid Zoho app password.")
        cycle_report["phases"]["inbox"] = {"skipped": "IMAP auth broken"}
    else:
        try:
            # First: pull fresh emails from IMAP
            from automation.inbox_reader import process_inbox
            inbox_result = process_inbox()
            new_leads = inbox_result.get("leads", 0) + inbox_result.get("demos", 0)
            logger.info(f"  Inbox: {inbox_result.get('processed', 0)} processed, {new_leads} new leads")

            # Then: auto-respond to any unresponded leads
            from openclaw.inbox_agent import process_new_leads
            reply_result = process_new_leads(dry_run=False)
            if reply_result["processed"] > 0:
                logger.info(f"  Responses: {reply_result['sent']} sent, {reply_result['errors']} errors")
                log_decision(
                    actor="NERVE",
                    action="inbox_response",
                    reasoning=f"Cycle #{cycle_num} — inbound lead auto-response",
                    outcome=f"{reply_result['processed']} drafted, {reply_result['sent']} sent",
                )
                cycle_report["decisions_made"] += 1
            else:
                logger.info(f"  No new leads pending response.")

            cycle_report["phases"]["inbox"] = {
                "emails_processed": inbox_result.get("processed", 0),
                "new_leads": new_leads,
                "responses_sent": reply_result["sent"],
            }
        except Exception as e:
            logger.error(f"  [ERROR] Inbox processing failed: {e}")
            cycle_report["phases"]["inbox"] = {"error": str(e)}

    # ── Phase 14: OpenClaw Full Freelance Cycle (every 2 cycles) ──
    if cycle_num % 2 == 0:
        logger.info(f"\n[PHASE 14] OpenClaw Freelance Cycle (all platforms)...")
        try:
            from openclaw.engine import OpenClawEngine
            oc = OpenClawEngine()
            fc_result = oc.freelance_cycle(
                platforms=["freelancer", "upwork", "fiverr", "pph", "guru"],
                scan_only=False,
            )
            jobs_found = fc_result.get("phases", {}).get("aggregation", {}).get("total_jobs", 0)
            bids_queued = fc_result.get("phases", {}).get("bidding", {}).get("bids_queued", 0)
            logger.info(f"  Jobs found: {jobs_found} | Bids queued: {bids_queued}")
            log_decision(
                actor="NERVE",
                action="openclaw_freelance_cycle",
                reasoning=f"Cycle #{cycle_num} — full cross-platform job hunt + bid",
                outcome=f"{jobs_found} jobs aggregated, {bids_queued} bids queued",
            )
            cycle_report["decisions_made"] += 1
            cycle_report["phases"]["openclaw_freelance"] = {
                "jobs_found": jobs_found,
                "bids_queued": bids_queued,
                "elapsed_s": fc_result.get("elapsed_s", 0),
            }
        except Exception as e:
            logger.error(f"  [ERROR] OpenClaw freelance cycle failed: {e}")
            cycle_report["phases"]["openclaw_freelance"] = {"error": str(e)}

    # ── Phase 15: X/Twitter Daily Post (every cycle, self-throttled) ──
    logger.info(f"\n[PHASE 15] X/Twitter Daily Post (@agentbravo069)...")
    try:
        from automation.x_poster import post_next, show_status as x_status
        result = post_next()
        if result.get("success"):
            logger.info(f"  Posted tweet: {result.get('tweet_id')}")
            log_decision(
                actor="NERVE",
                action="x_daily_post",
                reasoning=f"Cycle #{cycle_num} — daily X/Twitter post",
                outcome=f"Tweet posted: {result.get('tweet_id')}",
            )
            cycle_report["decisions_made"] += 1
        elif result.get("queued"):
            logger.info(f"  Tweet queued (API read-only, needs OAuth 1.0a)")
        elif "Already posted today" in result.get("error", ""):
            logger.info(f"  Already posted today — skipping.")
        else:
            logger.warning(f"  X post failed: {result.get('error', 'unknown')}")
        cycle_report["phases"]["x_poster"] = result
    except Exception as e:
        logger.error(f"  [ERROR] X poster failed: {e}")
        cycle_report["phases"]["x_poster"] = {"error": str(e)}

    # ── Phase 16: Lead Scoring Refresh (every 3 cycles) ───────
    if cycle_num % 3 == 0:
        logger.info(f"\n[PHASE 16] Lead Scoring Refresh...")
        try:
            from automation.lead_scorer import score_all_prospects, get_top_prospects
            scores = score_all_prospects(rescore=True)
            top = get_top_prospects(5)
            top_names = [t["company"] for t in top]
            logger.info(f"  Scored {len(scores)} prospects. Top 5: {', '.join(top_names)}")
            log_decision(
                actor="NERVE",
                action="lead_scoring",
                reasoning=f"Cycle #{cycle_num} — periodic lead score refresh",
                outcome=f"{len(scores)} scored, top: {', '.join(top_names)}",
            )
            cycle_report["phases"]["lead_scoring"] = {
                "total_scored": len(scores),
                "top_5": top_names,
            }
        except Exception as e:
            logger.error(f"  [ERROR] Lead scoring failed: {e}")
            cycle_report["phases"]["lead_scoring"] = {"error": str(e)}

    # ── Phase 17: Email Tracking Sync (every cycle) ───────────
    logger.info(f"\n[PHASE 17] Email Tracking Sync...")
    try:
        from automation.email_tracker import sync_inbox_replies, build_tracking_report
        matches = sync_inbox_replies()
        report = build_tracking_report()
        funnel = report.get("funnel", {})
        logger.info(f"  Funnel: {funnel.get('total_emails_sent', 0)} sent → {funnel.get('replies_received', 0)} replies ({funnel.get('reply_rate_pct', 0)}%)")
        if matches > 0:
            logger.info(f"  Synced {matches} new reply matches")
            log_decision(
                actor="NERVE",
                action="email_tracking_sync",
                reasoning=f"Cycle #{cycle_num} — synced inbox replies",
                outcome=f"{matches} new replies matched, {funnel.get('reply_rate_pct', 0)}% reply rate",
            )
            cycle_report["decisions_made"] += 1
        cycle_report["phases"]["email_tracking"] = funnel
    except Exception as e:
        logger.error(f"  [ERROR] Email tracking failed: {e}")
        cycle_report["phases"]["email_tracking"] = {"error": str(e)}

    # ── Phase 18: Resonance Sync (NCC/NCL/AAC — every 3 cycles) ──
    if cycle_num % 3 == 0:
        logger.info(f"\n[PHASE 18] Resonance Sync (NCC/NCL/AAC)...")
        try:
            from resonance.sync import run_due_jobs
            ran_jobs = run_due_jobs()
            if ran_jobs:
                logger.info(f"  Resonance sync ran: {', '.join(ran_jobs)}")
                log_decision(
                    actor="NERVE",
                    action="resonance_sync",
                    reasoning=f"Cycle #{cycle_num} — cross-pillar sync",
                    outcome=f"Ran: {', '.join(ran_jobs)}",
                )
                cycle_report["decisions_made"] += 1
            else:
                logger.info(f"  No sync jobs due this cycle")
            cycle_report["phases"]["resonance_sync"] = {"ran": ran_jobs}
        except Exception as e:
            logger.error(f"  [ERROR] Resonance sync failed: {e}")
            cycle_report["phases"]["resonance_sync"] = {"error": str(e)}

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

    logger.info(f"\n{'='*70}")
    logger.info(f"  NERVE CYCLE #{cycle_num} COMPLETE — {elapsed:.1f}s")
    logger.info(f"  Decisions: {cycle_report['decisions_made']} | Healed: {cycle_report['issues_healed']} | Escalations: {cycle_report['escalations']}")
    logger.info(f"{'='*70}")

    return cycle_report


# ── 24/7 Daemon ────────────────────────────────────────────────

def daemon_loop():
    """Run NERVE continuously — the autonomous heartbeat."""
    global _shutdown_requested

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    if hasattr(signal, "SIGBREAK"):  # Windows
        signal.signal(signal.SIGBREAK, _handle_shutdown)

    logger.info(f"\n{'#'*70}")
    logger.info(f"  NERVE DAEMON ONLINE")
    logger.info(f"  Nexus Engine for Resilient Vigilant Execution")
    logger.info(f"  Cycle interval: {CYCLE_INTERVAL_MINUTES} minutes")
    logger.info(f"  Outreach batch: {OUTREACH_BATCH_SIZE} leads/cycle")
    logger.info(f"  Graceful shutdown: SIGTERM/SIGINT/Ctrl+C")
    logger.info(f"{'#'*70}")

    log_decision(
        actor="NERVE",
        action="daemon_start",
        reasoning="NERVE daemon initiated",
        outcome="Running 24/7 autonomous mode",
        severity="INFO",
    )

    consecutive_failures = 0
    max_failures = 5

    while not _shutdown_requested:
        try:
            run_cycle()
            consecutive_failures = 0
        except KeyboardInterrupt:
            _shutdown_requested = True
            break
        except Exception as e:
            consecutive_failures += 1
            logger.info(f"\n[NERVE] Cycle failed: {e}")
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
                logger.info(f"\n[NERVE] {consecutive_failures} consecutive failures. Pausing for 10 minutes...")
                # Interruptible sleep
                for _ in range(600):
                    if _shutdown_requested:
                        break
                    time.sleep(1)
                consecutive_failures = 0
            else:
                # Interruptible brief pause
                for _ in range(60):
                    if _shutdown_requested:
                        break
                    time.sleep(1)
                continue

        if _shutdown_requested:
            break

        # Interruptible wait for next cycle
        logger.info(f"\n[NERVE] Next cycle in {CYCLE_INTERVAL_MINUTES} minutes...")
        wait_seconds = CYCLE_INTERVAL_MINUTES * 60
        for _ in range(wait_seconds):
            if _shutdown_requested:
                break
            time.sleep(1)

    # Clean shutdown
    logger.info(f"\n[NERVE] Daemon shutting down gracefully.")
    log_decision(
        actor="NERVE",
        action="daemon_stop",
        reasoning="Graceful shutdown requested" if _shutdown_requested else "Operator interrupted",
        outcome="Clean shutdown",
    )
    logger.info(f"[NERVE] Goodbye.")


# ── Status Display ─────────────────────────────────────────────

def show_status():
    """Display NERVE operational status."""
    state = _load_state()
    logger.info(f"\n{'='*60}")
    logger.info(f"  NERVE — Operational Status")
    logger.info(f"{'='*60}")
    logger.info(f"  Cycles run: {state.get('cycles_run', 0)}")
    logger.info(f"  First started: {state.get('started_at', 'never')}")
    logger.info(f"  Last cycle: {state.get('last_cycle', 'never')}")
    logger.info(f"  Last status: {state.get('last_status', 'unknown')}")

    # Recent decisions
    summary = decision_summary(hours=24)
    logger.info(f"\n── Last 24h ──")
    logger.info(f"  Decisions: {summary['total_decisions']}")
    logger.info(f"  By actor: {summary['by_actor']}")
    logger.info(f"  Pending escalations: {summary['escalations_pending']}")

    # Pending escalations
    esc = get_escalations(unacknowledged_only=True)
    if esc:
        logger.info(f"\n── Pending Escalations ──")
        for e in esc[-5:]:
            logger.info(f"  [{e['severity']}] {e['issue']} ({e['timestamp'][:16]})")


def show_decisions(limit: int = 20):
    """Show recent autonomous decisions."""
    decisions = get_decisions(limit=limit)
    logger.info(f"\n{'='*60}")
    logger.info(f"  NERVE — Recent Decisions (last {limit})")
    logger.info(f"{'='*60}")
    for d in decisions:
        ts = d['timestamp'][:16]
        logger.info(f"  [{ts}] {d['actor']}: {d['action']}")
        logger.info(f"           {d['outcome']}")


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NERVE — Autonomous BIT RAGE LABOUR daemon")
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
