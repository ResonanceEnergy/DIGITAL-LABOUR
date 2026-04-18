#!/usr/bin/env python3
"""Fiverr Order Fulfillment CLI — Quick fulfillment from the command line.

Dispatches orders to the appropriate agent pipeline, saves deliverables,
and records revenue.

Usage:
    python tools/fulfill.py --gig product_desc --input "32oz steel water bottle, vacuum insulated" --platform amazon
    python tools/fulfill.py --gig resume --input "5 years Python dev, AWS certified" --role "Senior Engineer"
    python tools/fulfill.py --gig seo --input "Why AI automation matters for SMBs" --words 1500
    python tools/fulfill.py --gig ad_copy --input "AI sales automation SaaS" --platform google_search
    python tools/fulfill.py --gig email_sequence --input "SaaS onboarding tool, $49/mo" --tone conversational
"""

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Gig type aliases (accept short names)
GIG_ALIASES = {
    "product_desc": "product_desc",
    "product": "product_desc",
    "pd": "product_desc",
    "seo_content": "seo_content",
    "seo": "seo_content",
    "blog": "seo_content",
    "resume": "resume",
    "cv": "resume",
    "ad_copy": "ad_copy",
    "ads": "ad_copy",
    "ad": "ad_copy",
    "email_sequence": "email_sequence",
    "email": "email_sequence",
    "emails": "email_sequence",
    "grant_proposal": "grant_proposal",
    "grant": "grant_proposal",
    "compliance_document": "compliance_document",
    "compliance": "compliance_document",
    "insurance_appeal": "insurance_appeal",
    "appeal": "insurance_appeal",
    "data_report": "data_report",
    "report": "data_report",
}

GIG_LABELS = {
    "product_desc": "Product Descriptions",
    "seo_content": "SEO Blog Post",
    "resume": "Resume Writing",
    "ad_copy": "Ad Copy",
    "email_sequence": "Email Sequence",
    "grant_proposal": "Grant Proposal",
    "compliance_document": "Compliance Document",
    "insurance_appeal": "Insurance Appeal",
    "data_report": "Data Report",
}

BASE_REVENUE = {
    "product_desc": 25.00,
    "seo_content": 75.00,
    "resume": 35.00,
    "ad_copy": 40.00,
    "email_sequence": 100.00,
    "grant_proposal": 150.00,
    "compliance_document": 120.00,
    "insurance_appeal": 80.00,
    "data_report": 60.00,
}

OUTPUT_DIR = PROJECT_ROOT / "output" / "fulfillment"


def resolve_gig(raw: str) -> str:
    """Resolve a gig alias to the canonical gig type."""
    key = raw.lower().strip().replace("-", "_")
    if key not in GIG_ALIASES:
        print(f"[ERROR] Unknown gig type: '{raw}'")
        print(f"  Valid types: {', '.join(sorted(set(GIG_ALIASES.values())))}")
        print(f"  Aliases: {', '.join(sorted(GIG_ALIASES.keys()))}")
        sys.exit(1)
    return GIG_ALIASES[key]


def dispatch(gig_type: str, args: argparse.Namespace) -> dict:
    """Dispatch to the appropriate agent pipeline and return results."""

    if gig_type == "product_desc":
        from agents.product_desc.runner import run_pipeline, save_output
        result = run_pipeline(
            product_specs=args.input,
            platform=args.platform or "amazon",
            audience=args.audience or "",
            tone=args.tone or "professional",
            keywords=args.keywords or "",
        )
        save_output(result)
        return result.model_dump()

    elif gig_type == "seo_content":
        from agents.seo_content.runner import run_pipeline, save_output
        kwargs = {
            "topic": args.input,
            "content_type": "blog",
            "audience": args.audience or "",
            "tone": args.tone or "professional",
        }
        if args.keywords:
            kwargs["seed_keywords"] = args.keywords
        if args.words:
            kwargs["word_count"] = args.words
        result = run_pipeline(**kwargs)
        save_output(result)
        return result.model_dump()

    elif gig_type == "resume":
        from agents.resume_writer.runner import run_pipeline, save_output
        result = run_pipeline(
            career_data=args.input,
            target_role=args.role or "",
            industry=args.audience or "",
        )
        save_output(result)
        return result.model_dump()

    elif gig_type == "ad_copy":
        from agents.ad_copy.runner import run_pipeline, save_output
        result = run_pipeline(
            product_info=args.input,
            platform=args.platform or "google_search",
            audience=args.audience or "",
            tone=args.tone or "professional",
        )
        save_output(result)
        return result.model_dump()

    elif gig_type == "email_sequence":
        from agents.email_marketing.runner import run_pipeline, save_output
        result = run_pipeline(
            business_info=args.input,
            goal="sales",
            audience=args.audience or "",
            tone=args.tone or "professional",
        )
        save_output(result)
        return result.model_dump()

    elif gig_type == "grant_proposal":
        from agents.grant_writer.runner import run_pipeline, save_output
        result = run_pipeline(
            content=args.input,
            grant_type="sbir_phase1",
            agency="sba",
        )
        save_output(result)
        return result.model_dump()

    elif gig_type == "compliance_document":
        from agents.compliance_docs.runner import run_pipeline, save_output
        result = run_pipeline(
            content=args.input,
            doc_type="employee_handbook",
            company="",
            jurisdiction="us_federal",
        )
        save_output(result)
        return result.model_dump()

    elif gig_type == "insurance_appeal":
        from agents.insurance_appeals.runner import run_pipeline, save_output
        result = run_pipeline(
            content=args.input,
            letter_type="first_level_appeal",
            urgency="routine",
        )
        save_output(result)
        return result.model_dump()

    elif gig_type == "data_report":
        from agents.data_reporter.runner import run_pipeline, save_output
        result = run_pipeline(
            content=args.input,
            report_type="monthly_performance",
            period="",
            audience=args.audience or "executive",
        )
        save_output(result)
        return result.model_dump()

    else:
        print(f"[ERROR] No dispatcher for gig type: {gig_type}")
        sys.exit(1)


