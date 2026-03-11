"""Prospect Engine — LLM-powered prospect list generation.

When the prospect CSV is exhausted, this module uses LLM intelligence to
generate fresh, high-quality prospect lists targeting ideal customer profiles.

Usage:
    from automation.prospect_engine import generate_prospects, enrich_prospect
    count = generate_prospects(count=25)
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm
from automation.decision_log import log_decision

PROSPECTS_FILE = Path(__file__).parent / "prospects.csv"
SENT_LOG = Path(__file__).parent / "sent_log.json"

# ── Verticals & personas DL sells to ──────────────────────────

VERTICALS = [
    "SaaS", "Agency", "Startup", "E-commerce", "Consulting",
    "FinTech", "HealthTech", "EdTech", "MarTech", "PropTech",
    "LegalTech", "Logistics", "Recruiting", "Media", "Professional Services",
]

ROLES = [
    "VP of Sales", "Head of Growth", "CEO", "Founder", "Co-founder",
    "SDR Manager", "Revenue Ops", "Marketing Director", "Head of CX",
    "Account Director", "Growth Lead", "Director of Sales", "CMO",
    "VP of Marketing", "Head of Sales Ops", "Chief Revenue Officer",
]

PROSPECT_PROMPT = """You are a B2B sales intelligence agent for DIGITAL LABOUR — an AI labor company
that provides AI workers for sales outreach, customer support, content repurposing,
and document extraction. Starting at $1/task, 98% margins, QA-checked outputs.

Generate a list of {count} REAL companies that would benefit from AI labor services.

RULES:
- Each company must be a REAL, currently operating company (not made up)
- Focus on companies with 20-500 employees — big enough to need automation, small enough to buy
- Mix across these verticals: {verticals}
- Each needs: company name, decision-maker role, vertical, priority (high/medium)
- Do NOT include any of these already-contacted companies: {exclude}
- Prioritize companies that are:
  * Growing fast (hiring, funding, expanding)
  * In sales-heavy industries
  * Likely doing manual outreach/support currently
  * B2B focused (they understand the value proposition)

Output ONLY valid JSON array, no markdown fences:
[
  {{"company": "ExampleCorp", "role": "VP of Sales", "vertical": "SaaS", "priority": "high"}},
  ...
]
"""


def _get_contacted_companies() -> set[str]:
    """Get all companies already contacted or in prospect list."""
    companies = set()

    # From sent log
    if SENT_LOG.exists():
        sent = json.loads(SENT_LOG.read_text(encoding="utf-8"))
        companies.update(s["company"].lower() for s in sent)

    # From current CSV
    if PROSPECTS_FILE.exists():
        with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.add(row["company"].lower())

    return companies


def generate_prospects(count: int = 25) -> int:
    """Use LLM to generate new prospects and append to CSV."""
    contacted = _get_contacted_companies()
    exclude_str = ", ".join(sorted(contacted)[:60])  # Limit to prevent prompt overflow

    # Pick a mix of verticals for this batch
    import random
    batch_verticals = random.sample(VERTICALS, min(6, len(VERTICALS)))
    verticals_str = ", ".join(batch_verticals)

    prompt = PROSPECT_PROMPT.format(
        count=count,
        verticals=verticals_str,
        exclude=exclude_str if exclude_str else "none yet",
    )

    print(f"[PROSPECT ENGINE] Generating {count} new prospects...")
    print(f"  Verticals: {verticals_str}")
    print(f"  Excluding: {len(contacted)} already-contacted companies")

    try:
        raw = call_llm(
            system_prompt="You are a B2B sales intelligence agent. Output only valid JSON.",
            user_message=prompt,
        )

        # Parse response — strip fences if present
        import re
        cleaned = re.sub(r'```(?:json)?\s*\n?', '', raw).strip().rstrip('`')
        prospects = json.loads(cleaned)

        if not isinstance(prospects, list):
            raise ValueError("LLM returned non-list response")

        # Validate and deduplicate
        valid = []
        for p in prospects:
            if not isinstance(p, dict):
                continue
            if not all(k in p for k in ["company", "role", "vertical", "priority"]):
                continue
            if p["company"].lower() in contacted:
                continue
            contacted.add(p["company"].lower())  # Prevent dupes within batch
            valid.append(p)

        if not valid:
            print("[PROSPECT ENGINE] No valid new prospects generated.")
            return 0

        # Append to CSV
        file_exists = PROSPECTS_FILE.exists()
        with open(PROSPECTS_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["company", "role", "vertical", "priority"])
            if not file_exists:
                writer.writeheader()
            for p in valid:
                writer.writerow({
                    "company": p["company"],
                    "role": p["role"],
                    "vertical": p.get("vertical", "General"),
                    "priority": p.get("priority", "medium"),
                })

        log_decision(
            actor="PROSPECT_ENGINE",
            action="generate_prospects",
            reasoning=f"Prospect list depleted/low. Generated {len(valid)} new prospects.",
            outcome=f"Added {len(valid)} prospects across {verticals_str}",
            data={"count": len(valid), "verticals": batch_verticals},
        )

        print(f"[PROSPECT ENGINE] Added {len(valid)} new prospects to pipeline")
        return len(valid)

    except json.JSONDecodeError as e:
        print(f"[PROSPECT ENGINE] Failed to parse LLM response: {e}")
        log_decision(
            actor="PROSPECT_ENGINE",
            action="generate_prospects",
            reasoning="Prospect replenishment attempted",
            outcome=f"Failed — JSON parse error: {e}",
            severity="WARNING",
        )
        return 0
    except Exception as e:
        print(f"[PROSPECT ENGINE] Error: {e}")
        log_decision(
            actor="PROSPECT_ENGINE",
            action="generate_prospects",
            reasoning="Prospect replenishment attempted",
            outcome=f"Failed — {e}",
            severity="WARNING",
        )
        return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate new prospects using LLM")
    parser.add_argument("--count", type=int, default=25, help="Number of prospects to generate")
    args = parser.parse_args()
    added = generate_prospects(count=args.count)
    print(f"\nTotal added: {added}")
