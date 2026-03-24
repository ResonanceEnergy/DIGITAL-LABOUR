"""Freelancer.com Job Hunt — automated project search, scoring, and bid submission.

Opens Edge browser, searches Freelancer.com for matching projects, scores them,
generates tailored proposals via the freelancer_work agent, and submits bids.

Usage:
    python -m automation.freelancer_jobhunt               # Full run: search + bid
    python -m automation.freelancer_jobhunt --scan-only    # Search + score, no submit
    python -m automation.freelancer_jobhunt --search "ai data entry"  # Custom search
    python -m automation.freelancer_jobhunt --category "data-processing"
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
EDGE_PROFILE_DIR = PROJECT / "data" / "platform_browser" / "freelancer_edge_profile"
EDGE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

COOKIE_FILE = PROJECT / "data" / "platform_browser" / "cookies" / "freelancer_cookies.json"
SS_DIR = PROJECT / "output" / "platform_screenshots"
SS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = PROJECT / "data" / "freelancer_jobs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
JOB_LOG = DATA_DIR / "project_log.jsonl"
BID_LOG = DATA_DIR / "bids_submitted.json"

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# ── Search queries targeting our 20 agent capabilities ──────────────────────
SEARCH_QUERIES = [
    "data entry",
    "web scraping python",
    "email marketing campaign",
    "seo blog writing",
    "lead generation",
    "cold email outreach",
    "content writing",
    "social media content",
    "product descriptions",
    "bookkeeping data entry",
    "resume writing",
    "market research report",
    "business plan writing",
    "ad copy google facebook",
    "technical documentation",
    "press release writing",
    "proposal writing",
    "crm data cleanup",
    "document data extraction",
    "customer support agent",
]

# Keywords for scoring — mapped to our agent capabilities
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

MIN_SCORE = 0.25  # Minimum score to consider bidding
MAX_BIDS_PER_RUN = 10


def _human_delay(min_s: float = 2.0, max_s: float = 5.0):
    """Random sleep to mimic human browsing rhythm."""
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


def _load_bid_history() -> set:
    """Load previously-bid project IDs."""
    if BID_LOG.exists():
        data = json.loads(BID_LOG.read_text(encoding="utf-8"))
        return set(str(b.get("project_id", "")) for b in data if b.get("project_id"))
    return set()


def _save_bid(bid: dict):
    """Append bid to bid log."""
    bids = []
    if BID_LOG.exists():
        bids = json.loads(BID_LOG.read_text(encoding="utf-8"))
    bids.append(bid)
    BID_LOG.write_text(json.dumps(bids, indent=2), encoding="utf-8")


def _log_project(project: dict):
    """Append project to JSONL log."""
    with open(JOB_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(project) + "\n")


def score_project(title: str, description: str) -> float:
    """Score a Freelancer.com project 0-1 based on keyword match to our agents."""
    text = f"{title} {description}".lower()
    core_hits = sum(1 for kw in CORE_KEYWORDS if kw in text)
    bonus_hits = sum(1 for kw in BONUS_KEYWORDS if kw in text)
    negs = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    raw = (core_hits * 0.07) + (bonus_hits * 0.03) - (negs * 0.15)
    return round(max(0.0, min(1.0, raw)), 2)


def generate_proposal(title: str, description: str, budget: str = "") -> str:
    """Generate a tailored bid proposal for a Freelancer.com project.

    Uses LLM via the freelancer_work agent for best results,
    falls back to template-based generation.
    """
    try:
        from agents.freelancer_work.runner import run_pipeline
        result = run_pipeline(
            action="bid",
            project_data={
                "title": title,
                "description": description,
                "budget_max": _parse_budget(budget),
            },
        )
        if result and result.bid:
            return result.bid.body
    except Exception as e:
        print(f"    [WARN] LLM bid gen failed ({e}), using template")

    # Fallback: keyword-matched template proposal
    return _template_proposal(title, description)


def _parse_budget(budget_str: str) -> float:
    """Extract numeric budget from string like '$250 - $750'."""
    import re
    nums = re.findall(r'[\d,]+\.?\d*', budget_str.replace(',', ''))
    if nums:
        return float(nums[-1])  # Take the higher end
    return 0


def _template_proposal(title: str, description: str) -> str:
    """Template-based proposal generation as fallback."""
    text = f"{title} {description}".lower()
    blocks = []

    if any(kw in text for kw in ["data entry", "data processing", "spreadsheet", "excel", "csv"]):
        blocks.append(
            "I have a production AI data processing agent that handles data cleaning, "
            "standardization, deduplication, and format conversion — processing 5,000+ rows/hour "
            "with validation reports on every batch."
        )
    if any(kw in text for kw in ["web scraping", "scrape", "data mining", "data extraction"]):
        blocks.append(
            "I've built AI extraction agents that pull structured data from web pages "
            "and documents — delivering clean JSON/CSV with field mapping and quality scores."
        )
    if any(kw in text for kw in ["email", "newsletter", "campaign", "drip", "mailchimp"]):
        blocks.append(
            "I build complete email marketing sequences with A/B subject lines, "
            "send timing recommendations, and merge tag placeholders for any ESP."
        )
    if any(kw in text for kw in ["seo", "blog", "article", "content writing"]):
        blocks.append(
            "I produce SEO-optimized content through a 3-stage AI pipeline: "
            "Keyword Research → Content Writing → QA Verification. Publish-ready."
        )
    if any(kw in text for kw in ["lead", "prospecting", "b2b", "cold email", "outreach"]):
        blocks.append(
            "I build qualified B2B lead lists — each lead individually researched and scored "
            "against your ICP, with buying signals and recommended approach angles."
        )
    if any(kw in text for kw in ["social media", "linkedin", "instagram", "twitter", "facebook"]):
        blocks.append(
            "I generate platform-optimized social content — character limits enforced, "
            "hashtag strategy included, consistent brand voice across platforms."
        )
    if any(kw in text for kw in ["product description", "amazon", "shopify", "etsy", "ebay"]):
        blocks.append(
            "I write converting product descriptions optimized per platform — Amazon ALL CAPS "
            "bullet format, Shopify SEO meta, Etsy tags. Character limits enforced."
        )
    if any(kw in text for kw in ["resume", "cv", "cover letter", "career"]):
        blocks.append(
            "I write ATS-optimized resumes with CAR-format bullets, quantified achievements, "
            "and targeted keyword integration for your specific role and industry."
        )
    if any(kw in text for kw in ["bookkeeping", "accounting", "expense", "quickbooks", "xero"]):
        blocks.append(
            "I process financial records with AI — expense categorization mapped to your "
            "chart of accounts, transaction matching, reconciliation, and QBO-compatible export."
        )

    if not blocks:
        blocks.append(
            "I run an AI agent agency with 20 specialized agents in production — "
            "sales, content, data processing, research, and documents. "
            "I can deliver this project quickly with automated QA on every output."
        )

    relevant = blocks[:3]

    return f"""Hi,

