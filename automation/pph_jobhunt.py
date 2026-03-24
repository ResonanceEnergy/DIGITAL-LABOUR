"""PeoplePerHour Job Hunt — automated project search, scoring, and proposal submission.

Opens Edge browser, searches PPH for matching projects, scores them
against our 20 agent capabilities, generates tailored proposals, and submits offers.

Usage:
    python -m automation.pph_jobhunt                          # Full run: search + send offers
    python -m automation.pph_jobhunt --scan-only              # Search + score, no submit
    python -m automation.pph_jobhunt --search "data entry"   # Custom search
"""

import argparse
import json
import os
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
DATA_DIR = PROJECT / "data" / "pph_jobs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
JOB_LOG = DATA_DIR / "project_log.jsonl"
BID_LOG = DATA_DIR / "proposals_sent.json"

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# PPH job search URL — keyword appended
PPH_SEARCH_BASE = "https://www.peopleperhour.com/freelance-jobs"

# ── Search queries targeting our 20 agent capabilities ──────────────────────
SEARCH_QUERIES = [
    "data entry",
    "web scraping",
    "email marketing",
    "seo content writing",
    "lead generation",
    "cold email outreach",
    "content writing",
    "social media management",
    "product descriptions",
    "bookkeeping",
    "resume writing",
    "market research",
    "business plan",
    "google ads copy",
    "technical documentation",
    "press release",
    "proposal writing",
    "crm data",
    "document extraction",
    "customer support",
]

# Scoring keywords — matched to our agent capabilities
CORE_KEYWORDS = [
    "ai", "automation", "automate", "python", "data entry", "data processing",
    "web scraping", "email marketing", "email campaign", "seo", "blog",
    "lead generation", "cold email", "outreach", "content writing",
    "social media", "product description", "bookkeeping", "resume",
    "market research", "business plan", "ad copy", "technical writing",
    "press release", "proposal", "crm", "document extraction",
    "support ticket", "help desk", "copywriting",
]

BONUS_KEYWORDS = [
    "csv", "excel", "json", "pdf", "invoice", "contract",
    "newsletter", "drip campaign", "linkedin", "instagram",
    "amazon listing", "shopify", "etsy", "google ads", "facebook ads",
    "swot analysis", "competitive analysis", "api documentation",
    "quickbooks", "xero", "salesforce", "hubspot",
]

NEGATIVE_KEYWORDS = [
    "blockchain", "solidity", "react native", "ios app",
    "android app", "unity", "game development", "wordpress theme",
    "php developer", "java spring", ".net developer", "c# developer",
    "video editing", "graphic design", "3d modeling", "animation",
]

MIN_SCORE = 0.25
MAX_BIDS_PER_RUN = 10


def _human_delay(min_s: float = 2.0, max_s: float = 5.0):
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
        print("    [!] Challenge/CAPTCHA — waiting for manual solve (up to 120s)...")
        for _ in range(120):
            time.sleep(1)
            body_text = (page.inner_text("body") or "").lower()[:2000]
            if not any(ind in body_text for ind in indicators):
                print("    [+] Challenge cleared!")
                return
        print("    [WARN] Challenge not cleared after 120s — continuing anyway")


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


def _load_bid_history() -> set:
    """Load previously-bid project IDs."""
    if BID_LOG.exists():
        data = json.loads(BID_LOG.read_text(encoding="utf-8"))
        return set(str(b.get("project_id", "")) for b in data if b.get("project_id"))
    return set()


def _save_bid(bid: dict):
    bids = []
    if BID_LOG.exists():
        bids = json.loads(BID_LOG.read_text(encoding="utf-8"))
    bids.append(bid)
    BID_LOG.write_text(json.dumps(bids, indent=2), encoding="utf-8")


def _log_project(project: dict):
    with open(JOB_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(project) + "\n")


def score_project(title: str, description: str) -> float:
    """Score a PPH project 0-1 based on keyword match to our agents."""
    text = f"{title} {description}".lower()
    core_hits = sum(1 for kw in CORE_KEYWORDS if kw in text)
    bonus_hits = sum(1 for kw in BONUS_KEYWORDS if kw in text)
    negs = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    raw = core_hits * 0.07 + bonus_hits * 0.03 - negs * 0.15
    return max(0.0, min(1.0, raw))


