"""Upwork Job Hunt — automated job search, matching, and proposal submission.

Opens Edge browser, searches Upwork for matching jobs, scores them,
generates tailored proposals, and submits applications.

Usage:
    python -m automation.upwork_jobhunt              # Full run: search + apply
    python -m automation.upwork_jobhunt --scan-only   # Search + score, no submit
    python -m automation.upwork_jobhunt --search "ai chatbot"  # Custom search
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

# Persistent Edge profile — retains history, cookies, extensions
EDGE_PROFILE_DIR = PROJECT / "data" / "platform_browser" / "edge_profile"
EDGE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

COOKIE_FILE = PROJECT / "data" / "platform_browser" / "cookies" / "upwork_cookies.json"
SS_DIR = PROJECT / "output" / "platform_screenshots"
SS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = PROJECT / "data" / "upwork_jobs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
JOB_LOG = DATA_DIR / "job_log.jsonl"
APPLIED_LOG = DATA_DIR / "applied.json"

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# ── Search queries targeting our agent capabilities ───────────
# Broader queries first (less likely to trigger CAPTCHA), niche queries later
SEARCH_QUERIES = [
    "python automation",
    "fastapi developer",
    "data extraction automation",
    "ai email automation",
    "ai content writer",
    "lead generation automation",
    "nlp developer",
    "langchain developer",
    "chatbot development",
    "openai api integration",
    "ai agent development",
    "ai automation",
    "web scraping python",
    "gpt developer",
    "workflow automation",
]

NEGATIVE_KEYWORDS = [
    "blockchain developer", "solidity", "react native", "ios",
    "android", "unity", "game", "wordpress theme", "php developer",
    "java spring", ".net developer", "c# developer",
]


def _human_delay(min_s: float = 2.0, max_s: float = 5.0):
    """Random sleep to mimic human browsing rhythm."""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def _handle_challenge(page):
    """Detect and wait for CAPTCHA / Cloudflare / bot-check pages."""
    challenge_indicators = [
        "verify you are human",
        "security check",
        "just a moment",
        "checking your browser",
        "captcha",
        "challenge-platform",
    ]
    body_text = (page.inner_text("body") or "").lower()[:2000]
    if any(ind in body_text for ind in challenge_indicators):
        print("    [!] Challenge/CAPTCHA detected — waiting for manual solve (up to 120s)...")
        for _ in range(120):
            time.sleep(1)
            body_text = (page.inner_text("body") or "").lower()[:2000]
            if not any(ind in body_text for ind in challenge_indicators):
                print("    [+] Challenge cleared!")
                return
        print("    [WARN] Challenge not cleared after 120s — continuing anyway")


def _load_applied() -> set:
    if APPLIED_LOG.exists():
        data = json.loads(APPLIED_LOG.read_text(encoding="utf-8"))
        return set(data.get("applied_urls", []))
    return set()


def _save_applied(urls: set):
    APPLIED_LOG.write_text(
        json.dumps({"applied_urls": sorted(urls), "updated": datetime.now(timezone.utc).isoformat()}, indent=2),
        encoding="utf-8",
    )


def _log_job(job: dict):
    with open(JOB_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(job) + "\n")


# Weighted keywords — critical matches score higher than nice-to-haves
CORE_KEYWORDS = [
    "ai agent", "chatbot", "automation", "automate", "python",
    "openai", "gpt", "claude", "gemini", "langchain",
    "fastapi", "data extraction", "web scraping", "api",
]
BONUS_KEYWORDS = [
    "nlp", "machine learning", "lead generation", "email automation",
    "content", "seo", "crm", "sales automation", "support", "ticket",
    "workflow", "pipeline", "backend", "scrape", "n8n",
]


def score_job(title: str, description: str) -> float:
    """Score a job 0-1 based on keyword relevance.

    Core keyword hits count 2x.  Needs only ~4 core matches to hit 0.50+.
    """
    text = f"{title} {description}".lower()
    core_hits = sum(1 for kw in CORE_KEYWORDS if kw in text)
    bonus_hits = sum(1 for kw in BONUS_KEYWORDS if kw in text)
    negs = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    # Weight: each core=0.10, each bonus=0.04, each negative=-0.15
    raw = (core_hits * 0.10) + (bonus_hits * 0.04) - (negs * 0.15)
    return round(max(0.0, min(1.0, raw)), 2)


def generate_proposal(title: str, description: str) -> str:
    """Generate a tailored proposal based on job details."""
    text = f"{title} {description}".lower()

    # Detect which of our agents match best
    pitch_blocks = []

    if any(kw in text for kw in ["sales", "outreach", "lead", "cold email", "b2b"]):
        pitch_blocks.append(
            "I run a production AI sales outreach pipeline that researches companies in real-time "
            "and generates personalized 3-email sequences — processing 50+ leads/hour with QA verification."
        )
    if any(kw in text for kw in ["support", "ticket", "customer service", "helpdesk"]):
        pitch_blocks.append(
            "I've built an AI support ticket resolver that handles triage, severity scoring, and draft responses "
            "— processing 200+ tickets/hour with <10s response time."
        )
    if any(kw in text for kw in ["content", "blog", "social media", "seo", "writing", "copywriting"]):
        pitch_blocks.append(
            "I have a content repurposing engine that converts 1 piece of content into 5 platform-optimized "
            "formats (LinkedIn, Twitter/X, email, Instagram, TikTok) — with tone matching and character limits."
        )
    if any(kw in text for kw in ["data extract", "document", "invoice", "pdf", "ocr", "scraping", "scrape"]):
        pitch_blocks.append(
            "I've built document extraction agents that parse invoices, contracts, and PDFs into structured "
            "JSON/CSV with entity extraction and 95%+ accuracy."
        )
    if any(kw in text for kw in ["chatbot", "chat bot", "conversational", "ai assistant"]):
        pitch_blocks.append(
            "I build production chatbots powered by GPT-4o/Claude with multi-turn memory, tool use, "
            "and API integrations — not simple prompt wrappers."
        )
    if any(kw in text for kw in ["automation", "workflow", "automate", "pipeline"]):
        pitch_blocks.append(
            "I specialize in end-to-end automation pipelines connecting AI models to business workflows "
            "via REST APIs, webhooks, and scheduled tasks."
        )
    if any(kw in text for kw in ["python", "fastapi", "api", "backend"]):
        pitch_blocks.append(
            "I'm a senior Python developer with production experience in FastAPI, async programming, "
            "and building scalable API services deployed on cloud infrastructure."
        )
    if any(kw in text for kw in ["openai", "gpt", "claude", "gemini", "llm", "langchain"]):
        pitch_blocks.append(
            "I have deep experience integrating OpenAI GPT-4o, Anthropic Claude, and Google Gemini APIs "
            "with automatic failover between providers for maximum reliability."
        )

    # Build the proposal
    if not pitch_blocks:
        pitch_blocks.append(
            "I build production AI systems with Python, FastAPI, and multi-LLM integration "
            "(GPT-4o, Claude, Gemini). I can deliver this project quickly with high quality."
        )

    # Take top 3 most relevant pitches
    relevant = pitch_blocks[:3]

    proposal = f"""Hi,

