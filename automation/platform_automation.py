"""Platform Signup & Profile Automation — Upwork, PPH, Guru.

Automates as much as possible of platform onboarding:
- Opens signup pages in Playwright
- Pre-fills profile fields (overview, skills, hourly rate, portfolio)
- Creates service listings / hourlies from platform_copy data
- Uploads CV PDF to each platform

Signup requires manual CAPTCHA / email verification, but once logged in
the profile filling and listing creation are fully automated.

Usage:
    python -m automation.platform_automation --signup upwork     # Open signup + guided fill
    python -m automation.platform_automation --signup pph
    python -m automation.platform_automation --signup guru
    python -m automation.platform_automation --signup all        # All three
    python -m automation.platform_automation --profile upwork    # Fill profile (must be logged in)
    python -m automation.platform_automation --profile all
    python -m automation.platform_automation --upload-cv upwork  # Upload CV PDF
    python -m automation.platform_automation --upload-cv all
"""

import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from income.freelance_listings import (
    UPWORK_PROFILE,
    PEOPLEPERHOUR_PROFILE,
    GURU_PROFILE,
)

BROWSER_DIR = PROJECT_ROOT / "data" / "platform_browser"
COOKIE_DIR = BROWSER_DIR / "cookies"
SS_DIR = PROJECT_ROOT / "output" / "platform_screenshots"
COPY_DIR = PROJECT_ROOT / "output" / "platform_copy"
CV_PDF = PROJECT_ROOT / "output" / "CV_digitallabour.pdf"
# Fallback CVs
CV_FALLBACKS = [
    PROJECT_ROOT / "output" / "digital_labour_systems.pdf",
    PROJECT_ROOT / "output" / "CV_digitallabour_clean.pdf",
]

PLATFORMS = {
    "upwork": {
        "name": "Upwork",
        "signup_url": "https://www.upwork.com/nx/signup/?dest=home",
        "login_url": "https://www.upwork.com/ab/account-security/login",
        "profile_url": "https://www.upwork.com/freelancers/settings/profile",
        "services_url": "https://www.upwork.com/freelancers/settings/services",
        "profile_data": UPWORK_PROFILE,
        "copy_file": "upwork_listings.txt",
    },
    "pph": {
        "name": "PeoplePerHour",
        "signup_url": "https://www.peopleperhour.com/register/freelancer",
        "login_url": "https://www.peopleperhour.com/login",
        "profile_url": "https://www.peopleperhour.com/freelancer/edit-profile",
        "hourlies_url": "https://www.peopleperhour.com/freelancer/hourlies/new",
        "profile_data": PEOPLEPERHOUR_PROFILE,
        "copy_file": "pph_listings.txt",
    },
    "guru": {
        "name": "Guru",
        "signup_url": "https://www.guru.com/freelancers/signup",
        "login_url": "https://www.guru.com/login.aspx",
        "profile_url": "https://www.guru.com/freelancers/editProfile.aspx",
        "services_url": "https://www.guru.com/freelancers/services/create",
        "profile_data": GURU_PROFILE,
        "copy_file": "guru_listings.txt",
    },
}


# ── BROWSER HELPERS ────────────────────────────────────────────

def _get_cookie_file(platform: str) -> Path:
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    return COOKIE_DIR / f"{platform}_cookies.json"


def _launch(platform: str, headless: bool = False):
    """Launch Playwright browser with platform-specific cookie persistence."""
    from playwright.sync_api import sync_playwright

    BROWSER_DIR.mkdir(parents=True, exist_ok=True)
    pw = sync_playwright().start()
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    browser = pw.chromium.launch(
        headless=headless,
        channel="msedge",
        executable_path=edge_path,
        args=["--disable-blink-features=AutomationControlled", "--disable-gpu", "--no-sandbox"],
    )
    ctx_kwargs: dict[str, Any] = {"viewport": {"width": 1400, "height": 900}}
    cookie_file = _get_cookie_file(platform)
    if cookie_file.exists():
        ctx_kwargs["storage_state"] = str(cookie_file)
    context = browser.new_context(**ctx_kwargs)
    return pw, browser, context


def _save_cookies(context, platform: str):
    cookie_file = _get_cookie_file(platform)
    context.storage_state(path=str(cookie_file))


def _close_all(pw, browser, context, platform: str):
    _save_cookies(context, platform)
    context.close()
    browser.close()
    pw.stop()


def _screenshot(page, name: str):
    SS_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SS_DIR / f"{name}.png"))


def _wait_and_click(page, selector: str, timeout: int = 3000) -> bool:
    try:
        el = page.wait_for_selector(selector, timeout=timeout)
        if el:
            el.click()
            return True
    except Exception:
        pass
    return False


