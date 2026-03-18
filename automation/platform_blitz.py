"""Multi-Platform Blitz — Sign up / log in to ALL freelance platforms at once.

Opens Edge with one tab per platform.  You log in to each.
Once ready, it fills profiles and creates listings automatically.

Usage:
    python -m automation.platform_blitz                   # Full blitz (all platforms)
    python -m automation.platform_blitz --only pph,guru   # Specific platforms
    python -m automation.platform_blitz --fiverr-publish   # Just publish Fiverr drafts
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

from income.freelance_listings import (
    FIVERR_GIGS,
    FREELANCER_PROFILE,
    PEOPLEPERHOUR_PROFILE,
    GURU_PROFILE,
    UPWORK_PROFILE,
)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PROFILE_DIR = PROJECT / "data" / "platform_browser" / "edge_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
SS_DIR = PROJECT / "output" / "platform_screenshots"
SS_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = PROJECT / "data" / "platform_blitz_state.json"
CV_PDF = PROJECT / "output" / "CV_digitallabour.pdf"
CV_FALLBACKS = [
    PROJECT / "output" / "bit_rage_labour_systems.pdf",
    PROJECT / "output" / "CV_digitallabour_clean.pdf",
]


# ── Platform configs ──────────────────────────────────────────

PLATFORMS = {
    "freelancer": {
        "name": "Freelancer.com",
        "signup": "https://www.freelancer.com/signup",
        "login": "https://www.freelancer.com/login",
        "dashboard": "https://www.freelancer.com/dashboard",
        "profile_edit": "https://www.freelancer.com/u/settings/profile",
        "dashboard_keywords": ["dashboard", "/u/", "feed"],
        "profile_data": FREELANCER_PROFILE,
    },
    "pph": {
        "name": "PeoplePerHour",
        "signup": "https://www.peopleperhour.com/register/freelancer",
        "login": "https://www.peopleperhour.com/login",
        "dashboard": "https://www.peopleperhour.com/freelancer/dashboard",
        "profile_edit": "https://www.peopleperhour.com/freelancer/edit-profile",
        "hourlies_create": "https://www.peopleperhour.com/freelancer/hourlies/new",
        "dashboard_keywords": ["dashboard", "freelancer", "account"],
        "profile_data": PEOPLEPERHOUR_PROFILE,
    },
    "guru": {
        "name": "Guru.com",
        "signup": "https://www.guru.com/freelancers/signup",
        "login": "https://www.guru.com/login.aspx",
        "dashboard": "https://www.guru.com/freelancers/dashboard",
        "profile_edit": "https://www.guru.com/freelancers/editProfile.aspx",
        "dashboard_keywords": ["dashboard", "myaccount", "freelancers"],
        "profile_data": GURU_PROFILE,
    },
}


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"platforms": {}, "last_run": None}


def _save_state(state: dict):
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _human_delay(lo: float = 1.5, hi: float = 4.0):
    time.sleep(random.uniform(lo, hi))


def _fill(page, selector: str, value: str, timeout: int = 3000) -> bool:
    try:
        el = page.wait_for_selector(selector, timeout=timeout)
        if el:
            el.click()
            el.fill(value)
            return True
    except Exception:
        return False


def _click(page, selector: str, timeout: int = 3000) -> bool:
    try:
        el = page.wait_for_selector(selector, timeout=timeout)
        if el and el.is_visible():
            el.click()
            return True
    except Exception:
        return False


def _cv_path() -> Path | None:
    if CV_PDF.exists():
        return CV_PDF
    for fb in CV_FALLBACKS:
        if fb.exists():
            return fb
    return None


# ── Profile fillers per platform ──────────────────────────────

def _fill_freelancer(page, profile: dict):
    """Fill Freelancer.com profile fields."""
    print("    Filling Freelancer profile...")

    # Navigate to profile edit
    page.goto("https://www.freelancer.com/u/settings/profile", wait_until="domcontentloaded")
    _human_delay(2, 4)

    # Tagline
    _fill(page, 'input[name="tagline"], input[placeholder*="tagline"], input[id*="tagline"]',
          profile.get("tagline", "")[:80])
    _human_delay()

    # Bio/Overview
    overview = profile.get("overview", "")[:3000]
    for sel in ['textarea[name="bio"]', 'textarea[name="about"]', 'textarea[name="summary"]',
                '#about-me-text', 'textarea.about-me', '[data-qa="about-me"] textarea']:
        if _fill(page, sel, overview):
            break
    _human_delay()

    # Hourly rate
    rate = profile.get("hourly_rate", "75").replace("$", "").split("-")[0].split("/")[0].strip()
    _fill(page, 'input[name="hourlyRate"], input[name="hourly_rate"], input[type="number"]', rate)
    _human_delay()

    # Skills
    for skill in profile.get("skills", [])[:10]:
        for sel in ['input[name="skills"]', '.skill-input input', 'input[placeholder*="skill"]',
                    'input[placeholder*="Add"]']:
            if _fill(page, sel, skill, timeout=2000):
                page.keyboard.press("Enter")
                _human_delay(0.5, 1)
                break

    page.screenshot(path=str(SS_DIR / "freelancer_profile_filled.png"))

    # Save
    for sel in ['button:has-text("Save")', 'button:has-text("Update")', 'button[type="submit"]']:
        if _click(page, sel, timeout=3000):
            print("    Save clicked.")
            break

    _human_delay(2, 4)
    print("    Freelancer profile done.")


def _fill_pph(page, profile: dict):
    """Fill PeoplePerHour profile fields."""
    print("    Filling PPH profile...")

    page.goto("https://www.peopleperhour.com/freelancer/edit-profile", wait_until="domcontentloaded")
    _human_delay(2, 4)

    # Tagline
    _fill(page, 'input[name="tagline"], input[placeholder*="tagline"]',
          profile.get("tagline", "")[:80])
    _human_delay()

    # Bio
    overview = profile.get("overview", "")[:3000]
    for sel in ['textarea[name="bio"]', 'textarea[name="overview"]', '#freelancerBio',
                'textarea.form-control']:
        if _fill(page, sel, overview):
            break
    _human_delay()

    # Hourly rate
    rate = profile.get("hourly_rate", "60").replace("\u00a3", "").replace("GBP", "").split("-")[0].split("/")[0].strip()
    _fill(page, 'input[name="hourly_rate"], input[name="rate"]', rate)
    _human_delay()

    # Skills
    for skill in profile.get("skills", [])[:10]:
        for sel in ['input[name="skills"]', '.skill-input input', 'input[placeholder*="skill"]']:
            if _fill(page, sel, skill, timeout=2000):
                page.keyboard.press("Enter")
                _human_delay(0.5, 1)
                break

    page.screenshot(path=str(SS_DIR / "pph_profile_filled.png"))

    for sel in ['button:has-text("Save")', 'button:has-text("Update")', 'button[type="submit"]']:
        if _click(page, sel, timeout=3000):
            print("    Save clicked.")
            break

    _human_delay(2, 4)
    print("    PPH profile done.")


def _fill_guru(page, profile: dict):
    """Fill Guru.com profile fields."""
    print("    Filling Guru profile...")

    page.goto("https://www.guru.com/freelancers/editProfile.aspx", wait_until="domcontentloaded")
    _human_delay(2, 4)

    # Tagline
    _fill(page, 'input[name="tagLine"], input[id="tagLine"], input[name="headline"]',
          profile.get("tagline", "")[:80])
    _human_delay()

    # Overview
    overview = profile.get("overview", "")[:3000]
    for sel in ['textarea[name="description"]', '#profileDescription', 'textarea[name="summary"]',
                'textarea.form-control']:
        if _fill(page, sel, overview):
            break
    _human_delay()

    # Hourly rate
    rate = profile.get("hourly_rate", "85").replace("$", "").split("-")[0].split("/")[0].strip()
    _fill(page, 'input[name="hourlyRate"], input[name="rate"]', rate)
    _human_delay()

    # Skills
    for skill in profile.get("skills", [])[:15]:
        for sel in ['input[name="skills"]', '.skill-input input', 'input[placeholder*="skill"]',
                    '#skillsInput']:
            if _fill(page, sel, skill, timeout=2000):
                page.keyboard.press("Enter")
                _human_delay(0.5, 1)
                break

    page.screenshot(path=str(SS_DIR / "guru_profile_filled.png"))

    for sel in ['button:has-text("Save")', 'button:has-text("Update")', 'button[type="submit"]']:
        if _click(page, sel, timeout=3000):
            print("    Save clicked.")
            break

    _human_delay(2, 4)
    print("    Guru profile done.")


FILLERS = {
    "freelancer": _fill_freelancer,
    "pph": _fill_pph,
    "guru": _fill_guru,
}


# ── Main blitz flow ───────────────────────────────────────────

def run_blitz(platforms: list[str]):
    """Open all platforms in tabs, wait for login, then fill profiles."""
    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth

    print(f"\n{'='*60}")
    print("  PLATFORM BLITZ \u2014 Multi-Tab Signup")
    print(f"  Platforms: {', '.join(p.upper() for p in platforms)}")
    print(f"{'='*60}\n")

    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
        channel="msedge",
        executable_path=EDGE_PATH,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        viewport={"width": 1400, "height": 900},
        locale="en-CA",
        timezone_id="America/Toronto",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    )

    stealth = Stealth()
    state = _load_state()

    # ── Step 1: Open a tab per platform ───────────────────────
    tabs = {}
    for plat in platforms:
        cfg = PLATFORMS[plat]
        page = context.new_page()
        stealth.apply_stealth_sync(page)
        page.goto(cfg["login"], wait_until="domcontentloaded")
        tabs[plat] = page
        print(f"  [{cfg['name']}] Tab opened \u2014 {cfg['login']}")
        _human_delay(1, 2)

    # Close the default blank tab if it exists
    if context.pages and "about:blank" in context.pages[0].url:
        context.pages[0].close()

    print(f"\n  \u2501\u2501\u2501 LOG IN TO EACH PLATFORM TAB \u2501\u2501\u2501")
    print("  Complete signups / logins in each tab.")
    print("  Script will detect when you reach the dashboard.")
    print("  Waiting up to 10 minutes...\n")

    # ── Step 2: Wait for all logins ───────────────────────────
    logged_in = {p: False for p in platforms}
    start = time.time()
    timeout = 600  # 10 min

    while not all(logged_in.values()) and (time.time() - start) < timeout:
        for plat in platforms:
            if logged_in[plat]:
                continue
            cfg = PLATFORMS[plat]
            try:
                url = tabs[plat].url.lower()
                # Check if we're past login/signup
                past_login = not any(kw in url for kw in ["login", "signin", "signup", "register"])
                on_dashboard = any(kw in url for kw in cfg["dashboard_keywords"])
                if past_login or on_dashboard:
                    logged_in[plat] = True
                    print(f"  \u2713 [{cfg['name']}] Logged in! ({tabs[plat].url[:60]})")
                    state["platforms"][plat] = {
                        "logged_in": True,
                        "logged_in_at": datetime.now(timezone.utc).isoformat(),
                    }
                    _save_state(state)
            except Exception:
                pass  # Page might be navigating
        time.sleep(2)

    not_logged = [p for p, v in logged_in.items() if not v]
    if not_logged:
        print(f"\n  \u26a0 Not logged in: {', '.join(not_logged)}")
        print("  Continuing with available platforms...\n")

    # ── Step 3: Fill profiles ─────────────────────────────────
    for plat in platforms:
        if not logged_in[plat]:
            continue
        cfg = PLATFORMS[plat]
        filler = FILLERS.get(plat)
        if filler:
            print(f"\n  ── {cfg['name']} Profile Fill ──")
            try:
                filler(tabs[plat], cfg["profile_data"])
                state["platforms"][plat]["profile_filled"] = True
                state["platforms"][plat]["profile_filled_at"] = datetime.now(timezone.utc).isoformat()
                _save_state(state)
            except Exception as e:
                print(f"    Profile fill error: {e}")
                tabs[plat].screenshot(path=str(SS_DIR / f"{plat}_error.png"))

    # ── Step 4: CV upload ─────────────────────────────────────
    cv = _cv_path()
    if cv:
        for plat in platforms:
            if not logged_in[plat]:
                continue
            cfg = PLATFORMS[plat]
            print(f"\n  ── {cfg['name']} CV Upload ──")
            try:
                page = tabs[plat]
                page.goto(cfg.get("profile_edit", cfg["dashboard"]), wait_until="domcontentloaded")
                _human_delay(2, 4)

                file_inputs = page.query_selector_all('input[type="file"]')
                uploaded = False
                for fi in file_inputs:
                    try:
                        fi.set_input_files(str(cv))
                        uploaded = True
                        print(f"    CV uploaded: {cv.name}")
                        break
                    except Exception:
                        continue

                if not uploaded:
                    # Try clicking upload button first
                    for sel in ['button:has-text("Upload")', 'a:has-text("Upload")',
                                'button:has-text("Add Resume")', 'button:has-text("Add CV")']:
                        if _click(page, sel, timeout=2000):
                            _human_delay(1, 2)
                            fi = page.query_selector('input[type="file"]')
                            if fi:
                                fi.set_input_files(str(cv))
                                uploaded = True
                                print(f"    CV uploaded: {cv.name}")
                                break

                if not uploaded:
                    print(f"    CV upload needs manual action.")

                state["platforms"][plat]["cv_uploaded"] = uploaded
                _save_state(state)
            except Exception as e:
                print(f"    CV upload error: {e}")
    else:
        print("\n  No CV PDF found. Skipping CV uploads.")

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  BLITZ COMPLETE")
    for plat in platforms:
        cfg = PLATFORMS[plat]
        s = state.get("platforms", {}).get(plat, {})
        login = "\u2713" if s.get("logged_in") else "\u2717"
        profile = "\u2713" if s.get("profile_filled") else "\u2717"
        cv_up = "\u2713" if s.get("cv_uploaded") else "\u2717"
        print(f"  {login} {cfg['name']:<20} Login:{login}  Profile:{profile}  CV:{cv_up}")
    print(f"{'='*60}")
    print("\n  Browser stays open \u2014 review profiles, then Ctrl+C to close.\n")

    try:
        while True:
            time.sleep(5)
            try:
                context.storage_state(path=str(PROFILE_DIR / "storage.json"))
            except Exception:
                break
    except KeyboardInterrupt:
        print("\n[+] Closing...")

    context.close()
    pw.stop()


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-Platform Blitz")
    parser.add_argument("--only", type=str, default=None,
                        help="Comma-separated platforms: freelancer,pph,guru")
    args = parser.parse_args()

    if args.only:
        platforms = [p.strip().lower() for p in args.only.split(",")
                     if p.strip().lower() in PLATFORMS]
    else:
        platforms = list(PLATFORMS.keys())

    if not platforms:
        print("No valid platforms. Use: freelancer, pph, guru")
        return

    run_blitz(platforms)


if __name__ == "__main__":
    main()
