"""Guru.com Job Hunt — automated project search, scoring, and proposal submission.

Opens Edge browser, searches Guru for matching projects, scores them
against our 20 agent capabilities, generates tailored proposals, and submits bids.

Usage:
    python -m automation.guru_jobhunt                          # Full run: search + bid
    python -m automation.guru_jobhunt --scan-only              # Search + score, no submit
    python -m automation.guru_jobhunt --search "data entry"   # Custom search
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
DATA_DIR = PROJECT / "data" / "guru_jobs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
JOB_LOG = DATA_DIR / "project_log.jsonl"
BID_LOG = DATA_DIR / "bids_submitted.json"

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# Guru job search URL
GURU_SEARCH_BASE = "https://www.guru.com/d/jobs/"

# ── Search queries targeting our 20 agent capabilities ──────────────────────
SEARCH_QUERIES = [
    "data entry",
    "web scraping python",
    "email marketing campaign",
    "seo content writing",
    "lead generation",
    "cold email outreach",
    "content writing",
    "social media management",
    "product descriptions",
    "bookkeeping",
    "resume writing",
    "market research",
    "business plan writing",
    "ad copywriting",
    "technical documentation",
    "press release writing",
    "proposal writing",
    "crm data management",
    "document data extraction",
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
    """Score a Guru project 0-1 based on keyword match to our agents."""
    text = f"{title} {description}".lower()
    core_hits = sum(1 for kw in CORE_KEYWORDS if kw in text)
    bonus_hits = sum(1 for kw in BONUS_KEYWORDS if kw in text)
    negs = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    raw = core_hits * 0.07 + bonus_hits * 0.03 - negs * 0.15
    return max(0.0, min(1.0, raw))


def generate_proposal(title: str, description: str) -> str:
    """Generate a tailored proposal using LLM with template fallback."""
    prompt = f"""Write a short, professional freelancer proposal (150-200 words) for this Guru.com job:

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

    return f"""Hi there,

I came across your project "{title}" and I'm confident I can help.

I run BIT RAGE SYSTEMS, an AI-powered business services agency. We specialise in exactly this type of work and use advanced automation tools to deliver fast, accurate results.

I'd love to discuss your requirements in more detail and get started quickly.

Best regards,
BIT RAGE SYSTEMS — AI-Powered Business Services"""


# ── Search Projects ─────────────────────────────────────────────────────────

