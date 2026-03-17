"""Create Stripe subscription products and per-task prices for all retainer tiers.

Non-interactive — reads STRIPE_API_KEY from .env, creates products, saves IDs.

Usage:
    python -m billing.stripe_products --create   # create all products (idempotent)
    python -m billing.stripe_products --list     # list created products
    python -m billing.stripe_products --check    # verify all products exist in Stripe
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH  = PROJECT_ROOT / "data" / "stripe_products.json"

# ── Retainer products to create ───────────────────────────────────────────────
# Each entry maps to a Stripe Product + recurring Price

RETAINER_PRODUCTS = [
    {
        "key":         "sales_starter",
        "name":        "Digital Labour — Sales Starter",
        "description": "AI sales automation: 50 tasks/mo (outreach, lead gen, CRM ops)",
        "price_cents": 75000,      # $750/mo
        "tasks":       50,
        "overage_usd": 12.00,
    },
    {
        "key":         "sales_growth",
        "name":        "Digital Labour — Sales Growth",
        "description": "AI sales automation: 100 tasks/mo (outreach, lead gen, CRM ops)",
        "price_cents": 140000,     # $1 400/mo
        "tasks":       100,
        "overage_usd": 10.00,
    },
    {
        "key":         "sales_scale",
        "name":        "Digital Labour — Sales Scale",
        "description": "AI sales automation: 200 tasks/mo (outreach, lead gen, CRM ops)",
        "price_cents": 250000,     # $2 500/mo
        "tasks":       200,
        "overage_usd": 8.00,
    },
    {
        "key":         "support_starter",
        "name":        "Digital Labour — Support Starter",
        "description": "AI support automation: 200 tickets/mo (triage, resolve, escalate)",
        "price_cents": 40000,      # $400/mo
        "tasks":       200,
        "overage_usd": 1.50,
    },
    {
        "key":         "support_growth",
        "name":        "Digital Labour — Support Growth",
        "description": "AI support automation: 500 tickets/mo (triage, resolve, escalate)",
        "price_cents": 80000,      # $800/mo
        "tasks":       500,
        "overage_usd": 1.20,
    },
    {
        "key":         "support_scale",
        "name":        "Digital Labour — Support Scale",
        "description": "AI support automation: 1 000 tickets/mo (triage, resolve, escalate)",
        "price_cents": 140000,     # $1 400/mo
        "tasks":       1000,
        "overage_usd": 1.00,
    },
]

# Per-task pay-as-you-go products for top 5 agents
PER_TASK_PRODUCTS = [
    {"key": "payg_sales_outreach",   "name": "Digital Labour — Sales Outreach (per task)",     "price_cents": 240},
    {"key": "payg_support_ticket",   "name": "Digital Labour — Support Ticket (per task)",     "price_cents": 100},
    {"key": "payg_lead_gen",         "name": "Digital Labour — Lead Generation (per task)",    "price_cents": 300},
    {"key": "payg_market_research",  "name": "Digital Labour — Market Research (per task)",    "price_cents": 500},
    {"key": "payg_business_plan",    "name": "Digital Labour — Business Plan (per task)",      "price_cents": 800},
]


def _get_stripe_key() -> str:
    """Load STRIPE_API_KEY from .env."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("STRIPE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    key = os.environ.get("STRIPE_API_KEY", "")
    return key


def _stripe_import():
    """Import stripe or exit with helpful error."""
    try:
        import stripe  # noqa: PLC0415
        return stripe
    except ImportError:
        print("ERROR: stripe package not installed. Run: pip install stripe", file=sys.stderr)
        sys.exit(1)


