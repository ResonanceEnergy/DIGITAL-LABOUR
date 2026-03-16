"""Upwork profile automation — full wizard flow in single Edge session.

Handles the entire Upwork create-profile wizard:
  1. Login (manual, waits for you)
  2. Categories page — detect & select
  3. Skills page — type and pick from suggestions
  4. Scope/experience page — select options
  5. Hourly rate page — fill $45
  6. Title & overview page — fill from UPWORK_PROFILE
  7. Photo/portfolio — skip or handle
  8. CV/resume upload
  9. Submit/publish profile

Each step: detect current page → fill → click Next → repeat.
"""

import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from playwright.sync_api import sync_playwright
from income.freelance_listings import UPWORK_PROFILE

COOKIE_FILE = PROJECT / "data" / "platform_browser" / "cookies" / "upwork_cookies.json"
CV_PDF = PROJECT / "output" / "CV_digitallabour.pdf"
SS_DIR = PROJECT / "output" / "platform_screenshots"
SS_DIR.mkdir(parents=True, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


# ── Helpers ───────────────────────────────────────────────────

def screenshot(page, name):
    page.screenshot(path=str(SS_DIR / f"{name}.png"))


def wait_click(page, selector, timeout=3000):
    """Try to click an element, return True if successful."""
    try:
        el = page.wait_for_selector(selector, timeout=timeout)
        if el and el.is_visible():
            el.scroll_into_view_if_needed()
            el.click()
            return True
    except Exception:
        pass
    return False


def fill_field(page, selector, value, timeout=3000):
    """Try to fill a field, return True if successful."""
    try:
        el = page.wait_for_selector(selector, timeout=timeout)
        if el:
            el.click()
            el.fill("")  # clear first
            el.fill(value)
            return True
    except Exception:
        pass
    return False


def click_next(page):
    """Find and click Next/Continue/Save button."""
    for sel in [
        'button:has-text("Next")',
        'button:has-text("Continue")',
        'button:has-text("Next, add your experience")',
        'button:has-text("Next, write your profile")',
        'button:has-text("Next, add your rate")',
        'button:has-text("Next, add a profile photo")',
        'button:has-text("Review your profile")',
        'button:has-text("Submit profile")',
        'button:has-text("Save")',
        'button[data-test="next-btn"]',
        'button[data-test="btn-next"]',
        'button[data-qa="next-btn"]',
        'button[data-qa="btn-next"]',
    ]:
        if wait_click(page, sel, timeout=2000):
            print(f"    -> Clicked: {sel}")
            time.sleep(3)
            return True
    return False


def detect_page(page):
    """Detect which wizard page we're on by URL and page content."""
    url = page.url.lower()
    text = ""
    try:
        text = page.inner_text("body")[:2000].lower()
    except Exception:
        pass

    if "login" in url or "account-security" in url:
        return "login"
    if "categories" in url or "category" in url:
        return "categories"
    if "/skills" in url or "your skills" in text or "search for skills" in text:
        return "skills"
    if "/scope" in url or "/experience" in url or "what level of experience" in text or "work experience" in text:
        return "experience"
    if "/rate" in url or "hourly rate" in text or "set your rate" in text:
        return "rate"
    if "/title" in url or "write a title" in text or "professional title" in text:
        return "title"
    if "/overview" in url or "/bio" in url or "write your bio" in text or "professional overview" in text or "write an overview" in text:
        return "overview"
    if "/photo" in url or "profile photo" in text or "upload a photo" in text:
        return "photo"
    if "/resume" in url or "add your resume" in text or "upload your resume" in text or "add resume" in text:
        return "resume"
    if "/location" in url or "where are you based" in text:
        return "location"
    if "/phone" in url or "phone number" in text:
        return "phone"
    if "/education" in url or "add your education" in text:
        return "education"
    if "/employment" in url or "employment history" in text or "work history" in text:
        return "employment"
    if "/languages" in url or "add a language" in text or "what languages" in text:
        return "languages"
    if "/review" in url or "review your profile" in text or "looks good" in text:
        return "review"
    if "/submit" in url or "submit profile" in text:
        return "submit"
    if "dashboard" in url or "find-work" in url or "best matches" in text:
        return "done"
    return "unknown"


# ── Page handlers ─────────────────────────────────────────────

def handle_categories(page):
    """Select relevant work categories."""
    print("\n[CATEGORIES] Selecting work categories...")

    # Upwork create-profile categories page uses clickable cards/buttons
    # Try multiple selector strategies
    keywords = [
        "IT & Networking", "Web, Mobile & Software Dev",
        "Data Science & Analytics", "AI & Machine Learning",
        "Writing", "Admin Support", "Customer Service",
        "Sales & Marketing", "Engineering & Architecture",
    ]

    selected = []
    # Strategy 1: Click elements containing category keywords
    all_els = page.query_selector_all(
        "button, [role='button'], [role='option'], label, "
        "[class*='category'], [class*='tile'], [class*='card'], "
        "[data-test], [data-ev-label], [data-qa], li, div[tabindex]"
    )
    for el in all_els:
        try:
            txt = el.inner_text().strip()
            if not txt or len(txt) > 100:
                continue
            txt_lower = txt.lower()
            for kw in keywords:
                if kw.lower() in txt_lower:
                    el.scroll_into_view_if_needed()
                    el.click()
                    selected.append(txt[:50])
                    print(f"    [SELECTED] {txt[:50]}")
                    time.sleep(0.5)
                    break
            if len(selected) >= 4:
                break
        except Exception:
            continue

    if not selected:
        # Strategy 2: try text-based selectors
        for kw in keywords[:5]:
            for tag in ["button", "label", "div", "span", "li"]:
                if wait_click(page, f'{tag}:has-text("{kw}")', timeout=1500):
                    selected.append(kw)
                    print(f"    [SELECTED] {kw}")
                    time.sleep(0.5)
                    break
            if len(selected) >= 3:
                break

    print(f"    Total selected: {len(selected)}")
    screenshot(page, "upwork_categories")
    return click_next(page)


def handle_skills(page):
    """Add skills from UPWORK_PROFILE."""
    print("\n[SKILLS] Adding skills...")
    profile = UPWORK_PROFILE
    skills = profile.get("skills", [])[:15]

    added = []
    for skill in skills:
        # Find the skills search input
        for sel in [
            'input[placeholder*="Search"]',
            'input[placeholder*="search"]',
            'input[placeholder*="skill"]',
            'input[aria-label*="skill"]',
            'input[data-test*="skill"]',
            'input[type="text"]',
        ]:
            try:
                el = page.wait_for_selector(sel, timeout=2000)
                if el:
                    el.click()
                    el.fill("")
                    el.type(skill, delay=50)
                    time.sleep(1)
                    # Pick first suggestion
                    for opt in [
                        f'[role="option"]:has-text("{skill}")',
                        f'li:has-text("{skill}")',
                        f'[data-test="suggestion"]:has-text("{skill}")',
                        '[role="option"]:first-child',
                        'li[class*="suggestion"]:first-child',
                        'ul[role="listbox"] li:first-child',
                    ]:
                        if wait_click(page, opt, timeout=1500):
                            added.append(skill)
                            print(f"    [ADDED] {skill}")
                            time.sleep(0.3)
                            break
                    break
            except Exception:
                continue
        if len(added) >= 10:
            break

    print(f"    Total added: {len(added)}")
    screenshot(page, "upwork_skills")
    return click_next(page)


def handle_experience(page):
    """Select experience level — Expert."""
    print("\n[EXPERIENCE] Setting experience level...")

    # Try to select Expert level
    for sel in [
        'button:has-text("Expert")',
        'label:has-text("Expert")',
        '[data-test*="expert"]',
        'div:has-text("Expert") >> input[type="radio"]',
        'input[value="expert"]',
        'input[value="3"]',  # often expert = 3
    ]:
        if wait_click(page, sel, timeout=2000):
            print("    [SELECTED] Expert")
            break

    screenshot(page, "upwork_experience")
    time.sleep(1)
    return click_next(page)


def handle_rate(page):
    """Set hourly rate to $45."""
    print("\n[RATE] Setting hourly rate to $45...")

    for sel in [
        'input[data-test*="rate"]',
        'input[aria-label*="rate"]',
        'input[aria-label*="Hourly"]',
        'input[placeholder*="rate"]',
        'input[id*="rate"]',
        'input[name*="rate"]',
        'input[type="number"]',
        'input[inputmode="decimal"]',
    ]:
        if fill_field(page, sel, "45"):
            print("    [SET] $45/hr")
            break

    screenshot(page, "upwork_rate")
    time.sleep(1)
    return click_next(page)


def handle_title(page):
    """Set professional title."""
    print("\n[TITLE] Setting professional title...")
    title = UPWORK_PROFILE.get("title", "AI Agent Developer | Multi-Agent Pipelines")

    for sel in [
        'input[data-test*="title"]',
        'input[aria-label*="title"]',
        'input[placeholder*="title"]',
        'input[id*="title"]',
        'input[name*="title"]',
        'input[type="text"]',
    ]:
        if fill_field(page, sel, title):
            print(f"    [SET] {title[:50]}...")
            break

    screenshot(page, "upwork_title")
    time.sleep(1)
    return click_next(page)


def handle_overview(page):
    """Set professional overview/bio."""
    print("\n[OVERVIEW] Setting professional overview...")
    overview = UPWORK_PROFILE.get("overview", "")[:5000]

    for sel in [
        'textarea[data-test*="overview"]',
        'textarea[aria-label*="overview"]',
        'textarea[aria-label*="bio"]',
        'textarea[placeholder*="overview"]',
        'textarea[placeholder*="Highlight"]',
        'textarea[id*="overview"]',
        'textarea[name*="overview"]',
        'textarea',
        'div[contenteditable="true"]',
    ]:
        try:
            el = page.wait_for_selector(sel, timeout=3000)
            if el:
                el.click()
                el.fill("")
                el.fill(overview)
                print(f"    [SET] Overview ({len(overview)} chars)")
                break
        except Exception:
            continue

    screenshot(page, "upwork_overview")
    time.sleep(1)
    return click_next(page)


def handle_photo(page):
    """Skip or handle photo upload."""
    print("\n[PHOTO] Photo upload page...")
    # Try to skip
    for sel in [
        'button:has-text("Skip")',
        'button:has-text("Skip for now")',
        'a:has-text("Skip")',
        'a:has-text("skip")',
    ]:
        if wait_click(page, sel, timeout=2000):
            print("    [SKIPPED] Photo upload")
            time.sleep(2)
            return True

    # If no skip, try Next
    screenshot(page, "upwork_photo")
    return click_next(page)


def handle_resume(page):
    """Upload CV PDF."""
    print("\n[RESUME] Uploading resume/CV...")

    if not CV_PDF.exists():
        print(f"    [WARN] CV not found: {CV_PDF}")
        return click_next(page)

    print(f"    PDF: {CV_PDF.name} ({CV_PDF.stat().st_size:,} bytes)")

    # Method 1: Direct file input
    file_inputs = page.query_selector_all('input[type="file"]')
    if file_inputs:
        file_inputs[0].set_input_files(str(CV_PDF))
        print("    [UPLOADED] via file input")
        time.sleep(3)
        screenshot(page, "upwork_resume_uploaded")
        return click_next(page)

    # Method 2: Click upload button to reveal file input
    for sel in [
        'button:has-text("Upload")',
        'button:has-text("upload")',
        'button:has-text("Add resume")',
        'button:has-text("Add Resume")',
        'a:has-text("Upload")',
        'label:has-text("Upload")',
        '[class*="upload"]',
        'button:has-text("Browse")',
    ]:
        if wait_click(page, sel, timeout=2000):
            time.sleep(2)
            fi = page.query_selector('input[type="file"]')
            if fi:
                fi.set_input_files(str(CV_PDF))
                print("    [UPLOADED] after clicking button")
                time.sleep(3)
                screenshot(page, "upwork_resume_uploaded")
                return click_next(page)

    # Method 3: use page.set_input_files on any file input that appeared
    try:
        page.set_input_files('input[type="file"]', str(CV_PDF))
        print("    [UPLOADED] via set_input_files")
        time.sleep(3)
    except Exception:
        print("    [SKIP] No file input found — skipping resume")

    screenshot(page, "upwork_resume")

    # Try skip if upload failed
    for sel in ['button:has-text("Skip")', 'a:has-text("Skip")']:
        if wait_click(page, sel, timeout=2000):
            print("    [SKIPPED] Resume upload")
            time.sleep(2)
            return True

    return click_next(page)


def handle_location(page):
    """Handle location page — should auto-detect Canada."""
    print("\n[LOCATION] Location page...")
    # Usually pre-filled. Just click Next.
    screenshot(page, "upwork_location")
    time.sleep(1)
    return click_next(page)


def handle_phone(page):
    """Handle phone verification page."""
    print("\n[PHONE] Phone verification page...")
    print("    Manual action may be required for phone verification.")
    screenshot(page, "upwork_phone")
    time.sleep(1)

    # Try skip
    for sel in ['button:has-text("Skip")', 'a:has-text("Skip")']:
        if wait_click(page, sel, timeout=2000):
            print("    [SKIPPED]")
            time.sleep(2)
            return True

    return click_next(page)


def handle_education(page):
    """Handle education page — skip or click Next."""
    print("\n[EDUCATION] Education page...")
    # Try skip
    for sel in ['button:has-text("Skip")', 'a:has-text("Skip")']:
        if wait_click(page, sel, timeout=2000):
            print("    [SKIPPED]")
            return True
    screenshot(page, "upwork_education")
    return click_next(page)


def handle_employment(page):
    """Handle employment history — skip or click Next."""
    print("\n[EMPLOYMENT] Employment history page...")
    for sel in ['button:has-text("Skip")', 'a:has-text("Skip")']:
        if wait_click(page, sel, timeout=2000):
            print("    [SKIPPED]")
            return True
    screenshot(page, "upwork_employment")
    return click_next(page)


def handle_languages(page):
    """Handle languages page — English should be pre-selected."""
    print("\n[LANGUAGES] Languages page...")
    screenshot(page, "upwork_languages")
    time.sleep(1)
    return click_next(page)


def handle_review(page):
    """Review profile and submit."""
    print("\n[REVIEW] Profile review page...")
    screenshot(page, "upwork_review")

    # Click submit
    for sel in [
        'button:has-text("Submit profile")',
        'button:has-text("Submit")',
        'button:has-text("Publish")',
        'button:has-text("Done")',
        'button[data-test="submit-profile"]',
    ]:
        if wait_click(page, sel, timeout=3000):
            print("    [SUBMITTED] Profile submitted!")
            time.sleep(5)
            screenshot(page, "upwork_submitted")
            return True

    return click_next(page)


def handle_unknown(page):
    """Handle unknown pages — inspect and try to proceed."""
    url = page.url
    print(f"\n[UNKNOWN] Unrecognized page: {url[:80]}")

    # Dump page info
    try:
        headings = page.query_selector_all("h1, h2, h3")
        for h in headings[:5]:
            txt = h.inner_text().strip()
            if txt:
                print(f"    Heading: {txt[:60]}")
    except Exception:
        pass

    screenshot(page, f"upwork_unknown_{int(time.time())}")

    # Try Next/Continue/Skip
    for sel in ['button:has-text("Skip")', 'a:has-text("Skip")']:
        if wait_click(page, sel, timeout=2000):
            print("    [SKIPPED]")
            return True

    return click_next(page)


PAGE_HANDLERS = {
    "categories": handle_categories,
    "skills": handle_skills,
    "experience": handle_experience,
    "rate": handle_rate,
    "title": handle_title,
    "overview": handle_overview,
    "photo": handle_photo,
    "resume": handle_resume,
    "location": handle_location,
    "phone": handle_phone,
    "education": handle_education,
    "employment": handle_employment,
    "languages": handle_languages,
    "review": handle_review,
    "submit": handle_review,
    "unknown": handle_unknown,
}


# ── Main ──────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  UPWORK FULL PROFILE AUTOMATION — Edge")
    print("  Handles entire create-profile wizard")
    print("=" * 60)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=False,
        channel="msedge",
        executable_path=EDGE_PATH,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-gpu",
            "--no-sandbox",
        ],
    )
    ctx_args = {"viewport": {"width": 1400, "height": 900}}
    if COOKIE_FILE.exists():
        ctx_args["storage_state"] = str(COOKIE_FILE)
        print("[+] Loaded saved cookies")
    context = browser.new_context(**ctx_args)
    page = context.new_page()

    # ── Navigate to wherever you are in the wizard ────────────
    start_url = "https://www.upwork.com/nx/create-profile/categories"
    print(f"\n[+] Opening {start_url}")
    page.goto(start_url, wait_until="domcontentloaded")
    time.sleep(4)

    # ── Login check ───────────────────────────────────────────
    current_page = detect_page(page)
    if current_page == "login":
        print("[!] Not logged in — please log in manually in Edge...")
        print("    Waiting up to 5 minutes...")
        for _ in range(300):
            time.sleep(1)
            current_page = detect_page(page)
            if current_page != "login":
                print("[+] Login detected!")
                break
        context.storage_state(path=str(COOKIE_FILE))
        page.goto(start_url, wait_until="domcontentloaded")
        time.sleep(4)

    # ── Main wizard loop ──────────────────────────────────────
    max_steps = 20
    step = 0
    visited = set()

    while step < max_steps:
        step += 1
        current_page = detect_page(page)
        current_url = page.url

        print(f"\n{'='*50}")
        print(f"  Step {step}: [{current_page.upper()}]")
        print(f"  URL: {current_url[:80]}")
        print(f"{'='*50}")

        if current_page == "done":
            print("\n[+] PROFILE COMPLETE — reached dashboard!")
            screenshot(page, "upwork_done")
            break

        if current_page == "login":
            print("[!] Redirected to login — waiting...")
            for _ in range(120):
                time.sleep(1)
                if detect_page(page) != "login":
                    break
            context.storage_state(path=str(COOKIE_FILE))
            continue

        # Avoid infinite loops on same page
        page_key = f"{current_page}:{current_url}"
        if page_key in visited:
            print(f"    [WARN] Already visited this page, trying to advance...")
            if not click_next(page):
                print("    [STUCK] Cannot advance — stopping")
                break
            time.sleep(3)
            continue
        visited.add(page_key)

        # Run the handler for this page
        handler = PAGE_HANDLERS.get(current_page, handle_unknown)
        result = handler(page)

        if not result:
            print(f"    [WARN] Handler returned False — page may need manual action")
            print("    Waiting 30s for manual intervention, then retrying...")
            time.sleep(30)

        # Save cookies after each step
        context.storage_state(path=str(COOKIE_FILE))
        time.sleep(2)

    # ── Done ──────────────────────────────────────────────────
    context.storage_state(path=str(COOKIE_FILE))
    screenshot(page, "upwork_final")

    print("\n" + "=" * 60)
    print("  AUTOMATION COMPLETE")
    print(f"  Steps completed: {step}")
    print(f"  Final URL: {page.url[:80]}")
    print("  Browser stays open for review — Ctrl+C to close")
    print("=" * 60)

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
    browser.close()
    pw.stop()
    print("Browser closed.")


if __name__ == "__main__":
    main()