def search_projects(page, query: str = "", max_pages: int = 3) -> list[dict]:
    """Search Guru for projects matching our capabilities."""
    projects = []
    previous_bids = _load_bid_history()

    for page_num in range(1, max_pages + 1):
        # Guru search: /d/jobs/q/keyword/pg/N/
        q_part = f"q/{query.replace(' ', '-')}/" if query else ""
        pg_part = f"pg/{page_num}/" if page_num > 1 else ""
        url = f"{GURU_SEARCH_BASE}{q_part}{pg_part}"

        print(f"  >> Searching Guru page {page_num}: {url[:80]}...")

        page.goto(url, wait_until="domcontentloaded")
        _human_delay(3, 5)
        _handle_challenge(page)

        # Guru job cards
        project_els = page.query_selector_all(
            'div[class*="jobRecord"], div[class*="job-record"], '
            'div[class*="JobListing"], article[class*="job"], '
            'div.jobList > div, tr.jobRecord, '
            'div[class*="record-list"] > div'
        )

        if not project_els:
            project_els = page.query_selector_all(
                'div[data-job-id], li[class*="job"], '
                'div.services__list > div'
            )

        for el in project_els[:15]:
            try:
                # Title
                title_el = el.query_selector('h2 a, h3 a, a[class*="title"], a[class*="jobTitle"]')
                title = title_el.inner_text().strip() if title_el else ""
                if not title or len(title) < 5:
                    continue

                href = title_el.get_attribute("href") if title_el else ""
                proj_url = href if href and href.startswith("http") else f"https://www.guru.com{href}" if href else ""

                # Description
                desc_el = el.query_selector('p, div[class*="desc"], div[class*="detail"], div[class*="snippet"]')
                desc = desc_el.inner_text().strip()[:500] if desc_el else ""

                # Budget
                budget_el = el.query_selector('[class*="budget"], [class*="price"], [class*="cost"], [class*="Budget"]')
                budget = budget_el.inner_text().strip() if budget_el else ""

                # Skills
                skills_els = el.query_selector_all('[class*="skill"] a, [class*="tag"]')
                skills = [s.inner_text().strip() for s in skills_els[:8]]

                # Project ID from URL
                pid = proj_url.split("/")[-1].split("?")[0] if proj_url else title[:40]

                score = score_project(title, f"{desc} {' '.join(skills)}")

                project = {
                    "platform": "guru",
                    "project_id": pid,
                    "title": title[:150],
                    "description": desc,
                    "budget": budget,
                    "skills": skills,
                    "url": proj_url,
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

    print(f"\n  Total Guru projects found: {len(projects)}")
    return projects


# ── Submit Proposal ─────────────────────────────────────────────────────────

def submit_proposal(page, project: dict, proposal_text: str) -> bool:
    """Navigate to a Guru project and submit a proposal/quote."""
    url = project.get("url", "")
    if not url:
        return False

    print(f"\n  [BID] Submitting proposal for: {project['title'][:50]}...")

    page.goto(url, wait_until="domcontentloaded")
    _human_delay(2, 4)
    _handle_challenge(page)

    # Click "Submit a Quote" / "Submit Proposal" button
    for sel in [
        'a:has-text("Submit a Quote")',
        'button:has-text("Submit a Quote")',
        'a:has-text("Submit Quote")',
        'a:has-text("Submit Proposal")',
        'button:has-text("Apply")',
        'a[class*="submit-quote"]',
        'a[href*="submitQuote"]',
    ]:
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            btn.click()
            _human_delay(2, 3)
            break

    # Fill proposal/cover letter
    filled = False
    for sel in [
        'textarea[name*="cover"]',
        'textarea[name*="proposal"]',
        'textarea[name*="message"]',
        'textarea[placeholder*="proposal"]',
        'textarea[id*="cover"]',
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
        page.screenshot(path=str(SS_DIR / f"guru_bid_fail_{int(time.time())}.png"))
        return False

    # Submit
    submitted = False
    for sel in [
        'button:has-text("Submit")',
        'button:has-text("Send Quote")',
        'button:has-text("Send Proposal")',
        'input[type="submit"]',
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
            "platform": "guru",
            "project_id": project.get("project_id", ""),
            "title": project.get("title", ""),
            "score": project.get("score", 0),
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        })
        print(f"    [OK] Quote submitted!")
    else:
        print("    [WARN] Submit button not found")
        page.screenshot(path=str(SS_DIR / f"guru_submit_fail_{int(time.time())}.png"))

    return submitted


# ── Main ────────────────────────────────────────────────────────────────────

def run_hunt(scan_only: bool = False, custom_search: str = ""):
    """Full Guru job hunt cycle."""
    pw, browser, _, page = _launch_browser()

    try:
        queries = [custom_search] if custom_search else SEARCH_QUERIES
        all_projects = []
        bids_sent = 0

        for q in queries:
            print(f"\n{'='*60}")
            print(f"  GURU SEARCH: {q}")
            print(f"{'='*60}")

            found = search_projects(page, query=q, max_pages=2)
            all_projects.extend(found)

            if not scan_only:
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
        print(f"  GURU HUNT SUMMARY")
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
    parser = argparse.ArgumentParser(description="Guru.com Job Hunt")
    parser.add_argument("--scan-only", action="store_true", help="Search only, don't submit proposals")
    parser.add_argument("--search", type=str, default="", help="Custom search query")
    args = parser.parse_args()

    run_hunt(scan_only=args.scan_only, custom_search=args.search)


if __name__ == "__main__":
    main()
