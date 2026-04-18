"""JOB DISCOVERY ENGINE — Scan, match, draft proposals, notify for human approval.

Refactored from the original autobidder. Bids are NEVER auto-submitted.
All matched projects go to a notification queue and require explicit human
approval before any bid is placed on a platform.

Integrates with:
- campaign.freelancer_deploy.match_project() for scoring
- agents.automation_manager.runner for spend tracking + platform status
- automation.nerve for daemon integration
- automation.decision_log for audit trail
- Matrix monitor (HTTP POST to /matrix/notify) for notifications

Usage:
    python -m automation.autobidder --discover          # One discovery cycle
    python -m automation.autobidder --daemon            # Continuous discovery mode
    python -m automation.autobidder --status            # Show discovery stats
    python -m automation.autobidder --history           # Recent discovery log
    python -m automation.autobidder --dry-run           # Match without queuing
    python -m automation.autobidder --queue             # Show pending approval queue
    python -m automation.autobidder --approve <bid_id>  # Approve and submit a bid
    python -m automation.autobidder --reject <bid_id>   # Reject a queued bid
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import traceback
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ── Logging ───────────────────────────────────────────────────
logger = logging.getLogger("job_discovery")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(_handler)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from campaign.freelancer_deploy import match_project, BID_TEMPLATES, AGENCY_PROFILE
from automation.decision_log import log_decision

# Zoho CRM integration -- sync discoveries as Deals
try:
    from utils.zoho_client import sync_freelance_job
    ZOHO_AVAILABLE = True
except ImportError:
    ZOHO_AVAILABLE = False


# ── Config ────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS = 900       # 15 minutes between scans
MIN_CONFIDENCE = 0.7              # Minimum match confidence to surface
MAX_DISCOVERIES_PER_SCAN = 10     # Cap discoveries per cycle
AUTO_PAUSE_FAILURES = 5           # Pause platform after N consecutive fails
MATRIX_NOTIFY_URL = os.getenv("MATRIX_NOTIFY_URL", "")  # e.g. http://localhost:8090/matrix/notify

# ── Paths ─────────────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data" / "autobidder"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BID_LOG_FILE = DATA_DIR / "bid_log.jsonl"
STATE_FILE = DATA_DIR / "autobidder_state.json"
APPROVAL_QUEUE_FILE = DATA_DIR / "approval_queue.json"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATE MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_state() -> dict:
    """Load persisted engine state from disk."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "total_discoveries": 0,
        "total_approved": 0,
        "total_rejected": 0,
        "daily_discoveries": 0,
        "daily_reset_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "consecutive_failures": 0,
        "paused": False,
        "pause_reason": None,
        "seen_project_ids": [],
        "scans_run": 0,
        "last_scan": None,
    }


def _save_state(state: dict):
    """Atomically persist engine state to disk."""
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(STATE_FILE))


