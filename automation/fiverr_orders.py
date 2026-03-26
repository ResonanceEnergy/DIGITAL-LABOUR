"""Fiverr Order Manager — incoming order detection, fulfillment, and buyer request responses.

Fiverr has NO seller API. This script uses browser automation to:
  - Check for new orders in the seller dashboard
  - Read order requirements from buyers
  - Route work to the correct internal agent
  - Deliver completed work
  - Respond to buyer requests (Fiverr's bid system)
  - Handle revision requests

Usage:
    python -m automation.fiverr_orders --action check          # Check for new orders
    python -m automation.fiverr_orders --action deliver --order-url URL --files file1.json
    python -m automation.fiverr_orders --action buyer-requests  # Scan & respond to buyer requests
    python -m automation.fiverr_orders --action inbox           # Check messages
    python -m automation.fiverr_orders --action send --order-url URL --message "text"
    python -m automation.fiverr_orders --action status          # Dashboard summary
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from dotenv import load_dotenv
load_dotenv(PROJECT / ".env")

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ── Paths ───────────────────────────────────────────────────────────────────
EDGE_PROFILE_DIR = PROJECT / "data" / "platform_browser" / "edge_profile"
EDGE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
SS_DIR = PROJECT / "output" / "platform_screenshots"
SS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = PROJECT / "data" / "fiverr_orders"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ORDER_LOG = DATA_DIR / "orders.jsonl"
BR_LOG = DATA_DIR / "buyer_requests.jsonl"
DELIVERY_LOG = DATA_DIR / "deliveries.jsonl"

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

FIVERR_DASHBOARD = "https://www.fiverr.com/users/{username}/manage_orders"
FIVERR_ORDERS = "https://www.fiverr.com/users/{username}/manage_orders?status=active"
FIVERR_BR = "https://www.fiverr.com/users/{username}/buyer_requests"
FIVERR_INBOX = "https://www.fiverr.com/inbox"

# Map gig keywords to internal agent names
GIG_TO_AGENT = {
    "sales": "sales_ops", "outreach": "sales_ops",
    "support": "support", "ticket": "support", "customer service": "support",
    "content": "content_repurpose", "repurpose": "content_repurpose",
    "document": "doc_extract", "extract": "doc_extract", "invoice": "doc_extract",
    "lead": "lead_gen", "prospect": "lead_gen",
    "email": "email_marketing", "newsletter": "email_marketing", "campaign": "email_marketing",
    "seo": "seo_content", "blog": "seo_content", "article": "seo_content",
    "social media": "social_media", "linkedin": "social_media", "instagram": "social_media",
    "data entry": "data_entry", "spreadsheet": "data_entry", "csv": "data_entry",
    "web scrap": "web_scraper", "scrape": "web_scraper", "data mining": "web_scraper",
    "crm": "crm_ops", "salesforce": "crm_ops", "hubspot": "crm_ops",
    "bookkeeping": "bookkeeping", "accounting": "bookkeeping", "expense": "bookkeeping",
    "proposal": "proposal_writer", "bid writing": "proposal_writer",
    "product desc": "product_desc", "amazon": "product_desc", "shopify": "product_desc",
    "resume": "resume_writer", "cv": "resume_writer",
    "ad copy": "ad_copy", "google ads": "ad_copy", "facebook ads": "ad_copy",
    "market research": "market_research", "competitive analysis": "market_research",
    "business plan": "business_plan",
    "press release": "press_release",
    "tech doc": "tech_docs", "api doc": "tech_docs", "documentation": "tech_docs",
}


def _human_delay(min_s: float = 1.5, max_s: float = 4.0):
    time.sleep(random.uniform(min_s, max_s))


def _handle_challenge(page):
    """Detect and wait for CAPTCHA / Cloudflare / bot-check pages."""
    indicators = [
        "verify you are human", "security check", "just a moment",
        "checking your browser", "captcha", "challenge-platform",
        "recaptcha", "hcaptcha",
    ]
    body_text = (page.inner_text("body") or "").lower()[:2000]
    if any(ind in body_text for ind in indicators):
        print("  [!] Challenge/CAPTCHA — waiting for manual solve (up to 120s)...")
        for _ in range(120):
            time.sleep(1)
            body_text = (page.inner_text("body") or "").lower()[:2000]
            if not any(ind in body_text for ind in indicators):
                print("  [+] Challenge cleared!")
                return
        print("  [WARN] Challenge not cleared after 120s")


def _launch_browser():
    """Launch Edge browser with persistent profile and stealth."""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        executable_path=EDGE_PATH,
        headless=False,
        args=[
            f"--user-data-dir={EDGE_PROFILE_DIR}",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1366, "height": 768},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
        ),
    )
    page = context.new_page()
    stealth = Stealth()
    stealth.apply_stealth_sync(page)
    return pw, browser, context, page


def _log_entry(filepath: Path, entry: dict):
    """Append entry to a JSONL file."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _match_agent(text: str) -> str:
    """Match order text to the best internal agent."""
    text_lower = text.lower()
    for keyword, agent in GIG_TO_AGENT.items():
        if keyword in text_lower:
            return agent
    return "support"  # Default fallback


