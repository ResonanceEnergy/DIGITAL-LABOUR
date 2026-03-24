"""Income Tracker — Monitors revenue across all 19 income sources.

Persistent tracking of:
    - Platform registration status (not_started → registered → active → earning)
    - Revenue per source (daily/weekly/monthly)
    - Total revenue across all channels
    - Action items and next steps

Usage:
    python -m income.tracker                    # Full status report
    python -m income.tracker --update SOURCE STATUS  # Update source status
    python -m income.tracker --revenue SOURCE AMOUNT # Log revenue
    python -m income.tracker --summary          # Quick summary
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TRACKER_FILE = PROJECT_ROOT / "data" / "income_tracker.json"

# Valid statuses in order of progression
STATUSES = ["not_started", "researched", "registered", "configured", "active", "earning"]


def _load_tracker() -> dict:
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
    return _init_tracker()


def _save_tracker(data: dict):
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _init_tracker() -> dict:
    """Initialize tracker with all 19 income sources."""
    sources = {
        # Tier 1 — Direct / Quick
        "stripe_direct": {"name": "Stripe Direct Sales", "category": "direct", "status": "configured", "revenue_total": 0, "revenue_log": [], "url": "https://dashboard.stripe.com", "notes": "10 products created. Test mode."},
        "freelancer": {"name": "Freelancer.com", "category": "freelance", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://freelancer.com", "notes": "21 active AI agent jobs"},
        "fiverr": {"name": "Fiverr AI Services", "category": "freelance", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://fiverr.com", "notes": "4 gigs ready to post"},
        "email_outreach": {"name": "Email Outreach", "category": "direct", "status": "configured", "revenue_total": 0, "revenue_log": [], "url": "", "notes": "50 enriched prospects. Zoho SMTP ready."},

        # Tier 2 — Crypto Agent Economy
        "virtuals": {"name": "Virtuals Protocol ACP", "category": "crypto_agent", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://virtuals.io", "notes": "$479M aGDP, $3.3M agent revenue"},
        "agentverse": {"name": "Fetch.ai Agentverse", "category": "crypto_agent", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://agentverse.ai", "notes": "2.7M agents registered"},
        "olas": {"name": "Olas Network", "category": "crypto_agent", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://build.olas.network/monetize", "notes": "$1M grants, 62 builders"},
        "elizaos": {"name": "ElizaOS / Eliza Cloud", "category": "crypto_agent", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://elizaos.ai", "notes": "90+ plugins, 2-command deploy"},
        "singularitynet": {"name": "SingularityNET", "category": "crypto_agent", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://singularitynet.io", "notes": "ASI token, DEEP Funding"},
        "morpheus": {"name": "Morpheus Network", "category": "crypto_agent", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://mor.org", "notes": "320K+ staked ETH, MOR rewards"},

        # Tier 3 — Platform Marketplace
        "chatbase": {"name": "Chatbase White-Label", "category": "platform", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://chatbase.co", "notes": "Free tier. White-label bots."},
        "botpress": {"name": "Botpress Managed", "category": "platform", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://botpress.com", "notes": "Free PAYG tier."},
        "relevance_ai": {"name": "Relevance AI", "category": "platform", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://relevanceai.com", "notes": "Used by Canva, Databricks"},
        "zapier": {"name": "Zapier Agents", "category": "platform", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://zapier.com", "notes": "2.2M companies"},

        # Tier 4 — DeFi
        "wayfinder": {"name": "Wayfinder DeFi", "category": "defi", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://wayfinder.ai", "notes": "$PROMPT token rewards"},
        "xrp_ledger": {"name": "XRP Ledger Agents", "category": "defi", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://xrpl.org", "notes": "Low fees, fast settlement"},

        # Tier 5 — Enterprise / API
        "upwork": {"name": "Upwork Premium", "category": "freelance", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://upwork.com", "notes": "$50-200/hr for AI agent dev"},
        "consulting": {"name": "Direct Consulting", "category": "enterprise", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "", "notes": "$2K setup + $750/mo retainer"},
        "rapidapi": {"name": "RapidAPI Hub", "category": "api_marketplace", "status": "not_started", "revenue_total": 0, "revenue_log": [], "url": "https://rapidapi.com", "notes": "30M+ developers"},
    }

    data = {
        "created": datetime.now(timezone.utc).isoformat(),
        "updated": datetime.now(timezone.utc).isoformat(),
        "total_revenue": 0,
        "sources": sources,
    }
    _save_tracker(data)
    return data


def update_status(source_key: str, new_status: str, notes: str = ""):
    """Update the status of an income source."""
    if new_status not in STATUSES:
        print(f"[TRACKER] Invalid status '{new_status}'. Valid: {STATUSES}")
        return

    data = _load_tracker()
    if source_key not in data["sources"]:
        print(f"[TRACKER] Unknown source '{source_key}'. Valid keys:")
        for k in sorted(data["sources"]):
            print(f"  - {k}")
        return

    old_status = data["sources"][source_key]["status"]
    data["sources"][source_key]["status"] = new_status
    if notes:
        data["sources"][source_key]["notes"] = notes
    data["updated"] = datetime.now(timezone.utc).isoformat()
    _save_tracker(data)
    print(f"[TRACKER] {source_key}: {old_status} → {new_status}")


def log_revenue(source_key: str, amount: float, description: str = ""):
    """Log revenue from a source."""
    data = _load_tracker()
    if source_key not in data["sources"]:
        print(f"[TRACKER] Unknown source '{source_key}'")
        return

    entry = {
        "amount": amount,
        "date": datetime.now(timezone.utc).isoformat(),
        "description": description,
    }
    data["sources"][source_key]["revenue_log"].append(entry)
    data["sources"][source_key]["revenue_total"] += amount
    data["sources"][source_key]["status"] = "earning"
    data["total_revenue"] += amount
    data["updated"] = datetime.now(timezone.utc).isoformat()
    _save_tracker(data)
    print(f"[TRACKER] +${amount:.2f} from {source_key} (total: ${data['total_revenue']:.2f})")


def print_status():
    """Print full income tracker status."""
    data = _load_tracker()
    sources = data["sources"]

    # Group by category
    categories = {}
    for key, src in sources.items():
        cat = src["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, src))

    status_icons = {
        "not_started": "[ ]",
        "researched": "[R]",
        "registered": "[*]",
        "configured": "[C]",
        "active": "[A]",
        "earning": "[$]",
    }

    total = data["total_revenue"]
    earning_count = sum(1 for s in sources.values() if s["status"] == "earning")
    active_count = sum(1 for s in sources.values() if s["status"] in ("active", "earning"))
    registered_count = sum(1 for s in sources.values() if s["status"] in ("registered", "configured", "active", "earning"))

    print(f"""
{'='*70}
  BIT RAGE SYSTEMS — INCOME TRACKER
{'='*70}
  Total Revenue:   ${total:,.2f}
  Sources Earning: {earning_count}/19
  Sources Active:  {active_count}/19
  Registered:      {registered_count}/19
  Updated:         {data.get('updated', 'N/A')[:19]}
{'='*70}""")

    cat_names = {
        "direct": "DIRECT SALES",
        "freelance": "FREELANCE PLATFORMS",
        "crypto_agent": "CRYPTO AGENT ECONOMY",
        "platform": "PLATFORM MARKETPLACE",
        "defi": "DEFI / PASSIVE",
        "enterprise": "ENTERPRISE B2B",
        "api_marketplace": "API MARKETPLACE",
    }

    for cat, items in categories.items():
        cat_revenue = sum(s["revenue_total"] for _, s in items)
        print(f"\n  {cat_names.get(cat, cat.upper())} (${cat_revenue:,.2f})")
        print(f"  {'─'*66}")
        for key, src in items:
            icon = status_icons.get(src["status"], "[?]")
            rev = f"${src['revenue_total']:,.2f}" if src["revenue_total"] > 0 else ""
            print(f"    {icon} {src['name']:<35} {rev:>12}  {src['notes'][:30]}")

    print(f"\n{'='*70}")
    print("  Legend: [ ]=Not Started  [R]=Researched  [*]=Registered")
    print("          [C]=Configured   [A]=Active      [$]=Earning")
    print(f"{'='*70}\n")


def print_summary():
    """Quick one-line summary."""
    data = _load_tracker()
    total = data["total_revenue"]
    earning = sum(1 for s in data["sources"].values() if s["status"] == "earning")
    active = sum(1 for s in data["sources"].values() if s["status"] in ("active", "earning"))
    print(f"[INCOME] ${total:,.2f} total | {earning} earning | {active} active | 19 sources")


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Income Source Tracker")
    parser.add_argument("--update", nargs=2, metavar=("SOURCE", "STATUS"), help="Update source status")
    parser.add_argument("--revenue", nargs=2, metavar=("SOURCE", "AMOUNT"), help="Log revenue")
    parser.add_argument("--summary", action="store_true", help="Quick summary")
    parser.add_argument("--notes", default="", help="Notes for --update")
    parser.add_argument("--desc", default="", help="Description for --revenue")
    parser.add_argument("--auto", action="store_true", help="Run auto-registration prep + status")
    args = parser.parse_args()

    if args.update:
        update_status(args.update[0], args.update[1], args.notes)
    elif args.revenue:
        log_revenue(args.revenue[0], float(args.revenue[1]), args.desc)
    elif args.summary:
        print_summary()
    elif args.auto:
        from income.auto_register import show_status as auto_status, prepare_all
        prepare_all()
        auto_status()
    else:
        print_status()
