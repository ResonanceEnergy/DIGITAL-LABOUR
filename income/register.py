"""Platform Registration Checklist — Step-by-step onboarding for all income sources.

Interactive checklist that walks through registration for each platform.
Tracks progress and provides direct URLs and instructions.

Usage:
    python -m income.register               # Full registration guide
    python -m income.register --quick       # Quick wins only (this week)
    python -m income.register --crypto      # Crypto agent platforms
    python -m income.register --check       # Check what's done
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Registration Checklists ─────────────────────────────────────

REGISTRATIONS = {
    "stripe_live": {
        "name": "Stripe — Switch to Live Mode",
        "priority": 1,
        "time": "15 minutes",
        "steps": [
            "1. Go to https://dashboard.stripe.com/settings/account",
            "2. Complete business verification (name, address, bank account)",
            "3. Go to https://dashboard.stripe.com/apikeys",
            "4. Copy LIVE secret key (sk_live_...)",
            "5. Copy LIVE publishable key (pk_live_...)",
            "6. Update .env: STRIPE_API_KEY=sk_live_...",
            "7. Update .env: STRIPE_PUBLIC_KEY=pk_live_...",
            "8. Update .env: STRIPE_LIVE=1",
            "9. Run: python -m billing.payment_links (creates live payment links)",
            "10. Verify: python -m billing.payment_links --list",
        ],
        "url": "https://dashboard.stripe.com/settings/account",
        "requires": ["Government ID or business registration", "Bank account for payouts"],
    },
    "freelancer": {
        "name": "Freelancer.com — Agency Profile",
        "priority": 2,
        "time": "30 minutes",
        "steps": [
            "1. Go to https://www.freelancer.com/signup",
            "2. Sign up as 'Freelancer' (not employer)",
            "3. Go to Profile → Edit → Set up as agency: 'DIGITAL LABOUR'",
            "4. Add tagline: 'Production AI agents for sales, support, content & doc automation'",
            "5. Add skills: AI, Python, FastAPI, NLP, Chatbot, Automation, API Dev",
            "6. Set hourly rate: $75-200/hr",
            "7. Upload portfolio: use demo outputs from output/meta_outreach/",
            "8. Verify email and phone",
            "9. Search 'AI agent' in jobs → bid on 5-10 matching jobs",
            "10. Use bid templates from: python -m income.freelance_listings --freelancer",
        ],
        "url": "https://www.freelancer.com/signup",
        "requires": ["Email", "Phone number", "Portfolio samples"],
    },
    "fiverr": {
        "name": "Fiverr — 4 AI Service Gigs",
        "priority": 3,
        "time": "45 minutes",
        "steps": [
            "1. Go to https://www.fiverr.com/join",
            "2. Complete seller onboarding",
            "3. Go to 'Selling' → 'Gigs' → 'Create a New Gig'",
            "4. Create gig #1: Sales Outreach Agent (see freelance_listings.py)",
            "5. Create gig #2: Support Resolver Agent",
            "6. Create gig #3: Content Repurposer Agent",
            "7. Create gig #4: Document Extractor Agent",
            "8. Set 3-tier pricing for each (Basic/Standard/Premium)",
            "9. Add FAQ to each gig",
            "10. Publish all 4 gigs",
            "11. Get gig listings: python -m income.freelance_listings --fiverr",
        ],
        "url": "https://www.fiverr.com/join",
        "requires": ["Email", "Profile photo", "Gig descriptions (generated for you)"],
    },
    "upwork": {
        "name": "Upwork — Premium Agency Profile",
        "priority": 4,
        "time": "30 minutes",
        "steps": [
            "1. Go to https://www.upwork.com/nx/signup/",
            "2. Sign up as a freelancer",
            "3. Set title: 'AI Agent Developer — Production Multi-Agent Systems'",
            "4. Set rate: $100-200/hr",
            "5. Add skills: AI, Python, FastAPI, LLM, NLP, Automation",
            "6. Write profile summary using about text from freelance_listings.py",
            "7. Set availability and preferences",
            "8. Apply to 5-10 AI agent/chatbot jobs",
        ],
        "url": "https://www.upwork.com/nx/signup/",
        "requires": ["Email", "Phone", "Government ID for verification"],
    },
    "rapidapi": {
        "name": "RapidAPI — List Agent APIs",
        "priority": 5,
        "time": "20 minutes + deployment",
        "steps": [
            "1. Go to https://rapidapi.com/auth/sign-up",
            "2. Create provider account",
            "3. Go to https://rapidapi.com/provider/dashboard",
            "4. Click 'My APIs' → 'Add New API'",
            "5. Name: 'DIGITAL LABOUR — AI Agents'",
            "6. Category: 'Artificial Intelligence'",
            "7. Generate OpenAPI spec: python -m api.rapidapi --spec > openapi.json",
            "8. Upload openapi.json to RapidAPI",
            "9. Set base URL to your deployed server",
            "10. Configure pricing: Free (5 calls/day), Pro ($20/mo), Enterprise ($100/mo)",
            "11. Set RAPIDAPI_SECRET in .env from RapidAPI dashboard",
            "12. Publish API listing",
        ],
        "url": "https://rapidapi.com/auth/sign-up",
        "requires": ["Deployed server with public URL", "OpenAPI spec (auto-generated)"],
    },
    "chatbase": {
        "name": "Chatbase — White-Label Bot Marketplace",
        "priority": 6,
        "time": "15 minutes",
        "steps": [
            "1. Go to https://www.chatbase.co/",
            "2. Sign up (free tier available)",
            "3. Create first bot: 'SaaS Support Bot' template",
            "4. Upload generic SaaS FAQ as training data",
            "5. Test the bot with 10 questions",
            "6. Create demo link to show prospects",
            "7. Add to service offerings on Fiverr/Freelancer",
            "8. Get templates: python -m income.platform_bots --chatbase",
        ],
        "url": "https://www.chatbase.co/",
        "requires": ["Email", "FAQ/docs for training data"],
    },
    "botpress": {
        "name": "Botpress — Managed Bot Service",
        "priority": 7,
        "time": "20 minutes",
        "steps": [
            "1. Go to https://botpress.com",
            "2. Sign up for Botpress Cloud (free PAYG)",
            "3. Create new bot → 'AI Agent' template",
            "4. Build multi-channel support flow",
            "5. Test all conversation paths",
            "6. Generate embed code for client sites",
            "7. Get templates: python -m income.platform_bots --botpress",
        ],
        "url": "https://botpress.com/",
        "requires": ["Email"],
    },
    "virtuals": {
        "name": "Virtuals Protocol — Agent Commerce Protocol",
        "priority": 8,
        "time": "1-2 hours",
        "steps": [
            "1. Go to https://app.virtuals.io",
            "2. Connect wallet (MetaMask on Base chain)",
            "3. Get VIRTUAL tokens (needed for agent registration)",
            "4. Go to Agent Builder → Create Agent",
            "5. Register 'DIGITAL LABOUR Sales Agent' with ACP capabilities",
            "6. Define service endpoints (point to your FastAPI server)",
            "7. Set pricing in USDC per task",
            "8. Deploy agent to Virtuals marketplace",
            "9. Monitor earnings in Virtuals dashboard",
        ],
        "url": "https://app.virtuals.io",
        "requires": ["MetaMask wallet", "Base chain ETH for gas", "VIRTUAL tokens", "Deployed API server"],
    },
    "agentverse": {
        "name": "Fetch.ai Agentverse — Register External Agent",
        "priority": 9,
        "time": "1-2 hours",
        "steps": [
            "1. Go to https://agentverse.ai",
            "2. Create account",
            "3. Go to 'My Agents' → 'Register External Agent'",
            "4. Provide agent endpoint URL",
            "5. Define agent capabilities (sales, support, content, extract)",
            "6. Set pricing per task",
            "7. Complete agent verification",
            "8. Publish to Agentverse marketplace",
        ],
        "url": "https://agentverse.ai",
        "requires": ["Account", "Deployed API endpoint", "Agent description"],
    },
    "olas": {
        "name": "Olas Network — Mech Marketplace",
        "priority": 10,
        "time": "2-4 hours",
        "steps": [
            "1. Go to https://build.olas.network/monetize",
            "2. Read: https://stack.olas.network/mech-server/",
            "3. Install Olas SDK: pip install open-aea",
            "4. Create Olas agent package (wrap existing agents)",
            "5. Register agent on Mech Marketplace",
            "6. Stake OLAS tokens for Dev Rewards",
            "7. Apply for grants: https://olas.network/build ($100K available per agent)",
            "8. Deploy sovereign agent",
        ],
        "url": "https://build.olas.network/monetize",
        "requires": ["Olas SDK", "OLAS tokens for staking", "Deployed agent code"],
    },
}


def print_registrations(filter_keys: list = None):
    """Print registration checklists."""
    items = REGISTRATIONS
    if filter_keys:
        items = {k: v for k, v in items.items() if k in filter_keys}

    print(f"\n{'='*70}")
    print("  PLATFORM REGISTRATION GUIDE")
    print(f"{'='*70}")

    for key, reg in sorted(items.items(), key=lambda x: x[1]["priority"]):
        print(f"\n{'─'*70}")
        print(f"  #{reg['priority']} {reg['name']}")
        print(f"  Time: {reg['time']} | URL: {reg['url']}")
        if reg.get("requires"):
            print(f"  Requires: {', '.join(reg['requires'])}")
        print(f"{'─'*70}")
        for step in reg["steps"]:
            print(f"    {step}")

    print(f"\n{'='*70}\n")


def print_quick_wins():
    """Print only quick-win registrations (priority 1-7)."""
    quick = {k: v for k, v in REGISTRATIONS.items() if v["priority"] <= 7}
    print_registrations(list(quick.keys()))


def print_crypto():
    """Print only crypto agent platform registrations."""
    crypto = {k: v for k, v in REGISTRATIONS.items() if k in ("virtuals", "agentverse", "olas")}
    print_registrations(list(crypto.keys()))


def check_status():
    """Cross-reference with income tracker."""
    try:
        from income.tracker import _load_tracker
        data = _load_tracker()
        print(f"\n{'='*70}")
        print("  REGISTRATION STATUS CHECK")
        print(f"{'='*70}")
        for key in REGISTRATIONS:
            if key in data["sources"]:
                src = data["sources"][key]
                status = src["status"]
                icon = {"not_started": "[ ]", "researched": "[R]", "registered": "[*]",
                        "configured": "[C]", "active": "[A]", "earning": "[$]"}.get(status, "[?]")
                print(f"  {icon} {REGISTRATIONS[key]['name']}")
            elif key == "stripe_live":
                # Special case — check via stripe_direct
                src = data["sources"].get("stripe_direct", {})
                icon = "[C]" if src.get("status") == "configured" else "[ ]"
                print(f"  {icon} {REGISTRATIONS[key]['name']}")
        print(f"{'='*70}\n")
    except Exception as e:
        print(f"[CHECK] Could not load tracker: {e}")
        print("  Run: python -m income.tracker  (to initialize)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Platform Registration Guide")
    parser.add_argument("--quick", action="store_true", help="Quick wins only")
    parser.add_argument("--crypto", action="store_true", help="Crypto platforms only")
    parser.add_argument("--check", action="store_true", help="Check registration status")
    args = parser.parse_args()

    if args.quick:
        print_quick_wins()
    elif args.crypto:
        print_crypto()
    elif args.check:
        check_status()
    else:
        print_registrations()