def _reset_daily_if_needed(state: dict) -> dict:
    """Reset daily counters at midnight UTC."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("daily_reset_date") != today:
        state["daily_discoveries"] = 0
        state["daily_reset_date"] = today
        state["consecutive_failures"] = 0
        if state.get("pause_reason") == "auto_pause_failures":
            state["paused"] = False
            state["pause_reason"] = None
    return state


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PROJECT POLLING (unchanged from original autobidder)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def poll_freelancer_projects() -> list[dict]:
    """Poll for Freelancer.com projects from multiple sources.

    Priority order:
    1. Freelancer API (if FREELANCER_API_TOKEN is set in .env)
    2. Browser-scraped project log from freelancer_jobhunt.py

    Returns list of normalized project dicts with: id, title, description,
    budget_min, budget_max, currency, skills, platform, url
    """
    api_token = os.getenv("FREELANCER_API_TOKEN", "")
    if api_token:
        return _poll_freelancer_api(api_token)

    scraped_log = PROJECT_ROOT / "data" / "freelancer_jobs" / "project_log.jsonl"
    if scraped_log.exists():
        return _load_scraped_projects(scraped_log)

    return []


def _poll_freelancer_api(token: str) -> list[dict]:
    """Poll Freelancer.com API v0.1 for active projects.

    GET https://www.freelancer.com/api/projects/0.1/projects/active/
    Headers: freelancer-oauth-v1: <token>
    """
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
        logger.warning("Freelancer API poll failed: %s", e)
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
#  BID ID GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _generate_bid_id(project: dict) -> str:
    """Generate a deterministic, short bid ID from project data.

    Format: BID-<8 hex chars> derived from platform + project ID + timestamp.
    """
    raw = f"{project.get('platform', '')}-{project.get('id', '')}-{datetime.now(timezone.utc).isoformat()}"
    return "BID-" + hashlib.sha256(raw.encode()).hexdigest()[:8].upper()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PROPOSAL DRAFTING (formerly "bid generation")
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def draft_proposal(project: dict, match: dict) -> dict:
    """Draft a proposal from template + project details.

    This generates the proposal text and suggested bid amount but does NOT
    submit anything. The proposal enters the approval queue for human review.

    Args:
        project: Normalized project dict from polling
        match: Result from match_project() with agent, confidence, bid_template

    Returns proposal dict ready for the approval queue.
    """
    template = match.get("bid_template", {})
    max_bid = min(
        match.get("max_bid_usd", 200.0),
        project.get("budget_max", 200.0) or 200.0,
        200.0,
    )

    # Scale bid based on project budget (aim for 70-90% of budget max)
    budget_max = project.get("budget_max", max_bid) or max_bid
    bid_amount = min(round(budget_max * 0.8, 2), max_bid)
    bid_amount = max(bid_amount, 5.0)  # Floor of $5

    subject = template.get("subject", f"Re: {project.get('title', 'Your Project')}")
    body = template.get("body", "")

    # Personalize template with project title
    title = project.get("title", "your project")
    body = body.replace("{project_title}", title)
    body = body.replace("{client_name}", project.get("client_name", "there"))

    bid_id = _generate_bid_id(project)

    return {
        "bid_id": bid_id,
        "project_id": project.get("id"),
        "project_title": project.get("title"),
        "project_url": project.get("url", ""),
        "platform": project.get("platform", "freelancer"),
        "agent": match["agent"],
        "confidence": match["confidence"],
        "bid_amount_usd": bid_amount,
        "budget_max": project.get("budget_max", 0),
        "skills": project.get("skills", []),
        "subject": subject,
        "body": body,
        "drafted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_approval",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  APPROVAL QUEUE MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_approval_queue() -> list[dict]:
    """Load the approval queue from disk."""
    if APPROVAL_QUEUE_FILE.exists():
        try:
            return json.loads(APPROVAL_QUEUE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load approval queue: %s", e)
            return []
    return []


def _save_approval_queue(queue: list[dict]):
    """Atomically persist the approval queue to disk."""
    tmp = APPROVAL_QUEUE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(APPROVAL_QUEUE_FILE))


def _add_to_approval_queue(proposal: dict):
    """Add a drafted proposal to the human approval queue."""
    queue = _load_approval_queue()
    proposal["status"] = "pending_approval"
    proposal["queued_at"] = datetime.now(timezone.utc).isoformat()
    queue.append(proposal)
    _save_approval_queue(queue)
    logger.info("Queued for approval: %s [%s] $%.2f",
                proposal.get("bid_id"), proposal.get("project_title", "")[:40],
                proposal.get("bid_amount_usd", 0))


def get_approval_queue(status_filter: Optional[str] = "pending_approval") -> list[dict]:
    """Get items from the approval queue, optionally filtered by status.

    Args:
        status_filter: Filter by status. None returns all items.
            Valid values: 'pending_approval', 'approved', 'rejected', 'submitted'
    """
    queue = _load_approval_queue()
    if status_filter is None:
        return queue
    return [item for item in queue if item.get("status") == status_filter]


def approve_bid(bid_id: str) -> dict:
    """Approve a queued bid and submit it to the platform.

    This is the ONLY path through which a bid can be submitted. It requires
    explicit human action (CLI flag, API call, or Matrix command).

    Args:
        bid_id: The BID-XXXXXXXX identifier from the approval queue.

    Returns:
        Result dict with status and details of the submission.
    """
    queue = _load_approval_queue()
    target = None
    target_idx = None

    for idx, item in enumerate(queue):
        if item.get("bid_id") == bid_id:
            target = item
            target_idx = idx
            break

    if target is None:
        logger.error("Bid %s not found in approval queue", bid_id)
        return {"status": "error", "message": f"Bid {bid_id} not found in approval queue"}

    if target.get("status") != "pending_approval":
        logger.warning("Bid %s has status '%s', not pending_approval", bid_id, target.get("status"))
        return {"status": "error", "message": f"Bid {bid_id} is '{target.get('status')}', not pending_approval"}

    # Submit the bid to the platform
    now = datetime.now(timezone.utc).isoformat()
    result = _submit_to_platform(target)

    # Update queue entry
    target["status"] = result["status"]
    target["approved_at"] = now
    target["submitted_at"] = now
    target["submission_note"] = result.get("note", "")
    if result.get("api_response_id"):
        target["api_response_id"] = result["api_response_id"]

    queue[target_idx] = target
    _save_approval_queue(queue)

    # Log the bid
    _log_bid(target)

    # Log decision
    log_decision(
        actor="JOB_DISCOVERY",
        action="approve_and_submit_bid",
        reasoning=f"Human approved bid {bid_id}",
        outcome=f"Bid ${target.get('bid_amount_usd', 0)} on '{target.get('project_title', '')[:50]}' -> {result['status']}",
    )

    # Sync to Zoho CRM
    if ZOHO_AVAILABLE:
        try:
            sync_freelance_job(
                platform=target.get("platform", "freelancer"),
                job_data={
                    "title": target.get("project_title", ""),
                    "id": target.get("project_id", ""),
                    "url": target.get("project_url", ""),
                    "skills": target.get("skills", []),
                    "budget": target.get("budget_max", 0),
                },
                stage="Bid Submitted",
            )
        except Exception:
            pass  # CRM sync is non-blocking

    logger.info("Approved and submitted bid %s: %s", bid_id, result["status"])
    return {"status": result["status"], "bid_id": bid_id, "note": result.get("note", "")}


def reject_bid(bid_id: str, reason: str = "") -> dict:
    """Reject a queued bid. It will NOT be submitted.

    Args:
        bid_id: The BID-XXXXXXXX identifier from the approval queue.
        reason: Optional human-provided reason for rejection.

    Returns:
        Result dict with status.
    """
    queue = _load_approval_queue()
    target = None
    target_idx = None

    for idx, item in enumerate(queue):
        if item.get("bid_id") == bid_id:
            target = item
            target_idx = idx
            break

    if target is None:
        logger.error("Bid %s not found in approval queue", bid_id)
        return {"status": "error", "message": f"Bid {bid_id} not found in approval queue"}

    if target.get("status") != "pending_approval":
        logger.warning("Bid %s has status '%s', not pending_approval", bid_id, target.get("status"))
        return {"status": "error", "message": f"Bid {bid_id} is '{target.get('status')}', not pending_approval"}

    now = datetime.now(timezone.utc).isoformat()
    target["status"] = "rejected"
    target["rejected_at"] = now
    target["rejection_reason"] = reason

    queue[target_idx] = target
    _save_approval_queue(queue)

    # Log the bid as rejected
    _log_bid(target)

    # Update state counters
    state = _load_state()
    state["total_rejected"] = state.get("total_rejected", 0) + 1
    _save_state(state)

    log_decision(
        actor="JOB_DISCOVERY",
        action="reject_bid",
        reasoning=f"Human rejected bid {bid_id}" + (f": {reason}" if reason else ""),
        outcome=f"Bid on '{target.get('project_title', '')[:50]}' rejected",
    )

    logger.info("Rejected bid %s%s", bid_id, f" ({reason})" if reason else "")
    return {"status": "rejected", "bid_id": bid_id}


def _submit_to_platform(proposal: dict) -> dict:
    """Submit an approved bid to the target platform API.

    Routes to platform-specific submission. Falls back to 'queued' status
    if API credentials are missing.

    Returns dict with status, note, and optionally api_response_id.
    """
    platform = proposal.get("platform", "freelancer")

    if platform == "freelancer":
        token = os.getenv("FREELANCER_API_TOKEN", "")
        if not token:
            return {
                "status": "queued_manual",
                "note": "FREELANCER_API_TOKEN not set -- approved bid queued for manual submission",
            }

        payload = json.dumps({
            "project_id": int(proposal.get("project_id", 0)),
            "amount": proposal.get("bid_amount_usd", 0),
            "period": 7,
            "milestone_percentage": 100,
            "description": proposal.get("body", ""),
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
                return {
                    "status": "submitted",
                    "note": "Submitted via Freelancer API",
                    "api_response_id": result.get("result", {}).get("id", ""),
                }
            else:
                return {
                    "status": "api_error",
                    "note": f"API returned: {result.get('message', 'unknown error')}",
                }
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            return {"status": "api_error", "note": f"API call failed: {e}"}

    elif platform == "upwork":
        return {
            "status": "queued_manual",
            "note": "Upwork requires OAuth2 flow -- approved bid queued for manual submission",
        }

    else:
        return {
            "status": "queued_manual",
            "note": f"No API integration for {platform} -- approved bid queued for manual submission",
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NOTIFICATION SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def notify_match(proposal: dict):
    """Send a matched job notification to the Matrix monitor and stdout.

    Attempts HTTP POST to MATRIX_NOTIFY_URL. If unavailable, falls back
    to structured stdout logging for capture by the orchestrator.

    Args:
        proposal: The drafted proposal dict from draft_proposal().
    """
    notification = {
        "type": "job_discovery",
        "bid_id": proposal.get("bid_id"),
        "project_title": proposal.get("project_title", ""),
        "project_url": proposal.get("project_url", ""),
        "platform": proposal.get("platform", ""),
        "agent": proposal.get("agent", ""),
        "confidence": proposal.get("confidence", 0),
        "bid_amount_usd": proposal.get("bid_amount_usd", 0),
        "budget_max": proposal.get("budget_max", 0),
        "skills": proposal.get("skills", []),
        "message": (
            f"New match: {proposal.get('project_title', '')[:60]} "
            f"| {proposal.get('platform')} | {proposal.get('agent')} "
            f"| {proposal.get('confidence', 0):.0%} confidence "
            f"| ${proposal.get('bid_amount_usd', 0):.2f} proposed"
        ),
        "actions": {
            "approve": f"python -m automation.autobidder --approve {proposal.get('bid_id')}",
            "reject": f"python -m automation.autobidder --reject {proposal.get('bid_id')}",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Always log to stdout for orchestrator capture
    logger.info("MATCH FOUND: [%s] %s on %s -> %s (%.0f%%) $%.2f -- approve with: --approve %s",
                proposal.get("bid_id"),
                proposal.get("project_title", "")[:50],
                proposal.get("platform"),
                proposal.get("agent"),
                proposal.get("confidence", 0) * 100,
                proposal.get("bid_amount_usd", 0),
                proposal.get("bid_id"))

    # Attempt Matrix notification via HTTP POST
    if MATRIX_NOTIFY_URL:
        try:
            payload = json.dumps(notification).encode("utf-8")
            req = urllib.request.Request(
                MATRIX_NOTIFY_URL,
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    logger.info("Matrix notification sent for %s", proposal.get("bid_id"))
                else:
                    logger.warning("Matrix notification returned status %d", resp.status)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            logger.warning("Matrix notification failed (non-fatal): %s", e)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BID LOGGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _log_bid(bid: dict):
    """Append bid/proposal to JSONL log."""
    with open(BID_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(bid) + "\n")


def get_bid_history(limit: int = 20) -> list[dict]:
    """Get recent bid/proposal history."""
    if not BID_LOG_FILE.exists():
        return []
    lines = BID_LOG_FILE.read_text(encoding="utf-8").strip().split("\n")
    bids = [json.loads(line) for line in lines if line.strip()]
    return bids[-limit:]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DISCOVERY SCAN CYCLE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_discovery(dry_run: bool = False) -> dict:
    """Execute one job discovery cycle.

    1. Check state (paused? failure cap?)
    2. Poll platforms for new projects
    3. Match against AUTOBID_RULES via scoring engine
    4. Draft proposals for matches above confidence threshold
    5. Queue ALL matches for human approval (never auto-submit)
    6. Send notifications via Matrix / stdout
    7. Log everything

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
        "proposals_drafted": 0,
        "proposals_queued": 0,
        "skipped": 0,
        "dry_run": dry_run,
        "errors": [],
    }

    # Check if paused
    if state.get("paused"):
        report["status"] = "paused"
        report["pause_reason"] = state.get("pause_reason", "unknown")
        logger.warning("Job discovery paused: %s", state.get("pause_reason"))
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
        logger.info("No new projects found across %d platform(s)", len(platforms))
        state["scans_run"] = state.get("scans_run", 0) + 1
        state["last_scan"] = now.isoformat()
        _save_state(state)
        report["status"] = "no_projects"
        return report

    logger.info("Found %d new project(s) across %d platform(s)", len(new_projects), len(platforms))

    # Match, draft, and queue
    discoveries_this_scan = 0
    for project in new_projects:
        if discoveries_this_scan >= MAX_DISCOVERIES_PER_SCAN:
            report["skipped"] += 1
            continue

        # Mark as seen regardless of match outcome
        seen.add(str(project.get("id")))

        # Run matching engine
        try:
            matches = match_project(
                project.get("title", ""),
                project.get("description", ""),
            )
        except Exception as e:
            report["errors"].append(f"Match error for {project.get('id')}: {e}")
            continue

        if not matches:
            continue

        report["matches"] += 1
        best = matches[0]  # Highest confidence

        if best["confidence"] < MIN_CONFIDENCE:
            continue

        # Draft proposal
        proposal = draft_proposal(project, best)
        report["proposals_drafted"] += 1

        if dry_run:
            logger.info("[DRY RUN] %s -> %s (%.0f%%) $%.2f",
                        project["title"][:50], best["agent"],
                        best["confidence"] * 100, proposal["bid_amount_usd"])
            _log_bid({**proposal, "status": "dry_run"})
            continue

        # Queue for human approval (ALL matches, no exceptions)
        _add_to_approval_queue(proposal)
        report["proposals_queued"] += 1
        discoveries_this_scan += 1

        # Notify via Matrix + stdout
        notify_match(proposal)

        # Log decision
        log_decision(
            actor="JOB_DISCOVERY",
            action="discover_and_queue",
            reasoning=f"Matched {best['agent']} at {best['confidence']:.0%} confidence",
            outcome=f"Queued proposal {proposal['bid_id']} for '{project['title'][:50]}' -- awaiting human approval",
        )

        # Sync discovery to Zoho CRM (stage: Discovery)
        if ZOHO_AVAILABLE:
            try:
                sync_freelance_job(
                    platform=project.get("platform", "freelancer"),
                    job_data={
                        "title": project.get("title", ""),
                        "id": project.get("id", ""),
                        "url": project.get("url", ""),
                        "skills": project.get("skills", []),
                        "budget": project.get("budget_max", 0),
                        "client_name": project.get("client_name", ""),
                    },
                    stage="Discovery",
                )
            except Exception:
                pass  # CRM sync is non-blocking

    # Check failure threshold
    if state.get("consecutive_failures", 0) >= AUTO_PAUSE_FAILURES:
        state["paused"] = True
        state["pause_reason"] = "auto_pause_failures"

    # Update state
    state["seen_project_ids"] = list(seen)[-500:]  # Keep last 500
    state["scans_run"] = state.get("scans_run", 0) + 1
    state["last_scan"] = now.isoformat()
    state["total_discoveries"] = state.get("total_discoveries", 0) + report["proposals_queued"]
    state["daily_discoveries"] = state.get("daily_discoveries", 0) + report["proposals_queued"]
    _save_state(state)

    report["status"] = "completed"
    report["daily_discoveries"] = state["daily_discoveries"]
    return report


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DAEMON / DISCOVERY MODE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_daemon():
    """Run job discovery in continuous polling mode.

    Scans platforms, matches projects, drafts proposals, sends notifications,
    and waits for human approval. Bids are NEVER auto-submitted.
    """
    logger.info("=" * 70)
    logger.info("  JOB DISCOVERY DAEMON -- Polling every %ds", POLL_INTERVAL_SECONDS)
    logger.info("  Min confidence: %.0f%% | Max per scan: %d",
                MIN_CONFIDENCE * 100, MAX_DISCOVERIES_PER_SCAN)
    logger.info("  Matrix notify: %s", MATRIX_NOTIFY_URL or "(stdout only)")
    logger.info("  Bids require human approval -- NEVER auto-submitted")
    logger.info("=" * 70)

    while True:
        try:
            report = run_discovery()
            status = report.get("status", "unknown")
            logger.info(
                "Scan #%d: %s | Found: %d | Matched: %d | Queued: %d | Daily: %d",
                report["scan_number"], status,
                report["projects_found"], report["matches"],
                report["proposals_queued"],
                report.get("daily_discoveries", 0),
            )

            if status == "paused":
                logger.warning("Discovery paused. Sleeping 5 minutes before retry...")
                time.sleep(300)
            else:
                time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("Job discovery stopped by user")
            break
        except Exception as e:
            logger.error("Scan failed: %s", e)
            traceback.print_exc()
            time.sleep(60)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATUS & HISTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def print_status():
    """Print current job discovery engine status."""
    state = _load_state()
    state = _reset_daily_if_needed(state)
    pending = get_approval_queue("pending_approval")

    print(f"\n{'='*70}")
    print(f"  JOB DISCOVERY ENGINE STATUS")
    print(f"{'='*70}")
    print(f"  Paused:            {'YES -- ' + state.get('pause_reason', '') if state.get('paused') else 'No'}")
    print(f"  Scans Run:         {state.get('scans_run', 0)}")
    print(f"  Last Scan:         {state.get('last_scan', 'Never')}")
    print(f"  Total Discoveries: {state.get('total_discoveries', 0)}")
    print(f"  Total Approved:    {state.get('total_approved', 0)}")
    print(f"  Total Rejected:    {state.get('total_rejected', 0)}")
    print(f"  Today Discoveries: {state.get('daily_discoveries', 0)}")
    print(f"  Seen Projects:     {len(state.get('seen_project_ids', []))}")
    print(f"  Failures:          {state.get('consecutive_failures', 0)} / {AUTO_PAUSE_FAILURES}")
    print(f"  Pending Approval:  {len(pending)} item(s)")
    print(f"  Bids Auto-Submit:  DISABLED (human approval required)")
    print(f"{'='*70}\n")