def _load_existing() -> dict:
    """Load previously created product IDs from disk."""
    if OUTPUT_PATH.exists():
        try:
            return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def create_products(dry_run: bool = False) -> dict:
    """Create all retainer + per-task products in Stripe. Idempotent."""
    stripe = _stripe_import()
    key    = _get_stripe_key()
    if not key or not key.startswith("sk_"):
        print("ERROR: STRIPE_API_KEY not found or invalid in .env", file=sys.stderr)
        sys.exit(1)

    stripe.api_key = key
    mode = "TEST" if "test" in key else "LIVE"
    print(f"Stripe mode: {mode}")

    existing = _load_existing()
    result   = dict(existing)

    # ── Retainer subscriptions ────────────────────────────────────────────────
    for prod in RETAINER_PRODUCTS:
        key_name = f"retainer_{prod['key']}"
        if key_name in existing:
            print(f"  ✓ Skip  {prod['key']} (already exists: {existing[key_name]['product_id'][:20]}...)")
            continue

        if dry_run:
            print(f"  [DRY]  Would create {prod['key']}: ${prod['price_cents']/100:.0f}/mo")
            continue

        try:
            stripe_prod = stripe.Product.create(
                name        = prod["name"],
                description = prod["description"],
                metadata    = {
                    "tasks":       str(prod["tasks"]),
                    "overage_usd": str(prod["overage_usd"]),
                    "tier":        prod["key"],
                    "source":      "dl_stripe_products_py",
                },
            )
            stripe_price = stripe.Price.create(
                product    = stripe_prod["id"],
                unit_amount= prod["price_cents"],
                currency   = "usd",
                recurring  = {"interval": "month"},
                metadata   = {"tier": prod["key"]},
            )
            result[key_name] = {
                "product_id": stripe_prod["id"],
                "price_id":   stripe_price["id"],
                "name":       prod["name"],
                "amount_usd": prod["price_cents"] / 100,
                "tasks":      prod["tasks"],
                "overage_usd":prod["overage_usd"],
                "mode":       mode,
            }
            print(f"  ✓ Created {prod['key']}: {stripe_prod['id']} / price {stripe_price['id']}")
        except Exception as exc:
            print(f"  ✗ Failed {prod['key']}: {exc}", file=sys.stderr)

    # ── Per-task pay-as-you-go ────────────────────────────────────────────────
    for prod in PER_TASK_PRODUCTS:
        key_name = prod["key"]
        if key_name in existing:
            print(f"  ✓ Skip  {prod['key']} (already exists)")
            continue

        if dry_run:
            print(f"  [DRY]  Would create {prod['key']}: ${prod['price_cents']/100:.2f}/task")
            continue

        try:
            stripe_prod = stripe.Product.create(
                name     = prod["name"],
                metadata = {"task_key": prod["key"], "source": "dl_stripe_products_py"},
            )
            stripe_price = stripe.Price.create(
                product    = stripe_prod["id"],
                unit_amount= prod["price_cents"],
                currency   = "usd",
                metadata   = {"task_key": prod["key"]},
            )
            result[key_name] = {
                "product_id": stripe_prod["id"],
                "price_id":   stripe_price["id"],
                "name":       prod["name"],
                "amount_usd": prod["price_cents"] / 100,
                "mode":       mode,
            }
            print(f"  ✓ Created {prod['key']}: {stripe_prod['id']} / price {stripe_price['id']}")
        except Exception as exc:
            print(f"  ✗ Failed {prod['key']}: {exc}", file=sys.stderr)

    if not dry_run:
        _save(result)
        print(f"\nSaved {len(result)} products → {OUTPUT_PATH}")

    return result


def list_products() -> None:
    """Show all locally tracked products."""
    data = _load_existing()
    if not data:
        print("No products found. Run --create first.")
        return

    print(f"\n{'KEY':<30} {'PRODUCT ID':<30} {'PRICE ID':<30} {'AMOUNT':>10}")
    print("-" * 105)
    for key_name, info in sorted(data.items()):
        prod_id  = info.get("product_id", "—")[:28]
        price_id = info.get("price_id", "—")[:28]
        amount   = f"${info.get('amount_usd', 0):.2f}"
        tasks    = info.get("tasks", "")
        suffix   = f"/{tasks} tasks" if tasks else ""
        print(f"  {key_name:<28} {prod_id:<30} {price_id:<30} {amount+suffix:>15}")
    print(f"\nTotal: {len(data)} products")


def check_products() -> None:
    """Verify each locally tracked product still exists in Stripe."""
    stripe = _stripe_import()
    key    = _get_stripe_key()
    if not key:
        print("ERROR: STRIPE_API_KEY not found in .env", file=sys.stderr)
        sys.exit(1)
    stripe.api_key = key

    data = _load_existing()
    if not data:
        print("No products tracked locally. Run --create first.")
        return

    ok_count  = 0
    err_count = 0
    for key_name, info in sorted(data.items()):
        prod_id = info.get("product_id", "")
        try:
            prod = stripe.Product.retrieve(prod_id)
            active = prod.get("active", False)
            status = "ACTIVE" if active else "INACTIVE"
            print(f"  {'✓' if active else '!'} {key_name:<28} {status}")
            ok_count += 1
        except Exception as exc:
            print(f"  ✗ {key_name:<28} ERROR: {exc}", file=sys.stderr)
            err_count += 1

    print(f"\n{ok_count} OK, {err_count} errors")


def main() -> None:
    parser = argparse.ArgumentParser(description="Digital Labour — Stripe product setup")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create",   action="store_true", help="Create all Stripe products (idempotent)")
    group.add_argument("--list",     action="store_true", help="List locally tracked products")
    group.add_argument("--check",    action="store_true", help="Verify products exist in Stripe")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created without calling Stripe")
    args = parser.parse_args()

    if args.create:
        create_products(dry_run=args.dry_run)
    elif args.list:
        list_products()
    elif args.check:
        check_products()


if __name__ == "__main__":
    main()
