"""Client intake form — interactive CLI for onboarding new retainer clients.

Usage:
    python -m billing.intake_form
    python billing/intake_form.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from billing.tracker import BillingTracker, RETAINER_TIERS

OUTPUT_DIR = PROJECT_ROOT / "clients"


def run_intake() -> dict:
    """Interactive intake questionnaire. Returns client profile dict."""
    print("\n" + "=" * 60)
    print("  BIT RAGE LABOUR — New Client Intake")
    print("=" * 60 + "\n")

    # Basic info
    client_id = input("Client ID (short, no spaces): ").strip().lower()
    if not client_id:
        print("Client ID required.")
        return {}
    company = input("Company name: ").strip()
    contact = input("Primary contact name: ").strip()
    email = input("Contact email: ").strip()

    # Service selection
    print("\nAvailable services:")
    print("  1. Sales Outreach (AI lead enrichment + cold email)")
    print("  2. Support Resolution (AI ticket triage + response)")
    print("  3. Content Repurpose (blog → social + email + threads)")
    print("  4. Document Extraction (PDF/docs → structured data)")
    print("  5. Multiple services")
    service_choice = input("Select service(s) [1-5]: ").strip()

    services = []
    service_map = {"1": "sales_outreach", "2": "support_ticket", "3": "content_repurpose", "4": "doc_extract"}
    if service_choice == "5":
        subs = input("Enter numbers separated by commas (e.g. 1,2): ").strip()
        for s in subs.split(","):
            s = s.strip()
            if s in service_map:
                services.append(service_map[s])
    elif service_choice in service_map:
        services.append(service_map[service_choice])

    # Pricing model
    print("\nPricing model:")
    print("  1. Pay-per-task")
    print("  2. Monthly retainer")
    pricing = input("Select [1-2]: ").strip()

    retainer = ""
    if pricing == "2":
        print("\nRetainer tiers:")
        for i, (name, tier) in enumerate(RETAINER_TIERS.items(), 1):
            print(f"  {i}. {name}: ${tier['price']}/mo — {tier['tasks']} {tier['type']} tasks, ${tier['overage']}/overage")
        tier_choice = input(f"Select tier [1-{len(RETAINER_TIERS)}]: ").strip()
        tier_list = list(RETAINER_TIERS.keys())
        idx = int(tier_choice) - 1 if tier_choice.isdigit() else -1
        if 0 <= idx < len(tier_list):
            retainer = tier_list[idx]

    # Volume
    monthly_volume = input("\nEstimated monthly task volume: ").strip()

    # Special requirements
    special = input("Any special requirements or notes: ").strip()

    # Provider preference
    print("\nPreferred LLM provider (affects speed/quality):")
    print("  1. OpenAI (fastest, recommended)")
    print("  2. Anthropic (best nuance)")
    print("  3. Gemini (cheapest)")
    print("  4. Grok (fast alternative)")
    print("  5. Auto (best available)")
    prov_choice = input("Select [1-5]: ").strip()
    prov_map = {"1": "openai", "2": "anthropic", "3": "gemini", "4": "grok", "5": ""}
    provider = prov_map.get(prov_choice, "")

    # Delivery
    print("\nDelivery method:")
    print("  1. File export (JSON/CSV)")
    print("  2. Email")
    print("  3. Webhook (POST to your URL)")
    del_choice = input("Select [1-3]: ").strip()
    del_map = {"1": "file", "2": "email", "3": "webhook"}
    delivery = del_map.get(del_choice, "file")
    delivery_dest = ""
    if delivery == "email":
        delivery_dest = input("Delivery email: ").strip()
    elif delivery == "webhook":
        delivery_dest = input("Webhook URL: ").strip()

    # Build profile
    profile = {
        "client_id": client_id,
        "company": company,
        "contact": contact,
        "email": email,
        "services": services,
        "pricing": "retainer" if retainer else "per_task",
        "retainer_tier": retainer,
        "monthly_volume": monthly_volume,
        "provider": provider,
        "delivery_method": delivery,
        "delivery_destination": delivery_dest,
        "special_requirements": special,
        "onboarded_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }

    # Save to file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / f"{client_id}.json"
    filepath.write_text(json.dumps(profile, indent=2), encoding="utf-8")

    # Register in billing
    bt = BillingTracker()
    bt.add_client(client_id, name=company, email=email, retainer=retainer)

    print(f"\n✓ Client '{client_id}' onboarded successfully!")
    print(f"  Profile saved: {filepath}")
    print(f"  Services: {', '.join(services)}")
    if retainer:
        tier = RETAINER_TIERS[retainer]
        print(f"  Retainer: {retainer} — ${tier['price']}/mo")
    print()

    return profile


if __name__ == "__main__":
    run_intake()
