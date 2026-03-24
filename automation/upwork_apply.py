"""Upwork Auto-Apply — Automated job application engine for Upwork.

Reads scraped job listings from data/upwork_jobs/job_log.jsonl,
matches them against our service capabilities, generates proposals
using LLM + templates, and queues them for submission.

Usage:
    python -m automation.upwork_apply --scan           # Scan + match new jobs
    python -m automation.upwork_apply --apply 10        # Generate proposals for top 10 matches
    python -m automation.upwork_apply --status          # Show application stats
    python -m automation.upwork_apply --preview          # Preview next proposal
    python -m automation.upwork_apply --daemon          # Poll every 2 hrs
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from automation.decision_log import log_decision

JOB_LOG = PROJECT_ROOT / "data" / "upwork_jobs" / "job_log.jsonl"
STATE_FILE = PROJECT_ROOT / "data" / "upwork_apply_state.json"
PROPOSALS_DIR = PROJECT_ROOT / "data" / "upwork_proposals"
PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)

# Application limits
MAX_DAILY_APPLIES = 15          # Upwork daily connect budget
MAX_PROPOSAL_LENGTH = 2000      # Characters
MIN_MATCH_SCORE = 0.6           # Below this, skip the job
POLL_INTERVAL = 7200            # 2 hours

# ── Our Services (for matching) ────────────────────────────────

SERVICE_CAPABILITIES = {
    "lead_gen": {
        "keywords": ["lead generation", "prospecting", "cold email", "outreach",
                     "lead research", "contact list", "lead scraping", "b2b leads"],
        "title": "AI Lead Generation & Research",
        "hourly": "$25-45",
    },
    "data_entry": {
        "keywords": ["data entry", "data processing", "spreadsheet", "excel",
                     "csv", "database entry", "data cleaning", "data extraction"],
        "title": "AI Data Entry & Processing",
        "hourly": "$15-30",
    },
    "content": {
        "keywords": ["content writing", "blog", "article", "copywriting",
                     "social media content", "content repurpose", "seo content",
                     "content creation", "ghostwriting"],
        "title": "AI Content Creation & Repurposing",
        "hourly": "$20-40",
    },
    "support": {
        "keywords": ["customer support", "ticket", "helpdesk", "customer service",
                     "support agent", "chat support", "email support"],
        "title": "AI Customer Support & Ticket Triage",
        "hourly": "$20-35",
    },
    "doc_extract": {
        "keywords": ["document", "extraction", "invoice", "pdf", "ocr",
                     "contract review", "data extraction from pdf"],
        "title": "AI Document & Invoice Data Extraction",
        "hourly": "$20-35",
    },
    "web_scraping": {
        "keywords": ["web scraping", "scraper", "crawl", "selenium",
                     "data scraping", "web data", "automation"],
        "title": "AI Web Scraping & Data Collection",
        "hourly": "$25-45",
    },
    "email_marketing": {
        "keywords": ["email marketing", "email campaign", "drip campaign",
                     "newsletter", "mailchimp", "email automation"],
        "title": "AI Email Marketing & Campaign Automation",
        "hourly": "$20-40",
    },
    "market_research": {
        "keywords": ["market research", "competitor analysis", "industry report",
                     "market analysis", "competitive intelligence"],
        "title": "AI Market Research & Competitive Analysis",
        "hourly": "$30-50",
    },
}


# ── State Management ───────────────────────────────────────────

def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "total_applies": 0,
        "daily_applies": 0,
        "daily_reset_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "seen_job_ids": [],
        "scans_run": 0,
        "last_scan": None,
        "proposals_generated": 0,
    }


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _reset_daily(state: dict) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("daily_reset_date") != today:
        state["daily_applies"] = 0
        state["daily_reset_date"] = today
    return state


# ── Job Loading ────────────────────────────────────────────────

def load_new_jobs(state: dict) -> list[dict]:
    """Load jobs from job_log.jsonl that haven't been seen yet."""
    if not JOB_LOG.exists():
        return []

    seen = set(state.get("seen_job_ids", []))
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    jobs = []

    for line in JOB_LOG.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            job = json.loads(line)
        except json.JSONDecodeError:
            continue

        job_id = job.get("url", job.get("title", ""))[:80]
        if job_id in seen:
            continue
        if job.get("found_at", "") < cutoff:
            continue
        job["_id"] = job_id
        jobs.append(job)

    return jobs


# ── Matching Engine ────────────────────────────────────────────

def match_job(job: dict) -> dict:
    """Score a job against our service capabilities.

    Returns: {service, score, reasons}
    """
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    skills = [s.lower() for s in job.get("skills", [])]
    combined = f"{title} {description} {' '.join(skills)}"

    best_service = None
    best_score = 0.0
    best_reasons = []

    for service_key, svc in SERVICE_CAPABILITIES.items():
        score = 0.0
        reasons = []

        for kw in svc["keywords"]:
            if kw in combined:
                score += 0.15
                reasons.append(f"keyword: {kw}")

        # Title match is stronger
        for kw in svc["keywords"]:
            if kw in title:
                score += 0.10
                reasons.append(f"title match: {kw}")

        # Skill tag match
        for kw in svc["keywords"]:
            for skill in skills:
                if kw in skill or skill in kw:
                    score += 0.10
                    reasons.append(f"skill: {skill}")

        score = min(score, 1.0)  # Cap at 1.0

        if score > best_score:
            best_score = score
            best_service = service_key
            best_reasons = reasons

    return {
        "service": best_service,
        "score": round(best_score, 2),
        "reasons": best_reasons[:5],
    }


# ── Proposal Generation ───────────────────────────────────────

