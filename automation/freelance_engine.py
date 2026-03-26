"""Freelance Engine — Unified automation across Fiverr, Upwork, and Freelancer.

Single entry point that orchestrates:
  1. Job hunting across all platforms (aggregated + scored)
  2. Autobidding with safety caps and QA
  3. Order fulfillment with agent dispatch
  4. Revenue tracking and status reporting

This is the module NERVE calls for freelance automation.

Usage:
    python -m automation.freelance_engine                # Full cycle (all platforms)
    python -m automation.freelance_engine --hunt          # Job hunt only
    python -m automation.freelance_engine --bid           # Autobid only
    python -m automation.freelance_engine --deliver       # Check + fulfill orders
    python -m automation.freelance_engine --status        # Dashboard
    python -m automation.freelance_engine --platform upwork  # Single platform
"""

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from automation.decision_log import log_decision

STATE_FILE = PROJECT_ROOT / "data" / "freelance_engine_state.json"
LOG_DIR = PROJECT_ROOT / "data" / "freelance_engine_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "cycles_run": 0,
        "last_cycle": None,
        "total_jobs_found": 0,
        "total_bids_placed": 0,
        "total_deliveries": 0,
        "platform_stats": {},
    }


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Phase 1: Job Aggregation ────────────────────────────────────────────────

def hunt_jobs(platform_filter: str = "", max_age_hours: int = 48) -> dict:
    """Aggregate and rank jobs from all platforms."""
    print(f"\n{'='*60}")
    print(f"  FREELANCE ENGINE — Job Hunt")
    print(f"{'='*60}")

    result = {"jobs_found": 0, "unbid": 0, "top_agents": [], "errors": []}

    try:
        from automation.job_aggregator import aggregate
        feed = aggregate(max_age_hours=max_age_hours, platform_filter=platform_filter)
        unbid = [j for j in feed if not j.get("already_bid")]
        result["jobs_found"] = len(feed)
        result["unbid"] = len(unbid)

        # Top agent demand
        agent_counts: dict[str, int] = {}
        for j in feed:
            a = j.get("best_agent", "unknown")
            agent_counts[a] = agent_counts.get(a, 0) + 1
        result["top_agents"] = sorted(agent_counts.items(), key=lambda x: -x[1])[:5]

        # Platform breakdown
        plat_counts: dict[str, int] = {}
        for j in feed:
            p = j.get("platform", "unknown")
            plat_counts[p] = plat_counts.get(p, 0) + 1
        result["by_platform"] = plat_counts

        print(f"  Jobs found: {len(feed)} | Unbid: {len(unbid)}")
        for plat, count in plat_counts.items():
            print(f"    {plat}: {count}")

    except Exception as e:
        result["errors"].append(str(e))
        print(f"  [ERROR] Job aggregation: {e}")

    return result


# ── Phase 2: Autobidding ────────────────────────────────────────────────────

def run_autobid(dry_run: bool = False) -> dict:
    """Run one autobidder scan cycle."""
    print(f"\n{'='*60}")
    print(f"  FREELANCE ENGINE — Autobidder {'(DRY RUN)' if dry_run else ''}")
    print(f"{'='*60}")

    result = {"bids_generated": 0, "bids_submitted": 0, "bids_queued": 0, "errors": []}

    try:
        from automation.autobidder import run_scan
        scan_result = run_scan(dry_run=dry_run)
        if isinstance(scan_result, dict):
            result["bids_generated"] = scan_result.get("bids_generated", 0)
            result["bids_submitted"] = scan_result.get("bids_submitted", 0)
            result["bids_queued"] = scan_result.get("bids_queued_review", 0)
            print(f"  Generated: {result['bids_generated']} | Submitted: {result['bids_submitted']} | Queued: {result['bids_queued']}")
        else:
            print(f"  Scan returned unexpected result type")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"  [ERROR] Autobidder: {e}")

    return result


# ── Phase 3: Platform-specific job hunts ─────────────────────────────────────

def hunt_freelancer() -> dict:
    """Run Freelancer.com browser-based job hunt."""
    result = {"platform": "freelancer", "jobs_found": 0, "bids_placed": 0, "errors": []}
    try:
        from automation.freelancer_jobhunt import full_run
        run_result = full_run()
        if isinstance(run_result, dict):
            result["jobs_found"] = run_result.get("jobs_found", 0)
            result["bids_placed"] = run_result.get("bids_placed", 0)
        print(f"  Freelancer: {result['jobs_found']} jobs, {result['bids_placed']} bids")
    except ImportError:
        # full_run may not exist — fall back to scan functions
        result["errors"].append("freelancer_jobhunt.full_run not available")
        print(f"  Freelancer job hunt: function not available (use CLI)")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"  [ERROR] Freelancer hunt: {e}")
    return result


