"""Upwork deployment runner — orchestrates profile setup and job hunting.

Usage:
  python _upwork_deploy.py              # Status dashboard
  python _upwork_deploy.py --profile    # Run Upwork profile wizard (first-time setup)
  python _upwork_deploy.py --jobs       # Job hunt + auto-apply
  python _upwork_deploy.py --scan       # Scan jobs only (no apply)
  python _upwork_deploy.py --jobs --query "ai automation"  # Custom search
  python _upwork_deploy.py --jobs --max-applies 5          # Cap proposals
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

DATA_DIR = PROJECT / "data" / "upwork_jobs"
APPLIED_LOG = DATA_DIR / "applied.json"
JOB_LOG = DATA_DIR / "job_log.jsonl"
SS_DIR = PROJECT / "output" / "platform_screenshots"


# ── Status dashboard ────────────────────────────────────────────────────────

def show_status():
    print("=" * 60)
    print("  UPWORK STATUS DASHBOARD")
    print("=" * 60)

    applied_count = 0
    if APPLIED_LOG.exists():
        try:
            data = json.loads(APPLIED_LOG.read_text(encoding="utf-8"))
            applied_count = len(data.get("applied_urls", []))
        except Exception:
            pass

    scanned = 0
    if JOB_LOG.exists():
        try:
            with open(JOB_LOG, encoding="utf-8") as f:
                scanned = sum(1 for line in f if line.strip())
        except Exception:
            pass

    shots = list(SS_DIR.glob("upwork_*.png")) if SS_DIR.exists() else []
    last_run = "never"
    if shots:
        try:
            last_run = datetime.fromtimestamp(
                max(s.stat().st_mtime for s in shots)
            ).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

    print(f"  Jobs scanned:    {scanned}")
    print(f"  Applied:         {applied_count}")
    print(f"  Screenshots:     {len(shots)}")
    print(f"  Last run:        {last_run}")
    print()
    print("  Available commands:")
    print("    --profile              Run Upwork profile creation wizard")
    print("    --jobs                 Job hunt + auto-apply")
    print("    --scan                 Scan jobs only (no apply)")
    print("    --jobs --query TEXT    Custom search query")
    print("    --jobs --max-applies N Limit proposals to N")
    print("=" * 60)


# ── Profile wizard ──────────────────────────────────────────────────────────

def run_profile():
    """Run the Upwork full-profile automation wizard (automation/upwork_automate.py)."""
    print("[UPWORK] Starting profile wizard...")
    saved_argv = sys.argv[:]
    sys.argv = ["upwork_automate"]
    try:
        from automation.upwork_automate import main
        main()
    finally:
        sys.argv = saved_argv


# ── Job hunt ────────────────────────────────────────────────────────────────

def run_jobs(scan_only: bool = False, query: str | None = None, max_applies: int = 10):
    """Run Upwork job hunting (automation/upwork_jobhunt.py)."""
    mode = "SCAN ONLY" if scan_only else "SEARCH + APPLY"
    print(f"[UPWORK] Job hunt — {mode}")
    if query:
        print(f"[UPWORK] Custom query: {query!r}")

    saved_argv = sys.argv[:]
    sys.argv = ["upwork_jobhunt"]
    if scan_only:
        sys.argv.append("--scan-only")
    if query:
        sys.argv += ["--search", query]
    if max_applies != 10:
        sys.argv += ["--max-applies", str(max_applies)]

    try:
        from automation.upwork_jobhunt import main
        main()
    finally:
        sys.argv = saved_argv


# ── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Upwork deployment runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python _upwork_deploy.py --profile\n"
            "  python _upwork_deploy.py --jobs\n"
            "  python _upwork_deploy.py --scan\n"
            "  python _upwork_deploy.py --jobs --query 'ai automation'\n"
            "  python _upwork_deploy.py --jobs --max-applies 3\n"
        ),
    )
    parser.add_argument("--profile", action="store_true", help="Run Upwork profile wizard")
    parser.add_argument("--jobs", action="store_true", help="Job hunt + auto-apply")
    parser.add_argument("--scan", action="store_true", help="Scan jobs only (no apply)")
    parser.add_argument("--query", type=str, default=None, help="Custom search query")
    parser.add_argument("--max-applies", type=int, default=10, dest="max_applies",
                        help="Max proposals to submit (default: 10)")
    args = parser.parse_args()

    if args.profile:
        run_profile()
    elif args.jobs or args.scan or args.query:
        scan_only = args.scan and not args.jobs
        run_jobs(scan_only=scan_only, query=args.query, max_applies=args.max_applies)
    else:
        show_status()


if __name__ == "__main__":
    main()
