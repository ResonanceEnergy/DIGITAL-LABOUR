"""Lead Magnet API — Inbound lead capture with free demo task.

FastAPI router that provides:
- Landing page with email capture form
- Free demo task execution (one per email, limited scope)
- Lead storage into CRM tracker

Mount on the intake app:
    from api.lead_magnet import router as lead_router
    app.include_router(lead_router)
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/lead", tags=["Lead Magnet"])

STATE_FILE = PROJECT_ROOT / "data" / "lead_magnet_state.json"
DAILY_DEMO_CAP = 25


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"leads": [], "demos_today": 0, "demo_date": "", "total_leads": 0}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _reset_daily(state: dict) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("demo_date") != today:
        state["demos_today"] = 0
        state["demo_date"] = today
    return state


def _validate_email(email: str) -> bool:
    """Basic email format validation."""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


# ── Models ─────────────────────────────────────────────────────

class LeadCapture(BaseModel):
    email: str = Field(..., description="Contact email")
    name: str = Field(default="", description="Contact name")
    company: str = Field(default="", description="Company name")
    service: str = Field(default="general", description="Service interest")
    message: str = Field(default="", description="Optional message")


class DemoRequest(BaseModel):
    email: str = Field(..., description="Email for demo delivery")
    task_type: str = Field(default="product_desc", description="Demo task type")
    prompt: str = Field(default="", description="What to generate")


# ── Endpoints ──────────────────────────────────────────────────

DEMO_SERVICES = {
    "product_desc": {"label": "Product Description", "max_tokens": 500},
    "ad_copy": {"label": "Ad Copy", "max_tokens": 400},
    "seo_content": {"label": "SEO Blog Intro", "max_tokens": 600},
    "press_release": {"label": "Press Release Outline", "max_tokens": 500},
    "social_media": {"label": "Social Media Post Pack", "max_tokens": 400},
}


@router.get("/", response_class=HTMLResponse)
async def lead_page():
    """Landing page with email capture and free demo offer."""
    services_html = "\n".join(
        f'<option value="{k}">{v["label"]}</option>' for k, v in DEMO_SERVICES.items()
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BIT RAGE SYSTEMS — Free Demo</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 600px; margin: 2em auto; padding: 1em; background: #0a0a0a; color: #e0e0e0; }}
h1 {{ color: #00ff88; }} h2 {{ color: #aaa; font-weight: normal; }}
input, select, textarea {{ width: 100%; padding: 0.7em; margin: 0.3em 0 1em; background: #1a1a1a; border: 1px solid #333; color: #fff; border-radius: 4px; }}
button {{ background: #00ff88; color: #000; border: none; padding: 0.8em 2em; font-size: 1.1em; cursor: pointer; border-radius: 4px; font-weight: bold; }}
button:hover {{ background: #00cc66; }}
.result {{ background: #111; border: 1px solid #333; padding: 1em; margin-top: 1em; white-space: pre-wrap; display: none; }}
</style></head><body>
<h1>BIT RAGE SYSTEMS</h1>
<h2>AI Workforce — Try a Free Demo Task</h2>
<form id="demoForm">
<label>Email *</label><input type="email" name="email" required>
<label>Name</label><input type="text" name="name">
<label>Company</label><input type="text" name="company">
<label>Service</label><select name="task_type">{services_html}</select>
<label>What should we generate?</label><textarea name="prompt" rows="3" placeholder="Describe your product, brand, or content need..."></textarea>
<button type="submit">Generate Free Demo</button>
</form>
<div id="result" class="result"></div>
<script>
document.getElementById('demoForm').addEventListener('submit', async(e) => {{
  e.preventDefault();
  const fd = new FormData(e.target);
  const data = Object.fromEntries(fd.entries());
  const res = await fetch('/lead/demo', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(data) }});
  const json = await res.json();
  const el = document.getElementById('result');
  el.style.display = 'block';
  el.textContent = json.output || json.error || JSON.stringify(json);
}});
</script></body></html>"""