def print_history(limit: int = 20):
    """Print recent proposal/bid history."""
    bids = get_bid_history(limit)
    if not bids:
        print("\n  No proposals recorded yet.\n")
        return

    print(f"\n{'='*70}")
    print(f"  RECENT PROPOSALS (last {len(bids)})")
    print(f"{'='*70}")
    for bid in bids:
        status_icon = {
            "pending_approval": "[P]",
            "approved": "[A]",
            "submitted": "[S]",
            "queued_manual": "[M]",
            "rejected": "[X]",
            "dry_run": "[D]",
            "api_error": "[E]",
        }.get(bid.get("status", ""), "[?]")

        print(f"  {status_icon} {bid.get('bid_id', '?'):12s} {bid.get('project_title', 'Unknown')[:40]}")
        print(f"       Agent: {bid.get('agent')} | "
              f"${bid.get('bid_amount_usd', 0):.2f} | "
              f"{bid.get('confidence', 0):.0%} | "
              f"{bid.get('drafted_at', bid.get('generated_at', ''))[:10]}")
    print(f"{'='*70}\n")


def print_approval_queue():
    """Print the pending approval queue."""
    pending = get_approval_queue("pending_approval")
    if not pending:
        print("\n  Approval queue is empty. No bids awaiting human review.\n")
        return

    print(f"\n{'='*70}")
    print(f"  PENDING APPROVAL QUEUE ({len(pending)} item(s))")
    print(f"{'='*70}")
    for item in pending:
        print(f"  [{item.get('bid_id', '?')}] {item.get('project_title', '?')[:45]}")
        print(f"       Platform: {item.get('platform')} | "
              f"Agent: {item.get('agent')} | "
              f"Confidence: {item.get('confidence', 0):.0%} | "
              f"${item.get('bid_amount_usd', 0):.2f}")
        print(f"       URL: {item.get('project_url', 'N/A')}")
        print(f"       Approve: python -m automation.autobidder --approve {item.get('bid_id')}")
        print()
    print(f"{'='*70}\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="JOB DISCOVERY ENGINE -- Scan, match, draft, notify, await human approval")
    parser.add_argument("--discover", action="store_true",
                        help="Run one discovery cycle")
    parser.add_argument("--scan", action="store_true",
                        help="Alias for --discover (backward compat)")
    parser.add_argument("--daemon", action="store_true",
                        help="Run in continuous discovery mode")
    parser.add_argument("--status", action="store_true",
                        help="Show engine status")
    parser.add_argument("--history", action="store_true",
                        help="Show recent proposal history")
    parser.add_argument("--dry-run", action="store_true",
                        help="Match projects without queuing")
    parser.add_argument("--queue", action="store_true",
                        help="Show pending approval queue")
    parser.add_argument("--approve", type=str, metavar="BID_ID",
                        help="Approve and submit a bid by ID (e.g. BID-A1B2C3D4)")
    parser.add_argument("--reject", type=str, metavar="BID_ID",
                        help="Reject a queued bid by ID")
    parser.add_argument("--reject-reason", type=str, default="",
                        help="Reason for rejection (used with --reject)")
    parser.add_argument("--limit", type=int, default=20,
                        help="Number of history items to show")

    args = parser.parse_args()

    if args.approve:
        result = approve_bid(args.approve)
        print(f"\n  Approve result: {result.get('status')}")
        if result.get("note"):
            print(f"  Note: {result['note']}")
        print()

    elif args.reject:
        result = reject_bid(args.reject, reason=args.reject_reason)
        print(f"\n  Reject result: {result.get('status')}")
        print()

    elif args.status:
        print_status()

    elif args.history:
        print_history(args.limit)

    elif args.queue:
        print_approval_queue()

    elif args.daemon:
        run_daemon()

    elif args.discover or args.scan or args.dry_run:
        report = run_discovery(dry_run=args.dry_run)
        print(f"\n  Discovery result: {report.get('status', 'unknown')}")
        print(f"  Projects: {report['projects_found']} | "
              f"Matches: {report['matches']} | "
              f"Queued: {report['proposals_queued']}")
        if report.get("errors"):
            print(f"  Errors: {len(report['errors'])}")
        print()

    else:
        parser.print_help()