def generate_proposal(title: str, description: str) -> str:
    """Generate a tailored proposal using LLM with template fallback."""
    prompt = f"""Write a short, professional freelancer proposal (150-200 words) for this PeoplePerHour job:

Title: {title}
Description: {description[:500]}

The proposal should:
- Open with a hook that shows you understand the client's need
- Briefly mention relevant experience with similar projects
- Highlight that you use AI-assisted tools for speed and accuracy
- End with a clear call to action
- Sound human, warm, and confident — not generic

Sign off as "BIT RAGE SYSTEMS — AI-Powered Business Services"
"""
    # Try OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"    [LLM-WARN] OpenAI failed: {e}")

    # Template fallback
    return f"""Hi there,

I came across your project "{title}" and I'm confident I can help.

I run BIT RAGE SYSTEMS, an AI-powered business services agency. We specialise in exactly this type of work and use advanced automation tools to deliver fast, accurate results.

I'd love to discuss your requirements in more detail and get started quickly.

Best regards,
BIT RAGE SYSTEMS — AI-Powered Business Services"""


# ── Search Projects ─────────────────────────────────────────────────────────

def search_projects(page, query: str = "", max_pages: int = 3) -> list[dict]:
    """Search PPH for projects matching our capabilities."""
    search_url = f"{PPH_SEARCH_BASE}?keyword={query.replace(' ', '+')}" if query else PPH_SEARCH_BASE
    projects = []
    previous_bids = _load_bid_history()

    for page_num in range(1, max_pages + 1):
        url = f"{search_url}&page={page_num}" if page_num > 1 else search_url
        print(f"  >> Searching PPH page {page_num}: {url[:80]}...")

        page.goto(url, wait_until="domcontentloaded")
        _human_delay(3, 5)
        _handle_challenge(page)

        # PPH project cards
        project_els = page.query_selector_all(
            'div[class*="job-listing"], div[class*="project-listing"], '
            'article[class*="job"], li[class*="job"], '
            'div[class*="freelance-job"], div[class*="JobCard"]'
        )

        if not project_els:
            # Fallback: try generic card selectors
            project_els = page.query_selector_all(
                'div.listings-container > div, '
                'ul.job-list > li, '
                'div[data-job-id]'
            )

        for el in project_els[:15]:
            try:
                # Title
                title_el = el.query_selector('h3 a, h2 a, a[class*="title"], a[class*="job-title"]')
                title = title_el.inner_text().strip() if title_el else ""
                if not title or len(title) < 5:
                    continue

                href = title_el.get_attribute("href") if title_el else ""
                url = href if href and href.startswith("http") else f"https://www.peopleperhour.com{href}" if href else ""

                # Description
                desc_el = el.query_selector('p, div[class*="desc"], div[class*="detail"]')
                desc = desc_el.inner_text().strip()[:500] if desc_el else ""

                # Budget
                budget_el = el.query_selector('[class*="budget"], [class*="price"], [class*="cost"]')
                budget = budget_el.inner_text().strip() if budget_el else ""

                # Project ID from URL
                pid = url.split("/")[-1].split("?")[0] if url else title[:40]

                score = score_project(title, desc)

                project = {
                    "platform": "pph",
                    "project_id": pid,
                    "title": title[:150],
                    "description": desc,
                    "budget": budget,
                    "url": url,
                    "score": round(score, 3),
                    "already_bid": pid in previous_bids,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }

                projects.append(project)
                _log_project(project)

                flag = "✓" if score >= MIN_SCORE else "·"
                bid_flag = " [ALREADY BID]" if pid in previous_bids else ""
                print(f"    {flag} [{score:.2f}] {title[:50]} {budget}{bid_flag}")

            except Exception:
                continue

        _human_delay(2, 4)

    print(f"\n  Total PPH projects found: {len(projects)}")
    return projects


# ── Submit Proposal ─────────────────────────────────────────────────────────

