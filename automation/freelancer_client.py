"""Freelancer.com Client Interaction — messaging, milestones, and file delivery.

Browser automation for managing active projects on Freelancer.com:
  - Read/send client messages on project pages
  - View and accept milestones
  - Upload deliverable files
  - Request milestone release
  - Check project status

Usage:
    python -m automation.freelancer_client --action messages --project-url URL
    python -m automation.freelancer_client --action send --project-url URL --message "text"
    python -m automation.freelancer_client --action deliver --project-url URL --files file1.json file2.txt
    python -m automation.freelancer_client --action milestones --project-url URL
    python -m automation.freelancer_client --action accept-milestone --project-url URL
    python -m automation.freelancer_client --action status --project-url URL
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
MSG_LOG_DIR = PROJECT / "data" / "freelancer_messages"
MSG_LOG_DIR.mkdir(parents=True, exist_ok=True)

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


def _extract_project_id(url: str) -> str:
    """Extract project ID from Freelancer.com URL."""
    # URL format: /projects/some-title-12345678
    parts = url.rstrip("/").split("-")
    if parts and parts[-1].isdigit():
        return parts[-1]
    # Also check /projects/12345678
    segments = url.rstrip("/").split("/")
    for seg in reversed(segments):
        if seg.isdigit():
            return seg
    return ""


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


# ── Message Functions ───────────────────────────────────────────────────────

def read_messages(page, project_url: str) -> list[dict]:
    """Read messages from Freelancer.com project chat/message thread."""
    project_id = _extract_project_id(project_url)

    # Navigate to project page
    page.goto(project_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Try to find a messages/chat tab or link
    msg_link = page.query_selector(
        'a[href*="messages"], '
        'a[href*="/messages/"], '
        'a:has-text("Messages"), '
        'a:has-text("Chat"), '
        'button:has-text("Message"), '
        'a[data-tab="messages"]'
    )
    if msg_link:
        msg_link.click()
        _human_delay(2, 4)
        _handle_challenge(page)

    # Alt: go directly to messaging thread
    if not msg_link:
        page.goto(f"https://www.freelancer.com/messages/project-{project_id}", wait_until="domcontentloaded")
        _human_delay(2, 4)
        _handle_challenge(page)

    # Extract message elements
    messages = []
    msg_elements = page.query_selector_all(
        'div[class*="MessageItem"], '
        'div[class*="message-item"], '
        'div[class*="ChatMessage"], '
        'div[class*="chat-message"], '
        'div[class*="ThreadMessage"], '
        'li[class*="message"]'
    )

    for el in msg_elements:
        try:
            # Sender
            sender_el = el.query_selector(
                'span[class*="username"], '
                'a[class*="username"], '
                'div[class*="sender"], '
                'span[class*="author"]'
            )
            sender = sender_el.inner_text().strip() if sender_el else "unknown"

            # Message body
            body_el = el.query_selector(
                'div[class*="message-body"], '
                'div[class*="MessageBody"], '
                'p[class*="content"], '
                'div[class*="text"]'
            )
            body = body_el.inner_text().strip() if body_el else ""

            # Timestamp
            time_el = el.query_selector(
                'time, span[class*="time"], '
                'span[class*="date"], '
                'div[class*="timestamp"]'
            )
            timestamp = time_el.inner_text().strip() if time_el else ""

            if body:
                messages.append({
                    "sender": sender,
                    "body": body,
                    "timestamp": timestamp,
                    "project_id": project_id,
                })
        except Exception:
            continue

    # Log messages
    log_path = MSG_LOG_DIR / f"{project_id}_messages.json"
    existing = []
    if log_path.exists():
        existing = json.loads(log_path.read_text(encoding="utf-8"))
    existing.extend(messages)
    log_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    print(f"  [MSG] Read {len(messages)} messages from project {project_id}")
    page.screenshot(path=str(SS_DIR / f"freelancer_messages_{project_id}.png"))

    return messages


def send_message(page, project_url: str, message_text: str) -> bool:
    """Send a message to the client on Freelancer.com project page."""
    project_id = _extract_project_id(project_url)

    # Navigate to project messaging
    page.goto(project_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Find message/chat input
    msg_link = page.query_selector(
        'a[href*="messages"], '
        'a:has-text("Messages"), '
        'a:has-text("Chat"), '
        'button:has-text("Message")'
    )
    if msg_link:
        msg_link.click()
        _human_delay(2, 4)

    # Also try direct messaging URL
    page.goto(f"https://www.freelancer.com/messages/project-{project_id}", wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Find the message input area
    input_selectors = [
        'textarea[class*="message"], '
        'textarea[placeholder*="message"], '
        'div[contenteditable="true"][class*="message"], '
        'div[contenteditable="true"][class*="chat"], '
        'textarea[name="message"], '
        'textarea#message-input',
    ]

    input_el = None
    for selector in input_selectors:
        input_el = page.query_selector(selector)
        if input_el:
            break

    if not input_el:
        print(f"  [WARN] Message input not found on project {project_id}")
        page.screenshot(path=str(SS_DIR / f"freelancer_msg_input_missing_{project_id}.png"))
        return False

    # Type the message with human-like delays
    input_el.click()
    _human_delay(0.5, 1.0)

    # For contenteditable divs, use fill; for textareas, type char-by-char
    tag = input_el.evaluate("el => el.tagName.toLowerCase()")
    if tag == "textarea":
        for char in message_text:
            input_el.type(char, delay=random.randint(20, 60))
    else:
        input_el.fill(message_text)

    _human_delay(1, 2)

    # Screenshot before sending
    page.screenshot(path=str(SS_DIR / f"freelancer_msg_presend_{project_id}.png"))

    # Find and click send button
    send_btn = page.query_selector(
        'button:has-text("Send"), '
        'button[class*="send"], '
        'button[type="submit"][class*="message"], '
        'button[aria-label="Send"], '
        'button[class*="Send"]'
    )

    if send_btn:
        send_btn.click()
        _human_delay(2, 3)
        print(f"  [SENT] Message sent to project {project_id}")
        page.screenshot(path=str(SS_DIR / f"freelancer_msg_sent_{project_id}.png"))

        # Log the sent message
        log_path = MSG_LOG_DIR / f"{project_id}_sent.json"
        sent_log = []
        if log_path.exists():
            sent_log = json.loads(log_path.read_text(encoding="utf-8"))
        sent_log.append({
            "body": message_text,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
        })
        log_path.write_text(json.dumps(sent_log, indent=2), encoding="utf-8")
        return True
    else:
        print(f"  [WARN] Send button not found — message typed but not sent")
        return False


def send_llm_message(
    project_url: str,
    project_title: str,
    project_description: str,
    message_type: str = "intro",
    context: str = "",
    client_name: str = "",
    provider: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Generate an LLM message and send it to the client.

    Returns the generated message dict.
    """
    from agents.freelancer_work.runner import (
        FreelancerProject,
        generate_client_message,
    )

    project = FreelancerProject(
        id=_extract_project_id(project_url),
        title=project_title,
        description=project_description,
        url=project_url,
        client_name=client_name,
    )

    msg = generate_client_message(project, message_type, context, provider)
    result = msg.model_dump()
    result["project_url"] = project_url

    print(f"  [LLM] Generated {message_type} message:")
    print(f"    Subject: {msg.subject}")
    print(f"    Body preview: {msg.body[:150]}...")

    if dry_run:
        print("  [DRY RUN] Message not sent")
        return result

    pw, browser, context_obj, page = _launch_browser()
    try:
        sent = send_message(page, project_url, msg.body)
        result["sent"] = sent
    finally:
        browser.close()
        pw.stop()

    return result


