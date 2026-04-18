"""Stripe Checkout flow — connects service landing pages to agent fulfillment.

Endpoints:
    POST /checkout/create-session  — Create Stripe Checkout Session
    POST /checkout/webhook         — Stripe webhook handler
    GET  /checkout/orders/{id}     — Get order status + deliverables
    GET  /checkout/orders          — List orders (optionally by email)
    GET  /checkout/success         — Post-payment success page
    GET  /checkout/cancel          — Payment cancelled page
"""

import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("api.checkout")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "orders.db"

router = APIRouter(prefix="/checkout", tags=["checkout"])

# ── Price Table (cents) ──────────────────────────────────────────────────────

PRICE_TABLE: dict[str, dict[str, dict]] = {
    "product_desc": {
        "basic":    {"price_cents": 50000,  "label": "50 Product Descriptions",   "agent": "product_desc"},
        "standard": {"price_cents": 150000, "label": "200 Product Descriptions",  "agent": "product_desc"},
        "premium":  {"price_cents": 300000, "label": "500 Product Descriptions",  "agent": "product_desc"},
    },
    "seo_content": {
        "starter":  {"price_cents": 80000,  "label": "SEO Content — 4 posts/mo",  "agent": "seo_content"},
        "growth":   {"price_cents": 200000, "label": "SEO Content — 12 posts/mo", "agent": "seo_content"},
        "scale":    {"price_cents": 450000, "label": "SEO Content — 30 posts/mo", "agent": "seo_content"},
    },
    "resume": {
        "basic":    {"price_cents": 4900,   "label": "Resume Only",                "agent": "resume_writer"},
        "standard": {"price_cents": 9900,   "label": "Resume + Cover Letter",      "agent": "resume_writer"},
        "premium":  {"price_cents": 11900,  "label": "Resume + Cover + LinkedIn",  "agent": "resume_writer"},
    },
    "ad_copy": {
        "basic":    {"price_cents": 15000,  "label": "Ad Copy — 1 Platform",      "agent": "ad_copy"},
        "standard": {"price_cents": 35000,  "label": "Ad Copy — 3 Platforms",     "agent": "ad_copy"},
        "premium":  {"price_cents": 60000,  "label": "Ad Copy — All Platforms",   "agent": "ad_copy"},
    },
    "email_sequence": {
        "basic":    {"price_cents": 80000,  "label": "Email Sequence — 3 Emails",       "agent": "email_marketing"},
        "standard": {"price_cents": 150000, "label": "Email Sequence — 5 Emails",       "agent": "email_marketing"},
        "premium":  {"price_cents": 250000, "label": "Email Sequence — 7 Emails + A/B", "agent": "email_marketing"},
    },
}

# Tier aliases: accept both naming conventions
_TIER_ALIASES = {
    "starter": "starter", "growth": "growth", "scale": "scale",
    "basic": "basic", "standard": "standard", "premium": "premium",
}


def _resolve_tier(service_type: str, tier: str) -> Optional[dict]:
    """Resolve a tier name to a price entry, handling aliases."""
    service = PRICE_TABLE.get(service_type)
    if not service:
        return None
    return service.get(tier)


# ── SQLite Setup ─────────────────────────────────────────────────────────────

_db_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        # Fallback for filesystems that don't support WAL (e.g. FUSE)
        conn.execute("PRAGMA journal_mode=DELETE")
    return conn


def _init_db():
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id           TEXT PRIMARY KEY,
                stripe_session_id  TEXT,
                service_type       TEXT NOT NULL,
                package_tier       TEXT NOT NULL,
                customer_email     TEXT NOT NULL,
                customer_name      TEXT NOT NULL DEFAULT '',
                price_cents        INTEGER NOT NULL,
                status             TEXT NOT NULL DEFAULT 'pending_payment',
                requirements       TEXT NOT NULL DEFAULT '{}',
                fulfillment_task_id TEXT,
                deliverables       TEXT NOT NULL DEFAULT '{}',
                created_at         TEXT NOT NULL,
                paid_at            TEXT,
                completed_at       TEXT,
                stripe_payment_intent TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_email ON orders(customer_email)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_session ON orders(stripe_session_id)")
        conn.commit()
    except Exception as exc:
        logger.warning("[CHECKOUT] DB init warning: %s", exc)
    finally:
        conn.close()


try:
    _init_db()
except Exception as exc:
    logger.warning("[CHECKOUT] Deferred DB init due to: %s", exc)


# ── Request Models ───────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    service_type: str = Field(..., description="Service: product_desc, seo_content, resume, ad_copy, email_sequence")
    package_tier: str = Field(..., description="Tier: basic/standard/premium or starter/growth/scale")
    customer_email: str = Field(..., min_length=5)
    customer_name: str = Field(default="")
    requirements: dict = Field(default_factory=dict, description="Specs and requirements for the order")


