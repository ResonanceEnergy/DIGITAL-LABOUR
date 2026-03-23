"""Meta Sales Ops — DIGITAL LABOUR selling itself using its own Sales Ops agent.

This module automates cold outreach for DIGITAL LABOUR's own services.
It feeds target companies into the Sales Ops pipeline with DL-specific product
positioning, then queues the output for human review before sending.

Usage:
    python -m meta.self_sell --target "Acme Corp" --role "VP Sales"
    python -m meta.self_sell --batch targets.csv
    python -m meta.self_sell --demo          # Run 3 demo targets
"""

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── DL Product Positioning ─────────────────────────────────────

PRODUCT_DESCRIPTIONS = {
    "sales_outreach": (
        "DIGITAL LABOUR runs an AI agent that researches a target company, "
        "finds a real signal (funding round, product launch, hiring surge), "
        "and writes a 3-email outreach sequence referencing that signal. "
        "Not templates — each output is personalized and QA-checked. "
        "80%+ first-pass quality rate, 13 seconds per lead."
    ),
    "support_ticket": (
        "DIGITAL LABOUR runs an AI agent that triages inbound support tickets, "
        "matches them against your knowledge base, and drafts professional responses. "
        "Handles tier-1 tickets end-to-end, escalates complex ones with context."
    ),
    "content_repurpose": (
        "DIGITAL LABOUR runs an AI agent that takes a single piece of content "
        "(blog post, video transcript, whitepaper) and repurposes it into "
        "LinkedIn posts, tweet threads, email newsletters, and short-form summaries."
    ),
    "full_suite": (
        "DIGITAL LABOUR provides an AI workforce that handles sales outreach, "
        "customer support, and content repurposing — end-to-end, QA-checked, "
        "delivered as ready-to-use outputs. No tools to learn, no prompts to write. "
        "You submit work, we deliver results. Starting at $1/task."
    ),
}

# Target personas
IDEAL_TARGETS = [
    {"vertical": "SaaS", "roles": ["VP Sales", "Head of Growth", "SDR Manager", "Revenue Ops"]},
    {"vertical": "Agency", "roles": ["Founder", "Account Director", "Growth Lead"]},
    {"vertical": "Startup", "roles": ["CEO", "Co-founder", "Head of Sales"]},
    {"vertical": "E-commerce", "roles": ["Marketing Director", "Head of CX"]},
    {"vertical": "Consulting", "roles": ["Partner", "Managing Director"]},
]

# Demo targets for --demo mode
DEMO_TARGETS = [
    {"company": "Vidyard", "role": "VP Sales"},
    {"company": "Lemlist", "role": "Head of Growth"},
    {"company": "Reply.io", "role": "CEO"},
]


# ── Pipeline ───────────────────────────────────────────────────

def run_self_sell(
    company: str,
    role: str,
    service: str = "full_suite",
    provider: str | None = None,
) -> dict:
    """Run the Sales Ops pipeline with DL-specific positioning."""
    from agents.sales_ops.runner import run_pipeline, save_output

    product = PRODUCT_DESCRIPTIONS.get(service, PRODUCT_DESCRIPTIONS["full_suite"])

    print(f"\n{'='*60}")
    print(f"[META SELL] Target: {company} / {role}")
    print(f"[META SELL] Service: {service}")
    print(f"{'='*60}")

    result = run_pipeline(
        company=company,
        role=role,
        product=product,
        tone="direct",
        max_retries=1,
        provider=provider,
    )

    if not result:
        return {"status": "failed", "company": company, "role": role}

    # Save to meta output directory
    meta_dir = PROJECT_ROOT / "output" / "meta_outreach"
    meta_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": {"company": company, "role": role},
        "service_pitched": service,
        "qa_status": result.qa_status,
        "enrichment": result.lead_enrichment.model_dump(),
        "emails": result.emails.model_dump(),
        "send_status": "pending_review",  # Human must approve before sending
    }

    import re as _re
    safe_name = _re.sub(r'[^\w\-]', '_', company)[:40].strip('_')
    filename = f"meta_{safe_name}_{uuid4().hex[:6]}.json"
    filepath = meta_dir / filename
    filepath.write_text(json.dumps(output, indent=2), encoding="utf-8")

    # Also save through the standard sales ops output
    save_output(result)

    print(f"[META SELL] QA: {result.qa_status}")
    print(f"[META SELL] Saved: {filepath.name}")
    print(f"[META SELL] Status: PENDING HUMAN REVIEW")

    return output


