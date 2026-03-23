"""Step 94 — Direct sales push: 50-message outreach blast.

One-shot script that:
  1. Generates fresh prospects (if needed) to fill up to 50 targets
  2. Runs self-sell pipeline on each prospect
  3. Auto-approves all PASS results
  4. Sends via Zoho SMTP (or logs to file if SMTP not configured)
  5. Prints a final campaign summary

Usage:
    python -m automation.outreach_push                    # 50 targets, default provider
    python -m automation.outreach_push --count 25         # custom count
    python -m automation.outreach_push --provider gemini  # choose LLM provider
    python -m automation.outreach_push --dry-run          # generate + QA only, no send
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

PROSPECTS_FILE  = PROJECT_ROOT / "automation" / "prospects.csv"
SENT_LOG        = PROJECT_ROOT / "automation" / "sent_log.json"
PUSH_LOG        = PROJECT_ROOT / "data" / "outreach_push_log.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_sent_log() -> list[dict]:
    if SENT_LOG.exists():
        return json.loads(SENT_LOG.read_text(encoding="utf-8"))
    return []


def _save_sent_log(log: list[dict]) -> None:
    SENT_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")


def _load_prospects() -> list[dict]:
    """Load uncontacted prospects from CSV."""
    if not PROSPECTS_FILE.exists():
        return []
    sent      = {s["company"].lower() for s in _load_sent_log()}
    prospects = []
    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("company", "").lower() not in sent:
                prospects.append(row)
    return prospects


def _append_to_push_log(entry: dict) -> None:
    existing = []
    if PUSH_LOG.exists():
        try:
            existing = json.loads(PUSH_LOG.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing.append(entry)
    PUSH_LOG.parent.mkdir(parents=True, exist_ok=True)
    PUSH_LOG.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def _fill_prospects(needed: int) -> int:
    """Generate new prospects if CSV doesn't have enough uncontacted ones."""
    try:
        from automation.prospect_engine import generate_prospects  # noqa: PLC0415
        print(f"[PUSH] Generating {needed} fresh prospect(s) via LLM...")
        added = generate_prospects(count=needed)
        print(f"[PUSH] Added {added} new prospect(s) to {PROSPECTS_FILE.name}")
        return added
    except Exception as exc:
        print(f"[PUSH] WARNING: Could not generate prospects: {exc}")
        return 0


# ── Core push logic ───────────────────────────────────────────────────────────

def run_push(count: int = 50, provider: str = "openai", dry_run: bool = False) -> dict:
    """Run the full 50-message outreach push campaign."""
    print()
    print("=" * 70)
    print(f"  DIGITAL LABOUR - DIRECT SALES PUSH")
    print(f"  Targets: {count}  |  Provider: {provider.upper()}  |  "
          f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 70)
    print()

    # Ensure enough uncontacted prospects
    available = _load_prospects()
    if len(available) < count:
        deficit = count - len(available)
        _fill_prospects(deficit)
        available = _load_prospects()

    targets = available[:count]
    if not targets:
        print("[PUSH] No prospects available. Check prospects.csv.")
        return {"sent": 0, "failed": 0, "total": 0}

    print(f"[PUSH] Loaded {len(targets)} target(s)")

    # ── Run self-sell pipeline on each target ─────────────────────────────────
    from meta.self_sell import run_self_sell  # noqa: PLC0415

    sent_log  = _load_sent_log()
    generated = []
    fails     = []

    for i, prospect in enumerate(targets, 1):
        company  = prospect.get("company", "Unknown")
        role     = prospect.get("role",    "Decision Maker")
        vertical = prospect.get("vertical", "")
        print(f"\n[{i:02d}/{len(targets)}] {company} ({role})", end="  ")

        try:
            result = run_self_sell(
                company  = company,
                role     = role,
                service  = "full_suite",
                provider = provider,
            )
            qa_status = result.get("qa_status", "UNKNOWN")
            print(f"-> QA: {qa_status}")
            generated.append({
                "company":   company,
                "role":      role,
                "vertical":  vertical,
                "qa_status": qa_status,
                "file":      result.get("file", ""),
                "result":    result,
            })
        except Exception as exc:
            print(f"-> ERROR: {exc}")
            fails.append({"company": company, "role": role, "error": str(exc)})

        if i < len(targets):
            time.sleep(2)  # 2-second rate limit between LLM calls

    pass_results = [g for g in generated if g["qa_status"] == "PASS"]
    print(f"\n[PUSH] Generation complete: {len(pass_results)}/{len(targets)} passed QA")

    if dry_run:
        print(f"[PUSH] DRY RUN - skipping send. {len(pass_results)} messages ready.")
        summary = {
            "mode":         "dry_run",
            "timestamp":    datetime.now(timezone.utc).isoformat(),
            "targets":      len(targets),
            "generated":    len(generated),
            "passed_qa":    len(pass_results),
            "sent":         0,
            "failed_gen":   len(fails),
            "provider":     provider,
        }
        _append_to_push_log(summary)
        _print_summary(summary)
        return summary

    # ── Send via outreach.send_approved pathway ───────────────────────────────
    from automation.outreach import send_approved  # noqa: PLC0415
    print(f"\n[PUSH] Sending {len(pass_results)} approved messages...")

    sent_results = send_approved(auto_approve=True)
    sent_count   = len([r for r in sent_results if r.get("status") == "sent"])

    # Refresh sent log after sending
    sent_log = _load_sent_log()

    summary = {
        "mode":         "live",
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "targets":      len(targets),
        "generated":    len(generated),
        "passed_qa":    len(pass_results),
        "sent":         sent_count,
        "failed_gen":   len(fails),
        "total_sent_ever": len(sent_log),
        "provider":     provider,
    }
    _append_to_push_log(summary)
    _print_summary(summary)
    return summary


def _print_summary(summary: dict) -> None:
    print()
    print("-" * 70)
    print("  PUSH SUMMARY")
    print("-" * 70)
    print(f"  Targets loaded  : {summary['targets']}")
    print(f"  Generated       : {summary['generated']}")
    print(f"  Passed QA       : {summary['passed_qa']}")
    if summary.get("mode") != "dry_run":
        print(f"  Sent            : {summary['sent']}")
        print(f"  Total sent ever : {summary.get('total_sent_ever', '?')}")
    print(f"  Gen failures    : {summary['failed_gen']}")
    print(f"  Provider        : {summary['provider'].upper()}")
    print(f"  Mode            : {summary['mode'].upper()}")
    print("-" * 70)
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DIGITAL LABOUR - 50-message direct sales push (Step 94)"
    )
    parser.add_argument("--count",    type=int,  default=50,      help="Number of targets (default: 50)")
    parser.add_argument("--provider", type=str,  default="openai", help="LLM provider (default: openai)")
    parser.add_argument("--dry-run",  action="store_true",        help="Generate + QA only, skip send")
    args = parser.parse_args()

    result = run_push(count=args.count, provider=args.provider, dry_run=args.dry_run)
    sys.exit(0 if result.get("sent", 0) > 0 or args.dry_run else 1)


if __name__ == "__main__":
    main()