def _fill_field(page, selector: str, value: str, timeout: int = 3000) -> bool:
    try:
        el = page.wait_for_selector(selector, timeout=timeout)
        if el:
            el.click()
            el.fill(value)
            return True
    except Exception:
        pass
    return False


def _get_cv_path() -> Path | None:
    """Find the best CV PDF to upload."""
    if CV_PDF.exists():
        return CV_PDF
    for fb in CV_FALLBACKS:
        if fb.exists():
            return fb
    return None


# ── SIGNUP FLOW (opens browser, user completes CAPTCHA) ────────

def signup_flow(platform: str):
    """Open signup page and provide guided instructions.

    CAPTCHAs and email verification must be done manually.
    Once signed up, saves cookies for profile automation.
    """
    cfg = PLATFORMS[platform]
    print(f"\n{'='*60}")
    print(f"  {cfg['name']} — SIGNUP FLOW")
    print(f"  URL: {cfg['signup_url']}")
    print(f"{'='*60}")

    pw, browser, context = _launch(platform, headless=False)
    page = context.new_page()

    page.goto(cfg["signup_url"], wait_until="domcontentloaded")
    time.sleep(3)
    _screenshot(page, f"{platform}_signup_start")

    print(f"\n  Browser opened to {cfg['name']} signup.")
    print("  Complete signup manually (CAPTCHA + email verification).")
    print("  Once you reach the profile/dashboard, press Enter here...")
    print("  (Cookies will be saved for future automation)")
    print("  Waiting up to 10 minutes...\n")

    # Wait for user to reach the dashboard / profile area
    try:
        for _ in range(600):  # 10 min max
            time.sleep(1)
            url = page.url.lower()
            # Detect that user has progressed past signup
            if any(kw in url for kw in ["dashboard", "profile", "home", "settings", "freelancer"]):
                if "signup" not in url and "register" not in url and "login" not in url:
                    print(f"  Detected logged-in state: {page.url[:80]}")
                    break
        else:
            print("  Timeout — saving cookies anyway.")
    except KeyboardInterrupt:
        print("  Interrupted — saving cookies.")

    _screenshot(page, f"{platform}_signup_done")
    _save_cookies(context, platform)
    print(f"  Cookies saved for {cfg['name']}.\n")

    # Offer to continue to profile filling
    _close_all(pw, browser, context, platform)


# ── PROFILE FILL ───────────────────────────────────────────────

def fill_profile_upwork(page, profile: dict):
    """Fill Upwork freelancer profile fields."""
    print("  Filling Upwork profile...")

    # Title/headline
    _fill_field(page, '[data-test="title"] input, input[aria-label*="title"], #profileTitle', profile.get("title", ""), timeout=5000)
    time.sleep(1)

    # Overview / professional overview
    for sel in ['[data-test="overview"] textarea', 'textarea[aria-label*="overview"]', '#profileOverview', 'textarea.up-textarea']:
        if _fill_field(page, sel, profile.get("overview", "")[:5000], timeout=3000):
            break
    time.sleep(1)

    # Hourly rate
    for sel in ['[data-test="rate"] input', 'input[aria-label*="rate"]', 'input[data-test="hourly-rate"]']:
        if _fill_field(page, sel, "85", timeout=3000):
            break
    time.sleep(1)

    # Skills — Upwork has a tag-style skill picker
    skills = profile.get("skills", [])[:15]
    for skill in skills:
        for sel in ['[data-test="skills"] input', 'input[aria-label*="skill"]', '.skills-input input']:
            el = None
            try:
                el = page.wait_for_selector(sel, timeout=2000)
            except Exception:
                continue
            if el:
                el.fill(skill)
                time.sleep(0.5)
                # Select the dropdown suggestion if it appears
                _wait_and_click(page, f'[role="option"]:has-text("{skill}"), li:has-text("{skill}")', timeout=2000)
                time.sleep(0.3)
                break

    _screenshot(page, "upwork_profile_filled")
    print("  Upwork profile fields filled.")


def fill_profile_pph(page, profile: dict):
    """Fill PeoplePerHour profile fields."""
    print("  Filling PPH profile...")

    # Tagline
    _fill_field(page, 'input[name="tagline"], input[placeholder*="tagline"]', profile.get("tagline", "")[:80])
    time.sleep(1)

    # Bio/Overview
    for sel in ['textarea[name="bio"]', 'textarea[name="overview"]', '#freelancerBio', 'textarea.form-control']:
        if _fill_field(page, sel, profile.get("overview", "")[:3000]):
            break
    time.sleep(1)

    # Hourly rate
    _fill_field(page, 'input[name="hourly_rate"], input[name="rate"]', "80")
    time.sleep(1)

    # Skills
    skills = profile.get("skills", [])[:10]
    for skill in skills:
        el = None
        for sel in ['input[name="skills"]', '.skill-input input', 'input[placeholder*="skill"]']:
            try:
                el = page.wait_for_selector(sel, timeout=2000)
            except Exception:
                continue
            if el:
                el.fill(skill)
                time.sleep(0.5)
                _wait_and_click(page, f'[role="option"]:has-text("{skill}"), li:has-text("{skill}")', timeout=2000)
                time.sleep(0.3)
                break

    _screenshot(page, "pph_profile_filled")
    print("  PPH profile fields filled.")