# ── Stripe Helpers ───────────────────────────────────────────────────────────

def _get_stripe():
    """Lazy import and configure stripe."""
    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY", "")
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured. Set STRIPE_API_KEY in .env")
    return stripe


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/create-session")
def create_checkout_session(req: CreateSessionRequest):
    """Create a Stripe Checkout Session and store order in SQLite."""
    # Validate service + tier
    tier_info = _resolve_tier(req.service_type, req.package_tier)
    if not tier_info:
        valid_services = list(PRICE_TABLE.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service_type '{req.service_type}' or package_tier '{req.package_tier}'. "
                   f"Valid services: {valid_services}",
        )

    price_cents = tier_info["price_cents"]
    label = tier_info["label"]
    order_id = f"ord_{uuid4().hex[:16]}"
    now = datetime.now(timezone.utc).isoformat()

    # Store order in SQLite
    with _db_lock:
        conn = _get_conn()
        conn.execute(
            """INSERT INTO orders
               (order_id, service_type, package_tier, customer_email, customer_name,
                price_cents, status, requirements, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pending_payment', ?, ?)""",
            (order_id, req.service_type, req.package_tier, req.customer_email,
             req.customer_name, price_cents, json.dumps(req.requirements), now),
        )
        conn.commit()
        conn.close()

    # Create Stripe Checkout Session
    stripe = _get_stripe()
    try:
        base_url = os.environ.get("BASE_URL", "").rstrip("/")
        if not base_url:
            base_url = "https://bitrage-labour-api-production.up.railway.app"

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            customer_email=req.customer_email,
            client_reference_id=order_id,
            metadata={
                "order_id": order_id,
                "service_type": req.service_type,
                "package_tier": req.package_tier,
                "customer_name": req.customer_name,
            },
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": price_cents,
                    "product_data": {
                        "name": f"DIGITAL LABOUR — {label}",
                        "description": f"{req.service_type} / {req.package_tier}",
                    },
                },
                "quantity": 1,
            }],
            success_url=f"{base_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&order_id={order_id}",
            cancel_url=f"{base_url}/checkout/cancel?order_id={order_id}",
        )
    except Exception as e:
        logger.error("[CHECKOUT] Stripe session creation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)}")

    # Update order with Stripe session ID
    with _db_lock:
        conn = _get_conn()
        conn.execute(
            "UPDATE orders SET stripe_session_id = ? WHERE order_id = ?",
            (session.id, order_id),
        )
        conn.commit()
        conn.close()

    logger.info("[CHECKOUT] Session created: order=%s session=%s price=$%.2f",
                order_id, session.id, price_cents / 100)

    return {
        "order_id": order_id,
        "checkout_url": session.url,
        "session_id": session.id,
        "price_usd": price_cents / 100,
        "label": label,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events. Verifies signature when webhook secret is set."""
    stripe = _get_stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    event = None

    if webhook_secret and sig:
        # Verify signature
        try:
            event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
        except stripe.error.SignatureVerificationError:
            logger.warning("[WEBHOOK] Signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            logger.error("[WEBHOOK] Event construction failed: %s", e)
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # No webhook secret — parse raw (testing mode)
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        logger.warning("[WEBHOOK] No STRIPE_WEBHOOK_SECRET set — skipping signature verification")

    event_type = event.get("type", "") if isinstance(event, dict) else event.type

    if event_type == "checkout.session.completed":
        session_data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object
        _handle_checkout_completed(session_data)
    else:
        logger.debug("[WEBHOOK] Ignoring event type: %s", event_type)

    return {"status": "ok", "type": event_type}


def _handle_checkout_completed(session_data):
    """Process a completed checkout session: mark paid, dispatch to agents, record revenue."""
    session_id = session_data.get("id", "") if isinstance(session_data, dict) else session_data.id
    order_id = (
        session_data.get("metadata", {}).get("order_id", "")
        if isinstance(session_data, dict)
        else session_data.metadata.get("order_id", "")
    )
    payment_intent = (
        session_data.get("payment_intent", "")
        if isinstance(session_data, dict)
        else getattr(session_data, "payment_intent", "")
    )

    if not order_id:
        # Try to find by session ID
        with _db_lock:
            conn = _get_conn()
            row = conn.execute(
                "SELECT order_id FROM orders WHERE stripe_session_id = ?", (session_id,)
            ).fetchone()
            conn.close()
        if row:
            order_id = row["order_id"]
        else:
            logger.error("[WEBHOOK] No order found for session %s", session_id)
            return

    now = datetime.now(timezone.utc).isoformat()

    # Mark order as paid
    with _db_lock:
        conn = _get_conn()
        conn.execute(
            """UPDATE orders SET status = 'paid', paid_at = ?, stripe_payment_intent = ?
               WHERE order_id = ?""",
            (now, payment_intent, order_id),
        )
        conn.commit()

        # Fetch order details for fulfillment
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        conn.close()

    if not row:
        logger.error("[WEBHOOK] Order %s not found after update", order_id)
        return

    service_type = row["service_type"]
    package_tier = row["package_tier"]
    customer_email = row["customer_email"]
    customer_name = row["customer_name"]
    price_cents = row["price_cents"]
    requirements = json.loads(row["requirements"]) if row["requirements"] else {}

    logger.info("[CHECKOUT] Payment confirmed: order=%s service=%s tier=%s $%.2f",
                order_id, service_type, package_tier, price_cents / 100)

    # Record revenue
    try:
        from billing.revenue_tracker import record_revenue
        record_revenue(
            channel="direct",
            agent=PRICE_TABLE.get(service_type, {}).get(package_tier, {}).get("agent", service_type),
            client_id=customer_email,
            amount=price_cents / 100,
            cost=0.0,  # LLM cost recorded post-fulfillment
            description=f"Checkout: {service_type}/{package_tier} for {customer_name or customer_email}",
        )
    except Exception as exc:
        logger.error("[CHECKOUT] Revenue recording failed: %s", exc)

    # Dispatch to agent fulfillment
    try:
        _dispatch_to_fulfillment(order_id, service_type, package_tier, customer_email, requirements)
    except Exception as exc:
        logger.error("[CHECKOUT] Fulfillment dispatch failed for order %s: %s", order_id, exc)
        # Mark order as paid but fulfillment pending
        with _db_lock:
            conn = _get_conn()
            conn.execute(
                "UPDATE orders SET status = 'fulfillment_error' WHERE order_id = ?",
                (order_id,),
            )
            conn.commit()
            conn.close()


def _dispatch_to_fulfillment(order_id: str, service_type: str, package_tier: str,
                             customer_email: str, requirements: dict):
    """Dispatch paid order to the agent fulfillment pipeline via dispatcher/router."""
    from dispatcher.router import create_event, route_task

    # Map service_type to task_type
    tier_info = PRICE_TABLE.get(service_type, {}).get(package_tier, {})
    task_type = tier_info.get("agent", service_type)

    # Build inputs from requirements + order metadata
    inputs = {
        **requirements,
        "order_id": order_id,
        "package_tier": package_tier,
        "customer_email": customer_email,
    }

    # Map service-specific fields
    if task_type == "product_desc":
        inputs.setdefault("raw_input", requirements.get("product_specs", ""))
        inputs.setdefault("platform", requirements.get("platform", "general"))
    elif task_type == "seo_content":
        inputs.setdefault("topic", requirements.get("topic", ""))
        inputs.setdefault("content_type", requirements.get("content_type", "blog_post"))
    elif task_type == "resume_writer":
        inputs.setdefault("raw_input", requirements.get("career_data", ""))
        inputs.setdefault("target_role", requirements.get("target_role", ""))
    elif task_type == "ad_copy":
        inputs.setdefault("brief", requirements.get("brief", ""))
        inputs.setdefault("platform", requirements.get("platform", "google_search"))
    elif task_type == "email_marketing":
        inputs.setdefault("business", requirements.get("business", ""))
        inputs.setdefault("audience", requirements.get("audience", ""))
        inputs.setdefault("email_count", {"basic": 3, "standard": 5, "premium": 7}.get(package_tier, 5))

    event = create_event(task_type=task_type, inputs=inputs, client_id=customer_email)
    result = route_task(event)

    qa_status = result.get("qa", {}).get("status", "FAIL")
    outputs = result.get("outputs", {})

    # Update order with results
    now = datetime.now(timezone.utc).isoformat()
    new_status = "completed" if qa_status == "PASS" else "fulfillment_error"

    with _db_lock:
        conn = _get_conn()
        conn.execute(
            """UPDATE orders SET status = ?, fulfillment_task_id = ?, deliverables = ?,
               completed_at = ? WHERE order_id = ?""",
            (new_status, result.get("event_id", ""), json.dumps(outputs, default=str),
             now if qa_status == "PASS" else None, order_id),
        )
        conn.commit()
        conn.close()

    logger.info("[FULFILLMENT] order=%s task=%s qa=%s", order_id, task_type, qa_status)


@router.get("/orders/{order_id}")
def get_order(order_id: str):
    """Get order status, details, and deliverables."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": row["order_id"],
        "service_type": row["service_type"],
        "package_tier": row["package_tier"],
        "customer_email": row["customer_email"],
        "customer_name": row["customer_name"],
        "price_usd": row["price_cents"] / 100,
        "status": row["status"],
        "requirements": json.loads(row["requirements"]) if row["requirements"] else {},
        "fulfillment_task_id": row["fulfillment_task_id"],
        "deliverables": json.loads(row["deliverables"]) if row["deliverables"] else {},
        "created_at": row["created_at"],
        "paid_at": row["paid_at"],
        "completed_at": row["completed_at"],
    }