def run_batch(targets: list[dict], service: str = "full_suite", provider: str | None = None) -> list[dict]:
    """Run self-sell pipeline on multiple targets."""
    results = []
    for i, target in enumerate(targets, 1):
        print(f"\n[BATCH] {i}/{len(targets)}")
        result = run_self_sell(
            company=target["company"],
            role=target["role"],
            service=service,
            provider=provider,
        )
        results.append(result)
        if i < len(targets):
            time.sleep(2)  # Rate limiting courtesy

    # Summary
    passed = sum(1 for r in results if r.get("qa_status") == "PASS")
    print(f"\n{'='*60}")
    print(f"[BATCH COMPLETE] {passed}/{len(results)} passed QA")
    print(f"[NEXT] Review outputs in output/meta_outreach/")
    print(f"[NEXT] Approve and send manually (LinkedIn/email)")
    return results


def review_queue() -> list[dict]:
    """List all pending outreach awaiting human review."""
    meta_dir = PROJECT_ROOT / "output" / "meta_outreach"
    if not meta_dir.exists():
        return []

    pending = []
    for f in sorted(meta_dir.glob("meta_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("send_status") == "pending_review":
            pending.append({
                "file": f.name,
                "company": data["target"]["company"],
                "role": data["target"]["role"],
                "qa_status": data["qa_status"],
                "service": data["service_pitched"],
                "generated": data["generated_at"],
            })
    return pending


def mark_sent(filename: str):
    """Mark an outreach as sent after human approval."""
    filepath = PROJECT_ROOT / "output" / "meta_outreach" / filename
    if not filepath.exists():
        print(f"File not found: {filename}")
        return
    data = json.loads(filepath.read_text(encoding="utf-8"))
    data["send_status"] = "sent"
    data["sent_at"] = datetime.now(timezone.utc).isoformat()
    filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[SENT] Marked as sent: {filename}")


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Meta Sales Ops — DL sells itself")
    parser.add_argument("--target", help="Target company name")
    parser.add_argument("--role", default="Head of Growth", help="Target role")
    parser.add_argument("--service", default="full_suite",
                        choices=list(PRODUCT_DESCRIPTIONS.keys()),
                        help="Service to pitch")
    parser.add_argument("--provider", default=None, help="LLM provider")
    parser.add_argument("--batch", help="CSV file with company,role columns")
    parser.add_argument("--demo", action="store_true", help="Run demo targets")
    parser.add_argument("--review", action="store_true", help="Show pending review queue")
    parser.add_argument("--sent", help="Mark a file as sent")
    args = parser.parse_args()

    if args.review:
        pending = review_queue()
        if not pending:
            print("No outreach pending review.")
        else:
            print(f"\n{'='*60}")
            print(f"PENDING REVIEW: {len(pending)} items")
            print(f"{'='*60}")
            for p in pending:
                print(f"  {p['company']:20s} | {p['role']:20s} | QA: {p['qa_status']} | {p['file']}")
    elif args.sent:
        mark_sent(args.sent)
    elif args.demo:
        run_batch(DEMO_TARGETS, service=args.service, provider=args.provider)
    elif args.batch:
        targets = []
        with open(args.batch, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                targets.append({"company": row["company"], "role": row["role"]})
        run_batch(targets, service=args.service, provider=args.provider)
    elif args.target:
        run_self_sell(args.target, args.role, service=args.service, provider=args.provider)
    else:
        parser.print_help()