def fill_profile_guru(page, profile: dict):
    """Fill Guru freelancer profile fields."""
    print("  Filling Guru profile...")

    # Tagline / professional headline
    _fill_field(page, 'input[name="tagLine"], input[id="tagLine"], input[name="headline"]', profile.get("tagline", "")[:80])
    time.sleep(1)

    # Description
    for sel in ['textarea[name="description"]', '#profileDescription', 'textarea[name="summary"]', 'textarea.form-control']:
        if _fill_field(page, sel, profile.get("overview", "")[:3000]):
            break
    time.sleep(1)

    # Hourly rate
    _fill_field(page, 'input[name="hourlyRate"], input[name="rate"]', "85")
    time.sleep(1)

    # Skills
    skills = profile.get("skills", [])[:15]
    for skill in skills:
        for sel in ['input[name="skills"]', '.skill-input input', 'input[placeholder*="skill"]', '#skillsInput']:
            el = None
            try:
                el = page.wait_for_selector(sel, timeout=2000)
            except Exception:
                continue
            if el:
                el.fill(skill)
                time.sleep(0.5)
                _wait_and_click(page, f'[role="option"]:has-text("{skill}"), li:has-text("{skill}")', timeout=2000)
                time.sleep(0.3)
                break

    _screenshot(page, "guru_profile_filled")
    print("  Guru profile fields filled.")


PROFILE_FILLERS = {
    "upwork": fill_profile_upwork,
    "pph": fill_profile_pph,
    "guru": fill_profile_guru,
}


def fill_profile(platform: str):
    """Navigate to profile page and auto-fill fields."""
    cfg = PLATFORMS[platform]
    profile = cfg["profile_data"]

    print(f"\n{'='*60}")
    print(f"  {cfg['name']} — PROFILE FILL")
    print(f"{'='*60}")

    pw, browser, context = _launch(platform, headless=False)
    page = context.new_page()

    page.goto(cfg.get("profile_url", cfg["login_url"]), wait_until="domcontentloaded")
    time.sleep(3)

    # Check login
    if any(kw in page.url.lower() for kw in ["login", "signin", "signup"]):
        print(f"\n  Not logged in to {cfg['name']}. Please log in manually...")
        print("  Waiting up to 5 minutes...")
        try:
            for _ in range(300):
                time.sleep(1)
                if not any(kw in page.url.lower() for kw in ["login", "signin", "signup"]):
                    break
            _save_cookies(context, platform)
        except KeyboardInterrupt:
            pass

        # Re-navigate to profile after login
        page.goto(cfg.get("profile_url", ""), wait_until="domcontentloaded")
        time.sleep(3)

    _screenshot(page, f"{platform}_profile_before")

    # Run platform-specific filler
    filler = PROFILE_FILLERS.get(platform)
    if filler:
        filler(page, profile)

    # Save profile changes — look for common save/submit buttons
    for save_sel in [
        'button:has-text("Save")',
        'button:has-text("Update")',
        'button:has-text("Submit")',
        'button[type="submit"]',
        'input[type="submit"]',
    ]:
        if _wait_and_click(page, save_sel, timeout=3000):
            print("  Save button clicked.")
            time.sleep(3)
            break

    _screenshot(page, f"{platform}_profile_after")
    _save_cookies(context, platform)

    print(f"  Profile fill complete for {cfg['name']}.")
    print("  Browser stays open 30s for review...")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass

    _close_all(pw, browser, context, platform)


# ── CV UPLOAD ──────────────────────────────────────────────────

