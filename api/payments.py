"""Payment & Client Signup API routes.

Endpoints:
    POST /payments/checkout          — Create Stripe checkout for invoice
    POST /payments/subscribe         — Create Stripe subscription for retainer
    POST /payments/webhook           — Stripe webhook receiver
    POST /payments/customer-portal   — Create Stripe Customer Portal session
    POST /payments/cancel-subscription — Cancel client subscription
    POST /payments/update-subscription — Change subscription tier
    GET  /payments/session-status    — Retrieve Checkout Session status
    GET  /payments/status/{client}   — Payment status for client
    GET  /payments/gateway           — Gateway health
    GET  /payments/success           — Checkout success page
    GET  /payments/cancel            — Checkout cancel page
    POST /signup                     — Self-serve client registration
    GET  /signup                     — Signup form page
"""

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter()


# ── Models ──────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    client: str
    amount_usd: float = Field(..., gt=0)
    description: str = ""

class SubscribeRequest(BaseModel):
    client: str
    tier: str
    email: str = ""

class PortalRequest(BaseModel):
    client: str
    return_url: str = ""

class CancelSubscriptionRequest(BaseModel):
    client: str
    at_period_end: bool = True

class UpdateSubscriptionRequest(BaseModel):
    client: str
    new_tier: str

class SignupRequest(BaseModel):
    client_id: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_-]+$")
    company: str
    contact_name: str
    email: str
    services: list[str] = Field(default_factory=list)
    pricing_model: str = "per_task"   # per_task or retainer
    retainer_tier: str = ""
    delivery_method: str = "file"     # file, webhook, email
    webhook_url: str = ""
    notes: str = ""


# ── Payment Endpoints ──────────────────────────────────────────