I read through your project details and this is right in my wheelhouse.

{chr(10).join(relevant)}

I run an AI agent agency (BIT RAGE SYSTEMS) with 20 specialized agents in production right now — so I'm not learning on your project, I'm applying proven systems.

**My approach for this project:**
1. Quick discovery call or async scope (15 min)
2. I build and test the solution (1-3 days typical)
3. You get API access + documentation + deployment

Every deliverable passes automated QA before I send it. Happy to start with a small proof-of-concept if you'd like to test the quality first.

Looking forward to discussing.

— BIT RAGE SYSTEMS
Python | AI Agents | GPT-4o | Claude | FastAPI"""

    return proposal


def search_jobs(page, query: str, max_results: int = 10) -> list[dict]:
    """Search Upwork for jobs matching query. Returns list of job dicts."""
    url = f"https://www.upwork.com/nx/search/jobs/?q={query.replace(' ', '%20')}&sort=recency"
    print(f"\n  [SEARCH] {query}")
    print(f"  URL: {url[:80]}")

    page.goto(url, wait_until="domcontentloaded")
    _human_delay(3, 6)

    # Check for CAPTCHA / challenge page
    _handle_challenge(page)

    jobs = []

    # Look for job listing tiles
    # Upwork uses various selectors — try multiple strategies
    job_tiles = page.query_selector_all(
        'article, [data-test="JobTile"], [data-test="job-tile"], '
        'section.job-tile, div.job-tile, [class*="JobTile"], '
        'div[data-ev-label="search_results_impression"]'
    )

    if not job_tiles:
        # Fallback: find sections with job-like content
        job_tiles = page.query_selector_all('section, article, div.up-card-section')

    print(f"  Found {len(job_tiles)} job elements")

    for tile in job_tiles[:max_results]:
        try:
            # Extract job details
            title_el = tile.query_selector(
                'a[data-test="job-tile-title-link"], '
                'a[class*="job-title"], '
                'h2 a, h3 a, '
                'a[href*="/jobs/"]'
            )
            if not title_el:
                continue

            title = title_el.inner_text().strip()
            href = title_el.get_attribute("href") or ""
            if not title or len(title) < 5:
                continue

            # Get description
            desc_el = tile.query_selector(
                '[data-test="JobDescription"], '
                '[data-test="job-description-text"], '
                'span[class*="description"], '
                'p, div[class*="break"]'
            )
            description = desc_el.inner_text().strip()[:500] if desc_el else ""

            # Get budget
            budget = ""
            budget_el = tile.query_selector(
                '[data-test="budget"], '
                '[data-test="job-type-label"], '
                'span[class*="budget"], '
                'strong[data-test]'
            )
            if budget_el:
                budget = budget_el.inner_text().strip()

            # Get skills/tags
            skill_els = tile.query_selector_all(
                '[data-test="token"], '
                'span[class*="skill"], '
                'a[class*="skill"], '
                'span[class*="tag"]'
            )
            skills = [s.inner_text().strip() for s in skill_els if s.inner_text().strip()][:10]

            # Build job URL
            job_url = href
            if href and not href.startswith("http"):
                job_url = f"https://www.upwork.com{href}"

            job = {
                "title": title,
                "description": description,
                "budget": budget,
                "skills": skills,
                "url": job_url,
                "search_query": query,
                "found_at": datetime.now(timezone.utc).isoformat(),
            }

            # Score the job
            job["score"] = score_job(title, description)

            jobs.append(job)
            print(f"    [{job['score']:.2f}] {title[:60]}")

        except Exception:
            continue

    return jobs


def apply_to_job(page, job: dict, proposal: str) -> bool:
    """Navigate to job page and submit proposal."""
    print(f"\n  [APPLY] {job['title'][:50]}...")
    print(f"  Score: {job['score']:.2f} | Budget: {job.get('budget', 'N/A')}")

    if not job.get("url"):
        print("    [SKIP] No URL")
        return False

    page.goto(job["url"], wait_until="domcontentloaded")
    time.sleep(3)

    # Look for Apply/Submit Proposal button
    applied = False
    for sel in [
        'button:has-text("Apply Now")',
        'a:has-text("Apply Now")',
        'button:has-text("Submit a Proposal")',
        'a:has-text("Submit a Proposal")',
        'button[data-test="apply-button"]',
        'a[data-test="apply-button"]',
    ]:
        try:
            el = page.wait_for_selector(sel, timeout=3000)
            if el and el.is_visible():
                el.scroll_into_view_if_needed()
                el.click()
                time.sleep(3)
                applied = True
                print("    [CLICKED] Apply button")
                break
        except Exception:
            continue

    if not applied:
        print("    [WARN] Could not find Apply button")
        page.screenshot(path=str(SS_DIR / f"upwork_apply_nobutton_{int(time.time())}.png"))
        return False

    # Fill in the proposal cover letter
    for sel in [
        'textarea[data-test="cover-letter"]',
        'textarea[aria-label*="cover letter"]',
        'textarea[aria-label*="Cover Letter"]',
        'textarea[placeholder*="cover letter"]',
        'textarea[id*="cover"]',
        'textarea[name*="cover"]',
        '#cover_letter',
        'textarea',
    ]:
        try:
            el = page.wait_for_selector(sel, timeout=3000)
            if el:
                el.click()
                el.fill("")
                el.fill(proposal)
                print(f"    [FILLED] Proposal ({len(proposal)} chars)")
                break
        except Exception:
            continue

    # Set hourly rate if field exists
    for sel in [
        'input[data-test*="rate"]',
        'input[aria-label*="rate"]',
        'input[aria-label*="Hourly"]',
        'input[placeholder*="rate"]',
        'input[type="number"]',
    ]:
        try:
            el = page.wait_for_selector(sel, timeout=2000)
            if el:
                el.click()
                el.fill("")
                el.fill("45")
                print("    [SET] Rate: $45/hr")
                break
        except Exception:
            continue

    page.screenshot(path=str(SS_DIR / f"upwork_proposal_{int(time.time())}.png"))

    # Submit the proposal
    for sel in [
        'button:has-text("Submit")',
        'button:has-text("Send")',
        'button:has-text("Submit Proposal")',
        'button[data-test="submit-proposal"]',
        'button[type="submit"]',
    ]:
        try:
            el = page.wait_for_selector(sel, timeout=3000)
            if el and el.is_visible():
                el.scroll_into_view_if_needed()
                el.click()
                print("    [SUBMITTED] Proposal sent!")
                time.sleep(3)
                page.screenshot(path=str(SS_DIR / f"upwork_submitted_{int(time.time())}.png"))
                return True
        except Exception:
            continue

    print("    [WARN] Could not find Submit button — proposal may need manual submit")
    return False


# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Upwork Job Hunt Automation")
    parser.add_argument("--scan-only", action="store_true", help="Search + score only, don't apply")
    parser.add_argument("--search", type=str, help="Custom search query")
    parser.add_argument("--max-applies", type=int, default=10, help="Max proposals to submit")
    parser.add_argument("--min-score", type=float, default=0.15, help="Minimum job score to apply")
    args = parser.parse_args()

    queries = [args.search] if args.search else SEARCH_QUERIES

    print("=" * 60)
    print("  UPWORK JOB HUNT — Edge Browser")
    print(f"  Queries: {len(queries)}")
    print(f"  Mode: {'SCAN ONLY' if args.scan_only else 'SEARCH + APPLY'}")
    print(f"  Min score: {args.min_score} | Max applies: {args.max_applies}")
    print("=" * 60)

    pw = sync_playwright().start()
    # Use launch_persistent_context — keeps Edge profile with history,
    # cookies, and fingerprint so Upwork sees a real returning user
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(EDGE_PROFILE_DIR),
        headless=False,
        channel="msedge",
        executable_path=EDGE_PATH,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
        viewport={"width": 1366, "height": 768},
        locale="en-CA",
        timezone_id="America/Toronto",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    )
    page = context.pages[0] if context.pages else context.new_page()
    stealth = Stealth()
    stealth.apply_stealth_sync(page)
    print("[+] Stealth mode active + persistent Edge profile")

    # ── Login check ───────────────────────────────────────────
    page.goto("https://www.upwork.com/nx/find-work/best-matches", wait_until="domcontentloaded")
    time.sleep(4)

    url = page.url.lower()
    if "login" in url or "account-security" in url:
        print("[!] Not logged in — please log in manually...")
        print("    Waiting up to 5 minutes...")
        for _ in range(300):
            time.sleep(1)
            if "login" not in page.url.lower() and "account-security" not in page.url.lower():
                print("[+] Login detected!")
                break
        context.storage_state(path=str(COOKIE_FILE))

    # ── Search + collect jobs ─────────────────────────────────
    all_jobs = []
    applied_urls = _load_applied()

    for query in queries:
        try:
            jobs = search_jobs(page, query, max_results=8)
            # Filter out already-applied and duplicates
            for job in jobs:
                if job["url"] not in applied_urls and not any(j["url"] == job["url"] for j in all_jobs):
                    all_jobs.append(job)
                    _log_job(job)
        except Exception as e:
            print(f"    [ERR] Search failed for '{query}': {e}")
            continue
        _human_delay(4, 9)  # Human-like pause between searches

    # Sort by score (best matches first)
    all_jobs.sort(key=lambda j: j["score"], reverse=True)

    print(f"\n{'='*60}")
    print(f"  FOUND {len(all_jobs)} unique jobs")
    print(f"{'='*60}")
    for i, job in enumerate(all_jobs[:20], 1):
        marker = "★" if job["score"] >= args.min_score else "·"
        print(f"  {marker} [{job['score']:.2f}] {job['title'][:55]}")
        if job.get("budget"):
            print(f"         Budget: {job['budget']}")

    # ── Apply to qualifying jobs ──────────────────────────────
    if args.scan_only:
        print(f"\n  [SCAN ONLY] Skipping applications. {len(all_jobs)} jobs logged.")
    else:
        qualifying = [j for j in all_jobs if j["score"] >= args.min_score]
        print(f"\n  [APPLYING] {len(qualifying)} jobs above {args.min_score} threshold")

        applied_count = 0
        for job in qualifying:
            if applied_count >= args.max_applies:
                print(f"\n  [LIMIT] Reached max applies ({args.max_applies})")
                break

            proposal = generate_proposal(job["title"], job["description"])
            success = apply_to_job(page, job, proposal)

            if success:
                applied_urls.add(job["url"])
                _save_applied(applied_urls)
                applied_count += 1
                job["applied"] = True
                job["applied_at"] = datetime.now(timezone.utc).isoformat()
            else:
                job["applied"] = False

            time.sleep(3)  # Pause between applications

        print(f"\n  Applied to {applied_count} / {len(qualifying)} qualifying jobs")

    # ── Save state + screenshot ───────────────────────────────
    context.storage_state(path=str(COOKIE_FILE))
    page.screenshot(path=str(SS_DIR / "upwork_jobhunt_final.png"))

    # Summary
    print(f"\n{'='*60}")
    print("  UPWORK JOB HUNT COMPLETE")
    print(f"  Jobs found: {len(all_jobs)}")
    print(f"  Qualifying (score >= {args.min_score}): {len([j for j in all_jobs if j['score'] >= args.min_score])}")
    if not args.scan_only:
        print(f"  Applied: {len([j for j in all_jobs if j.get('applied')])}")
    print(f"  Job log: {JOB_LOG}")
    print("  Browser stays open \u2014 Ctrl+C to close")
    print(f"{'='*60}")

    try:
        while True:
            time.sleep(5)
            try:
                context.storage_state(path=str(COOKIE_FILE))
            except Exception:
                break
    except KeyboardInterrupt:
        print("\n[+] Closing...")

    context.close()
    pw.stop()


if __name__ == "__main__":
    main()