# ── Check New Orders ────────────────────────────────────────────────────────

def check_orders(page) -> list[dict]:
    """Navigate to Fiverr seller dashboard and find active/new orders."""
    print("\n[CHECK] Scanning Fiverr orders...")

    # Go to manage orders page — use generic URL (Fiverr redirects to user's dashboard)
    page.goto("https://www.fiverr.com/selling", wait_until="domcontentloaded")
    _human_delay(3, 5)
    _handle_challenge(page)

    # Click on "Orders" or "Active Orders" tab
    for sel in [
        'a:has-text("Orders")', 'a:has-text("Active")',
        'a[href*="manage_orders"]', 'a[href*="orders"]',
        'button:has-text("Orders")',
    ]:
        link = page.query_selector(sel)
        if link and link.is_visible():
            link.click()
            _human_delay(2, 4)
            break

    orders = []

    # Find order cards/rows
    order_els = page.query_selector_all(
        'tr[class*="order"], div[class*="order-row"], '
        'div[class*="OrderRow"], li[class*="order"], '
        'div[class*="manage-order"], table tbody tr'
    )

    for el in order_els[:20]:
        try:
            # Get order title (gig name)
            title_el = el.query_selector('a, td:first-child, div[class*="title"]')
            title = title_el.inner_text().strip() if title_el else ""
            if not title or len(title) < 3:
                continue

            href_el = el.query_selector('a[href*="order"]')
            href = href_el.get_attribute("href") if href_el else ""
            url = href if href and href.startswith("http") else f"https://www.fiverr.com{href}" if href else ""

            # Status (New, In Progress, Delivered, etc.)
            status_el = el.query_selector('[class*="status"], [class*="badge"], td:nth-child(3)')
            status = status_el.inner_text().strip() if status_el else "unknown"

            # Due date
            due_el = el.query_selector('[class*="due"], [class*="deadline"], td:nth-child(4)')
            due = due_el.inner_text().strip() if due_el else ""

            # Buyer
            buyer_el = el.query_selector('[class*="buyer"], [class*="username"]')
            buyer = buyer_el.inner_text().strip() if buyer_el else ""

            order = {
                "title": title[:100],
                "url": url,
                "status": status,
                "due": due,
                "buyer": buyer,
                "agent": _match_agent(title),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            orders.append(order)
            _log_entry(ORDER_LOG, order)
            print(f"  [{status}] {title[:50]} -> {order['agent']} (due: {due})")

        except Exception:
            continue

    if not orders:
        print("  No orders found (or page layout changed)")
        page.screenshot(path=str(SS_DIR / f"fiverr_orders_{int(time.time())}.png"))

    print(f"\n  Total orders found: {len(orders)}")
    return orders


# ── Read Order Requirements ─────────────────────────────────────────────────

def read_order_requirements(page, order_url: str) -> dict:
    """Navigate to an order page and extract buyer's requirements."""
    print(f"\n[REQUIREMENTS] Reading {order_url[:60]}...")

    page.goto(order_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    requirements = {
        "url": order_url,
        "requirements_text": "",
        "attachments": [],
    }

    # Look for requirements section
    for sel in [
        'div[class*="requirements"]',
        'div[class*="Requirements"]',
        'div[class*="order-info"]',
        'div[class*="buyer-requirements"]',
        'section[class*="requirement"]',
    ]:
        el = page.query_selector(sel)
        if el:
            requirements["requirements_text"] = el.inner_text().strip()[:2000]
            break

    # Check for attached files
    attachment_els = page.query_selector_all(
        'a[href*="attachment"], a[class*="file"], '
        'div[class*="attachment"] a, a[download]'
    )
    for att in attachment_els:
        name = att.inner_text().strip()
        href = att.get_attribute("href") or ""
        if name:
            requirements["attachments"].append({"name": name, "url": href})

    print(f"  Requirements: {len(requirements['requirements_text'])} chars")
    print(f"  Attachments: {len(requirements['attachments'])}")
    return requirements


# ── Deliver Order ───────────────────────────────────────────────────────────

def deliver_order(page, order_url: str, files: list[str], message: str = "") -> bool:
    """Navigate to order page and submit delivery."""
    print(f"\n[DELIVER] Delivering to {order_url[:60]}...")

    page.goto(order_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Click "Deliver Now" or "Deliver Your Order" button
    for sel in [
        'button:has-text("Deliver Now")',
        'button:has-text("Deliver")',
        'a:has-text("Deliver Now")',
        'a:has-text("Deliver Your Order")',
        'button[class*="deliver"]',
    ]:
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            btn.click()
            _human_delay(2, 4)
            break

    # Upload files
    uploaded = 0
    for filepath in files:
        fpath = Path(filepath)
        if not fpath.exists():
            print(f"  [WARN] File not found: {filepath}")
            continue

        file_input = page.query_selector('input[type="file"]')
        if file_input:
            file_input.set_input_files(str(fpath))
            _human_delay(2, 3)
            uploaded += 1
            print(f"  [UPLOAD] {fpath.name}")

    # Add delivery message
    if message:
        for sel in [
            'textarea[class*="message"]',
            'textarea[placeholder*="message"]',
            'textarea[aria-label*="message"]',
            'textarea',
        ]:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(message)
                break

    # Click submit delivery
    submitted = False
    for sel in [
        'button:has-text("Deliver Work")',
        'button:has-text("Submit")',
        'button:has-text("Deliver")',
        'button[type="submit"]',
    ]:
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            btn.click()
            submitted = True
            _human_delay(2, 3)
            print(f"  [DELIVERED] {uploaded} file(s)")
            break

    if submitted:
        _log_entry(DELIVERY_LOG, {
            "order_url": order_url,
            "files": [str(f) for f in files],
            "message": message[:200],
            "delivered_at": datetime.now(timezone.utc).isoformat(),
        })
    else:
        print("  [WARN] Could not find delivery submit button")
        page.screenshot(path=str(SS_DIR / f"fiverr_deliver_fail_{int(time.time())}.png"))

    return submitted


# ── Buyer Requests (Fiverr's Bid System) ────────────────────────────────────

def scan_buyer_requests(page, max_responses: int = 5) -> list[dict]:
    """Scan Fiverr buyer requests and optionally respond."""
    print("\n[BUYER REQUESTS] Scanning...")

    page.goto("https://www.fiverr.com/users/buyer_requests", wait_until="domcontentloaded")
    _human_delay(3, 5)
    _handle_challenge(page)

    requests = []
    req_els = page.query_selector_all(
        'div[class*="buyer-request"], div[class*="BuyerRequest"], '
        'tr[class*="request"], li[class*="request"], '
        'div[class*="request-card"]'
    )

    for el in req_els[:20]:
        try:
            title_el = el.query_selector('h3, h4, div[class*="title"], strong')
            title = title_el.inner_text().strip() if title_el else ""
            desc_el = el.query_selector('p, div[class*="desc"], div[class*="text"]')
            desc = desc_el.inner_text().strip()[:500] if desc_el else ""
            budget_el = el.query_selector('[class*="budget"], [class*="price"]')
            budget = budget_el.inner_text().strip() if budget_el else ""

            agent = _match_agent(f"{title} {desc}")

            req = {
                "title": title[:100],
                "description": desc,
                "budget": budget,
                "agent": agent,
                "found_at": datetime.now(timezone.utc).isoformat(),
            }
            requests.append(req)
            _log_entry(BR_LOG, req)
            print(f"  [{budget}] {title[:50]} -> {agent}")

        except Exception:
            continue

    print(f"\n  Found {len(requests)} buyer requests")
    return requests


# ── Send Message ────────────────────────────────────────────────────────────

def send_message(page, order_url: str, message: str) -> bool:
    """Send a message on a Fiverr order page."""
    print(f"\n[SEND] Messaging on {order_url[:60]}...")

    page.goto(order_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    sent = False
    for sel in [
        'textarea[class*="message"]',
        'textarea[placeholder*="Type"]',
        'div[contenteditable="true"]',
        'textarea',
    ]:
        el = page.query_selector(sel)
        if el and el.is_visible():
            el.click()
            _human_delay(0.5, 1.0)
            for char in message:
                el.type(char, delay=random.randint(30, 80))
            _human_delay(0.5, 1.0)

            for btn_sel in [
                'button:has-text("Send")',
                'button[type="submit"]',
                'button[aria-label*="Send"]',
            ]:
                btn = page.query_selector(btn_sel)
                if btn and btn.is_visible():
                    btn.click()
                    sent = True
                    print(f"  [SENT] {len(message)} chars")
                    break
            break

    if not sent:
        print("  [WARN] Could not send message")

    return sent


# ── Order → Agent Dispatch ──────────────────────────────────────────────────

def dispatch_order(page, order: dict) -> dict:
    """Full pipeline: read requirements → route to agent → generate delivery → deliver.

    Args:
        page: Playwright page object (already launched).
        order: Order dict from check_orders() with title, url, agent, status.

    Returns:
        Dispatch result dict with agent output and delivery status.
    """
    result = {
        "order": order,
        "requirements": {},
        "agent_output": {},
        "delivered": False,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
    }

    order_url = order.get("url", "")
    if not order_url:
        result["error"] = "No order URL"
        return result

    # Step 1: Read buyer requirements
    print(f"\n[DISPATCH] Processing: {order.get('title', '')[:50]}")
    reqs = read_order_requirements(page, order_url)
    result["requirements"] = reqs

    requirement_text = reqs.get("requirements_text", "")
    gig_title = order.get("title", "")
    agent_name = order.get("agent", _match_agent(gig_title))

    # Step 2: Route to internal agent for content generation
    print(f"  Agent: {agent_name} | Generating delivery...")
    try:
        from agents.fiverr_work.runner import run_pipeline, save_output
        agent_result = run_pipeline(
            action="deliver",
            order_data={
                "gig_title": gig_title,
                "requirements": requirement_text,
                "buyer": order.get("buyer", ""),
                "due_date": order.get("due", ""),
            },
            provider="openai",
        )
        result["agent_output"] = agent_result.model_dump()
        output_path = save_output(agent_result)
        result["output_file"] = str(output_path)

        qa_status = agent_result.qa.status if agent_result.qa else "UNKNOWN"
        print(f"  QA: {qa_status} | Output: {output_path.name}")

        # Step 3: Deliver if QA passed
        if qa_status == "PASS":
            delivery_msg = agent_result.delivery.message if agent_result.delivery else ""
            if delivery_msg and order_url:
                delivered = deliver_order(page, order_url, [], delivery_msg)
                result["delivered"] = delivered
                if delivered:
                    print(f"  [SUCCESS] Order delivered via agent {agent_name}")
                    _log_entry(DELIVERY_LOG, {
                        "order_url": order_url,
                        "agent": agent_name,
                        "qa_status": qa_status,
                        "dispatched_at": result["dispatched_at"],
                        "auto_delivered": True,
                    })
        else:
            print(f"  [HOLD] QA {qa_status} — holding for manual review")
            result["hold_reason"] = f"QA status: {qa_status}"

    except Exception as e:
        result["error"] = str(e)
        print(f"  [ERROR] Agent dispatch failed: {e}")

    return result


def process_all_orders(page) -> list[dict]:
    """Check for new/active orders and auto-dispatch each through the agent pipeline."""
    orders = check_orders(page)
    results = []

    actionable = [
        o for o in orders
        if o.get("status", "").lower() in ("new", "active", "in progress")
        and o.get("url")
    ]
    print(f"\n[AUTO-DISPATCH] {len(actionable)} actionable orders out of {len(orders)} total")

    for order in actionable:
        result = dispatch_order(page, order)
        results.append(result)

    delivered = sum(1 for r in results if r.get("delivered"))
    held = sum(1 for r in results if r.get("hold_reason"))
    errors = sum(1 for r in results if r.get("error"))
    print(f"\n[SUMMARY] Delivered: {delivered} | Held: {held} | Errors: {errors}")
    return results


def respond_to_buyer_requests(page, max_responses: int = 5) -> list[dict]:
    """Scan buyer requests → generate LLM responses → submit."""
    requests = scan_buyer_requests(page, max_responses=max_responses)
    results = []

    for req in requests[:max_responses]:
        try:
            from agents.fiverr_work.runner import run_pipeline
            agent_result = run_pipeline(
                action="buyer-request",
                request_data=req,
                provider="openai",
            )
            qa_status = agent_result.qa.status if agent_result.qa else "UNKNOWN"
            results.append({
                "request": req,
                "response": agent_result.buyer_request.response_text if agent_result.buyer_request else "",
                "qa": qa_status,
                "submitted": False,  # Fiverr BR submission requires form interaction
            })
            print(f"  [RESPONSE] {req.get('title', '')[:40]} -> QA: {qa_status}")
        except Exception as e:
            results.append({"request": req, "error": str(e)})

    return results


# ── Status Dashboard ────────────────────────────────────────────────────────

def show_status():
    """Show summary of Fiverr order state from local logs."""
    print(f"\n{'='*60}")
    print(f"  FIVERR ORDER MANAGER — Status")
    print(f"{'='*60}")

    # Orders
    if ORDER_LOG.exists():
        lines = ORDER_LOG.read_text(encoding="utf-8").strip().split("\n")
        orders = [json.loads(l) for l in lines if l.strip()]
        active = [o for o in orders if o.get("status", "").lower() in ("active", "in progress", "new")]
        print(f"  Total orders logged: {len(orders)}")
        print(f"  Active/new: {len(active)}")
        for o in active[-5:]:
            print(f"    [{o.get('status')}] {o.get('title', '')[:50]} -> {o.get('agent')}")
    else:
        print("  No orders logged yet.")

    # Deliveries
    if DELIVERY_LOG.exists():
        lines = DELIVERY_LOG.read_text(encoding="utf-8").strip().split("\n")
        deliveries = [json.loads(l) for l in lines if l.strip()]
        print(f"\n  Deliveries made: {len(deliveries)}")
    else:
        print(f"\n  No deliveries yet.")

    # Buyer requests
    if BR_LOG.exists():
        lines = BR_LOG.read_text(encoding="utf-8").strip().split("\n")
        brs = [json.loads(l) for l in lines if l.strip()]
        print(f"  Buyer requests scanned: {len(brs)}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fiverr Order Manager")
    parser.add_argument("--action", required=True,
                        choices=["check", "deliver", "buyer-requests", "inbox", "send", "status",
                                 "dispatch", "auto", "respond-br"],
                        help="Action to perform")
    parser.add_argument("--order-url", help="Fiverr order URL")
    parser.add_argument("--message", help="Message text")
    parser.add_argument("--files", nargs="*", help="File paths to deliver")
    args = parser.parse_args()

    if args.action == "status":
        show_status()
        return

    pw, browser, context, page = _launch_browser()

    try:
        if args.action == "check":
            orders = check_orders(page)
            # Auto-read requirements for new orders
            for order in orders:
                if order.get("status", "").lower() in ("new", "active") and order.get("url"):
                    read_order_requirements(page, order["url"])

        elif args.action == "deliver":
            if not args.order_url or not args.files:
                print("[ERROR] --order-url and --files required")
                return
            deliver_order(page, args.order_url, args.files, args.message or "")

        elif args.action == "buyer-requests":
            scan_buyer_requests(page)

        elif args.action == "inbox":
            page.goto(FIVERR_INBOX, wait_until="domcontentloaded")
            _human_delay(3, 5)
            print("  Fiverr inbox opened. Review manually.")

        elif args.action == "send":
            if not args.order_url or not args.message:
                print("[ERROR] --order-url and --message required")
                return
            send_message(page, args.order_url, args.message)

        elif args.action == "dispatch":
            if not args.order_url:
                print("[ERROR] --order-url required")
                return
            order = {"title": "Manual dispatch", "url": args.order_url, "status": "active"}
            dispatch_order(page, order)

        elif args.action == "auto":
            process_all_orders(page)

        elif args.action == "respond-br":
            respond_to_buyer_requests(page)

        print("\n[DONE] Leaving browser open for manual inspection.")
        input("Press Enter to close browser...")

    finally:
        browser.close()
        pw.stop()


if __name__ == "__main__":
    main()