@router.post("/payments/checkout")
def create_checkout(req: CheckoutRequest):
    """Create a Stripe checkout session for a one-time invoice payment."""
    from billing.payments import payments
    if not payments.configured:
        raise HTTPException(status_code=503, detail="Payment gateway not configured. Set STRIPE_API_KEY in .env")

    result = payments.create_checkout(
        client=req.client,
        amount_cents=int(req.amount_usd * 100),
        description=req.description or f"Invoice — {req.client}",
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/payments/subscribe")
def create_subscription(req: SubscribeRequest):
    """Create a Stripe subscription for a retainer tier."""
    from billing.payments import payments
    if not payments.configured:
        raise HTTPException(status_code=503, detail="Payment gateway not configured. Set STRIPE_API_KEY in .env")

    result = payments.create_subscription(
        client=req.client,
        tier=req.tier,
        email=req.email,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/payments/webhook")
async def stripe_webhook(request: Request):
    """Receive and process Stripe webhook events."""
    from billing.payments import payments
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if not sig:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    result = payments.handle_webhook(payload, sig)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/payments/customer-portal")
def customer_portal(req: PortalRequest):
    """Create a Stripe Customer Portal session for billing management."""
    from billing.payments import payments
    if not payments.configured:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")

    result = payments.create_portal_session(
        client=req.client,
        return_url=req.return_url,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/payments/cancel-subscription")
def cancel_subscription(req: CancelSubscriptionRequest):
    """Cancel a client's active subscription."""
    from billing.payments import payments
    if not payments.configured:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")

    result = payments.cancel_subscription(
        client=req.client,
        at_period_end=req.at_period_end,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/payments/update-subscription")
def update_subscription(req: UpdateSubscriptionRequest):
    """Change a client's subscription to a different tier."""
    from billing.payments import payments
    if not payments.configured:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")

    result = payments.update_subscription(
        client=req.client,
        new_tier=req.new_tier,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/payments/session-status")
def session_status(session_id: str):
    """Retrieve Checkout Session status (for post-checkout confirmation)."""
    from billing.payments import payments
    if not payments.configured:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")

    result = payments.get_session_status(session_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/payments/status/{client}")
def payment_status(client: str):
    """Get payment history and subscription status for a client."""
    from billing.payments import payments
    return payments.payment_status(client)


@router.get("/payments/gateway")
def gateway_health():
    """Get payment gateway configuration and health."""
    from billing.payments import payments
    return payments.gateway_status()


@router.get("/payments/success", response_class=HTMLResponse)
def payment_success(session_id: str = ""):
    """Payment success landing page."""
    display_id = session_id[:20] if session_id else ""
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Payment Successful</title>
<style>body{{font-family:system-ui;background:#0a0a0a;color:#e0e0e0;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}}
.box{{text-align:center;padding:40px;border:1px solid #2a2a2a;border-radius:12px;background:#111;max-width:480px}}
h1{{color:#00ff88;font-size:2em}}p{{color:#999}}
a.btn{{display:inline-block;margin-top:20px;padding:12px 28px;background:#00ff88;color:#0a0a0a;text-decoration:none;border-radius:6px;font-weight:700}}
a.btn:hover{{background:#00cc66}}</style></head>
<body><div class="box"><h1>Payment Received</h1>
<p>Thank you. Your payment has been processed successfully.</p>
<p style="font-size:0.8em;color:#555">Session: {display_id}...</p>
<a class="btn" href="mailto:sales@digital-labour.com?subject=Manage%20Billing">Manage Billing</a>
</div></body></html>""")


@router.get("/payments/cancel", response_class=HTMLResponse)
def payment_cancel():
    """Payment cancellation page."""
    return HTMLResponse("""<!DOCTYPE html>
<html><head><title>Payment Cancelled</title>
<style>body{font-family:system-ui;background:#0a0a0a;color:#e0e0e0;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.box{text-align:center;padding:40px;border:1px solid #2a2a2a;border-radius:12px;background:#111}
h1{color:#ff6644;font-size:2em}p{color:#999}</style></head>
<body><div class="box"><h1>Payment Cancelled</h1>
<p>No charge was made. You can retry anytime.</p></div></body></html>""")


# ── Client Signup ───────────────────────────────────────────────

@router.post("/signup")
def client_signup(req: SignupRequest):
    """Self-serve client registration. Creates profile + API key + billing record."""
    from billing.tracker import BillingTracker, RETAINER_TIERS

    # Validate
    if req.pricing_model == "retainer" and req.retainer_tier and req.retainer_tier not in RETAINER_TIERS:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {req.retainer_tier}")

    valid_services = {"sales_outreach", "support_ticket", "content_repurpose", "doc_extract"}
    for s in req.services:
        if s not in valid_services:
            raise HTTPException(status_code=400, detail=f"Unknown service: {s}")

    # Check if client already exists
    clients_dir = PROJECT_ROOT / "clients"
    clients_dir.mkdir(parents=True, exist_ok=True)
    profile_path = clients_dir / f"{req.client_id}.json"
    if profile_path.exists():
        raise HTTPException(status_code=409, detail=f"Client '{req.client_id}' already exists")

    # Generate API key
    api_key = f"dl_{secrets.token_urlsafe(32)}"

    # Build profile
    now = datetime.now(timezone.utc).isoformat()
    profile = {
        "client_id": req.client_id,
        "company": req.company,
        "contact_name": req.contact_name,
        "email": req.email,
        "services": req.services or list(valid_services),
        "pricing_model": req.pricing_model,
        "retainer_tier": req.retainer_tier,
        "delivery_method": req.delivery_method,
        "webhook_url": req.webhook_url,
        "notes": req.notes,
        "api_key": api_key,
        "status": "active",
        "onboarded_at": now,
    }

    # Save profile
    profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")

    # Register in billing tracker
    bt = BillingTracker()
    bt.add_client(
        client=req.client_id,
        name=req.company,
        email=req.email,
        retainer=req.retainer_tier,
    )

    return {
        "status": "registered",
        "client_id": req.client_id,
        "api_key": api_key,
        "services": profile["services"],
        "pricing_model": req.pricing_model,
        "message": "Welcome to Digital Labour. Use your API key to submit tasks.",
    }


@router.get("/signup", response_class=HTMLResponse)
def signup_page():
    """Self-serve client signup form."""
    html_path = Path(__file__).parent / "signup.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    # Fallback minimal form
    return HTMLResponse("""<!DOCTYPE html><html><head><title>Digital Labour — Sign Up</title></head>
<body><h1>Sign Up</h1><p>POST to /signup with JSON body. See API docs at /docs</p></body></html>""")
