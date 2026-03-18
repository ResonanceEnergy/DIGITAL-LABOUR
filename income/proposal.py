"""Consulting Proposal Generator — Auto-generates enterprise proposals.

Creates custom proposals for B2B consulting engagements using AI.
Templates cover setup fees, monthly retainers, scope of work, and timelines.

Usage:
    python -m income.proposal --company "Acme Corp" --role "CTO"
    python -m income.proposal --company "Acme Corp" --package enterprise
    python -m income.proposal --template          # Show blank template
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

PROPOSAL_DIR = PROJECT_ROOT / "output" / "proposals"


# ── Packages ───────────────────────────────────────────────────

PACKAGES = {
    "starter": {
        "name": "Starter — AI Agent Pilot",
        "setup_fee": 500,
        "monthly": 250,
        "agents": 1,
        "tasks_per_month": 50,
        "duration": "3 months",
        "includes": [
            "1 AI agent (Sales Outreach OR Support OR Content)",
            "Up to 50 automated tasks/month",
            "Weekly performance reports",
            "Email support (48h response)",
            "QA verification on all outputs",
        ],
    },
    "professional": {
        "name": "Professional — Multi-Agent Suite",
        "setup_fee": 1500,
        "monthly": 750,
        "agents": 3,
        "tasks_per_month": 200,
        "duration": "6 months",
        "includes": [
            "3 AI agents of your choice",
            "Up to 200 automated tasks/month",
            "Daily performance dashboards",
            "Priority email + Slack support",
            "QA verification + custom tuning",
            "Monthly strategy call (30 min)",
            "Custom agent configuration",
        ],
    },
    "enterprise": {
        "name": "Enterprise — Full Digital Workforce",
        "setup_fee": 5000,
        "monthly": 2500,
        "agents": 4,
        "tasks_per_month": 999,
        "duration": "12 months",
        "includes": [
            "All 4 AI agents (Sales, Support, Content, Extract)",
            "Unlimited automated tasks",
            "Real-time dashboard access",
            "24/7 priority support + dedicated Slack",
            "QA verification + custom model tuning",
            "Weekly strategy calls (60 min)",
            "Custom agent development",
            "API access for integration",
            "Multi-LLM failover (OpenAI, Claude, Gemini, Grok)",
            "Dedicated account manager (AI-powered)",
        ],
    },
}


def generate_proposal(company: str, role: str = "CTO",
                       package: str = "professional", notes: str = "") -> dict:
    """Generate a professional consulting proposal."""
    pkg = PACKAGES.get(package, PACKAGES["professional"])
    now = datetime.now(timezone.utc)
    valid_until = now + timedelta(days=14)

    proposal = {
        "metadata": {
            "generated": now.isoformat(),
            "valid_until": valid_until.isoformat(),
            "proposal_id": f"DL-{now.strftime('%Y%m%d')}-{company[:4].upper()}",
            "version": "1.0",
        },
        "company": company,
        "contact_role": role,
        "package": pkg["name"],
        "pricing": {
            "setup_fee": f"${pkg['setup_fee']:,}",
            "monthly_retainer": f"${pkg['monthly']:,}/mo",
            "contract_duration": pkg["duration"],
            "total_contract_value": f"${pkg['setup_fee'] + pkg['monthly'] * int(pkg['duration'].split()[0]):,}",
        },
        "scope_of_work": {
            "agents_deployed": pkg["agents"],
            "tasks_per_month": pkg["tasks_per_month"],
            "deliverables": pkg["includes"],
        },
        "timeline": {
            "week_1": "Discovery call + requirements gathering",
            "week_2": "Agent configuration + custom prompt tuning",
            "week_3": "Pilot run (50 tasks) with QA review",
            "week_4": "Full deployment + monitoring dashboard access",
        },
        "why_bit_rage_labour": [
            "4 specialized AI agents, each trained for specific business functions",
            "Multi-LLM architecture (OpenAI, Claude, Gemini, Grok) for best-in-class outputs",
            "QA verification on every single output before delivery",
            "Self-healing infrastructure — 24/7 autonomous operation via NERVE daemon",
            "Transparent pricing — no hidden fees, no per-token charges",
            "Real results: automated outreach, support resolution, content at scale",
        ],
        "next_steps": [
            f"1. Reply to confirm interest in the {pkg['name']} package",
            "2. Schedule a 15-minute discovery call",
            "3. Receive customized scope document within 24 hours",
            "4. Sign agreement and pay setup fee to begin",
        ],
        "payment_methods": [
            "Stripe (credit/debit card) — instant setup",
            "Bank transfer — NET 15 terms available for Enterprise",
            "Crypto (BTC/ETH/USDC) — for Web3-native companies",
        ],
    }

    # Save to file
    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
    safe_company = company.replace(" ", "_").replace("/", "_")
    filename = f"proposal_{safe_company}_{now.strftime('%Y%m%d')}.json"
    filepath = PROPOSAL_DIR / filename
    filepath.write_text(json.dumps(proposal, indent=2), encoding="utf-8")

    # Also generate markdown version
    md = _to_markdown(proposal)
    md_path = PROPOSAL_DIR / filename.replace(".json", ".md")
    md_path.write_text(md, encoding="utf-8")

    print(f"[PROPOSAL] Generated for {company}")
    print(f"  Package: {pkg['name']}")
    print(f"  Setup: {proposal['pricing']['setup_fee']} | Monthly: {proposal['pricing']['monthly_retainer']}")
    print(f"  Contract: {proposal['pricing']['total_contract_value']}")
    print(f"  Saved: {filepath.name}")
    print(f"  Markdown: {md_path.name}")

    return proposal


def _to_markdown(p: dict) -> str:
    """Convert proposal to a clean markdown document."""
    lines = [
        f"# Proposal: AI Digital Workforce for {p['company']}",
        f"",
        f"**Proposal ID:** {p['metadata']['proposal_id']}",
        f"**Date:** {p['metadata']['generated'][:10]}",
        f"**Valid Until:** {p['metadata']['valid_until'][:10]}",
        f"**Prepared For:** {p['contact_role']} at {p['company']}",
        f"",
        f"---",
        f"",
        f"## Package: {p['package']}",
        f"",
        f"| Item | Amount |",
        f"|------|--------|",
        f"| Setup Fee | {p['pricing']['setup_fee']} |",
        f"| Monthly Retainer | {p['pricing']['monthly_retainer']} |",
        f"| Contract Duration | {p['pricing']['contract_duration']} |",
        f"| **Total Contract Value** | **{p['pricing']['total_contract_value']}** |",
        f"",
        f"## Scope of Work",
        f"",
        f"- **AI Agents Deployed:** {p['scope_of_work']['agents_deployed']}",
        f"- **Tasks Per Month:** {p['scope_of_work']['tasks_per_month']}",
        f"",
        f"### Deliverables",
        f"",
    ]
    for d in p["scope_of_work"]["deliverables"]:
        lines.append(f"- {d}")

    lines.extend([
        f"",
        f"## Timeline",
        f"",
    ])
    for week, desc in p["timeline"].items():
        lines.append(f"- **{week.replace('_', ' ').title()}:** {desc}")

    lines.extend([
        f"",
        f"## Why Bit Rage Labour?",
        f"",
    ])
    for reason in p["why_bit_rage_labour"]:
        lines.append(f"- {reason}")

    lines.extend([
        f"",
        f"## Next Steps",
        f"",
    ])
    for step in p["next_steps"]:
        lines.append(f"{step}")

    lines.extend([
        f"",
        f"## Payment Methods",
        f"",
    ])
    for method in p["payment_methods"]:
        lines.append(f"- {method}")

    lines.extend([
        f"",
        f"---",
        f"",
        f"*Bit Rage Labour — AI agents that work while you sleep.*",
        f"*sales@bit-rage-labour.com | bit-rage-labour.com*",
    ])

    return "\n".join(lines) + "\n"


def show_template():
    """Show a blank proposal template."""
    print(f"\n{'='*60}")
    print(f"  PROPOSAL TEMPLATE — Available Packages")
    print(f"{'='*60}")
    for key, pkg in PACKAGES.items():
        print(f"\n  [{key.upper()}] {pkg['name']}")
        print(f"    Setup: ${pkg['setup_fee']:,} | Monthly: ${pkg['monthly']:,}/mo")
        print(f"    Duration: {pkg['duration']} | Agents: {pkg['agents']}")
        for item in pkg["includes"]:
            print(f"      • {item}")


def main():
    parser = argparse.ArgumentParser(description="Consulting Proposal Generator")
    parser.add_argument("--company", help="Target company name")
    parser.add_argument("--role", default="CTO", help="Contact role (default: CTO)")
    parser.add_argument("--package", default="professional",
                        choices=["starter", "professional", "enterprise"],
                        help="Package tier")
    parser.add_argument("--template", action="store_true", help="Show blank template")
    args = parser.parse_args()

    if args.template:
        show_template()
    elif args.company:
        generate_proposal(company=args.company, role=args.role, package=args.package)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
