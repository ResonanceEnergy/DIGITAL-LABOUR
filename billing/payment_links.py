"""Stripe Payment Links — Generate shareable buy-now URLs for all products.

Creates Stripe Payment Links for every product in stripe_products.json.
Links can be embedded on the website, shared in emails, or posted on platforms.

Usage:
    python -m billing.payment_links              # Create all payment links
    python -m billing.payment_links --list       # List existing links
    python -m billing.payment_links --html       # Generate embeddable HTML snippet
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

PRODUCTS_FILE = PROJECT_ROOT / "data" / "stripe_products.json"
LINKS_FILE = PROJECT_ROOT / "data" / "stripe_payment_links.json"


def load_products() -> dict:
    if not PRODUCTS_FILE.exists():
        print("[LINKS] No stripe_products.json found. Run billing.stripe_setup first.")
        return {}
    return json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))


def create_payment_links() -> dict:
    """Create Stripe Payment Links for all products."""
    try:
        import stripe
    except ImportError:
        print("[LINKS] stripe package not installed. Run: pip install stripe")
        return {}

    api_key = os.getenv("STRIPE_API_KEY", "")
    if not api_key or not api_key.startswith("sk_"):
        print("[LINKS] STRIPE_API_KEY not configured or invalid.")
        return {}

    stripe.api_key = api_key
    mode = "TEST" if "test" in api_key else "LIVE"
    print(f"[LINKS] Creating payment links ({mode} mode)...\n")

    products = load_products()
    if not products:
        return {}

    links = {}
    for key, product in products.items():
        price_id = product.get("price_id", "")
        if not price_id:
            print(f"  [SKIP] {key} — no price_id")
            continue

        try:
            link = stripe.PaymentLink.create(
                line_items=[{"price": price_id, "quantity": 1}],
                after_completion={
                    "type": "redirect",
                    "redirect": {"url": "https://bit-rage-labour.com?thanks=1"},
                },
                metadata={"product_key": key, "source": "digital_labour"},
            )
            links[key] = {
                "url": link.url,
                "link_id": link.id,
                "product_name": product["name"],
                "cents": product["cents"],
                "mode": product["mode"],
                "stripe_mode": mode.lower(),
            }
            price_str = f"${product['cents']/100:.2f}"
            freq = "/mo" if product["mode"] == "recurring" else ""
            print(f"  [OK] {product['name']} — {price_str}{freq}")
            print(f"        {link.url}")
        except Exception as e:
            print(f"  [FAIL] {key}: {e}")

    # Save links
    LINKS_FILE.write_text(json.dumps(links, indent=2), encoding="utf-8")
    print(f"\n[LINKS] Created {len(links)} payment links → {LINKS_FILE.name}")
    return links


def load_links() -> dict:
    if not LINKS_FILE.exists():
        return {}
    return json.loads(LINKS_FILE.read_text(encoding="utf-8"))


def list_links():
    """Print all existing payment links."""
    links = load_links()
    if not links:
        print("[LINKS] No payment links found. Run: python -m billing.payment_links")
        return
    print(f"\n{'='*70}")
    print("  STRIPE PAYMENT LINKS")
    print(f"{'='*70}")
    for key, link in links.items():
        price = f"${link['cents']/100:.2f}"
        freq = "/mo" if link["mode"] == "recurring" else ""
        mode_badge = f"[{link.get('stripe_mode', 'test').upper()}]"
        print(f"  {mode_badge} {link['product_name']}")
        print(f"         {price}{freq} — {link['url']}")
    print(f"{'='*70}\n")


def generate_html_buttons() -> str:
    """Generate embeddable HTML for payment link buttons."""
    links = load_links()
    if not links:
        return "<!-- No payment links available -->"

    # Group by type
    per_task = {k: v for k, v in links.items() if v["mode"] == "one_time"}
    retainers = {k: v for k, v in links.items() if v["mode"] == "recurring"}

    html_parts = []

    # Per-task buttons
    if per_task:
        html_parts.append('<div class="payment-links-grid">')
        for key, link in per_task.items():
            price = f"${link['cents']/100:.2f}"
            html_parts.append(f'''  <a href="{link['url']}" target="_blank" class="btn btn-primary btn-sm pay-link" data-product="{key}">
    {link['product_name']} — {price}
  </a>''')
        html_parts.append('</div>')

    # Retainer buttons
    if retainers:
        html_parts.append('<div class="payment-links-grid retainers">')
        for key, link in retainers.items():
            price = f"${link['cents']/100:.2f}/mo"
            html_parts.append(f'''  <a href="{link['url']}" target="_blank" class="btn btn-secondary btn-sm pay-link" data-product="{key}">
    {link['product_name']} — {price}
  </a>''')
        html_parts.append('</div>')

    return "\n".join(html_parts)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Stripe Payment Links")
    parser.add_argument("--list", action="store_true", help="List existing links")
    parser.add_argument("--html", action="store_true", help="Generate HTML buttons")
    args = parser.parse_args()

    if args.list:
        list_links()
    elif args.html:
        print(generate_html_buttons())
    else:
        create_payment_links()