I reviewed your project requirements and this matches my production capabilities exactly.

{chr(10).join(relevant)}

I run BIT RAGE SYSTEMS — an AI agent agency with 20 specialized agents. Every deliverable passes automated QA verification before delivery.

**How I'd handle this:**
1. Quick scope confirmation (async or call)
2. Build and process using my AI pipeline
3. Deliver structured output with quality report

Happy to start with a small sample to demonstrate quality.

— BIT RAGE SYSTEMS (Canada)"""


def search_projects(page, query: str, max_results: int = 10) -> list[dict]:
    """Search Freelancer.com for projects matching query."""
    url = f"https://www.freelancer.com/jobs/?keyword={query.replace(' ', '+')}&sortBy=latest"
    print(f"\n  [SEARCH] {query}")

    page.goto(url, wait_until="domcontentloaded")
    _human_delay(3, 6)
    _handle_challenge(page)

    projects = []

    # Freelancer.com project listing selectors
    project_tiles = page.query_selector_all(
        'div.JobSearchCard-item, '
        'div[class*="JobSearchCard"], '
        'div.project-list-item, '
        'fl-project-card, '
        'div[data-project-id], '
        'div.search-result-item'
    )

    if not project_tiles:
        # Broader fallback
        project_tiles = page.query_selector_all(
            'div.JobSearchCard-primary-heading-container, '
            'div[class*="project"], '
            'article'
        )

    print(f"  Found {len(project_tiles)} project elements")

    for tile in project_tiles[:max_results]:
        try:
            # Title & link
            title_el = tile.query_selector(
                'a.JobSearchCard-primary-heading-link, '
                'a[class*="heading-link"], '
                'a[href*="/projects/"], '
                'h2 a, h3 a'
            )
            if not title_el:
                continue

            title = title_el.inner_text().strip()
            href = title_el.get_attribute("href") or ""
            if not title or len(title) < 5:
                continue

            # Description
            desc_el = tile.query_selector(
                'p.JobSearchCard-primary-description, '
                'div[class*="description"], '
                'p[class*="description"]'
            )
            description = desc_el.inner_text().strip()[:500] if desc_el else ""

            # Budget
            budget_el = tile.query_selector(
                'div.JobSearchCard-secondary-price, '
                'span[class*="price"], '
                'div[class*="budget"], '
                'span[class*="Budget"]'
            )
            budget = budget_el.inner_text().strip() if budget_el else ""

            # Skills/tags
            skill_els = tile.query_selector_all(
                'a.JobSearchCard-primary-tagsLink, '
                'a[class*="tags"], '
                'span[class*="skill"], '
                'a[href*="/jobs/"]'
            )
            skills = [s.inner_text().strip() for s in skill_els if s.inner_text().strip()][:10]

            # Bid count
            bid_el = tile.query_selector(
                'div.JobSearchCard-secondary-entry span, '
                'span[class*="bid-count"], '
                'div[class*="entries"]'
            )
            bids_text = bid_el.inner_text().strip() if bid_el else ""

            # Project ID from URL or data attribute
            project_id = tile.get_attribute("data-project-id") or ""
            if not project_id and href:
                # Extract from URL: /projects/some-title-12345678
                parts = href.rstrip("/").split("-")
                if parts and parts[-1].isdigit():
                    project_id = parts[-1]

            project_url = href
            if href and not href.startswith("http"):
                project_url = f"https://www.freelancer.com{href}"

            project = {
                "id": project_id,
                "title": title,
                "description": description,
                "budget": budget,
                "budget_max": _parse_budget(budget),
                "skills": skills,
                "bids_text": bids_text,
                "url": project_url,
                "platform": "freelancer",
                "query": query,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }

            score = score_project(title, description)
            project["score"] = score

            projects.append(project)
            _log_project(project)

        except Exception as e:
            print(f"    [WARN] Failed to parse project tile: {e}")
            continue

    return projects


def run_job_hunt(
    scan_only: bool = False,
    custom_search: str | None = None,
    max_queries: int = 5,
    category: str | None = None,
):
    """Main job hunt loop.

    1. Open Edge browser with persistent profile
    2. Search Freelancer.com for matching projects
    3. Score each project
    4. Generate and submit proposals (unless scan_only)
    """
    queries = [custom_search] if custom_search else SEARCH_QUERIES[:max_queries]
    bid_history = _load_bid_history()
    bids_submitted = 0

    print(f"\n{'='*60}")
    print(f"  FREELANCER.COM JOB HUNT")
    print(f"  Queries: {len(queries)} | Scan only: {scan_only}")
    print(f"  Previously bid: {len(bid_history)} projects")
    print(f"{'='*60}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
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

        # Navigate to Freelancer.com first
        print("\n[NAV] Opening Freelancer.com...")
        page.goto("https://www.freelancer.com", wait_until="domcontentloaded")
        _human_delay(3, 5)
        _handle_challenge(page)

        # Take a screenshot of the landing state
        page.screenshot(path=str(SS_DIR / "freelancer_landing.png"))

        all_projects = []

        for qi, query in enumerate(queries):
            if bids_submitted >= MAX_BIDS_PER_RUN:
                print(f"\n  [CAP] Max bids per run ({MAX_BIDS_PER_RUN}) reached")
                break

            projects = search_projects(page, query)
            print(f"  Found {len(projects)} projects for '{query}'")

            for proj in projects:
                if proj["score"] < MIN_SCORE:
                    continue
                if str(proj.get("id", "")) in bid_history:
                    print(f"    [SKIP] Already bid: {proj['title'][:40]}...")
                    continue

                all_projects.append(proj)
                print(f"    [{proj['score']:.2f}] {proj['title'][:50]} — {proj['budget']}")

                if not scan_only and bids_submitted < MAX_BIDS_PER_RUN:
                    try:
                        print(f"    [BID] Generating proposal...")
                        proposal = generate_proposal(proj["title"], proj["description"], proj["budget"])

                        bid_record = {
                            "project_id": proj.get("id", ""),
                            "project_title": proj["title"],
                            "project_url": proj["url"],
                            "score": proj["score"],
                            "budget": proj["budget"],
                            "proposal_preview": proposal[:200],
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                            "status": "generated",
                            "submitted": False,
                        }

                        # Navigate to project page to submit
                        if proj["url"]:
                            page.goto(proj["url"], wait_until="domcontentloaded")
                            _human_delay(2, 4)
                            _handle_challenge(page)

                            # Look for bid/proposal form
                            bid_button = page.query_selector(
                                'button[class*="BidBtn"], '
                                'a[class*="PlaceBid"], '
                                'button:has-text("Place Bid"), '
                                'button:has-text("Bid on this"), '
                                'a:has-text("Place Bid")'
                            )

                            if bid_button:
                                bid_button.click()
                                _human_delay(2, 3)

                                # Fill proposal text
                                proposal_field = page.query_selector(
                                    'textarea[name="descr"], '
                                    'textarea[id="descr"], '
                                    'textarea[class*="proposal"], '
                                    'textarea[placeholder*="proposal"], '
                                    'textarea'
                                )

                                if proposal_field:
                                    proposal_field.fill(proposal)
                                    _human_delay(1, 2)

                                    # Fill bid amount if field exists
                                    bid_amount = min(proj["budget_max"] * 0.8, 200) if proj["budget_max"] > 0 else 50
                                    amount_field = page.query_selector(
                                        'input[name="amount"], '
                                        'input[id="amount"], '
                                        'input[class*="bid-amount"], '
                                        'input[type="number"]'
                                    )
                                    if amount_field:
                                        amount_field.fill(str(int(bid_amount)))
                                        _human_delay(0.5, 1)

                                    # Screenshot before submit
                                    page.screenshot(
                                        path=str(SS_DIR / f"freelancer_bid_{proj.get('id', 'unknown')}.png")
                                    )

                                    # Submit bid
                                    submit_btn = page.query_selector(
                                        'button[type="submit"]:has-text("Place Bid"), '
                                        'button[type="submit"]:has-text("Submit"), '
                                        'button[class*="submit"]'
                                    )
                                    if submit_btn:
                                        submit_btn.click()
                                        _human_delay(3, 5)
                                        bid_record["submitted"] = True
                                        bid_record["status"] = "submitted"
                                        bids_submitted += 1
                                        print(f"    [OK] Bid submitted! (${int(bid_amount)})")
                                    else:
                                        bid_record["status"] = "submit_button_not_found"
                                        print(f"    [WARN] Submit button not found")
                                else:
                                    bid_record["status"] = "proposal_field_not_found"
                                    print(f"    [WARN] Proposal field not found")
                            else:
                                bid_record["status"] = "bid_button_not_found"
                                print(f"    [WARN] Bid button not found (may need login)")

                        _save_bid(bid_record)
                        bid_history.add(str(proj.get("id", "")))

                    except Exception as e:
                        print(f"    [ERROR] Bid failed: {e}")

            # Delay between searches to avoid rate limiting
            if qi < len(queries) - 1:
                _human_delay(5, 10)

        browser.close()

    # Print summary
    print(f"\n{'='*60}")
    print(f"  HUNT COMPLETE")
    print(f"{'='*60}")
    print(f"  Projects found: {len(all_projects)}")
    print(f"  Above threshold ({MIN_SCORE}): {len([p for p in all_projects if p['score'] >= MIN_SCORE])}")
    print(f"  Bids submitted: {bids_submitted}")

    if all_projects:
        top = sorted(all_projects, key=lambda x: x["score"], reverse=True)[:5]
        print(f"\n  TOP 5 MATCHES:")
        for p in top:
            print(f"    [{p['score']:.2f}] {p['title'][:50]} — {p['budget']}")
            print(f"           {p['url']}")

    print(f"{'='*60}\n")

    return {"projects_found": len(all_projects), "bids_submitted": bids_submitted}


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Freelancer.com Job Hunt Automation")
    parser.add_argument("--scan-only", action="store_true", help="Search + score only, no bids")
    parser.add_argument("--search", help="Custom search query")
    parser.add_argument("--category", help="Freelancer category filter")
    parser.add_argument("--max-queries", type=int, default=5, help="Max search queries to run")
    args = parser.parse_args()

    run_job_hunt(
        scan_only=args.scan_only,
        custom_search=args.search,
        max_queries=args.max_queries,
        category=args.category,
    )


if __name__ == "__main__":
    main()
