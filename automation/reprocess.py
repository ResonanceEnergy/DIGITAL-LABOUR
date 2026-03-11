"""Reprocess FAIL Outreach — Regenerates failed QA leads for another attempt.

Scans output/meta_outreach for files with qa_status=FAIL, regenerates them
with improved prompts, and re-queues for approval.

Usage:
    python -m automation.reprocess              # Reprocess all FAIL files
    python -m automation.reprocess --count 5    # Reprocess up to 5
    python -m automation.reprocess --list       # List all FAIL files
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTREACH_DIR = PROJECT_ROOT / "output" / "meta_outreach"


def find_fail_files() -> list[Path]:
    """Find all outreach files with FAIL or pending_review status."""
    fails = []
    if not OUTREACH_DIR.exists():
        return fails

    for f in sorted(OUTREACH_DIR.glob("meta_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            status = data.get("qa_status", "")
            send_status = data.get("send_status", "")
            # Only reprocess unsent failures
            if status == "FAIL" and send_status != "sent":
                fails.append(f)
        except Exception:
            continue
    return fails


def list_fails():
    """Display all FAIL outreach files."""
    fails = find_fail_files()
    if not fails:
        print("[REPROCESS] No FAIL files found. All outreach passing QA or already sent.")
        return

    print(f"\n{'='*60}")
    print(f"  FAIL OUTREACH FILES — {len(fails)} found")
    print(f"{'='*60}")
    for f in fails:
        data = json.loads(f.read_text(encoding="utf-8"))
        company = data.get("target", {}).get("company", "?")
        qa_notes = data.get("qa_notes", "")[:60]
        print(f"  {f.name:40s} {company:20s} {qa_notes}")


def reprocess(count: int = 0):
    """Regenerate FAIL outreach with improved approach."""
    fails = find_fail_files()
    if not fails:
        print("[REPROCESS] No FAIL files to reprocess.")
        return

    if count:
        fails = fails[:count]

    print(f"\n[REPROCESS] Regenerating {len(fails)} failed outreach files...\n")

    from meta.self_sell import run_self_sell
    success = 0
    still_fail = 0

    for i, f in enumerate(fails, 1):
        data = json.loads(f.read_text(encoding="utf-8"))
        company = data.get("target", {}).get("company", "Unknown")
        role = data.get("target", {}).get("role", "Operations Manager")

        print(f"[{i}/{len(fails)}] {company} — {role}")

        # Archive old file
        archive_dir = OUTREACH_DIR / "archive"
        archive_dir.mkdir(exist_ok=True)
        archive_name = f"fail_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}_{f.name}"
        f.rename(archive_dir / archive_name)

        try:
            result = run_self_sell(
                company=company,
                role=role,
                service="full_suite",
            )
            status = result.get("qa_status", "UNKNOWN")
            if status == "PASS":
                success += 1
                print(f"  [PASS] Regenerated successfully")
            else:
                still_fail += 1
                print(f"  [FAIL] Still failing QA: {result.get('qa_notes', '')[:60]}")
        except Exception as e:
            still_fail += 1
            print(f"  [ERROR] {e}")

    print(f"\n[REPROCESS] Done: {success} now passing, {still_fail} still failing")
    return {"success": success, "still_fail": still_fail}


def main():
    parser = argparse.ArgumentParser(description="Reprocess FAIL Outreach")
    parser.add_argument("--count", type=int, default=0, help="Max files to reprocess (0=all)")
    parser.add_argument("--list", action="store_true", help="List all FAIL files")
    args = parser.parse_args()

    if args.list:
        list_fails()
    else:
        reprocess(count=args.count)


if __name__ == "__main__":
    main()