def submit_proposal(page, project: dict, proposal_text: str) -> bool:
    """Navigate to a PPH project and submit a proposal."""
    url = project.get("url", "")
    if not url:
        return False

    print(f"\n  [BID] Submitting proposal for: {project['title'][:50]}...")

    page.goto(url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Look for "Send Proposal" / "Make an Offer" button
    for sel in [
        'button:has-text("Send Proposal")',
        'button:has-text("Make an Offer")',
        'a:has-text("Send Proposal")',
        'a:has-text("Make an Offer")',
        'button:has-text("Apply")',
        'a:has-text("Apply Now")',
    ]:
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            btn.click()
            _human_delay(2, 3)
            break

    # Fill proposal text
    filled = False
    for sel in [
        'textarea[name*="proposal"]',
        'textarea[name*="cover"]',
        'textarea[placeholder*="proposal"]',
        'textarea[placeholder*="message"]',
        'textarea[class*="proposal"]',
        'textarea',
    ]:
        el = page.query_selector(sel)
        if el and el.is_visible():
            el.fill(proposal_text)
            filled = True
            _human_delay(1, 2)
            break

    if not filled:
        print("    [WARN] No proposal textarea found")
        page.screenshot(path=str(SS_DIR / f"pph_bid_fail_{int(time.time())}.png"))
        return False

    # Submit
    submitted = False
    for sel in [
        'button:has-text("Submit")',
        'button:has-text("Send")',
        'button:has-text("Apply")',
        'button[type="submit"]',
    ]:
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            btn.click()
            submitted = True
            _human_delay(2, 3)
            break

    if submitted:
        _save_bid({
            "platform": "pph",
            "project_id": project.get("project_id", ""),
            "title": project.get("title", ""),
            "score": project.get("score", 0),
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        })
        print(f"    [OK] Proposal sent!")
    else:
        print("    [WARN] Submit button not found")
        page.screenshot(path=str(SS_DIR / f"pph_submit_fail_{int(time.time())}.png"))

    return submitted


# ── Main ────────────────────────────────────────────────────────────────────

def run_hunt(scan_only: bool = False, custom_search: str = ""):
    """Full PPH job hunt cycle."""
    pw, browser, _, page = _launch_browser()

    try:
        queries = [custom_search] if custom_search else SEARCH_QUERIES
        all_projects = []
        bids_sent = 0

        for q in queries:
            print(f"\n{'='*60}")
            print(f"  PPH SEARCH: {q}")
            print(f"{'='*60}")

            found = search_projects(page, query=q, max_pages=2)
            all_projects.extend(found)

            if not scan_only:
                # Bid on top-scoring projects we haven't bid on yet
                eligible = [
                    p for p in found
                    if p["score"] >= MIN_SCORE and not p["already_bid"]
                ]
                eligible.sort(key=lambda x: x["score"], reverse=True)

                for proj in eligible[:3]:
                    if bids_sent >= MAX_BIDS_PER_RUN:
                        print(f"\n  [CAP] Max bids ({MAX_BIDS_PER_RUN}) reached.")
                        break

                    proposal = generate_proposal(proj["title"], proj["description"])
                    if submit_proposal(page, proj, proposal):
                        bids_sent += 1

                if bids_sent >= MAX_BIDS_PER_RUN:
                    break

            _human_delay(5, 10)

        # Summary
        scored = [p for p in all_projects if p["score"] >= MIN_SCORE]
        print(f"\n{'='*60}")
        print(f"  PPH HUNT SUMMARY")
        print(f"  Total scanned: {len(all_projects)}")
        print(f"  Above threshold ({MIN_SCORE}): {len(scored)}")
        print(f"  Proposals sent: {bids_sent}")
        print(f"{'='*60}")

        print("\n  Leaving browser open for manual review.")
        input("  Press Enter to close browser...")

    finally:
        browser.close()
        pw.stop()


def main():
    parser = argparse.ArgumentParser(description="PeoplePerHour Job Hunt")
    parser.add_argument("--scan-only", action="store_true", help="Search only, don't submit proposals")
    parser.add_argument("--search", type=str, default="", help="Custom search query")
    args = parser.parse_args()

    run_hunt(scan_only=args.scan_only, custom_search=args.search)


if __name__ == "__main__":
    main()