def hunt_upwork() -> dict:
    """Run Upwork browser-based job hunt."""
    result = {"platform": "upwork", "jobs_found": 0, "proposals_queued": 0, "errors": []}
    try:
        from automation.upwork_jobhunt import full_run
        run_result = full_run()
        if isinstance(run_result, dict):
            result["jobs_found"] = run_result.get("jobs_found", 0)
            result["proposals_queued"] = run_result.get("proposals_queued", 0)
        print(f"  Upwork: {result['jobs_found']} jobs, {result['proposals_queued']} proposals queued")
    except ImportError:
        result["errors"].append("upwork_jobhunt.full_run not available")
        print(f"  Upwork job hunt: function not available (use CLI)")
    except Exception as e:
        result["errors"].append(str(e))
        print(f"  [ERROR] Upwork hunt: {e}")
    return result


# ── Phase 4: Order fulfillment ───────────────────────────────────────────────

def check_and_deliver() -> dict:
    """Check all platforms for pending orders and auto-deliver."""
    print(f"\n{'='*60}")
    print(f"  FREELANCE ENGINE — Order Fulfillment")
    print(f"{'='*60}")

    result = {
        "fiverr": {"orders_found": 0, "delivered": 0, "errors": []},
        "freelancer": {"active_projects": 0, "errors": []},
        "upwork": {"active_contracts": 0, "errors": []},
    }

    # Fiverr — browser-based order check + agent dispatch
    try:
        from automation.fiverr_orders import show_status
        show_status()
        # Note: Full auto-dispatch requires browser session.
        # Use `python -m automation.fiverr_orders --action auto` for live dispatch.
        print("  Fiverr: Status checked. Run --action auto for live dispatch.")
    except Exception as e:
        result["fiverr"]["errors"].append(str(e))
        print(f"  [ERROR] Fiverr order check: {e}")

    # Freelancer — check active project status
    try:
        from automation.freelancer_client import show_status as fl_status
        fl_status()
        print("  Freelancer: Status checked.")
    except (ImportError, AttributeError):
        print("  Freelancer: No status function available")
    except Exception as e:
        result["freelancer"]["errors"].append(str(e))

    # Upwork — check message/contract status
    try:
        from automation.upwork_delivery import show_status as up_status
        up_status()
        print("  Upwork: Delivery status checked.")
    except (ImportError, AttributeError):
        print("  Upwork: No status function available")
    except Exception as e:
        result["upwork"]["errors"].append(str(e))

    return result


# ── Phase 5: Revenue tracking ───────────────────────────────────────────────

def track_revenue() -> dict:
    """Check revenue from all freelance sources."""
    print(f"\n{'='*60}")
    print(f"  FREELANCE ENGINE — Revenue")
    print(f"{'='*60}")

    revenue = {"stripe": 0, "platforms": {}, "total": 0, "errors": []}

    try:
        from automation.revenue_daemon import check_stripe_revenue
        stripe = check_stripe_revenue()
        revenue["stripe"] = stripe.get("total", 0)
        print(f"  Stripe: ${revenue['stripe']:.2f}")
    except Exception as e:
        revenue["errors"].append(f"stripe: {e}")

    # Check platform earnings files
    data_dir = PROJECT_ROOT / "data"
    for platform in ["freelancer", "upwork", "fiverr"]:
        earnings_file = data_dir / f"{platform}_jobs" / "earnings.json"
        if earnings_file.exists():
            try:
                data = json.loads(earnings_file.read_text(encoding="utf-8"))
                total = sum(e.get("amount", 0) for e in data) if isinstance(data, list) else data.get("total", 0)
                revenue["platforms"][platform] = round(total, 2)
                revenue["total"] += total
                print(f"  {platform}: ${total:.2f}")
            except Exception as e:
                revenue["errors"].append(f"{platform}: {e}")

    revenue["total"] += revenue["stripe"]
    print(f"  TOTAL: ${revenue['total']:.2f}")
    return revenue


# ── Full Cycle ──────────────────────────────────────────────────────────────

