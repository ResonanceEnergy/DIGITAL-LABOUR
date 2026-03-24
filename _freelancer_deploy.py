"""Freelancer.com deployment runner — orchestrates job hunting and project bidding.

Usage:
  python _freelancer_deploy.py              # Status dashboard
  python _freelancer_deploy.py --jobs       # Search projects + submit bids
  python _freelancer_deploy.py --scan       # Scan projects only (no bidding)
  python _freelancer_deploy.py --jobs --query "data entry"   # Custom search
  python _freelancer_deploy.py --jobs --max-queries 10       # More queries
  python _freelancer_deploy.py --messages --project-url URL  # Read messages
  python _freelancer_deploy.py --deliver --project-url URL   # Deliver files
"""

import io
import sys

# Ensure UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import json
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))

DATA_DIR = PROJECT / "data" / "freelancer_jobs"
BID_LOG = DATA_DIR / "bids_submitted.json"
JOB_LOG = DATA_DIR / "project_log.jsonl"
SS_DIR = PROJECT / "output" / "platform_screenshots"


# ── Status dashboard ────────────────────────────────────────────────────────

def show_status():
    print("=" * 60)
    print("  FREELANCER STATUS DASHBOARD")
    print("=" * 60)

    bids = 0
    submitted = 0
    if BID_LOG.exists():
        try:
            data = json.loads(BID_LOG.read_text(encoding="utf-8"))
            if isinstance(data, list):
                bids = len(data)
                submitted = sum(1 for b in data if b.get("submitted"))
        except Exception:
            pass

    scanned = 0
    if JOB_LOG.exists():
        try:
            with open(JOB_LOG, encoding="utf-8") as f:
                scanned = sum(1 for line in f if line.strip())
        except Exception:
            pass

    shots = list(SS_DIR.glob("freelancer_*.png")) if SS_DIR.exists() else []
    last_run = "never"
    if shots:
        try:
            last_run = datetime.fromtimestamp(
                max(s.stat().st_mtime for s in shots)
            ).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

    print(f"  Projects scanned:  {scanned}")
    print(f"  Bids generated:    {bids}")
    print(f"  Bids submitted:    {submitted}")
    print(f"  Screenshots:       {len(shots)}")
    print(f"  Last run:          {last_run}")
    print()

    # Show most recent bids
    if bids > 0 and BID_LOG.exists():
        try:
            data = json.loads(BID_LOG.read_text(encoding="utf-8"))
            recent = sorted(data, key=lambda x: x.get("generated_at", ""), reverse=True)[:5]
            print("  Recent bids:")
            for b in recent:
                status = "SUBMITTED" if b.get("submitted") else "generated"
                title = b.get("project_title", "?")[:45]
                score = b.get("score", 0)
                budget = b.get("budget", "?")
                print(f"    [{status}] [{score:.2f}] {title} — {budget}")
            print()
        except Exception:
            pass

    print("  Available commands:")
    print("    --jobs                       Job hunt + auto-bid")
    print("    --scan                       Scan projects only (no bids)")
    print("    --jobs --query TEXT          Custom search query")
    print("    --jobs --max-queries N       How many search queries to run")
    print("    --messages --project-url URL Read project messages")
    print("    --deliver --project-url URL  Deliver files to a project")
    print("=" * 60)


# ── Job hunt ────────────────────────────────────────────────────────────────

def run_jobs(scan_only: bool = False, query: str | None = None, max_queries: int = 5):
    """Search Freelancer.com for projects and submit bids."""
    mode = "SCAN ONLY" if scan_only else "SEARCH + BID"
    print(f"[FREELANCER] Job hunt — {mode}")
    if query:
        print(f"[FREELANCER] Custom query: {query!r}")
    if max_queries != 5:
        print(f"[FREELANCER] Max queries: {max_queries}")

    from automation.freelancer_jobhunt import run_job_hunt
    run_job_hunt(scan_only=scan_only, custom_search=query, max_queries=max_queries)


# ── Client interactions (messages, milestones, delivery) ────────────────────

def run_client_action(action: str, project_url: str, message: str | None = None,
                       files: list[str] | None = None):
    """Perform a client interaction on an active project."""
    print(f"[FREELANCER] Client action: {action} on {project_url[:60]}")

    saved_argv = sys.argv[:]
    sys.argv = ["freelancer_client", "--action", action, "--project-url", project_url]
    if message:
        sys.argv += ["--message", message]
    if files:
        sys.argv += ["--files"] + files

    try:
        from automation.freelancer_client import main
        main()
    finally:
        sys.argv = saved_argv


# ── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Freelancer.com deployment runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python _freelancer_deploy.py --jobs\n"
            "  python _freelancer_deploy.py --scan\n"
            "  python _freelancer_deploy.py --jobs --query 'web scraping'\n"
            "  python _freelancer_deploy.py --jobs --max-queries 10\n"
            "  python _freelancer_deploy.py --messages --project-url URL\n"
            "  python _freelancer_deploy.py --deliver --project-url URL\n"
        ),
    )

    # Job hunt group
    parser.add_argument("--jobs", action="store_true", help="Job hunt + auto-bid")
    parser.add_argument("--scan", action="store_true", help="Scan projects only (no bids)")
    parser.add_argument("--query", type=str, default=None, help="Custom search query")
    parser.add_argument("--max-queries", type=int, default=5, dest="max_queries",
                        help="Number of search queries to run (default: 5)")

    # Client interaction group
    parser.add_argument("--messages", action="store_true", help="Read project messages")
    parser.add_argument("--deliver", action="store_true", help="Deliver files to a project")
    parser.add_argument("--milestones", action="store_true", help="View project milestones")
    parser.add_argument("--project-url", type=str, default=None, dest="project_url",
                        help="Freelancer project URL (for client actions)")
    parser.add_argument("--message", type=str, default=None,
                        help="Message text to send")
    parser.add_argument("--files", type=str, nargs="+", default=None,
                        help="Files to deliver")

    args = parser.parse_args()

    # Client interaction actions
    if args.messages and args.project_url:
        run_client_action("messages", args.project_url)
    elif args.deliver and args.project_url:
        run_client_action("deliver", args.project_url, files=args.files)
    elif args.milestones and args.project_url:
        run_client_action("milestones", args.project_url)

    # Job hunt
    elif args.jobs or args.scan or args.query:
        scan_only = args.scan and not args.jobs
        run_jobs(scan_only=scan_only, query=args.query, max_queries=args.max_queries)

    # Default: status
    else:
        show_status()


if __name__ == "__main__":
    main()
