"""Stripe Payment Gateway — Handles checkout, subscriptions, and webhooks.

Connects DIGITAL LABOUR billing to Stripe for real payment collection.

Setup:
    1. Create Stripe account at https://stripe.com
    2. Get API keys from https://dashboard.stripe.com/apikeys
    3. Set in .env:
       STRIPE_API_KEY=sk_live_...       (or sk_test_... for testing)
       STRIPE_WEBHOOK_SECRET=whsec_...  (from Stripe webhook settings)
    4. Create webhook endpoint in Stripe dashboard pointing to:
       https://your-domain.com/payments/webhook
       Events: checkout.session.completed, invoice.paid, customer.subscription.created

Usage:
    from billing.payments import payments

    # Create checkout for a single invoice
    url = payments.create_checkout("acme-corp", amount=2400, description="100 sales tasks")

    # Create retainer subscription
    url = payments.create_subscription("acme-corp", tier="sales_growth")

    # Check payment status
    status = payments.payment_status("acme-corp")
"""

import hashlib
import hmac
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

DB_PATH = PROJECT_ROOT / "data" / "payments.db"

# Stripe product IDs — created on first run, cached locally
PRODUCTS_CACHE = PROJECT_ROOT / "data" / "stripe_products.json"


class PaymentGateway:
    """Stripe payment integration for Digital Labour."""

    def __init__(self):
        self.api_key = os.getenv("STRIPE_API_KEY", "")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self._stripe = None
        self._init_db()

    @property
    def configured(self) -> bool:
        """Check if Stripe API key is set."""
        return bool(self.api_key and self.api_key.startswith("sk_"))

    @property
    def is_test_mode(self) -> bool:
        """Check if using test keys."""
        return self.api_key.startswith("sk_test_")

    def _get_stripe(self):
        """Lazy-load stripe module."""
        if self._stripe is None:
            import stripe
            stripe.api_key = self.api_key
            self._stripe = stripe
        return self._stripe

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS payments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                client          TEXT NOT NULL,
                stripe_session  TEXT DEFAULT '',
                stripe_customer TEXT DEFAULT '',
                amount_cents    INTEGER DEFAULT 0,
                currency        TEXT DEFAULT 'usd',
                status          TEXT DEFAULT 'pending',
                payment_type    TEXT DEFAULT 'one_time',
                description     TEXT DEFAULT '',
                created_at      TEXT NOT NULL,
                completed_at    TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                client          TEXT NOT NULL,
                stripe_sub_id   TEXT DEFAULT '',
                stripe_customer TEXT DEFAULT '',
                tier            TEXT NOT NULL,
                price_cents     INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'pending',
                created_at      TEXT NOT NULL,
                cancelled_at    TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_pay_client ON payments(client);
            CREATE INDEX IF NOT EXISTS idx_sub_client ON subscriptions(client);
        """)
        conn.commit()
        conn.close()

    # ── Stripe Product Setup ────────────────────────────────────

    def _load_products(self) -> dict:
        if PRODUCTS_CACHE.exists():
            return json.loads(PRODUCTS_CACHE.read_text(encoding="utf-8"))
        return {}

    def _save_products(self, products: dict):
        PRODUCTS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        PRODUCTS_CACHE.write_text(json.dumps(products, indent=2), encoding="utf-8")

    def ensure_products(self) -> dict:
        """Create Stripe products/prices if they don't exist yet."""
        if not self.configured:
            return {"error": "Stripe not configured"}

        products = self._load_products()
        if products:
            return products

        stripe = self._get_stripe()
        from billing.tracker import PRICING, RETAINER_TIERS

        # Per-task products
        for task_type, pricing in PRICING.items():
            product = stripe.Product.create(
                name=f"Digital Labour — {task_type.replace('_', ' ').title()}",
                description=f"AI-powered {task_type.replace('_', ' ')} task",
            )
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(pricing["per_task"] * 100),
                currency="usd",
            )
            products[task_type] = {"product_id": product.id, "price_id": price.id}

        # Retainer subscription products
        for tier_name, tier in RETAINER_TIERS.items():
            product = stripe.Product.create(
                name=f"Digital Labour — {tier_name.replace('_', ' ').title()} Retainer",
                description=f"{tier['tasks']} {tier['type'].replace('_', ' ')} tasks/month",
            )
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(tier["price"] * 100),
                currency="usd",
                recurring={"interval": "month"},
            )
            products[f"retainer_{tier_name}"] = {"product_id": product.id, "price_id": price.id}

        self._save_products(products)
        logger.info(f"Created {len(products)} Stripe products")
        return products

    # ── Get/Create Stripe Customer ──────────────────────────────

    def _get_or_create_customer(self, client: str, email: str = "") -> str:
        """Get existing Stripe customer or create new one."""
        stripe = self._get_stripe()

        # Check local DB first
        conn = self._conn()
        row = conn.execute(
            "SELECT stripe_customer FROM payments WHERE client = ? AND stripe_customer != '' LIMIT 1",
            (client,)
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT stripe_customer FROM subscriptions WHERE client = ? AND stripe_customer != '' LIMIT 1",
                (client,)
            ).fetchone()
        conn.close()

        if row and row["stripe_customer"]:
            return row["stripe_customer"]

        # Look up client email from billing DB if not provided
        if not email:
            from billing.tracker import BillingTracker
            bt = BillingTracker()
            bt_conn = bt._conn()
            client_row = bt_conn.execute("SELECT email FROM clients WHERE client = ?", (client,)).fetchone()
            bt_conn.close()
            email = client_row["email"] if client_row else f"{client}@clients.bit-rage-labour.com"

        customer = stripe.Customer.create(
            name=client,
            email=email,
            metadata={"dl_client_id": client},
        )
        return customer.id

    # ── Checkout (One-Time Payment) ─────────────────────────────

    def create_checkout(
        self, client: str, amount_cents: int, description: str = "",
        success_url: str = "", cancel_url: str = ""
    ) -> dict:
        """Create a Stripe Checkout session for one-time payment."""
        if not self.configured:
            return {"error": "Stripe not configured. Set STRIPE_API_KEY in .env"}

        stripe = self._get_stripe()
        customer_id = self._get_or_create_customer(client)

        if not success_url:
            success_url = "http://127.0.0.1:8000/payments/success?session_id={CHECKOUT_SESSION_ID}"
        if not cancel_url:
            cancel_url = "http://127.0.0.1:8000/payments/cancel"

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "product_data": {"name": description or f"Digital Labour Invoice — {client}"},
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"dl_client_id": client},
        )

        # Record in DB
        conn = self._conn()
        conn.execute(
            """INSERT INTO payments (client, stripe_session, stripe_customer, amount_cents,
               currency, status, payment_type, description, created_at)
               VALUES (?, ?, ?, ?, 'usd', 'pending', 'one_time', ?, ?)""",
            (client, session.id, customer_id, amount_cents,
             description, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "amount": amount_cents / 100,
            "client": client,
            "mode": "test" if self.is_test_mode else "live",
        }

    # ── Subscription (Retainer) ─────────────────────────────────

    def create_subscription(self, client: str, tier: str, email: str = "") -> dict:
        """Create a Stripe subscription for a retainer tier."""
        if not self.configured:
            return {"error": "Stripe not configured. Set STRIPE_API_KEY in .env"}

        from billing.tracker import RETAINER_TIERS
        if tier not in RETAINER_TIERS:
            return {"error": f"Unknown tier: {tier}. Options: {list(RETAINER_TIERS.keys())}"}

        products = self.ensure_products()
        price_key = f"retainer_{tier}"
        if price_key not in products:
            return {"error": f"Stripe product not created for tier: {tier}"}

        stripe = self._get_stripe()
        customer_id = self._get_or_create_customer(client, email=email)
        tier_data = RETAINER_TIERS[tier]

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": products[price_key]["price_id"], "quantity": 1}],
            mode="subscription",
            success_url="http://127.0.0.1:8000/payments/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://127.0.0.1:8000/payments/cancel",
            metadata={"dl_client_id": client, "tier": tier},
        )

        # Record in DB
        conn = self._conn()
        conn.execute(
            """INSERT INTO subscriptions (client, stripe_sub_id, stripe_customer, tier,
               price_cents, status, created_at)
               VALUES (?, '', ?, ?, ?, 'pending', ?)""",
            (client, customer_id, tier, int(tier_data["price"] * 100),
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "tier": tier,
            "monthly_price": tier_data["price"],
            "client": client,
            "mode": "test" if self.is_test_mode else "live",
        }

    # ── Webhook Handler ─────────────────────────────────────────

    def handle_webhook(self, payload: bytes, sig_header: str) -> dict:
        """Process incoming Stripe webhook event."""
        stripe = self._get_stripe()

        # Verify signature
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)
        except (ValueError, stripe.error.SignatureVerificationError):
            return {"error": "Invalid webhook signature"}

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            return self._handle_checkout_completed(data)
        elif event_type == "invoice.paid":
            return self._handle_invoice_paid(data)
        elif event_type == "customer.subscription.created":
            return self._handle_subscription_created(data)
        elif event_type == "customer.subscription.deleted":
            return self._handle_subscription_cancelled(data)

        return {"status": "ignored", "event_type": event_type}

    def _handle_checkout_completed(self, session: dict) -> dict:
        """Mark payment as completed."""
        session_id = session.get("id", "")
        client = session.get("metadata", {}).get("dl_client_id", "")
        now = datetime.now(timezone.utc).isoformat()

        conn = self._conn()
        conn.execute(
            "UPDATE payments SET status = 'paid', completed_at = ? WHERE stripe_session = ?",
            (now, session_id),
        )

        # If it was a subscription checkout, update subscription too
        sub_id = session.get("subscription", "")
        if sub_id:
            conn.execute(
                "UPDATE subscriptions SET stripe_sub_id = ?, status = 'active' WHERE client = ? AND status = 'pending'",
                (sub_id, client),
            )

        # Update billing tracker — mark invoice as paid
        try:
            from billing.tracker import BillingTracker
            bt = BillingTracker()
            bt_conn = bt._conn()
            bt_conn.execute(
                "UPDATE invoices SET status = 'paid' WHERE client = ? AND status = 'draft' ORDER BY created_at DESC LIMIT 1",
                (client,),
            )
            bt_conn.commit()
            bt_conn.close()
        except Exception:
            pass

        conn.commit()
        conn.close()

        logger.info(f"Payment completed: {client} — session {session_id}")
        return {"status": "paid", "client": client, "session_id": session_id}

    def _handle_invoice_paid(self, invoice: dict) -> dict:
        """Handle recurring subscription invoice payment."""
        customer_id = invoice.get("customer", "")
        amount = invoice.get("amount_paid", 0)

        conn = self._conn()
        conn.execute(
            """INSERT INTO payments (client, stripe_customer, amount_cents, currency,
               status, payment_type, description, created_at, completed_at)
               VALUES ((SELECT client FROM subscriptions WHERE stripe_customer = ? LIMIT 1),
                       ?, ?, 'usd', 'paid', 'subscription', 'Recurring retainer', ?, ?)""",
            (customer_id, customer_id, amount,
             datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

        return {"status": "recorded", "amount_cents": amount}

    def _handle_subscription_created(self, subscription: dict) -> dict:
        """Handle new subscription activation."""
        sub_id = subscription.get("id", "")
        customer_id = subscription.get("customer", "")

        conn = self._conn()
        conn.execute(
            "UPDATE subscriptions SET stripe_sub_id = ?, status = 'active' WHERE stripe_customer = ? AND status = 'pending'",
            (sub_id, customer_id),
        )
        conn.commit()
        conn.close()

        return {"status": "activated", "subscription_id": sub_id}

    def _handle_subscription_cancelled(self, subscription: dict) -> dict:
        """Handle subscription cancellation."""
        sub_id = subscription.get("id", "")

        conn = self._conn()
        conn.execute(
            "UPDATE subscriptions SET status = 'cancelled', cancelled_at = ? WHERE stripe_sub_id = ?",
            (datetime.now(timezone.utc).isoformat(), sub_id),
        )
        conn.commit()
        conn.close()

        return {"status": "cancelled", "subscription_id": sub_id}

    # ── Payment Status ──────────────────────────────────────────

    def payment_status(self, client: str) -> dict:
        """Get payment summary for a client."""
        conn = self._conn()

        payments = conn.execute(
            "SELECT * FROM payments WHERE client = ? ORDER BY created_at DESC LIMIT 10",
            (client,),
        ).fetchall()

        subs = conn.execute(
            "SELECT * FROM subscriptions WHERE client = ? ORDER BY created_at DESC",
            (client,),
        ).fetchall()

        total_paid = conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) as total FROM payments WHERE client = ? AND status = 'paid'",
            (client,),
        ).fetchone()

        conn.close()

        return {
            "client": client,
            "total_paid_usd": (total_paid["total"] if total_paid else 0) / 100,
            "recent_payments": [dict(p) for p in payments],
            "subscriptions": [dict(s) for s in subs],
            "has_active_subscription": any(s["status"] == "active" for s in subs),
        }

    def revenue_collected(self, days: int = 30) -> dict:
        """Total revenue actually collected via Stripe."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = self._conn()

        result = conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) as total, COUNT(*) as count FROM payments WHERE status = 'paid' AND completed_at >= ?",
            (cutoff,),
        ).fetchone()

        conn.close()
        return {
            "period_days": days,
            "total_collected_usd": result["total"] / 100 if result else 0,
            "payment_count": result["count"] if result else 0,
        }

    def gateway_status(self) -> dict:
        """Overall payment gateway health."""
        conn = self._conn()
        pending = conn.execute("SELECT COUNT(*) as c FROM payments WHERE status = 'pending'").fetchone()
        paid = conn.execute("SELECT COUNT(*) as c FROM payments WHERE status = 'paid'").fetchone()
        active_subs = conn.execute("SELECT COUNT(*) as c FROM subscriptions WHERE status = 'active'").fetchone()
        conn.close()

        return {
            "configured": self.configured,
            "test_mode": self.is_test_mode if self.configured else None,
            "pending_payments": pending["c"],
            "completed_payments": paid["c"],
            "active_subscriptions": active_subs["c"],
        }


# Module-level singleton
payments = PaymentGateway()