def full_cycle(platform_filter: str = "", dry_run: bool = False) -> dict:
    """Run complete freelance automation cycle: hunt → bid → deliver → revenue.

    This is the main entry point for NERVE integration.
    """
    cycle_start = time.time()
    now = datetime.now(timezone.utc)
    state = _load_state()

    report = {
        "cycle_number": state["cycles_run"] + 1,
        "started": now.isoformat(),
        "platform_filter": platform_filter or "all",
        "dry_run": dry_run,
        "phases": {},
    }

    print(f"\n{'#'*60}")
    print(f"  FREELANCE ENGINE — Full Cycle #{report['cycle_number']}")
    print(f"  Platforms: {platform_filter or 'ALL'} | Dry run: {dry_run}")
    print(f"{'#'*60}")

    # Phase 1: Hunt
    report["phases"]["hunt"] = hunt_jobs(platform_filter=platform_filter)

    # Phase 2: Autobid
    report["phases"]["autobid"] = run_autobid(dry_run=dry_run)

    # Phase 3: Order fulfillment
    report["phases"]["delivery"] = check_and_deliver()

    # Phase 4: Revenue
    report["phases"]["revenue"] = track_revenue()

    # Finalize
    elapsed = time.time() - cycle_start
    report["elapsed_s"] = round(elapsed, 1)
    report["finished"] = datetime.now(timezone.utc).isoformat()

    # Update state
    state["cycles_run"] += 1
    state["last_cycle"] = now.isoformat()
    hunt = report["phases"].get("hunt", {})
    state["total_jobs_found"] += hunt.get("jobs_found", 0)
    bid = report["phases"].get("autobid", {})
    state["total_bids_placed"] += bid.get("bids_submitted", 0)
    _save_state(state)

    # Log decision
    log_decision(
        actor="FREELANCE_ENGINE",
        action="full_cycle",
        reasoning=f"Cycle #{report['cycle_number']} — automated freelance pipeline",
        outcome=(
            f"Jobs: {hunt.get('jobs_found', 0)} | "
            f"Bids: {bid.get('bids_submitted', 0)} | "
            f"Elapsed: {elapsed:.1f}s"
        ),
    )

    # Save cycle log
    log_file = LOG_DIR / f"cycle_{report['cycle_number']:04d}.json"
    log_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'#'*60}")
    print(f"  CYCLE #{report['cycle_number']} COMPLETE — {elapsed:.1f}s")
    print(f"{'#'*60}")

    return report


# ── Status Dashboard ─────────────────────────────────────────────────────────

def status_dashboard() -> dict:
    """Show comprehensive freelance automation status."""
    state = _load_state()

    print(f"\n{'='*60}")
    print(f"  FREELANCE ENGINE — Status Dashboard")
    print(f"{'='*60}")
    print(f"  Cycles run:      {state['cycles_run']}")
    print(f"  Last cycle:      {state.get('last_cycle', 'never')}")
    print(f"  Total jobs found:{state['total_jobs_found']}")
    print(f"  Total bids:      {state['total_bids_placed']}")
    print(f"  Total deliveries:{state['total_deliveries']}")

    # Autobidder state
    try:
        from automation.autobidder import _load_state as load_bid_state
        bid_state = load_bid_state()
        print(f"\n  Autobidder:")
        print(f"    Total bids:    {bid_state.get('total_bids', 0)}")
        print(f"    Daily spend:   ${bid_state.get('daily_spend', 0):.2f}")
        print(f"    Paused:        {bid_state.get('paused', False)}")
        print(f"    Last scan:     {bid_state.get('last_scan', 'never')}")
    except Exception:
        pass

    # Per-platform status
    print(f"\n  Platform Status:")
    for platform in ["freelancer", "upwork", "fiverr"]:
        try:
            bid_log = PROJECT_ROOT / "data" / f"{platform}_jobs" / "bids_submitted.json"
            if bid_log.exists():
                data = json.loads(bid_log.read_text(encoding="utf-8"))
                count = len(data) if isinstance(data, list) else 0
                print(f"    {platform:12s} bids: {count}")
        except Exception:
            pass

    # Aggregated feed
    try:
        feed_file = PROJECT_ROOT / "data" / "aggregated_feed" / "ranked_feed.json"
        if feed_file.exists():
            feed = json.loads(feed_file.read_text(encoding="utf-8"))
            print(f"\n  Job Feed: {len(feed)} opportunities in ranked feed")
    except Exception:
        pass

    # Review queue
    try:
        review_file = PROJECT_ROOT / "data" / "autobidder" / "human_review_queue.json"
        if review_file.exists():
            queue = json.loads(review_file.read_text(encoding="utf-8"))
            if queue:
                print(f"\n  [!] {len(queue)} bids need human review")
    except Exception:
        pass

    return state


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DIGITAL LABOUR — Freelance Engine")
    parser.add_argument("--hunt", action="store_true", help="Job hunt only")
    parser.add_argument("--bid", action="store_true", help="Autobid only")
    parser.add_argument("--deliver", action="store_true", help="Check + fulfill orders")
    parser.add_argument("--revenue", action="store_true", help="Revenue tracking")
    parser.add_argument("--status", action="store_true", help="Status dashboard")
    parser.add_argument("--platform", type=str, default="", help="Filter to single platform")
    parser.add_argument("--dry-run", action="store_true", help="Don't submit real bids")
    args = parser.parse_args()

    if args.status:
        status_dashboard()
    elif args.hunt:
        hunt_jobs(platform_filter=args.platform)
    elif args.bid:
        run_autobid(dry_run=args.dry_run)
    elif args.deliver:
        check_and_deliver()
    elif args.revenue:
        track_revenue()
    else:
        full_cycle(platform_filter=args.platform, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
