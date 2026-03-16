"""Upwork Delivery Engine — contract management, messaging, and deliverable submission.

Browser automation for managing active Upwork contracts:
  - Read/send client messages on contract pages
  - Submit deliverables / work diary entries
  - View and manage milestones (fixed-price)
  - Request payment release
  - Check contract status

Usage:
    python -m automation.upwork_delivery --action messages --contract-url URL
    python -m automation.upwork_delivery --action send --contract-url URL --message "text"
    python -m automation.upwork_delivery --action deliver --contract-url URL --files file1.json
    python -m automation.upwork_delivery --action milestones --contract-url URL
    python -m automation.upwork_delivery --action status --contract-url URL
    python -m automation.upwork_delivery --action check-all
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
MSG_LOG_DIR = PROJECT / "data" / "upwork_messages"
MSG_LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = PROJECT / "data" / "upwork_jobs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONTRACT_LOG = DATA_DIR / "active_contracts.json"
DELIVERY_LOG = DATA_DIR / "deliveries.jsonl"

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


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


def _type_human(page, selector: str, text: str):
    """Type text with human-like delays between keystrokes."""
    el = page.query_selector(selector)
    if not el:
        return False
    el.click()
    _human_delay(0.3, 0.6)
    for char in text:
        el.type(char, delay=random.randint(30, 80))
    return True


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


def _log_delivery(entry: dict):
    """Append delivery record to JSONL log."""
    with open(DELIVERY_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ── Contract Status ─────────────────────────────────────────────────────────

def check_active_contracts(page) -> list[dict]:
    """Navigate to Upwork contracts page and list active contracts."""
    print("\n[CHECK] Scanning active Upwork contracts...")
    page.goto("https://www.upwork.com/nx/find-work/contract", wait_until="domcontentloaded")
    _human_delay(3, 5)
    _handle_challenge(page)

    # Try My Jobs / Active Contracts page
    page.goto("https://www.upwork.com/ab/find-work/domestic", wait_until="domcontentloaded")
    _human_delay(2, 4)

    contracts = []

    # Look for contract cards
    for selector in [
        '[data-test="contract-tile"]',
        'div[class*="contract"]',
        'section[class*="job"]',
        'div.up-card-section',
        'tr[class*="contract"]',
    ]:
        tiles = page.query_selector_all(selector)
        if tiles:
            break

    for tile in tiles[:20]:
        try:
            title_el = tile.query_selector('a[href*="/contracts/"], a[href*="/jobs/"], h3, h4')
            if not title_el:
                continue

            title = title_el.inner_text().strip()
            href = title_el.get_attribute("href") or ""
            url = href if href.startswith("http") else f"https://www.upwork.com{href}"

            status_el = tile.query_selector('[class*="status"], span[class*="badge"]')
            status = status_el.inner_text().strip() if status_el else "active"

            contracts.append({
                "title": title,
                "url": url,
                "status": status,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            })
            print(f"  [{status}] {title[:60]}")
        except Exception:
            continue

    # Save contracts list
    CONTRACT_LOG.write_text(json.dumps(contracts, indent=2), encoding="utf-8")
    print(f"\n  Total active contracts: {len(contracts)}")
    return contracts


# ── Message Reading ─────────────────────────────────────────────────────────

def read_messages(page, contract_url: str) -> list[dict]:
    """Read messages from an Upwork contract/job page."""
    print(f"\n[MESSAGES] Reading from {contract_url[:60]}...")

    page.goto(contract_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Try to navigate to messages tab
    for sel in [
        'a:has-text("Messages")', 'a:has-text("Message")',
        'button:has-text("Message")', 'a[href*="/messages/"]',
        'a[data-tab="messages"]',
    ]:
        link = page.query_selector(sel)
        if link:
            link.click()
            _human_delay(2, 4)
            break

    messages = []
    msg_els = page.query_selector_all(
        'div[class*="message"], div[class*="Message"], '
        'div[class*="chat-message"], li[class*="message"]'
    )

    for el in msg_els[-20:]:  # Last 20 messages
        try:
            sender_el = el.query_selector('[class*="sender"], [class*="name"], strong, b')
            sender = sender_el.inner_text().strip() if sender_el else "unknown"
            text = el.inner_text().strip()
            time_el = el.query_selector('[class*="time"], [class*="date"], time')
            timestamp = time_el.inner_text().strip() if time_el else ""

            messages.append({
                "sender": sender,
                "text": text[:500],
                "timestamp": timestamp,
            })
        except Exception:
            continue

    # Save messages
    safe_name = contract_url.split("/")[-1][:40] or "unknown"
    log_file = MSG_LOG_DIR / f"msgs_{safe_name}_{int(time.time())}.json"
    log_file.write_text(json.dumps(messages, indent=2), encoding="utf-8")
    print(f"  Read {len(messages)} messages")
    return messages


# ── Send Message ────────────────────────────────────────────────────────────

def send_message(page, contract_url: str, message: str) -> bool:
    """Send a message to a client on an Upwork contract page."""
    print(f"\n[SEND] Messaging client on {contract_url[:60]}...")

    page.goto(contract_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Find message input
    sent = False
    for sel in [
        'textarea[data-test="message-input"]',
        'textarea[aria-label*="message"]',
        'textarea[placeholder*="message"]',
        'textarea[placeholder*="Type"]',
        'div[contenteditable="true"]',
        'textarea',
    ]:
        el = page.query_selector(sel)
        if el and el.is_visible():
            el.click()
            _human_delay(0.5, 1.0)
            # Type with human delay
            for char in message:
                el.type(char, delay=random.randint(30, 80))
            _human_delay(0.5, 1.0)

            # Find send button
            for btn_sel in [
                'button:has-text("Send")',
                'button[data-test="send"]',
                'button[aria-label*="Send"]',
                'button[type="submit"]',
            ]:
                btn = page.query_selector(btn_sel)
                if btn and btn.is_visible():
                    btn.click()
                    sent = True
                    print(f"  [SENT] Message ({len(message)} chars)")
                    break
            break

    if not sent:
        print("  [WARN] Could not find message input or send button")
        page.screenshot(path=str(SS_DIR / f"upwork_send_fail_{int(time.time())}.png"))

    return sent


# ── Submit Deliverables ─────────────────────────────────────────────────────

def submit_deliverable(page, contract_url: str, files: list[str], message: str = "") -> bool:
    """Submit work deliverables on a contract page."""
    print(f"\n[DELIVER] Submitting to {contract_url[:60]}...")

    page.goto(contract_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Look for Submit Work / Upload Deliverable button
    for sel in [
        'button:has-text("Submit Work")',
        'button:has-text("Submit")',
        'a:has-text("Submit Work")',
        'button:has-text("Upload")',
        'button[data-test="submit-work"]',
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
            'textarea[data-test="message"]',
            'textarea[placeholder*="message"]',
            'textarea[aria-label*="message"]',
            'textarea',
        ]:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(message)
                break

    # Click final submit
    submitted = False
    for sel in [
        'button:has-text("Submit Work for Payment")',
        'button:has-text("Submit Work")',
        'button:has-text("Send")',
        'button[type="submit"]',
    ]:
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            btn.click()
            submitted = True
            _human_delay(2, 3)
            print(f"  [SUBMITTED] {uploaded} file(s)")
            break

    if submitted:
        _log_delivery({
            "contract_url": contract_url,
            "files": [str(f) for f in files],
            "message": message[:200],
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "status": "submitted",
        })
    else:
        print("  [WARN] Could not find submit button")
        page.screenshot(path=str(SS_DIR / f"upwork_deliver_fail_{int(time.time())}.png"))

    return submitted


# ── Milestone Management ────────────────────────────────────────────────────

def check_milestones(page, contract_url: str) -> list[dict]:
    """Check milestone status on a fixed-price contract."""
    print(f"\n[MILESTONES] Checking {contract_url[:60]}...")

    page.goto(contract_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    milestones = []
    ms_els = page.query_selector_all(
        'div[class*="milestone"], tr[class*="milestone"], '
        'div[class*="Milestone"], li[class*="milestone"]'
    )

    for el in ms_els:
        try:
            desc_el = el.query_selector('td, span, div[class*="desc"]')
            desc = desc_el.inner_text().strip() if desc_el else ""
            amount_el = el.query_selector('[class*="amount"], [class*="price"]')
            amount = amount_el.inner_text().strip() if amount_el else ""
            status_el = el.query_selector('[class*="status"], [class*="badge"]')
            status = status_el.inner_text().strip() if status_el else "unknown"

            milestones.append({
                "description": desc[:100],
                "amount": amount,
                "status": status,
            })
            print(f"  [{status}] {desc[:50]} — {amount}")
        except Exception:
            continue

    return milestones


# ── Check All Contracts ─────────────────────────────────────────────────────

def check_all(page) -> dict:
    """Full sweep: check contracts, read unread messages, identify deliverables due."""
    contracts = check_active_contracts(page)

    report = {
        "contracts": len(contracts),
        "messages_found": 0,
        "deliverables_due": 0,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    for contract in contracts:
        if contract.get("status", "").lower() in ("active", "in progress"):
            msgs = read_messages(page, contract["url"])
            report["messages_found"] += len(msgs)

            # Check if any messages are from client (potential work request)
            for msg in msgs:
                text = msg.get("text", "").lower()
                if any(kw in text for kw in ["deliver", "submit", "send me", "ready", "update"]):
                    report["deliverables_due"] += 1
                    print(f"  [!] Deliverable may be due: {contract['title'][:40]}")

    return report


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Upwork Delivery Engine")
    parser.add_argument("--action", required=True,
                        choices=["messages", "send", "deliver", "milestones", "status", "check-all"],
                        help="Action to perform")
    parser.add_argument("--contract-url", help="Upwork contract/job URL")
    parser.add_argument("--message", help="Message text to send")
    parser.add_argument("--files", nargs="*", help="File paths to deliver")
    args = parser.parse_args()

    pw, browser, context, page = _launch_browser()

    try:
        if args.action == "check-all":
            report = check_all(page)
            print(f"\n  Summary: {report['contracts']} contracts, "
                  f"{report['messages_found']} messages, "
                  f"{report['deliverables_due']} deliverables due")

        elif args.action == "status":
            check_active_contracts(page)

        elif args.action == "messages":
            if not args.contract_url:
                print("[ERROR] --contract-url required")
                return
            read_messages(page, args.contract_url)

        elif args.action == "send":
            if not args.contract_url or not args.message:
                print("[ERROR] --contract-url and --message required")
                return
            send_message(page, args.contract_url, args.message)

        elif args.action == "deliver":
            if not args.contract_url or not args.files:
                print("[ERROR] --contract-url and --files required")
                return
            submit_deliverable(page, args.contract_url, args.files, args.message or "")

        elif args.action == "milestones":
            if not args.contract_url:
                print("[ERROR] --contract-url required")
                return
            check_milestones(page, args.contract_url)

        print("\n[DONE] Leaving browser open for manual inspection.")
        input("Press Enter to close browser...")

    finally:
        browser.close()
        pw.stop()


if __name__ == "__main__":
    main()
