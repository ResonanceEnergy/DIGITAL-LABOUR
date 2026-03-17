"""AUTOBIDDER — Autonomous bid engine for freelance platforms.

Polls for new projects, matches them against AUTOBID_RULES via the
matching engine, generates bids from BID_TEMPLATES, and submits or
queues them for human review based on confidence and spend thresholds.

Integrates with:
- campaign.freelancer_deploy.match_project() for scoring
- agents.automation_manager.runner for spend tracking + platform status
- automation.nerve for daemon integration
- automation.decision_log for audit trail

Usage:
    python -m automation.autobidder --scan          # One scan cycle
    python -m automation.autobidder --daemon         # Continuous polling
    python -m automation.autobidder --status         # Show bid stats
    python -m automation.autobidder --history        # Recent bid log
    python -m automation.autobidder --dry-run        # Match without bidding
"""

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from campaign.freelancer_deploy import match_project, BID_TEMPLATES, AGENCY_PROFILE
from automation.decision_log import log_decision

# ── Config ─────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS = 900      # 15 minutes between scans
MAX_DAILY_SPEND_USD = 50.0       # Hard cap across all platforms
MAX_SINGLE_BID_USD = 200.0       # Per-bid ceiling
MIN_CONFIDENCE = 0.7             # Minimum match confidence to bid
HUMAN_REVIEW_THRESHOLD = 500.0   # Projects above this $ need human OK
MAX_BIDS_PER_SCAN = 5            # Don't flood — max bids per cycle
AUTO_PAUSE_FAILURES = 5          # Pause platform after N consecutive fails