def save_deliverable(gig_type: str, result: dict, fulfillment_id: str) -> Path:
    """Save the raw JSON result to the fulfillment output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{gig_type}_{ts}_{fulfillment_id}.json"
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return path


def record_history(entry: dict) -> None:
    """Append to the shared fulfillment history file."""
    history_file = PROJECT_ROOT / "data" / "fulfillment_history.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    history.append(entry)
    history_file.write_text(
        json.dumps(history[-500:], indent=2, default=str),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(
        description="DIGITAL LABOUR — Fiverr Order Fulfillment CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/fulfill.py --gig product_desc --input "32oz steel water bottle" --platform amazon
  python tools/fulfill.py --gig seo --input "AI automation for SMBs" --words 1500
  python tools/fulfill.py --gig resume --input "5 years Python dev" --role "Senior Engineer"
  python tools/fulfill.py --gig ads --input "AI sales tool" --platform facebook
  python tools/fulfill.py --gig email --input "SaaS onboarding, $49/mo" --tone casual
        """,
    )
    parser.add_argument("--gig", required=True, help="Gig type (product_desc, seo, resume, ad_copy, email)")
    parser.add_argument("--input", required=True, help="Order requirements (product specs, career data, topic, etc.)")
    parser.add_argument("--file", default="", help="Read requirements from a file instead of --input")
    parser.add_argument("--platform", default="", help="Target platform (amazon, shopify, google_search, etc.)")
    parser.add_argument("--audience", default="", help="Target audience")
    parser.add_argument("--tone", default="", help="Writing tone (professional, casual, luxury, etc.)")
    parser.add_argument("--keywords", default="", help="SEO keywords or key phrases")
    parser.add_argument("--words", type=int, default=0, help="Word count target (SEO content only)")
    parser.add_argument("--role", default="", help="Target job role (resume only)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted text")
    args = parser.parse_args()

    # Resolve input source
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"[ERROR] File not found: {args.file}")
            sys.exit(1)
        args.input = file_path.read_text(encoding="utf-8")

    if not args.input or len(args.input.strip()) < 10:
        print("[ERROR] Input too short. Provide at least 10 characters of requirements.")
        sys.exit(1)

    gig_type = resolve_gig(args.gig)
    fulfillment_id = uuid.uuid4().hex[:12]

    print(f"\n{'='*60}")
    print(f"  DIGITAL LABOUR — Fiverr Fulfillment")
    print(f"  Gig: {GIG_LABELS[gig_type]}")
    print(f"  ID:  ff-{fulfillment_id}")
    print(f"{'='*60}\n")

    start = time.time()

    try:
        result = dispatch(gig_type, args)
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        print(f"\n[FAILED] Pipeline error after {elapsed}s: {e}")
        record_history({
            "fulfillment_id": f"ff-{fulfillment_id}",
            "gig_type": gig_type,
            "status": "failed",
            "qa_status": "FAIL",
            "error": str(e),
            "revenue_usd": 0.0,
            "processing_time": elapsed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        sys.exit(1)

    elapsed = round(time.time() - start, 2)
    qa_status = result.get("qa", {}).get("status", "N/A")
    revenue = BASE_REVENUE.get(gig_type, 0.0)

    # Save deliverable
    output_path = save_deliverable(gig_type, result, fulfillment_id)

    # Record history
    record_history({
        "fulfillment_id": f"ff-{fulfillment_id}",
        "gig_type": gig_type,
        "status": "completed",
        "qa_status": qa_status,
        "revenue_usd": revenue,
        "processing_time": elapsed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Output
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"\n{'='*60}")
        print(f"  FULFILLMENT COMPLETE")
        print(f"  QA Status:  {qa_status}")
        print(f"  Revenue:    ${revenue:.2f}")
        print(f"  Time:       {elapsed}s")
        print(f"  Saved:      {output_path}")
        print(f"{'='*60}\n")

    # Attempt revenue recording
    try:
        from income.tracker import record_income
        record_income(
            source="fiverr",
            category=gig_type,
            amount=revenue,
            reference=f"ff-{fulfillment_id}",
        )
        print(f"  [REVENUE] ${revenue:.2f} recorded to income tracker")
    except ImportError:
        pass
    except Exception as e:
        print(f"  [WARN] Revenue recording failed: {e}")


if __name__ == "__main__":
    main()