@router.post("/capture")
async def capture_lead(lead: LeadCapture):
    """Capture a lead's contact info into CRM."""
    if not _validate_email(lead.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    state = _load_state()

    # Deduplicate
    existing_emails = {l.get("email", "").lower() for l in state.get("leads", [])}
    if lead.email.lower() in existing_emails:
        return JSONResponse({"status": "already_captured", "message": "Thanks! We already have your info."})

    entry = {
        "email": lead.email,
        "name": lead.name,
        "company": lead.company,
        "service": lead.service,
        "message": lead.message,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "lead_magnet",
    }
    state["leads"].append(entry)
    state["total_leads"] = len(state["leads"])
    _save_state(state)

    # Push to CRM
    try:
        from automation.crm_tracker import add_contact
        add_contact(
            company=lead.company or lead.email.split("@")[1],
            email=lead.email,
            name=lead.name,
            stage="prospect",
            source="lead_magnet",
        )
    except Exception:
        pass

    return JSONResponse({"status": "captured", "message": "Thanks! We'll be in touch."})


@router.post("/demo")
async def run_demo(req: DemoRequest):
    """Execute a free demo task for a lead. Limited scope, one per email."""
    if not _validate_email(req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    if req.task_type not in DEMO_SERVICES:
        raise HTTPException(status_code=400, detail=f"Invalid service. Choose from: {list(DEMO_SERVICES.keys())}")

    state = _load_state()
    state = _reset_daily(state)

    # Check daily cap
    if state["demos_today"] >= DAILY_DEMO_CAP:
        return JSONResponse(
            {"error": "Daily demo limit reached. Try again tomorrow or contact sales@bit-rage-labour.com"},
            status_code=429,
        )

    # Check if email already got a demo
    demo_emails = {l.get("email", "").lower() for l in state.get("leads", []) if l.get("demo_used")}
    if req.email.lower() in demo_emails:
        return JSONResponse({"error": "You've already used your free demo. Contact us for full service."})

    # Generate demo output
    service = DEMO_SERVICES[req.task_type]
    prompt = req.prompt or f"Generate a sample {service['label'].lower()} for a tech startup."

    try:
        from utils.llm_client import call_llm
        output = call_llm(
            system_prompt=f"You are a professional {service['label']} writer for BIT RAGE SYSTEMS agency. "
                          f"Generate a high-quality {service['label'].lower()}. Keep it under {service['max_tokens']} tokens. "
                          f"This is a free demo — make it impressive to convert the lead into a client.",
            user_message=prompt,
            temperature=0.7,
        )
    except Exception:
        return JSONResponse({"error": "Demo generation failed. Please try again."}, status_code=500)

    # Record the lead + demo usage
    lead_entry = {
        "email": req.email,
        "service": req.task_type,
        "demo_used": True,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "demo",
    }

    # Deduplicate — update if exists, add if not
    found = False
    for l in state.get("leads", []):
        if l.get("email", "").lower() == req.email.lower():
            l["demo_used"] = True
            found = True
            break
    if not found:
        state["leads"].append(lead_entry)

    state["demos_today"] += 1
    state["total_leads"] = len(state["leads"])
    _save_state(state)

    # CRM capture
    try:
        from automation.crm_tracker import add_contact, log_interaction
        cid = add_contact(
            company=req.email.split("@")[1],
            email=req.email,
            stage="contacted",
            source="demo",
        )
        log_interaction(cid, "demo", "inbound", f"Free {service['label']} demo", "Demo delivered via lead magnet")
    except Exception:
        pass

    # Email the demo result to the lead
    try:
        from delivery.sender import send_email
        send_email(
            to=req.email,
            subject=f"Your Free {service['label']} — BIT RAGE SYSTEMS",
            body_html=f"""<h2>Here's your free {service['label']}</h2>
<div style="background:#f5f5f5;padding:16px;border-radius:8px;white-space:pre-wrap;font-family:sans-serif">{output}</div>
<hr>
<p><strong>Impressed?</strong> This was generated by one of our 24 AI agents in seconds.</p>
<p>Get unlimited access: <a href="https://bit-rage-labour.com/signup">Sign up now</a></p>
<p>Questions? Reply to this email — a human will respond.</p>
<p style="color:#888;font-size:12px">BIT RAGE SYSTEMS — AI Workforce on Demand<br>
<a href="https://bit-rage-labour.com">bit-rage-labour.com</a></p>
""",
        )
    except Exception:
        pass  # Don't fail demo if email fails

    return JSONResponse({
        "status": "success",
        "service": service["label"],
        "output": output,
        "cta": "Impressed? Get unlimited access at https://bit-rage-labour.com/signup",
    })


@router.get("/stats")
async def lead_stats():
    """Lead magnet statistics."""
    state = _load_state()
    state = _reset_daily(state)
    return {
        "total_leads": state.get("total_leads", 0),
        "demos_today": state.get("demos_today", 0),
        "daily_cap": DAILY_DEMO_CAP,
    }