def upload_cv(platform: str):
    """Upload CV PDF to platform profile."""
    cfg = PLATFORMS[platform]
    cv_path = _get_cv_path()

    if not cv_path:
        print(f"  No CV PDF found. Generate one first:")
        print(f"  python output/gen_cv_pdf.py")
        return

    print(f"\n{'='*60}")
    print(f"  {cfg['name']} — CV UPLOAD")
    print(f"  PDF: {cv_path.name} ({cv_path.stat().st_size:,} bytes)")
    print(f"{'='*60}")

    pw, browser, context = _launch(platform, headless=False)
    page = context.new_page()

    # Platform-specific upload paths
    upload_urls = {
        "upwork": "https://www.upwork.com/freelancers/settings/profile",
        "pph": "https://www.peopleperhour.com/freelancer/edit-profile",
        "guru": "https://www.guru.com/freelancers/editProfile.aspx",
    }

    page.goto(upload_urls.get(platform) or cfg["profile_url"], wait_until="domcontentloaded")
    time.sleep(3)

    # Check login
    if any(kw in page.url.lower() for kw in ["login", "signin", "signup"]):
        print(f"  Not logged in to {cfg['name']}. Please log in manually...")
        for _ in range(300):
            time.sleep(1)
            if not any(kw in page.url.lower() for kw in ["login", "signin", "signup"]):
                break
        _save_cookies(context, platform)
        page.goto(upload_urls.get(platform) or cfg["profile_url"], wait_until="domcontentloaded")
        time.sleep(3)

    _screenshot(page, f"{platform}_cv_before")

    # Try to find file upload input — most platforms have a hidden <input type="file">
    upload_done = False

    # Approach 1: Direct file input
    file_inputs = page.query_selector_all('input[type="file"]')
    if file_inputs:
        for fi in file_inputs:
            # Check if it's likely a CV/resume/document upload
            parent_text = ""
            try:
                parent = fi.evaluate_handle("el => el.closest('section, div, form')")
                parent_text = parent.as_element().inner_text().lower() if parent.as_element() else ""  # type: ignore[union-attr]
            except Exception:
                pass

            if any(kw in parent_text for kw in ["resume", "cv", "portfolio", "document", "file", "upload", "attachment"]):
                fi.set_input_files(str(cv_path))
                upload_done = True
                print(f"  CV uploaded via file input: {cv_path.name}")
                break

        # If no matching context, use the first file input
        if not upload_done and file_inputs:
            file_inputs[0].set_input_files(str(cv_path))
            upload_done = True
            print(f"  CV uploaded via first file input: {cv_path.name}")

    # Approach 2: Click an upload button first to reveal the file input
    if not upload_done:
        for btn_sel in [
            'button:has-text("Upload")',
            'a:has-text("Upload")',
            'button:has-text("Add Resume")',
            'button:has-text("Add CV")',
            'button:has-text("Add Portfolio")',
            'button:has-text("Attach")',
            '[class*="upload"] button',
        ]:
            if _wait_and_click(page, btn_sel, timeout=2000):
                time.sleep(2)
                # Now look for file input that appeared
                fi = page.query_selector('input[type="file"]')
                if fi:
                    fi.set_input_files(str(cv_path))
                    upload_done = True
                    print(f"  CV uploaded after clicking upload button: {cv_path.name}")
                    break

    if not upload_done:
        print("  Could not find file upload input. Manual upload needed.")
        print(f"  File: {cv_path}")

    time.sleep(3)

    # Try to save/submit
    for save_sel in ['button:has-text("Save")', 'button:has-text("Upload")', 'button:has-text("Submit")', 'button[type="submit"]']:
        if _wait_and_click(page, save_sel, timeout=3000):
            print("  Save button clicked.")
            time.sleep(3)
            break

    _screenshot(page, f"{platform}_cv_after")
    _save_cookies(context, platform)

    print(f"  CV upload flow complete for {cfg['name']}.")
    print("  Browser stays open 30s for review...")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass

    _close_all(pw, browser, context, platform)


# ── FULL ONBOARDING PIPELINE ──────────────────────────────────

def full_onboarding(platform: str):
    """Run signup → profile fill → CV upload for a platform."""
    print(f"\n{'#'*60}")
    print(f"  FULL ONBOARDING: {PLATFORMS[platform]['name']}")
    print(f"{'#'*60}")

    signup_flow(platform)
    fill_profile(platform)
    upload_cv(platform)

    print(f"\n  {PLATFORMS[platform]['name']} onboarding complete!\n")


# ── CLI ────────────────────────────────────────────────────────

def _parse_platforms(val: str) -> list[str]:
    if val == "all":
        return list(PLATFORMS.keys())
    return [p.strip().lower() for p in val.split(",") if p.strip().lower() in PLATFORMS]


def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        return

    # Parse which platforms
    platforms = []
    for i, arg in enumerate(args):
        if arg.startswith("--") and i + 1 < len(args):
            platforms = _parse_platforms(args[i + 1])
            break

    if not platforms:
        # Try last arg
        platforms = _parse_platforms(args[-1])

    if not platforms:
        print("  No valid platform specified. Use: upwork, pph, guru, or all")
        return

    for platform in platforms:
        if "--signup" in args:
            signup_flow(platform)
        elif "--profile" in args:
            fill_profile(platform)
        elif "--upload-cv" in args or "--cv" in args:
            upload_cv(platform)
        elif "--full" in args:
            full_onboarding(platform)
        else:
            print(f"  Unknown action. Use: --signup, --profile, --upload-cv, --full")
            return


if __name__ == "__main__":
    main()