def generate_proposal(job: dict, match: dict) -> dict:
    """Generate a proposal for a matched job."""
    service = SERVICE_CAPABILITIES.get(match["service"], {})
    job_title = job.get("title", "the project")
    budget = job.get("budget", "")

    proposal_text = (
        f"Hi,\n\n"
        f"I noticed your posting for \"{job_title}\" and it's exactly what our "
        f"team specializes in.\n\n"
        f"We're BIT RAGE SYSTEMS — a 24-agent AI automation system built for "
        f"exactly this type of work. Our {service.get('title', 'AI automation')} "
        f"service handles this end-to-end with:\n\n"
        f"• AI-powered processing for speed and accuracy\n"
        f"• Quality assurance checks on every deliverable\n"
        f"• Fast turnaround (typically 24-48 hours)\n"
        f"• Unlimited revisions until you're satisfied\n\n"
        f"We've built specialized AI agents that can handle high volumes "
        f"while maintaining quality. Happy to share samples or do a quick "
        f"test task to prove our capability.\n\n"
        f"Let me know if you'd like to discuss!\n\n"
        f"Best,\nBIT RAGE SYSTEMS"
    )

    return {
        "id": str(uuid4())[:8],
        "job_id": job.get("_id", ""),
        "job_title": job_title,
        "job_url": job.get("url", ""),
        "service": match["service"],
        "match_score": match["score"],
        "proposal": proposal_text[:MAX_PROPOSAL_LENGTH],
        "hourly_range": service.get("hourly", "$20-40"),
        "budget_str": budget,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_submit",
    }


# ── Scan + Apply ───────────────────────────────────────────────

def run_scan(dry_run: bool = False) -> dict:
    """Scan new jobs, match, generate proposals."""
    state = _load_state()
    state = _reset_daily(state)
    jobs = load_new_jobs(state)

    results = {"scanned": len(jobs), "matched": 0, "proposals": 0, "skipped": 0}

    print(f"\n  UPWORK SCAN: {len(jobs)} new jobs found")

    matched_jobs = []
    for job in jobs:
        match = match_job(job)
        state["seen_job_ids"].append(job["_id"])

        if match["score"] >= MIN_MATCH_SCORE:
            matched_jobs.append((job, match))
            results["matched"] += 1
        else:
            results["skipped"] += 1

    # Sort by match score
    matched_jobs.sort(key=lambda x: x[1]["score"], reverse=True)

    # Keep seen list manageable
    state["seen_job_ids"] = state["seen_job_ids"][-500:]

    remaining = MAX_DAILY_APPLIES - state.get("daily_applies", 0)

    for job, match in matched_jobs[:remaining]:
        proposal = generate_proposal(job, match)

        if dry_run:
            print(f"  [PREVIEW] {job.get('title', '?')[:50]:50s} | score={match['score']} | {match['service']}")
            continue

        # Save proposal
        proposal_file = PROPOSALS_DIR / f"proposal_{proposal['id']}.json"
        proposal_file.write_text(json.dumps(proposal, indent=2), encoding="utf-8")

        state["proposals_generated"] = state.get("proposals_generated", 0) + 1
        state["daily_applies"] = state.get("daily_applies", 0) + 1
        results["proposals"] += 1

        log_decision(
            phase="upwork_apply",
            decision=f"Proposal generated for: {job.get('title', '?')[:60]}",
            data={"match_score": match["score"], "service": match["service"]},
        )

        print(f"  [PROPOSAL] {job.get('title', '?')[:50]:50s} | score={match['score']} | {match['service']}")

    state["scans_run"] = state.get("scans_run", 0) + 1
    state["last_scan"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)

    print(f"\n  RESULT: {results['matched']} matched | {results['proposals']} proposals | {results['skipped']} skipped")
    return results


def get_status() -> dict:
    """Get application status."""
    state = _load_state()
    proposals = list(PROPOSALS_DIR.glob("proposal_*.json"))
    pending = sum(
        1 for p in proposals
        if json.loads(p.read_text(encoding="utf-8")).get("status") == "pending_submit"
    )
    return {
        "total_applies": state.get("total_applies", 0),
        "daily_applies": state.get("daily_applies", 0),
        "daily_remaining": MAX_DAILY_APPLIES - state.get("daily_applies", 0),
        "scans_run": state.get("scans_run", 0),
        "proposals_generated": state.get("proposals_generated", 0),
        "pending_submit": pending,
        "last_scan": state.get("last_scan"),
    }


def daemon_loop():
    """Run scan every 2 hours."""
    print("[UPWORK APPLY] Daemon started")
    while True:
        try:
            run_scan()
        except Exception as e:
            print(f"  [ERROR] {e}")
        time.sleep(POLL_INTERVAL)


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Upwork Auto-Apply")
    parser.add_argument("--scan", action="store_true", help="Scan + match jobs")
    parser.add_argument("--apply", type=int, help="Generate N proposals")
    parser.add_argument("--status", action="store_true", help="Show stats")
    parser.add_argument("--preview", action="store_true", help="Preview without applying")
    parser.add_argument("--daemon", action="store_true", help="Poll every 2 hrs")
    args = parser.parse_args()

    if args.status:
        status = get_status()
        print(f"\n  Proposals generated: {status['proposals_generated']}")
        print(f"  Pending submit: {status['pending_submit']}")
        print(f"  Applied today: {status['daily_applies']} / {MAX_DAILY_APPLIES}")
        print(f"  Scans run: {status['scans_run']}")
        print(f"  Last scan: {status['last_scan']}")
    elif args.daemon:
        daemon_loop()
    elif args.preview:
        run_scan(dry_run=True)
    elif args.scan or args.apply:
        run_scan()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