# ── Paths ──────────────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data" / "autobidder"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BID_LOG_FILE = DATA_DIR / "bid_log.jsonl"
STATE_FILE = DATA_DIR / "autobidder_state.json"
REVIEW_QUEUE_FILE = DATA_DIR / "human_review_queue.json"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATE MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "total_bids": 0,
        "total_spend": 0.0,
        "daily_spend": 0.0,
        "daily_bids": 0,
        "daily_reset_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "consecutive_failures": 0,
        "paused": False,
        "pause_reason": None,
        "seen_project_ids": [],
        "scans_run": 0,
        "last_scan": None,
    }


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _reset_daily_if_needed(state: dict) -> dict:
    """Reset daily counters at midnight UTC."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("daily_reset_date") != today:
        state["daily_spend"] = 0.0
        state["daily_bids"] = 0
        state["daily_reset_date"] = today
        state["consecutive_failures"] = 0
        if state.get("pause_reason") == "daily_spend_cap":
            state["paused"] = False
            state["pause_reason"] = None
    return state


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PROJECT POLLING (STUB — replace with real API)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def poll_freelancer_projects() -> list[dict]:
    """Poll for Freelancer.com projects from multiple sources.

    Priority order:
    1. Freelancer API (if FREELANCER_API_TOKEN is set in .env)
    2. Browser-scraped project log from freelancer_jobhunt.py

    Returns list of normalized project dicts with: id, title, description,
    budget_min, budget_max, currency, skills, platform, url
    """
    import os

    # Source 1: Freelancer API (when token is available)
    api_token = os.getenv("FREELANCER_API_TOKEN", "")
    if api_token:
        return _poll_freelancer_api(api_token)

    # Source 2: Browser-scraped project data from freelancer_jobhunt
    scraped_log = PROJECT_ROOT / "data" / "freelancer_jobs" / "project_log.jsonl"
    if scraped_log.exists():
        return _load_scraped_projects(scraped_log)

    return []


def _poll_freelancer_api(token: str) -> list[dict]:
    """Poll Freelancer.com API v0.1 for active projects.

    GET https://www.freelancer.com/api/projects/0.1/projects/active/
    Headers: freelancer-oauth-v1: <token>
    """
    import urllib.request
    import urllib.error

    url = (
        "https://www.freelancer.com/api/projects/0.1/projects/active/"
        "?compact=true&limit=20&sort_field=time_submitted"
        "&job_details=true&project_types[]=fixed&project_types[]=hourly"
    )
    req = urllib.request.Request(url, headers={
        "freelancer-oauth-v1": token,
        "Content-Type": "application/json",
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"    [WARN] Freelancer API poll failed: {e}")
        return []

    projects = []
    for p in data.get("result", {}).get("projects", []):
        projects.append({
            "id": str(p.get("id", "")),
            "title": p.get("title", ""),
            "description": p.get("preview_description", p.get("description", "")),
            "budget_min": p.get("budget", {}).get("minimum", 0),
            "budget_max": p.get("budget", {}).get("maximum", 0),
            "currency": p.get("currency", {}).get("code", "USD"),
            "skills": [j.get("name", "") for j in p.get("jobs", [])],
            "platform": "freelancer",
            "url": f"https://www.freelancer.com/projects/{p.get('seo_url', '')}",
        })
    return projects


def _load_scraped_projects(log_path: Path) -> list[dict]:
    """Load projects from the browser-scraped JSONL log."""
    projects = []
    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    # Only use projects from the last 24 hours
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    for line in lines:
        if not line.strip():
            continue
        try:
            p = json.loads(line)
        except json.JSONDecodeError:
            continue

        scraped_at = p.get("scraped_at", "")
        if scraped_at < cutoff:
            continue

        projects.append({
            "id": str(p.get("id", "")),
            "title": p.get("title", ""),
            "description": p.get("description", ""),
            "budget_min": 0,
            "budget_max": p.get("budget_max", 0),
            "currency": "USD",
            "skills": p.get("skills", []),
            "platform": "freelancer",
            "url": p.get("url", ""),
        })
    return projects


def poll_upwork_projects() -> list[dict]:
    """Poll Upwork projects from browser-scraped job log."""
    scraped_log = PROJECT_ROOT / "data" / "upwork_jobs" / "job_log.jsonl"
    if not scraped_log.exists():
        return []

    projects = []
    lines = scraped_log.read_text(encoding="utf-8").strip().split("\n")
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    for line in lines:
        if not line.strip():
            continue
        try:
            p = json.loads(line)
        except json.JSONDecodeError:
            continue

        found_at = p.get("found_at", "")
        if found_at < cutoff:
            continue

        projects.append({
            "id": p.get("url", "").split("/")[-1] or p.get("title", "")[:40],
            "title": p.get("title", ""),
            "description": p.get("description", ""),
            "budget_min": 0,
            "budget_max": _parse_budget_str(p.get("budget", "")),
            "currency": "USD",
            "skills": p.get("skills", []),
            "platform": "upwork",
            "url": p.get("url", ""),
        })
    return projects


def _parse_budget_str(budget_str: str) -> float:
    """Extract numeric budget from string like '$250 - $750'."""
    import re
    nums = re.findall(r'[\d,]+\.?\d*', str(budget_str).replace(',', ''))
    return float(nums[-1]) if nums else 0


def poll_pph_projects() -> list[dict]:
    """Poll PeoplePerHour projects from browser-scraped job log."""
    scraped_log = PROJECT_ROOT / "data" / "pph_jobs" / "project_log.jsonl"
    if not scraped_log.exists():
        return []
    return _load_generic_scraped(scraped_log, "pph")


def poll_guru_projects() -> list[dict]:
    """Poll Guru projects from browser-scraped job log."""
    scraped_log = PROJECT_ROOT / "data" / "guru_jobs" / "project_log.jsonl"
    if not scraped_log.exists():
        return []
    return _load_generic_scraped(scraped_log, "guru")


def _load_generic_scraped(log_path: Path, platform: str) -> list[dict]:
    """Load projects from any browser-scraped JSONL log."""
    projects = []
    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    for line in lines:
        if not line.strip():
            continue
        try:
            p = json.loads(line)
        except json.JSONDecodeError:
            continue

        scraped_at = p.get("scraped_at", p.get("found_at", ""))
        if scraped_at < cutoff:
            continue

        projects.append({
            "id": str(p.get("id", p.get("url", "").split("/")[-1] or p.get("title", "")[:40])),
            "title": p.get("title", ""),
            "description": p.get("description", ""),
            "budget_min": p.get("budget_min", 0),
            "budget_max": p.get("budget_max", 0),
            "currency": p.get("currency", "USD"),
            "skills": p.get("skills", []),
            "platform": platform,
            "url": p.get("url", ""),
        })
    return projects


def poll_platform_projects(platform: str) -> list[dict]:
    """Poll any supported platform for new projects.

    Dispatches to platform-specific poller. Each returns normalized
    project dicts: {id, title, description, budget_min, budget_max,
    currency, skills, platform, url}
    """
    pollers = {
        "freelancer": poll_freelancer_projects,
        "upwork": poll_upwork_projects,
        "pph": poll_pph_projects,
        "guru": poll_guru_projects,
    }
    poller = pollers.get(platform)
    if poller:
        return poller()
    return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BID GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_bid(project: dict, match: dict) -> dict:
    """Generate a bid from template + project details.

    Args:
        project: Normalized project dict from polling
        match: Result from match_project() with agent, confidence, bid_template

    Returns bid dict ready for submission or review queue.
    """
    template = match.get("bid_template", {})
    max_bid = min(
        match.get("max_bid_usd", MAX_SINGLE_BID_USD),
        project.get("budget_max", MAX_SINGLE_BID_USD),
        MAX_SINGLE_BID_USD,
    )

    # Scale bid based on project budget (aim for 70-90% of budget max)
    budget_max = project.get("budget_max", max_bid)
    bid_amount = min(round(budget_max * 0.8, 2), max_bid)
    bid_amount = max(bid_amount, 5.0)  # Floor of $5

    subject = template.get("subject", f"Re: {project.get('title', 'Your Project')}")
    body = template.get("body", "")

    # Personalize template with project title
    title = project.get("title", "your project")
    body = body.replace("{project_title}", title)
    body = body.replace("{client_name}", project.get("client_name", "there"))

    return {
        "project_id": project.get("id"),
        "project_title": project.get("title"),
        "platform": project.get("platform", "freelancer"),
        "agent": match["agent"],
        "confidence": match["confidence"],
        "bid_amount_usd": bid_amount,
        "subject": subject,
        "body": body,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }


def submit_bid(bid: dict) -> dict:
    """Submit a bid to the platform API.

    Routes to platform-specific submission based on bid['platform'].
    Falls back to queued status if API credentials are missing.

    Returns updated bid dict with submission result.
    """
    import os
    import urllib.request
    import urllib.error

    platform = bid.get("platform", "freelancer")
    now = datetime.now(timezone.utc).isoformat()

    if platform == "freelancer":
        token = os.getenv("FREELANCER_API_TOKEN", "")
        if not token:
            bid["status"] = "queued"
            bid["submitted_at"] = now
            bid["submission_note"] = "FREELANCER_API_TOKEN not set — bid queued for manual submission"
            return bid

        payload = json.dumps({
            "project_id": int(bid.get("project_id", 0)),
            "amount": bid.get("bid_amount_usd", 0),
            "period": 7,
            "milestone_percentage": 100,
            "description": bid.get("body", ""),
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://www.freelancer.com/api/projects/0.1/bids/",
            data=payload,
            method="POST",
            headers={
                "freelancer-oauth-v1": token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            if result.get("status") == "success":
                bid["status"] = "submitted"
                bid["submitted_at"] = now
                bid["api_response_id"] = result.get("result", {}).get("id", "")
                bid["submission_note"] = "Submitted via Freelancer API"
            else:
                bid["status"] = "api_error"
                bid["submitted_at"] = now
                bid["submission_note"] = f"API returned: {result.get('message', 'unknown error')}"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            bid["status"] = "api_error"
            bid["submitted_at"] = now
            bid["submission_note"] = f"API call failed: {e}"

    elif platform == "upwork":
        # Upwork API requires OAuth2 — queue for manual submission
        bid["status"] = "queued"
        bid["submitted_at"] = now
        bid["submission_note"] = "Upwork requires OAuth2 flow — bid queued for manual submission"

    else:
        # PPH, Guru, etc. — no API, queue for manual
        bid["status"] = "queued"
        bid["submitted_at"] = now
        bid["submission_note"] = f"No API integration for {platform} — bid queued for manual submission"

    return bid


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BID LOGGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _log_bid(bid: dict):
    """Append bid to JSONL log."""
    with open(BID_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(bid) + "\n")


def _add_to_review_queue(bid: dict):
    """Add high-value bid to human review queue."""
    queue = []
    if REVIEW_QUEUE_FILE.exists():
        queue = json.loads(REVIEW_QUEUE_FILE.read_text(encoding="utf-8"))
    bid["status"] = "needs_human_review"
    bid["review_reason"] = f"Project budget ${bid['bid_amount_usd']} exceeds review threshold ${HUMAN_REVIEW_THRESHOLD}"
    queue.append(bid)
    REVIEW_QUEUE_FILE.write_text(json.dumps(queue, indent=2), encoding="utf-8")


def get_bid_history(limit: int = 20) -> list[dict]:
    """Get recent bid history."""
    if not BID_LOG_FILE.exists():
        return []
    lines = BID_LOG_FILE.read_text(encoding="utf-8").strip().split("\n")
    bids = [json.loads(line) for line in lines if line.strip()]
    return bids[-limit:]


def get_review_queue() -> list[dict]:
    """Get pending human review items."""
    if not REVIEW_QUEUE_FILE.exists():
        return []
    return json.loads(REVIEW_QUEUE_FILE.read_text(encoding="utf-8"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCAN CYCLE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_scan(dry_run: bool = False) -> dict:
    """Execute one autobidder scan cycle.

    1. Check state (paused? daily cap?)
    2. Poll platforms for new projects
    3. Match against AUTOBID_RULES
    4. Generate bids for matches above threshold
    5. Submit or queue for human review
    6. Log everything

    Returns scan report dict.
    """
    state = _load_state()
    state = _reset_daily_if_needed(state)
    now = datetime.now(timezone.utc)

    report = {
        "scan_number": state["scans_run"] + 1,
        "timestamp": now.isoformat(),
        "projects_found": 0,
        "matches": 0,
        "bids_generated": 0,
        "bids_submitted": 0,
        "bids_queued_review": 0,
        "bids_skipped": 0,
        "dry_run": dry_run,
        "errors": [],
    }

    # Check if paused
    if state.get("paused"):
        report["status"] = "paused"
        report["pause_reason"] = state.get("pause_reason", "unknown")
        print(f"  [PAUSED] Autobidder paused: {state.get('pause_reason')}")
        return report

    # Check daily spend cap
    if state["daily_spend"] >= MAX_DAILY_SPEND_USD:
        state["paused"] = True
        state["pause_reason"] = "daily_spend_cap"
        _save_state(state)
        report["status"] = "daily_cap_reached"
        print(f"  [CAP] Daily spend ${state['daily_spend']:.2f} >= ${MAX_DAILY_SPEND_USD}")
        return report

    # Poll all active platforms
    platforms = ["freelancer", "upwork", "pph", "guru"]
    all_projects = []
    for platform in platforms:
        try:
            projects = poll_platform_projects(platform)
            for p in projects:
                p["platform"] = platform
            all_projects.extend(projects)
        except Exception as e:
            report["errors"].append(f"Poll {platform}: {e}")
            state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1

    # Filter out already-seen projects
    seen = set(state.get("seen_project_ids", []))
    new_projects = [p for p in all_projects if str(p.get("id")) not in seen]
    report["projects_found"] = len(new_projects)

    if not new_projects:
        print(f"  [SCAN] No new projects found across {len(platforms)} platform(s)")
        state["scans_run"] = state.get("scans_run", 0) + 1
        state["last_scan"] = now.isoformat()
        _save_state(state)
        report["status"] = "no_projects"
        return report

    print(f"  [SCAN] Found {len(new_projects)} new project(s)")

    # Match and bid
    bids_this_scan = 0
    for project in new_projects:
        if bids_this_scan >= MAX_BIDS_PER_SCAN:
            report["bids_skipped"] += 1
            continue

        # Mark as seen
        seen.add(str(project.get("id")))

        # Run matching engine
        matches = match_project(
            project.get("title", ""),
            project.get("description", ""),
        )

        if not matches:
            continue

        report["matches"] += 1
        best = matches[0]  # Highest confidence

        if best["confidence"] < MIN_CONFIDENCE:
            continue

        # Generate bid
        bid = generate_bid(project, best)
        report["bids_generated"] += 1

        if dry_run:
            print(f"  [DRY] {project['title'][:50]} -> {best['agent']} "
                  f"({best['confidence']:.0%}) ${bid['bid_amount_usd']}")
            _log_bid({**bid, "status": "dry_run"})
            continue

        # Check spend cap before submitting
        if state["daily_spend"] + bid["bid_amount_usd"] > MAX_DAILY_SPEND_USD:
            print(f"  [CAP] Would exceed daily cap — skipping")
            report["bids_skipped"] += 1
            continue

        # Route: human review or auto-submit
        if bid["bid_amount_usd"] > HUMAN_REVIEW_THRESHOLD:
            _add_to_review_queue(bid)
            report["bids_queued_review"] += 1
            print(f"  [REVIEW] {project['title'][:40]} -> ${bid['bid_amount_usd']} (needs human review)")
        else:
            bid = submit_bid(bid)
            _log_bid(bid)
            state["daily_spend"] += bid["bid_amount_usd"]
            state["daily_bids"] += 1
            state["total_bids"] += 1
            state["total_spend"] += bid["bid_amount_usd"]
            bids_this_scan += 1
            report["bids_submitted"] += 1
            print(f"  [BID] {project['title'][:40]} -> {best['agent']} "
                  f"({best['confidence']:.0%}) ${bid['bid_amount_usd']}")

            log_decision(
                actor="AUTOBIDDER",
                action="submit_bid",
                reasoning=f"Matched {best['agent']} at {best['confidence']:.0%} confidence",
                outcome=f"Bid ${bid['bid_amount_usd']} on '{project['title'][:50]}'",
            )

    # Check failure threshold
    if state.get("consecutive_failures", 0) >= AUTO_PAUSE_FAILURES:
        state["paused"] = True
        state["pause_reason"] = f"{AUTO_PAUSE_FAILURES} consecutive poll failures"

    # Update state
    state["seen_project_ids"] = list(seen)[-500:]  # Keep last 500
    state["scans_run"] = state.get("scans_run", 0) + 1
    state["last_scan"] = now.isoformat()
    _save_state(state)

    report["status"] = "completed"
    report["daily_spend"] = state["daily_spend"]
    report["daily_bids"] = state["daily_bids"]
    return report


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DAEMON MODE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_daemon():
    """Run autobidder in continuous polling mode."""
    print(f"\n{'='*70}")
    print(f"  AUTOBIDDER DAEMON — Polling every {POLL_INTERVAL_SECONDS}s")
    print(f"  Daily cap: ${MAX_DAILY_SPEND_USD} | Max per bid: ${MAX_SINGLE_BID_USD}")
    print(f"  Min confidence: {MIN_CONFIDENCE:.0%} | Human review: >${HUMAN_REVIEW_THRESHOLD}")
    print(f"{'='*70}\n")

    while True:
        try:
            report = run_scan()
            status = report.get("status", "unknown")
            print(f"  [{datetime.now(timezone.utc).strftime('%H:%M')}] "
                  f"Scan #{report['scan_number']}: {status} | "
                  f"Found: {report['projects_found']} | "
                  f"Bids: {report['bids_submitted']} | "
                  f"Daily: ${report.get('daily_spend', 0):.2f}/${MAX_DAILY_SPEND_USD}")

            if status == "paused":
                print(f"  Autobidder paused. Sleeping 5 minutes before retry...")
                time.sleep(300)
            else:
                time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n  [STOP] Autobidder stopped by user")
            break
        except Exception as e:
            print(f"  [ERROR] Scan failed: {e}")
            traceback.print_exc()
            time.sleep(60)  # Wait 1 min on error


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATUS & HISTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def print_status():
    """Print current autobidder status."""
    state = _load_state()
    state = _reset_daily_if_needed(state)
    review_queue = get_review_queue()

    print(f"\n{'='*70}")
    print(f"  AUTOBIDDER STATUS")
    print(f"{'='*70}")
    print(f"  Paused:           {'YES — ' + state.get('pause_reason', '') if state.get('paused') else 'No'}")
    print(f"  Scans Run:        {state.get('scans_run', 0)}")
    print(f"  Last Scan:        {state.get('last_scan', 'Never')}")
    print(f"  Total Bids:       {state.get('total_bids', 0)}")
    print(f"  Total Spend:      ${state.get('total_spend', 0):.2f}")
    print(f"  Today Bids:       {state.get('daily_bids', 0)}")
    print(f"  Today Spend:      ${state.get('daily_spend', 0):.2f} / ${MAX_DAILY_SPEND_USD}")
    print(f"  Seen Projects:    {len(state.get('seen_project_ids', []))}")
    print(f"  Failures:         {state.get('consecutive_failures', 0)} / {AUTO_PAUSE_FAILURES}")
    print(f"  Review Queue:     {len(review_queue)} items pending")
    print(f"{'='*70}\n")


def print_history(limit: int = 20):
    """Print recent bid history."""
    bids = get_bid_history(limit)
    if not bids:
        print("\n  No bids recorded yet.\n")
        return

    print(f"\n{'='*70}")
    print(f"  RECENT BIDS (last {len(bids)})")
    print(f"{'='*70}")
    for bid in bids:
        status_icon = {
            "queued": "[Q]",
            "submitted": "[S]",
            "dry_run": "[D]",
            "needs_human_review": "[R]",
        }.get(bid.get("status", ""), "[?]")

        print(f"  {status_icon} {bid.get('project_title', 'Unknown')[:45]}")
        print(f"       Agent: {bid.get('agent')} | "
              f"${bid.get('bid_amount_usd', 0):.2f} | "
              f"{bid.get('confidence', 0):.0%} | "
              f"{bid.get('generated_at', '')[:10]}")
    print(f"{'='*70}\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AUTOBIDDER — Autonomous freelance bidding engine")
    parser.add_argument("--scan", action="store_true",
                        help="Run one scan cycle")
    parser.add_argument("--daemon", action="store_true",
                        help="Run in continuous polling mode")
    parser.add_argument("--status", action="store_true",
                        help="Show autobidder status")
    parser.add_argument("--history", action="store_true",
                        help="Show recent bid history")
    parser.add_argument("--dry-run", action="store_true",
                        help="Match projects without submitting bids")
    parser.add_argument("--review", action="store_true",
                        help="Show human review queue")
    parser.add_argument("--limit", type=int, default=20,
                        help="Number of history items to show")

    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.history:
        print_history(args.limit)
    elif args.review:
        queue = get_review_queue()
        if queue:
            print(f"\n  {len(queue)} item(s) in review queue:")
            for item in queue:
                print(f"    - {item.get('project_title', '?')[:40]} "
                      f"| ${item.get('bid_amount_usd', 0):.2f} "
                      f"| {item.get('review_reason', '')}")
        else:
            print("\n  Review queue is empty.\n")
    elif args.daemon:
        run_daemon()
    elif args.scan or args.dry_run:
        report = run_scan(dry_run=args.dry_run)
        print(f"\n  Scan result: {report.get('status', 'unknown')}")
        print(f"  Projects: {report['projects_found']} | "
              f"Matches: {report['matches']} | "
              f"Bids: {report['bids_submitted']}")
    else:
        parser.print_help()
