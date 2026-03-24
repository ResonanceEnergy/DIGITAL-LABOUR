"""Stripe Account Bootstrap — Guided setup wizard for Digital Labour payments.

Walks through:
    1. Validate Stripe API key
    2. Create products & prices for all task types + retainer tiers
    3. Create a webhook endpoint (for Stripe CLI local testing)
    4. Run a test checkout session
    5. Print summary and next steps

Usage:
    python -m billing.stripe_setup              # Full interactive setup
    python -m billing.stripe_setup --check      # Just check config status
    python -m billing.stripe_setup --products   # Create products only
    python -m billing.stripe_setup --test       # Run test checkout
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv, set_key
load_dotenv(PROJECT_ROOT / ".env")


# ── Console Helpers ────────────────────────────────────────────

def banner(text: str):
    w = max(len(text) + 4, 60)
    print(f"\n{'='*w}")
    print(f"  {text}")
    print(f"{'='*w}")

def ok(msg: str):
    print(f"  [OK]   {msg}")

def warn(msg: str):
    print(f"  [!!]   {msg}")

def fail(msg: str):
    print(f"  [FAIL] {msg}")

def info(msg: str):
    print(f"  [--]   {msg}")

def prompt(msg: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  > {msg}{suffix}: ").strip()
    return val or default


# ── Step 1: Validate API Key ──────────────────────────────────

def check_api_key() -> bool:
    """Validate the Stripe API key is set and functional."""
    banner("STEP 1 — Stripe API Key")

    key = os.getenv("STRIPE_API_KEY", "")
    if not key:
        fail("STRIPE_API_KEY is empty in .env")
        print()
        print("  You need a Stripe account to accept payments.")
        print()
        print("  HOW TO GET YOUR KEY:")
        print("  1. Go to https://dashboard.stripe.com/register")
        print("     - Email, full name, country, password")
        print("     - Verify your email")
        print()
        print("  2. Once logged in, go to:")
        print("     https://dashboard.stripe.com/test/apikeys")
        print()
        print("  3. Copy the 'Secret key' (starts with sk_test_)")
        print()
        print("  4. IMPORTANT: Do NOT use your publishable key (pk_)")
        print("     Only the SECRET key works server-side.")
        print()

        key = prompt("Paste your Stripe Secret Key here (sk_test_...)")
        if key and key.startswith("sk_"):
            env_path = PROJECT_ROOT / ".env"
            set_key(str(env_path), "STRIPE_API_KEY", key)
            os.environ["STRIPE_API_KEY"] = key
            ok(f"Key saved to .env ({'TEST' if 'test' in key else 'LIVE'} mode)")
        else:
            fail("Invalid key. Must start with sk_test_ or sk_live_")
            return False

    if not key.startswith("sk_"):
        fail(f"Key format invalid (starts with '{key[:5]}...'). Must start with sk_test_ or sk_live_")
        return False

    # Validate key by making a simple API call
    try:
        import stripe
        stripe.api_key = key
        account = stripe.Account.retrieve()
        ok(f"API key valid")
        ok(f"Account: {account.get('business_profile', {}).get('name', account.get('email', 'Unknown'))}")
        ok(f"Country: {account.get('country', '?')}")
        ok(f"Mode: {'TEST' if 'test' in key else 'LIVE'}")
        charges_enabled = account.get("charges_enabled", False)
        payouts_enabled = account.get("payouts_enabled", False)
        if charges_enabled:
            ok("Charges: ENABLED")
        else:
            warn("Charges: DISABLED — complete onboarding at https://dashboard.stripe.com/account/onboarding")
        if payouts_enabled:
            ok("Payouts: ENABLED")
        else:
            warn("Payouts: DISABLED — add bank details at https://dashboard.stripe.com/settings/payouts")
        return True
    except Exception as e:
        fail(f"API key validation failed: {e}")
        return False


# ── Step 2: Create Products ───────────────────────────────────

def create_products() -> dict:
    """Create Stripe products and prices for all DL services."""
    banner("STEP 2 — Create Products & Prices")

    from billing.payments import payments

    if not payments.configured:
        fail("Stripe not configured. Run step 1 first.")
        return {}

    # Check if already created
    from billing.payments import PRODUCTS_CACHE
    if PRODUCTS_CACHE.exists():
        products = json.loads(PRODUCTS_CACHE.read_text(encoding="utf-8"))
        ok(f"Products already exist: {len(products)} products cached")
        for name, ids in products.items():
            info(f"  {name}: prod={ids['product_id'][:20]}... price={ids['price_id'][:20]}...")
        return products

    info("Creating products in Stripe...")
    products = payments.ensure_products()

    if "error" in products:
        fail(f"Product creation failed: {products['error']}")
        return {}

    ok(f"Created {len(products)} products:")
    from billing.tracker import PRICING, RETAINER_TIERS
    for task_type, pricing in PRICING.items():
        if task_type in products:
            info(f"  {task_type}: ${pricing['per_task']}/task")
    for tier_name, tier in RETAINER_TIERS.items():
        key = f"retainer_{tier_name}"
        if key in products:
            info(f"  {tier_name}: ${tier['price']}/mo ({tier['tasks']} tasks)")

    return products


# ── Step 3: Webhook Setup ─────────────────────────────────────

def setup_webhook():
    """Guide webhook configuration."""
    banner("STEP 3 — Webhook Configuration")

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    if webhook_secret and webhook_secret.startswith("whsec_"):
        ok(f"Webhook secret is set (whsec_...{webhook_secret[-6:]})")
        return True

    print()
    print("  Webhooks let Stripe notify your server when payments complete.")
    print()
    print("  OPTION A — Local Testing (Stripe CLI):")
    print("  ─────────────────────────────────────────")
    print("  1. Install Stripe CLI:")
    print("     winget install Stripe.StripeCLI")
    print("     (or download from https://stripe.com/docs/stripe-cli)")
    print()
    print("  2. Login:")
    print("     stripe login")
    print()
    print("  3. Forward webhooks to your local server:")
    print("     stripe listen --forward-to http://127.0.0.1:8000/payments/webhook")
    print()
    print("  4. Copy the webhook signing secret (whsec_...) from the output")
    print()
    print("  OPTION B — Production (Stripe Dashboard):")
    print("  ──────────────────────────────────────────")
    print("  1. Go to https://dashboard.stripe.com/test/webhooks")
    print("  2. Click 'Add endpoint'")
    print("  3. URL: https://your-domain.com/payments/webhook")
    print("  4. Select events:")
    print("     - checkout.session.completed")
    print("     - invoice.paid")
    print("     - customer.subscription.created")
    print("     - customer.subscription.deleted")
    print("  5. Copy the signing secret")
    print()

    secret = prompt("Paste your webhook signing secret (whsec_...) or Enter to skip")
    if secret and secret.startswith("whsec_"):
        env_path = PROJECT_ROOT / ".env"
        set_key(str(env_path), "STRIPE_WEBHOOK_SECRET", secret)
        os.environ["STRIPE_WEBHOOK_SECRET"] = secret
        ok("Webhook secret saved to .env")
        return True
    else:
        warn("Webhook secret not set. Payment confirmations won't be processed.")
        warn("You can set it later in .env: STRIPE_WEBHOOK_SECRET=whsec_...")
        return False


# ── Step 4: Test Checkout ─────────────────────────────────────

def test_checkout():
    """Create a test checkout session to verify the pipeline."""
    banner("STEP 4 — Test Checkout")

    from billing.payments import payments

    if not payments.configured:
        fail("Stripe not configured. Complete setup first.")
        return

    info("Creating a test checkout session ($1.00)...")

    result = payments.create_checkout(
        client="dl-test",
        amount_cents=100,
        description="Digital Labour — Test Payment ($1.00)",
    )

    if "error" in result:
        fail(f"Checkout failed: {result['error']}")
        return

    ok(f"Checkout session created!")
    ok(f"Mode: {result.get('mode', '?')}")
    print()
    print(f"  Open this URL to complete the test payment:")
    print(f"  {result['checkout_url']}")
    print()
    print("  Use test card: 4242 4242 4242 4242")
    print("  Expiry: any future date | CVC: any 3 digits | ZIP: any 5 digits")
    print()

    return result


# ── Step 5: Business Details Guide ────────────────────────────

def business_setup_guide():
    """Print guide for completing Stripe business onboarding."""
    banner("STEP 5 — Business & Bank Details")

    print()
    print("  To receive real payouts, complete your Stripe account:")
    print()
    print("  1. BUSINESS DETAILS")
    print("     https://dashboard.stripe.com/settings/account")
    print("     - Business type: Individual / Sole Proprietor / Company")
    print("     - Business name: Digital Labour (or your legal name)")
    print("     - Country, address, phone")
    print()
    print("  2. BANK ACCOUNT (for payouts)")
    print("     https://dashboard.stripe.com/settings/payouts")
    print("     - Add your bank account for receiving payments")
    print("     - Stripe pays out on a rolling schedule (2-7 business days)")
    print()
    print("  3. TAX INFORMATION")
    print("     https://dashboard.stripe.com/settings/tax")
    print("     - Social Security Number (US) or Tax ID")
    print("     - Required for 1099 reporting above $600/year")
    print()
    print("  4. BRANDING")
    print("     https://dashboard.stripe.com/settings/branding")
    print("     - Company name on receipts: 'Digital Labour'")
    print("     - Support email, icon, accent color (#00ff88)")
    print()
    print("  5. GO LIVE")
    print("     When ready to accept real payments:")
    print("     - Get LIVE keys from https://dashboard.stripe.com/apikeys")
    print("     - Replace sk_test_ with sk_live_ in .env")
    print("     - Create a production webhook endpoint")
    print()


# ── Summary ───────────────────────────────────────────────────

def print_summary():
    """Print current configuration summary."""
    banner("CONFIGURATION SUMMARY")

    from billing.payments import payments, PRODUCTS_CACHE

    key = os.getenv("STRIPE_API_KEY", "")
    webhook = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    items = [
        ("API Key", "SET" if key.startswith("sk_") else "NOT SET", key.startswith("sk_")),
        ("Mode", "TEST" if "test" in key else ("LIVE" if "live" in key else "N/A"), bool(key)),
        ("Webhook Secret", "SET" if webhook.startswith("whsec_") else "NOT SET", webhook.startswith("whsec_")),
        ("Products Created", str(len(json.loads(PRODUCTS_CACHE.read_text(encoding="utf-8")))) if PRODUCTS_CACHE.exists() else "0", PRODUCTS_CACHE.exists()),
        ("Gateway Configured", str(payments.configured), payments.configured),
    ]

    for label, value, good in items:
        fn = ok if good else warn
        fn(f"{label}: {value}")

    print()
    print("  API Endpoints:")
    print("  ──────────────")
    print("  POST /payments/checkout     — Create one-time payment")
    print("  POST /payments/subscribe    — Create retainer subscription")
    print("  POST /payments/webhook      — Stripe webhook receiver")
    print("  GET  /payments/status/{id}  — Payment status")
    print("  GET  /payments/gateway      — Gateway health")
    print("  POST /signup                — Client self-registration")
    print("  GET  /signup                — Signup web form")
    print("  GET  /invoice/{client}      — Generate invoice PDF")
    print()

    gateway = payments.gateway_status()
    info(f"Pending: {gateway['pending_payments']} | Paid: {gateway['completed_payments']} | Subs: {gateway['active_subscriptions']}")


# ── Full Setup ────────────────────────────────────────────────

def full_setup():
    """Run the complete setup wizard."""
    banner("Digital Labour — STRIPE PAYMENT SETUP")
    print("  This wizard will configure Stripe for payment collection.")
    print("  You'll need a Stripe account (free to create).")
    print()

    # Step 1 — API Key
    if not check_api_key():
        print("\n  Fix the API key issue and run again.")
        return

    # Step 2 — Products
    products = create_products()

    # Step 3 — Webhooks
    setup_webhook()

    # Step 4 — Test
    print()
    do_test = prompt("Run a test checkout? (y/n)", "y")
    if do_test.lower() in ("y", "yes"):
        test_checkout()

    # Step 5 — Business guide
    business_setup_guide()

    # Summary
    print_summary()

    banner("SETUP COMPLETE")
    print("  Your payment pipeline is ready.")
    print("  Start the API server: python -m api.intake")
    print("  Signup page: http://127.0.0.1:8000/signup")
    print("  Gateway health: http://127.0.0.1:8000/payments/gateway")
    print()


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stripe Setup Wizard for Digital Labour")
    parser.add_argument("--check", action="store_true", help="Check config status only")
    parser.add_argument("--products", action="store_true", help="Create products only")
    parser.add_argument("--test", action="store_true", help="Run test checkout only")
    parser.add_argument("--guide", action="store_true", help="Show business setup guide")
    args = parser.parse_args()

    if args.check:
        check_api_key()
        print_summary()
    elif args.products:
        create_products()
    elif args.test:
        test_checkout()
    elif args.guide:
        business_setup_guide()
    else:
        full_setup()