@router.get("/orders")
def list_orders(email: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200)):
    """List orders, optionally filtered by customer email."""
    conn = _get_conn()
    if email:
        rows = conn.execute(
            "SELECT * FROM orders WHERE customer_email = ? ORDER BY created_at DESC LIMIT ?",
            (email, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()

    return {
        "count": len(rows),
        "orders": [
            {
                "order_id": r["order_id"],
                "service_type": r["service_type"],
                "package_tier": r["package_tier"],
                "customer_email": r["customer_email"],
                "customer_name": r["customer_name"],
                "price_usd": r["price_cents"] / 100,
                "status": r["status"],
                "created_at": r["created_at"],
                "paid_at": r["paid_at"],
                "completed_at": r["completed_at"],
            }
            for r in rows
        ],
    }


# ── Success / Cancel Pages ───────────────────────────────────────────────────

@router.get("/success", response_class=HTMLResponse)
def checkout_success(session_id: str = "", order_id: str = ""):
    """Post-payment success page."""
    order_info = ""
    if order_id:
        try:
            conn = _get_conn()
            row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            conn.close()
            if row:
                order_info = f"""
                <p><strong>Order:</strong> {row['order_id']}</p>
                <p><strong>Service:</strong> {row['service_type']} / {row['package_tier']}</p>
                <p><strong>Amount:</strong> ${row['price_cents'] / 100:.2f}</p>
                <p><strong>Status:</strong> {row['status']}</p>
                """
        except Exception:
            pass

    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Payment Successful - DIGITAL LABOUR</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#0a0a0a;color:#e0e0e0;display:flex;justify-content:center;align-items:center;min-height:100vh}}
.card{{text-align:center;padding:48px;border:1px solid #1a3a1a;border-radius:16px;background:#111;max-width:520px;width:90%}}
h1{{color:#00ff88;font-size:2em;margin-bottom:16px}}
.check{{font-size:4em;margin-bottom:16px}}
p{{color:#999;margin:8px 0;line-height:1.5}}
.order-info{{text-align:left;background:#0a0a0a;border:1px solid #222;border-radius:8px;padding:16px;margin:20px 0}}
.order-info p{{font-size:0.9em}}
.order-info strong{{color:#ccc}}
a.btn{{display:inline-block;margin-top:24px;padding:14px 32px;background:#00ff88;color:#0a0a0a;text-decoration:none;border-radius:8px;font-weight:700;transition:background 0.2s}}
a.btn:hover{{background:#00cc66}}
.note{{font-size:0.8em;color:#555;margin-top:20px}}
</style></head>
<body><div class="card">
<div class="check">&#10003;</div>
<h1>Payment Received</h1>
<p>Your order has been placed and our AI agents are working on your deliverables.</p>
{f'<div class="order-info">{order_info}</div>' if order_info else ''}
<p>You will receive your deliverables via email once they are ready.</p>
<a class="btn" href="/checkout/orders/{order_id}">Track Order</a>
<p class="note">Questions? Contact sales@bit-rage-labour.com</p>
</div></body></html>""")


@router.get("/cancel", response_class=HTMLResponse)
def checkout_cancel(order_id: str = ""):
    """Payment cancellation page."""
    return HTMLResponse("""<!DOCTYPE html>
<html><head><title>Payment Cancelled - DIGITAL LABOUR</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#0a0a0a;color:#e0e0e0;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{text-align:center;padding:48px;border:1px solid #3a1a1a;border-radius:16px;background:#111;max-width:520px;width:90%}
h1{color:#ff6644;font-size:2em;margin-bottom:16px}
p{color:#999;margin:8px 0;line-height:1.5}
a.btn{display:inline-block;margin-top:24px;padding:14px 32px;background:#333;color:#e0e0e0;text-decoration:none;border-radius:8px;font-weight:600;transition:background 0.2s}
a.btn:hover{background:#444}
</style></head>
<body><div class="card">
<h1>Payment Cancelled</h1>
<p>No charge was made. Your order has not been placed.</p>
<p>You can try again anytime.</p>
<a class="btn" href="/services">Back to Services</a>
</div></body></html>""")


# ── Price Table Endpoint (for frontend) ──────────────────────────────────────

@router.get("/prices")
def get_prices():
    """Return the full price table for frontend rendering."""
    result = {}
    for service, tiers in PRICE_TABLE.items():
        result[service] = {
            tier: {"price_usd": info["price_cents"] / 100, "label": info["label"]}
            for tier, info in tiers.items()
        }
    return result