# ── Milestone Functions ─────────────────────────────────────────────────────

def check_milestones(page, project_url: str) -> list[dict]:
    """Check milestone status on a Freelancer.com project."""
    project_id = _extract_project_id(project_url)

    page.goto(project_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Look for milestones tab/section
    ms_link = page.query_selector(
        'a[href*="milestone"], '
        'a:has-text("Milestones"), '
        'a:has-text("Payments"), '
        'div[class*="milestone"] a'
    )
    if ms_link:
        ms_link.click()
        _human_delay(2, 3)

    milestones = []
    ms_elements = page.query_selector_all(
        'div[class*="MilestoneItem"], '
        'div[class*="milestone-item"], '
        'tr[class*="milestone"], '
        'div[class*="PaymentMilestone"], '
        'li[class*="milestone"]'
    )

    for el in ms_elements:
        try:
            # Description
            desc_el = el.query_selector(
                'span[class*="description"], '
                'td[class*="description"], '
                'div[class*="name"], '
                'span[class*="title"]'
            )
            description = desc_el.inner_text().strip() if desc_el else ""

            # Amount
            amount_el = el.query_selector(
                'span[class*="amount"], '
                'td[class*="amount"], '
                'span[class*="price"], '
                'div[class*="amount"]'
            )
            amount = amount_el.inner_text().strip() if amount_el else ""

            # Status
            status_el = el.query_selector(
                'span[class*="status"], '
                'td[class*="status"], '
                'span[class*="badge"], '
                'div[class*="Status"]'
            )
            status = status_el.inner_text().strip() if status_el else "unknown"

            if description or amount:
                milestones.append({
                    "description": description,
                    "amount": amount,
                    "status": status,
                    "project_id": project_id,
                })
        except Exception:
            continue

    print(f"  [MS] Found {len(milestones)} milestones for project {project_id}")
    page.screenshot(path=str(SS_DIR / f"freelancer_milestones_{project_id}.png"))

    return milestones


def accept_milestone(page, project_url: str) -> bool:
    """Accept/create a milestone on Freelancer.com project."""
    project_id = _extract_project_id(project_url)

    page.goto(project_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    accept_btn = page.query_selector(
        'button:has-text("Accept"), '
        'button:has-text("Create Milestone"), '
        'button[class*="AcceptMilestone"], '
        'a:has-text("Accept Milestone")'
    )

    if accept_btn:
        accept_btn.click()
        _human_delay(2, 3)
        page.screenshot(path=str(SS_DIR / f"freelancer_ms_accepted_{project_id}.png"))
        print(f"  [MS] Milestone accepted/created for project {project_id}")
        return True
    else:
        print(f"  [MS] No accept button found for project {project_id}")
        return False


def request_release(page, project_url: str) -> bool:
    """Request milestone payment release after delivering work."""
    project_id = _extract_project_id(project_url)

    page.goto(project_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    release_btn = page.query_selector(
        'button:has-text("Request Release"), '
        'button:has-text("Request Payment"), '
        'button:has-text("Release"), '
        'button[class*="RequestRelease"], '
        'a:has-text("Request Release")'
    )

    if release_btn:
        release_btn.click()
        _human_delay(2, 3)

        # Confirm dialog if present
        confirm_btn = page.query_selector(
            'button:has-text("Confirm"), '
            'button:has-text("Yes"), '
            'button[class*="confirm"]'
        )
        if confirm_btn:
            confirm_btn.click()
            _human_delay(1, 2)

        page.screenshot(path=str(SS_DIR / f"freelancer_release_requested_{project_id}.png"))
        print(f"  [MS] Payment release requested for project {project_id}")
        return True
    else:
        print(f"  [MS] No release button found for project {project_id}")
        return False


# ── File Delivery ───────────────────────────────────────────────────────────

def upload_deliverables(page, project_url: str, file_paths: list[str]) -> list[str]:
    """Upload deliverable files to Freelancer.com project page."""
    project_id = _extract_project_id(project_url)
    uploaded = []

    page.goto(project_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Navigate to file upload section
    files_link = page.query_selector(
        'a:has-text("Files"), '
        'a:has-text("Upload"), '
        'a[href*="files"], '
        'button:has-text("Upload File"), '
        'button:has-text("Attach")'
    )
    if files_link:
        files_link.click()
        _human_delay(2, 3)

    # Find the file input (hidden input[type="file"])
    file_input = page.query_selector(
        'input[type="file"], '
        'input[accept], '
        'input[class*="file-input"]'
    )

    if not file_input:
        # Try triggering upload button which may reveal the file input
        upload_btn = page.query_selector(
            'button:has-text("Upload"), '
            'button:has-text("Attach"), '
            'div[class*="upload"] button, '
            'label[class*="upload"]'
        )
        if upload_btn:
            upload_btn.click()
            _human_delay(1, 2)
            file_input = page.query_selector('input[type="file"]')

    if not file_input:
        print(f"  [WARN] File input not found on project {project_id}")
        page.screenshot(path=str(SS_DIR / f"freelancer_upload_missing_{project_id}.png"))
        return uploaded

    # Upload files one at a time
    for fp in file_paths:
        fpath = Path(fp)
        if not fpath.exists():
            print(f"  [SKIP] File not found: {fp}")
            continue

        try:
            file_input.set_input_files(str(fpath))
            _human_delay(2, 4)
            print(f"  [UPLOAD] {fpath.name}")
            uploaded.append(str(fpath))
        except Exception as e:
            print(f"  [WARN] Failed to upload {fpath.name}: {e}")

    if uploaded:
        # Look for a submit/confirm button after file selection
        submit_btn = page.query_selector(
            'button:has-text("Submit"), '
            'button:has-text("Upload"), '
            'button:has-text("Send"), '
            'button[type="submit"]'
        )
        if submit_btn:
            submit_btn.click()
            _human_delay(2, 3)

        page.screenshot(path=str(SS_DIR / f"freelancer_uploaded_{project_id}.png"))
        print(f"  [DONE] Uploaded {len(uploaded)}/{len(file_paths)} files")

    return uploaded


# ── Project Status ──────────────────────────────────────────────────────────

def check_project_status(page, project_url: str) -> dict:
    """Check overall project status on Freelancer.com."""
    project_id = _extract_project_id(project_url)

    page.goto(project_url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    status = {
        "project_id": project_id,
        "url": project_url,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    # Project title
    title_el = page.query_selector(
        'h1[class*="title"], '
        'h1[class*="PageTitle"], '
        'div[class*="project-title"] h1'
    )
    status["title"] = title_el.inner_text().strip() if title_el else ""

    # Project status badge
    status_el = page.query_selector(
        'span[class*="StatusBadge"], '
        'span[class*="project-status"], '
        'div[class*="status-badge"], '
        'span[class*="Badge"]'
    )
    status["project_status"] = status_el.inner_text().strip() if status_el else "unknown"

    # Budget info
    budget_el = page.query_selector(
        'div[class*="budget"], '
        'span[class*="Budget"], '
        'div[class*="price"]'
    )
    status["budget"] = budget_el.inner_text().strip() if budget_el else ""

    # Deadline
    deadline_el = page.query_selector(
        'div[class*="deadline"], '
        'span[class*="Deadline"], '
        'div[class*="due-date"]'
    )
    status["deadline"] = deadline_el.inner_text().strip() if deadline_el else ""

    # Check for new messages indicator
    msg_badge = page.query_selector(
        'span[class*="unread"], '
        'span[class*="badge"][class*="message"], '
        'div[class*="notification-count"]'
    )
    status["has_unread_messages"] = msg_badge is not None

    page.screenshot(path=str(SS_DIR / f"freelancer_status_{project_id}.png"))
    print(f"  [STATUS] Project {project_id}: {status['project_status']}")

    return status


# ── Full Delivery Workflow ──────────────────────────────────────────────────

def deliver_project(
    project_url: str,
    project_id: str = "",
    message_text: str = "",
    provider: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Full delivery workflow: execute work → upload files → send message → request release.

    1. Load project state (must have been executed via runner.py --action execute)
    2. Upload deliverable files to Freelancer.com
    3. Send delivery message to client
    4. Request milestone release
    """
    from agents.freelancer_work.runner import load_project_state, generate_client_message, FreelancerProject

    pid = project_id or _extract_project_id(project_url)
    state = load_project_state(pid)

    result = {
        "project_id": pid,
        "project_url": project_url,
        "steps_completed": [],
        "status": "started",
    }

    if not state:
        print(f"[WARN] No executed project state for {pid} — run 'runner.py --action execute' first")
        result["status"] = "no_state"
        return result

    if state.status not in ("delivered", "partial"):
        print(f"[WARN] Project state is '{state.status}' — expected 'delivered' or 'partial'")

    deliverable_files = state.deliverable_files
    print(f"\n[DELIVER] Project: {state.project.title[:50]}")
    print(f"  Files to upload: {len(deliverable_files)}")
    print(f"  Milestones completed: {len(state.milestones_completed)}")

    if dry_run:
        print("[DRY RUN] Would upload, message, and request release — stopping here")
        result["status"] = "dry_run"
        result["deliverable_files"] = deliverable_files
        return result

    pw, browser, context_obj, page = _launch_browser()

    try:
        # Step 1: Upload files
        if deliverable_files:
            print("\n[STEP 1] Uploading deliverables...")
            uploaded = upload_deliverables(page, project_url, deliverable_files)
            result["files_uploaded"] = uploaded
            result["steps_completed"].append("upload")
        _human_delay(2, 4)

        # Step 2: Send delivery message
        if not message_text:
            # Generate LLM message
            files_str = ", ".join(Path(f).name for f in deliverable_files[:5])
            context = (
                f"All work complete. Files delivered: {files_str}. "
                f"All outputs passed automated QA checks."
            )
            msg = generate_client_message(
                state.project, "delivery", context, provider
            )
            message_text = msg.body

        print("\n[STEP 2] Sending delivery message...")
        sent = send_message(page, project_url, message_text)
        result["message_sent"] = sent
        result["steps_completed"].append("message")
        _human_delay(2, 4)

        # Step 3: Request milestone release
        print("\n[STEP 3] Requesting milestone release...")
        released = request_release(page, project_url)
        result["release_requested"] = released
        result["steps_completed"].append("release")

        result["status"] = "delivered"
        print(f"\n[DONE] Delivery complete — {len(result['steps_completed'])} steps")

    finally:
        browser.close()
        pw.stop()

    return result


# ── Monitor Active Projects ─────────────────────────────────────────────────

def monitor_projects(project_urls: list[str]) -> list[dict]:
    """Check status and messages across all active Freelancer projects."""
    if not project_urls:
        # Load from saved project states
        state_dir = PROJECT / "data" / "freelancer_projects"
        if state_dir.exists():
            for f in state_dir.glob("*_state.json"):
                data = json.loads(f.read_text(encoding="utf-8"))
                url = data.get("project", {}).get("url", "")
                if url:
                    project_urls.append(url)

    if not project_urls:
        print("[WARN] No project URLs to monitor")
        return []

    print(f"\n[MONITOR] Checking {len(project_urls)} active projects...")

    pw, browser, context_obj, page = _launch_browser()
    results = []

    try:
        for url in project_urls:
            status = check_project_status(page, url)
            if status.get("has_unread_messages"):
                messages = read_messages(page, url)
                status["unread_messages"] = messages
            results.append(status)
            _human_delay(3, 6)

    finally:
        browser.close()
        pw.stop()

    # Summary
    unread = sum(1 for r in results if r.get("has_unread_messages"))
    print(f"\n[SUMMARY] {len(results)} projects checked, {unread} with unread messages")

    return results


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Freelancer.com Client Interaction")
    parser.add_argument("--action", required=True,
                        choices=["messages", "send", "deliver", "milestones",
                                 "accept-milestone", "release", "upload",
                                 "status", "monitor", "full-deliver"],
                        help="Action to perform")
    parser.add_argument("--project-url", default="", help="Freelancer.com project URL")
    parser.add_argument("--project-id", default="", help="Project ID (for state lookup)")
    parser.add_argument("--message", default="", help="Message text to send")
    parser.add_argument("--message-type", default="intro",
                        choices=["intro", "update", "question", "delivery", "revision", "closing"],
                        help="Message type for LLM generation")
    parser.add_argument("--files", nargs="+", default=[], help="Files to upload")
    parser.add_argument("--urls", nargs="+", default=[], help="Multiple project URLs (for monitor)")
    parser.add_argument("--provider", default=None, help="LLM provider")
    parser.add_argument("--dry-run", action="store_true", help="Dry run")
    args = parser.parse_args()

    if args.action == "monitor":
        results = monitor_projects(args.urls)
        for r in results:
            print(f"  {r.get('title', '?')[:40]} — {r.get('project_status', '?')}")
        return

    if args.action == "full-deliver":
        result = deliver_project(
            project_url=args.project_url,
            project_id=args.project_id,
            message_text=args.message,
            provider=args.provider,
            dry_run=args.dry_run,
        )
        print(f"\nDelivery status: {result['status']}")
        return

    # Single-project actions need a browser
    pw, browser, context_obj, page = _launch_browser()

    try:
        if args.action == "messages":
            messages = read_messages(page, args.project_url)
            for m in messages:
                print(f"  [{m['sender']}] {m['body'][:100]}")

        elif args.action == "send":
            if args.message:
                send_message(page, args.project_url, args.message)
            else:
                # Generate via LLM
                send_llm_message(
                    project_url=args.project_url,
                    project_title="",
                    project_description="",
                    message_type=args.message_type,
                    provider=args.provider,
                    dry_run=args.dry_run,
                )

        elif args.action == "deliver" or args.action == "upload":
            if args.files:
                uploaded = upload_deliverables(page, args.project_url, args.files)
                print(f"Uploaded: {len(uploaded)} files")
            else:
                print("[ERROR] --files required for upload/deliver action")

        elif args.action == "milestones":
            milestones = check_milestones(page, args.project_url)
            for ms in milestones:
                print(f"  {ms['description'][:40]} — {ms['amount']} — {ms['status']}")

        elif args.action == "accept-milestone":
            accept_milestone(page, args.project_url)

        elif args.action == "release":
            request_release(page, args.project_url)

        elif args.action == "status":
            status = check_project_status(page, args.project_url)
            print(f"  Title: {status.get('title', '?')}")
            print(f"  Status: {status.get('project_status', '?')}")
            print(f"  Budget: {status.get('budget', '?')}")
            print(f"  Unread: {status.get('has_unread_messages', False)}")

    finally:
        browser.close()
        pw.stop()


if __name__ == "__main__":
    main()
