"""Fiverr Automation — Full gig deployment with browser automation + image generation.

Fiverr has NO public seller API. This script automates gig creation by:
  1. Generating professional cover images (Pillow, 1280x769px)
  2. Opening a persistent Playwright browser (saves cookies/login)
  3. Filling gig creation forms automatically
  4. Uploading generated images
  5. Falling back to clipboard-guided mode if automation fails

New sellers: 4 gigs max. Script picks the top 4 by default, or user chooses.

Usage:
    python -m automation.fiverr_automation --images          # Generate all gig images
    python -m automation.fiverr_automation --deploy           # Full browser automation
    python -m automation.fiverr_automation --deploy --gigs 3,7,8,16  # Specific gigs
    python -m automation.fiverr_automation --publish          # Publish all draft gigs
    python -m automation.fiverr_automation --publish --gigs 3,7  # Publish specific gigs
    python -m automation.fiverr_automation --guided           # Clipboard walk-through
    python -m automation.fiverr_automation --status           # Deployment dashboard
    python -m automation.fiverr_automation --login            # Just open browser & log in
"""

import json
import os
import re
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from income.freelance_listings import FIVERR_GIGS

IMAGE_DIR = PROJECT_ROOT / "output" / "fiverr_images"
STATE_FILE = PROJECT_ROOT / "data" / "fiverr_deploy_state.json"
BROWSER_DIR = PROJECT_ROOT / "data" / "fiverr_browser"
FIVERR_BASE = "https://www.fiverr.com"

# Best 4 gigs for a new seller (high-demand Fiverr categories)
DEFAULT_TOP_4 = [3, 7, 8, 16]  # Content Repurpose, SEO Blog, Social Media, Ad Copy

# Fiverr gig image spec
IMG_W, IMG_H = 1280, 769

# Color palette
COLORS = {
    "bg_dark":   (18,  18,  25),
    "bg_card":   (28,  28,  40),
    "accent":    (0,   200, 150),
    "accent2":   (80,  120, 255),
    "white":     (255, 255, 255),
    "grey":      (160, 160, 170),
    "light_grey": (200, 200, 210),
    "dark_grey": (60,  60,  75),
}

# Icon/emoji mapping for each gig type
GIG_ICONS = {
    "sales": "⚡", "support": "🎯", "content": "✍️", "document": "📄",
    "lead": "🔍", "email": "📧", "seo": "📈", "social": "💬",
    "data": "📊", "web": "🌐", "crm": "🔄", "expense": "💰",
    "proposal": "📝", "product": "🏷️", "resume": "📋", "ad": "🎨",
    "market": "📉", "business": "📑", "press": "📰", "tech": "⚙️",
}

# Map gig index (1-based) to icon key
GIG_ICON_MAP = {
    1: "sales", 2: "support", 3: "content", 4: "document",
    5: "lead", 6: "email", 7: "seo", 8: "social",
    9: "data", 10: "web", 11: "crm", 12: "expense",
    13: "proposal", 14: "product", 15: "resume", 16: "ad",
    17: "market", 18: "business", 19: "press", 20: "tech",
}


# ── STATE MANAGEMENT ───────────────────────────────────────────

def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"gigs": {}, "profile_created": False, "last_run": None}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── IMAGE GENERATION ───────────────────────────────────────────

def _get_font(name: str, size: int):
    """Load a Windows system font."""
    from PIL import ImageFont
    fonts_dir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    font_map = {
        "bold": "segoeuib.ttf",
        "regular": "segoeui.ttf",
        "light": "segoeuil.ttf",
        "italic": "segoeuii.ttf",
    }
    font_file = font_map.get(name, "segoeui.ttf")
    try:
        return ImageFont.truetype(os.path.join(fonts_dir, font_file), size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int, draw) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _extract_short_title(full_title: str) -> str:
    """Extract the catchy part from 'I will ...' gig title."""
    title = full_title
    if title.lower().startswith("i will "):
        title = title[7:]
    # Capitalize first letter
    return title[0].upper() + title[1:] if title else title


def _extract_price_range(packages: dict) -> str:
    """Extract price range from packages dict."""
    prices = []
    for key in packages:
        match = re.search(r'\$(\d+)', key)
        if match:
            prices.append(int(match.group(1)))
    if prices:
        return f"${min(prices)} – ${max(prices)}"
    return ""


def _extract_bullet_points(description: str, max_items: int = 4) -> list[str]:
    """Extract key bullet points from gig description."""
    bullets = []
    for line in description.split("\n"):
        line = line.strip()
        if line.startswith("- **") or line.startswith("- "):
            clean = line.lstrip("- ").strip()
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)  # Remove markdown bold
            # Take just the bold part before --
            if " -- " in clean or " — " in clean:
                clean = re.split(r' [-—]+ ', clean)[0]
            if len(clean) > 50:
                clean = clean[:47] + "..."
            bullets.append(clean)
            if len(bullets) >= max_items:
                break
    return bullets


def generate_gig_image(gig_index: int, gig: dict, output_dir: Path = None) -> Path:
    """Generate a professional 1280x769 cover image for a single gig."""
    from PIL import Image, ImageDraw

    if output_dir is None:
        output_dir = IMAGE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (IMG_W, IMG_H), COLORS["bg_dark"])
    draw = ImageDraw.Draw(img)

    # --- Background gradient effect ---
    for y in range(IMG_H):
        r = int(COLORS["bg_dark"][0] + (COLORS["bg_card"][0] - COLORS["bg_dark"][0]) * (y / IMG_H))
        g = int(COLORS["bg_dark"][1] + (COLORS["bg_card"][1] - COLORS["bg_dark"][1]) * (y / IMG_H))
        b = int(COLORS["bg_dark"][2] + (COLORS["bg_card"][2] - COLORS["bg_dark"][2]) * (y / IMG_H))
        draw.line([(0, y), (IMG_W, y)], fill=(r, g, b))

    # --- Accent bar at top ---
    draw.rectangle([(0, 0), (IMG_W, 6)], fill=COLORS["accent"])

    # --- Decorative corner elements ---
    for i in range(3):
        offset = i * 8
        alpha = max(30, 100 - i * 30)
        color = (*COLORS["accent"][:3],)
        draw.rectangle([(40 + offset, 40 + offset), (80 + offset, 42 + offset)], fill=color)
        draw.rectangle([(40 + offset, 40 + offset), (42 + offset, 80 + offset)], fill=color)

    # --- Brand name ---
    font_brand = _get_font("bold", 22)
    draw.text((120, 45), "BIT RAGE LABOUR SYSTEMS", font=font_brand, fill=COLORS["accent"])

    # --- Gig number badge ---
    badge_x = IMG_W - 120
    draw.rounded_rectangle([(badge_x, 35), (badge_x + 80, 70)],
                           radius=8, fill=COLORS["accent"])
    font_badge = _get_font("bold", 20)
    draw.text((badge_x + 15, 40), f"GIG {gig_index:02d}", font=font_badge, fill=COLORS["bg_dark"])

    # --- Main title ---
    short_title = _extract_short_title(gig["title"])
    font_title = _get_font("bold", 42)
    title_lines = _wrap_text(short_title, font_title, IMG_W - 200, draw)
    y_pos = 120
    for line in title_lines[:3]:
        draw.text((80, y_pos), line, font=font_title, fill=COLORS["white"])
        y_pos += 52

    # --- Separator line ---
    y_pos += 15
    draw.line([(80, y_pos), (IMG_W - 80, y_pos)], fill=COLORS["dark_grey"], width=2)
    y_pos += 25

    # --- Bullet points ---
    bullets = _extract_bullet_points(gig.get("description", ""))
    font_bullet = _get_font("regular", 24)
    icon_key = GIG_ICON_MAP.get(gig_index, "sales")

    for bullet in bullets:
        # Bullet dot
        draw.ellipse([(90, y_pos + 8), (100, y_pos + 18)], fill=COLORS["accent"])
        draw.text((115, y_pos), bullet, font=font_bullet, fill=COLORS["light_grey"])
        y_pos += 38

    # --- Price section ---
    y_pos = max(y_pos + 20, IMG_H - 200)
    price_range = _extract_price_range(gig.get("packages", {}))
    if price_range:
        # Price background card
        draw.rounded_rectangle([(60, y_pos), (400, y_pos + 80)],
                               radius=12, fill=COLORS["bg_dark"])
        draw.rounded_rectangle([(62, y_pos + 2), (398, y_pos + 78)],
                               radius=11, outline=COLORS["accent"], width=2)
        font_price_label = _get_font("regular", 16)
        font_price = _get_font("bold", 36)
        draw.text((85, y_pos + 8), "STARTING FROM", font=font_price_label, fill=COLORS["grey"])
        draw.text((85, y_pos + 30), price_range, font=font_price, fill=COLORS["accent"])

    # --- Package tiers ---
    packages = gig.get("packages", {})
    if packages:
        pkg_x = 440
        font_pkg_name = _get_font("bold", 18)
        font_pkg_desc = _get_font("regular", 14)
        for pkg_name, pkg_desc in list(packages.items())[:3]:
            # Extract tier name
            tier = pkg_name.split("(")[0].strip()
            price_match = re.search(r'\$\d+', pkg_name)
            price = price_match.group(0) if price_match else ""

            draw.rounded_rectangle([(pkg_x, y_pos), (pkg_x + 240, y_pos + 80)],
                                   radius=8, fill=COLORS["dark_grey"])
            draw.text((pkg_x + 12, y_pos + 8), f"{tier}", font=font_pkg_name, fill=COLORS["white"])
            draw.text((pkg_x + 12, y_pos + 30), price, font=font_pkg_name, fill=COLORS["accent"])

            # Truncate description
            desc_short = pkg_desc[:40] + ("..." if len(pkg_desc) > 40 else "")
            draw.text((pkg_x + 12, y_pos + 52), desc_short, font=font_pkg_desc, fill=COLORS["grey"])

            pkg_x += 260

    # --- Footer bar ---
    draw.rectangle([(0, IMG_H - 45), (IMG_W, IMG_H)], fill=COLORS["bg_dark"])
    draw.line([(0, IMG_H - 45), (IMG_W, IMG_H - 45)], fill=COLORS["dark_grey"], width=1)
    font_footer = _get_font("regular", 16)
    draw.text((80, IMG_H - 35), "🤖 AI Agent Pipeline  •  <60s Delivery  •  Multi-LLM (GPT-4o + Claude + Gemini)",
              font=font_footer, fill=COLORS["grey"])

    # --- Category tag ---
    cat = gig.get("category", "AI Services")
    cat_short = cat.split(" > ")[-1] if " > " in cat else cat
    font_cat = _get_font("regular", 16)
    cat_bbox = draw.textbbox((0, 0), cat_short, font=font_cat)
    cat_w = cat_bbox[2] - cat_bbox[0] + 20
    cat_x = IMG_W - cat_w - 80
    draw.rounded_rectangle([(cat_x, IMG_H - 90), (cat_x + cat_w, IMG_H - 60)],
                           radius=6, fill=COLORS["dark_grey"])
    draw.text((cat_x + 10, IMG_H - 88), cat_short, font=font_cat, fill=COLORS["accent"])

    # --- Save ---
    safe_title = re.sub(r'[^a-z0-9]+', '_', gig["title"].lower())[:60]
    filename = f"gig_{gig_index:02d}_{safe_title}.png"
    filepath = output_dir / filename
    img.save(filepath, "PNG", optimize=True)
    return filepath


def generate_all_images() -> list[Path]:
    """Generate cover images for all 20 gigs."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    print(f"\n{'='*60}")
    print("  GENERATING FIVERR GIG COVER IMAGES")
    print(f"  Output: {IMAGE_DIR}")
    print(f"{'='*60}\n")

    for i, gig in enumerate(FIVERR_GIGS, 1):
        path = generate_gig_image(i, gig)
        print(f"  [{i:2d}/20] {path.name}")
        paths.append(path)

    print(f"\n  Done — {len(paths)} images generated ({IMG_W}x{IMG_H}px)")
    return paths


# ── PLAYWRIGHT BROWSER AUTOMATION ──────────────────────────────

COOKIE_FILE = BROWSER_DIR / "cookies.json"


def _launch_browser(headless: bool = False):
    """Launch Playwright browser with cookie-based session persistence."""
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
    # Restore saved cookies if available
    ctx_kwargs = {"viewport": {"width": 1400, "height": 900}}
    if COOKIE_FILE.exists():
        ctx_kwargs["storage_state"] = str(COOKIE_FILE)
    context = browser.new_context(**ctx_kwargs)
    return pw, browser, context


def _save_cookies(context):
    """Save browser cookies for session reuse."""
    try:
        context.storage_state(path=str(COOKIE_FILE))
    except Exception:
        pass


def login_flow():
    """Open Fiverr in browser for manual login. Saves session for reuse."""
    print("\n  Opening Fiverr — log in manually. Session will be saved.")
    print("  Close the browser when done.\n")
    pw, browser, context = _launch_browser()
    page = context.new_page()
    page.goto(f"{FIVERR_BASE}/login", wait_until="domcontentloaded")
    try:
        page.wait_for_url("**/seller_dashboard**", timeout=300000)  # 5 min
        print("  Login detected! Session saved.")
        _save_cookies(context)
    except Exception:
        print("  Browser closed or timeout. Saving cookies anyway...")
        _save_cookies(context)
    context.close()
    browser.close()
    pw.stop()


def _wait_and_fill(page, selector: str, value: str, timeout: int = 5000):
    """Try to fill a form field, return True on success."""
    try:
        el = page.wait_for_selector(selector, timeout=timeout)
        if el:
            el.fill(value)
            return True
    except Exception:
        return False
    return False


def _wait_and_click(page, selector: str, timeout: int = 5000):
    """Try to click an element, return True on success."""
    try:
        el = page.wait_for_selector(selector, timeout=timeout)
        if el:
            el.click()
            return True
    except Exception:
        return False
    return False


def deploy_gig_browser(page, gig_index: int, gig: dict, image_path: Path = None) -> dict:
    """Automate a single gig creation via Playwright.

    Returns a result dict with status and any issues.
    """
    result = {"gig": gig_index, "title": gig["title"], "steps": {}}

    # Screenshot dir
    ss_dir = PROJECT_ROOT / "output" / "fiverr_screenshots"
    ss_dir.mkdir(parents=True, exist_ok=True)

    # Navigate to gig creation
    page.goto(f"{FIVERR_BASE}/seller_dashboard/gigs/create", wait_until="domcontentloaded")
    time.sleep(3)
    page.screenshot(path=str(ss_dir / f"gig_{gig_index:02d}_step0_loaded.png"))

    # ----- STEP 1: Overview -----
    print(f"    Step 1: Overview...")

    # Title
    title_filled = _wait_and_fill(page, 'textarea[name="title"], input[name="title"], [data-testid="gig-title"]', gig["title"])
    if not title_filled:
        # Try contenteditable or other patterns
        title_filled = _wait_and_fill(page, '.gig-title-input textarea, .gig-title textarea', gig["title"])
    result["steps"]["title"] = title_filled

    # Tags — Fiverr uses a tag input where you type and press Enter
    tag_selector = 'input[placeholder*="tag"], input[placeholder*="Tag"], [data-testid="search-tags"] input'
    for tag in gig.get("tags", [])[:5]:  # Fiverr allows up to 5 tags
        if _wait_and_fill(page, tag_selector, tag, timeout=2000):
            page.keyboard.press("Enter")
            time.sleep(0.5)
    result["steps"]["tags"] = True

    # Try to click Continue/Save
    _click_continue(page)
    time.sleep(2)

    # ----- STEP 2: Scope & Pricing -----
    print(f"    Step 2: Pricing...")
    packages = gig.get("packages", {})
    pkg_list = list(packages.items())

    # Fill basic package description and price
    for idx, (pkg_name, pkg_desc) in enumerate(pkg_list[:3]):
        price_match = re.search(r'\$(\d+)', pkg_name)
        if price_match:
            price = price_match.group(1)
            # Try filling price inputs (varies by Fiverr's current UI)
            price_selectors = [
                f'input[name*="price"][data-index="{idx}"]',
                f'.package-price input:nth-of-type({idx + 1})',
                f'input[name*="price"]:nth-of-type({idx + 1})',
            ]
            for sel in price_selectors:
                if _wait_and_fill(page, sel, price, timeout=1500):
                    break

        # Package description
        desc_selectors = [
            f'textarea[name*="description"][data-index="{idx}"]',
            f'.package-description textarea:nth-of-type({idx + 1})',
        ]
        for sel in desc_selectors:
            if _wait_and_fill(page, sel, pkg_desc, timeout=1500):
                break

    result["steps"]["pricing"] = True
    _click_continue(page)
    time.sleep(2)

    # ----- STEP 3: Description -----
    print(f"    Step 3: Description...")
    desc = gig.get("description", "")
    # Clean markdown for Fiverr's editor
    clean_desc = re.sub(r'#{1,3}\s+', '', desc)  # Remove markdown headers
    clean_desc = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_desc)  # Remove bold markers

    desc_filled = _wait_and_fill(page, 'textarea[name="description"], .gig-description textarea, [data-testid="gig-description"]', clean_desc)
    if not desc_filled:
        # Try contenteditable div
        try:
            desc_el = page.query_selector('[contenteditable="true"]')
            if desc_el:
                desc_el.fill(clean_desc)
                desc_filled = True
        except Exception:
            pass
    result["steps"]["description"] = desc_filled

    # FAQ
    faq = gig.get("faq", [])
    for q, a in faq[:5]:
        # Try clicking "Add FAQ" button
        _wait_and_click(page, 'button:has-text("Add FAQ"), button:has-text("Add a FAQ")', timeout=2000)
        time.sleep(1)
        # Fill question and answer
        _wait_and_fill(page, 'input[name*="question"], .faq-question input', q, timeout=2000)
        _wait_and_fill(page, 'textarea[name*="answer"], .faq-answer textarea', a, timeout=2000)
        # Confirm
        _wait_and_click(page, 'button:has-text("Add"), button:has-text("Save")', timeout=2000)
        time.sleep(0.5)
    result["steps"]["faq"] = bool(faq)

    _click_continue(page)
    time.sleep(2)

    # ----- STEP 4: Requirements -----
    print(f"    Step 4: Requirements...")
    _click_continue(page)
    time.sleep(2)
    result["steps"]["requirements"] = True

    # ----- STEP 5: Gallery -----
    print(f"    Step 5: Gallery...")
    if image_path and image_path.exists():
        try:
            file_input = page.query_selector('input[type="file"]')
            if file_input:
                file_input.set_input_files(str(image_path))
                time.sleep(3)
                result["steps"]["image_upload"] = True
            else:
                result["steps"]["image_upload"] = False
        except Exception as e:
            result["steps"]["image_upload"] = f"Error: {e}"
    else:
        result["steps"]["image_upload"] = "No image"

    _click_continue(page)
    time.sleep(2)

    # ----- STEP 6: Publish (DON'T auto-publish — leave for user review) -----
    print(f"    Step 6: Ready for review (NOT auto-publishing)")
    page.screenshot(path=str(ss_dir / f"gig_{gig_index:02d}_step6_ready.png"))
    result["steps"]["publish"] = "READY_FOR_REVIEW"
    result["status"] = "draft"

    return result


def _click_continue(page):
    """Try various 'Continue' / 'Save & Continue' button selectors."""
    selectors = [
        'button:has-text("Save & Continue")',
        'button:has-text("Save and Continue")',
        'button:has-text("Continue")',
        'button:has-text("Next")',
        'button[type="submit"]',
        '.btn-continue',
    ]
    for sel in selectors:
        if _wait_and_click(page, sel, timeout=2000):
            return True
    return False


def deploy_all_browser(gig_indices: list[int] = None):
    """Deploy gigs via browser automation.

    Args:
        gig_indices: 1-based gig numbers to deploy. Defaults to top 4.
    """
    if gig_indices is None:
        gig_indices = DEFAULT_TOP_4

    # Validate indices
    gig_indices = [i for i in gig_indices if 1 <= i <= len(FIVERR_GIGS)]
    if not gig_indices:
        print("  No valid gig indices provided.")
        return

    print(f"\n{'='*60}")
    print(f"  FIVERR GIG DEPLOYMENT — {len(gig_indices)} gigs")
    print(f"  Gigs: {gig_indices}")
    print(f"{'='*60}")

    # Ensure images exist
    for idx in gig_indices:
        img_path = _find_gig_image(idx)
        if not img_path:
            print(f"\n  Generating image for gig {idx}...")
            generate_gig_image(idx, FIVERR_GIGS[idx - 1])

    print("\n  Launching browser...")
    pw, browser, context = _launch_browser(headless=False)
    page = context.new_page()

    # Check if logged in
    page.goto(f"{FIVERR_BASE}/seller_dashboard", wait_until="domcontentloaded")
    time.sleep(3)

    if "login" in page.url.lower():
        print("\n  ⚠ Not logged in! Please log in manually...")
        print("  Waiting up to 5 minutes...")
        try:
            page.wait_for_url("**/seller_dashboard**", timeout=300000)
            _save_cookies(context)
        except Exception:
            print("  Login timeout. Aborting.")
            context.close()
            browser.close()
            pw.stop()
            return

    print("  Logged in!\n")
    _save_cookies(context)
    state = _load_state()
    results = []

    for idx in gig_indices:
        gig = FIVERR_GIGS[idx - 1]
        print(f"\n  ── GIG {idx}: {gig['title'][:60]}...")
        img_path = _find_gig_image(idx)
        result = deploy_gig_browser(page, idx, gig, img_path)
        results.append(result)

        state["gigs"][str(idx)] = {
            "status": result["status"],
            "deployed_at": datetime.now(timezone.utc).isoformat(),
            "steps": result["steps"],
        }
        _save_state(state)
        print(f"    Status: {result['status']}")
        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"  DEPLOYMENT COMPLETE")
    for r in results:
        status_icon = "\u2713" if r["status"] == "draft" else "\u2717"
        print(f"  {status_icon} Gig {r['gig']}: {r['status']}")
    print(f"{'='*60}\n")

    # Take final screenshot
    screenshots_dir = PROJECT_ROOT / "output" / "fiverr_screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(screenshots_dir / "deploy_final.png"))
        print(f"  Screenshot saved: {screenshots_dir / 'deploy_final.png'}")
    except Exception:
        pass

    # Keep browser open for 60s for user review, then close
    print("  Browser stays open 60s for review...")
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    _save_cookies(context)
    context.close()
    browser.close()
    pw.stop()


# ── PUBLISH DRAFT GIGS ────────────────────────────────────────

def publish_drafts(gig_indices: list[int] = None):
    """Navigate to seller dashboard and publish draft gigs.

    Fiverr's "My Gigs" page lists drafts with a "Publish" or "Activate" button.
    This function clicks through each draft to publish it.

    Args:
        gig_indices: 1-based gig numbers to publish. If None, publishes all drafts.
    """
    state = _load_state()
    draft_gigs = {k: v for k, v in state.get("gigs", {}).items()
                  if v.get("status") == "draft"}

    if gig_indices:
        draft_gigs = {k: v for k, v in draft_gigs.items() if int(k) in gig_indices}

    if not draft_gigs:
        print("  No draft gigs to publish.")
        return

    print(f"\n{'='*60}")
    print(f"  FIVERR GIG PUBLISHING — {len(draft_gigs)} drafts")
    print(f"  Gigs: {list(draft_gigs.keys())}")
    print(f"{'='*60}")

    pw, browser, context = _launch_browser(headless=False)
    page = context.new_page()

    # Navigate to seller dashboard
    page.goto(f"{FIVERR_BASE}/seller_dashboard", wait_until="domcontentloaded")
    time.sleep(3)

    if "login" in page.url.lower():
        print("\n  Not logged in — please log in manually...")
        print("  Waiting up to 5 minutes...")
        try:
            page.wait_for_url("**/seller_dashboard**", timeout=300000)
            _save_cookies(context)
        except Exception:
            print("  Login timeout. Aborting.")
            context.close()
            browser.close()
            pw.stop()
            return

    _save_cookies(context)
    print("  Logged in!\n")

    ss_dir = PROJECT_ROOT / "output" / "fiverr_screenshots"
    ss_dir.mkdir(parents=True, exist_ok=True)

    # Go to My Gigs page (lists all gigs including drafts)
    page.goto(f"{FIVERR_BASE}/seller_dashboard/gigs", wait_until="domcontentloaded")
    time.sleep(3)
    page.screenshot(path=str(ss_dir / "publish_gigs_page.png"))

    published = []
    failed = []

    for gig_key in draft_gigs:
        gig_idx = int(gig_key)
        gig_title = FIVERR_GIGS[gig_idx - 1]["title"][:50]
        print(f"\n  Publishing gig {gig_idx}: {gig_title}...")

        # Strategy: Look for draft gig rows and click their action button
        # Fiverr's gig management page shows gigs in a table/list
        # Each gig has Edit/Publish/Delete actions

        # Try to find and click the publish/activate button for this gig
        publish_success = False

        # Approach 1: Find gig by partial title match in the gig list
        try:
            # Look for any row containing part of the gig title
            short_title = gig_title[:30]
            gig_row = page.query_selector(f'tr:has-text("{short_title}"), .gig-row:has-text("{short_title}"), [class*="gig"]:has-text("{short_title}")')

            if gig_row:
                # Look for publish/activate button within this row
                for btn_text in ["Publish", "Activate", "Go Live"]:
                    btn = gig_row.query_selector(f'button:has-text("{btn_text}"), a:has-text("{btn_text}")')
                    if btn:
                        btn.click()
                        time.sleep(3)
                        publish_success = True
                        break

                # If no direct button, try the actions menu (three-dot menu)
                if not publish_success:
                    actions_btn = gig_row.query_selector('[class*="action"], [class*="menu"], button[class*="dots"], .kebab-menu')
                    if actions_btn:
                        actions_btn.click()
                        time.sleep(1)
                        for btn_text in ["Publish", "Activate", "Go Live"]:
                            if _wait_and_click(page, f'[role="menuitem"]:has-text("{btn_text}"), li:has-text("{btn_text}"), a:has-text("{btn_text}")', timeout=2000):
                                time.sleep(3)
                                publish_success = True
                                break
        except Exception as e:
            print(f"    Row search failed: {e}")

        # Approach 2: Click into the gig edit page and publish from there
        if not publish_success:
            try:
                # Try clicking the gig title link to go to edit
                link = page.query_selector(f'a:has-text("{gig_title[:25]}")')
                if link:
                    link.click()
                    time.sleep(3)

                    # On the gig edit/review page, find the publish button
                    for sel in [
                        'button:has-text("Publish")',
                        'button:has-text("Publish Gig")',
                        'button:has-text("Activate")',
                        'button:has-text("Go Live")',
                        'button[class*="publish"]',
                        '.publish-gig button',
                    ]:
                        if _wait_and_click(page, sel, timeout=2000):
                            time.sleep(3)
                            publish_success = True
                            break

                    # Go back to gigs list for next one
                    page.goto(f"{FIVERR_BASE}/seller_dashboard/gigs", wait_until="domcontentloaded")
                    time.sleep(3)
            except Exception as e:
                print(f"    Edit-page approach failed: {e}")
                page.goto(f"{FIVERR_BASE}/seller_dashboard/gigs", wait_until="domcontentloaded")
                time.sleep(3)

        # Approach 3: Use the draft filter + sequential publish
        if not publish_success:
            try:
                # Filter by drafts if available
                _wait_and_click(page, 'button:has-text("Drafts"), a:has-text("Drafts"), [data-tab="drafts"]', timeout=2000)
                time.sleep(2)

                # Click the first available publish button
                for sel in [
                    'button:has-text("Publish")',
                    'button:has-text("Activate")',
                    'a:has-text("Publish")',
                ]:
                    if _wait_and_click(page, sel, timeout=2000):
                        time.sleep(3)
                        publish_success = True
                        break
            except Exception as e:
                print(f"    Draft-filter approach failed: {e}")

        # Handle confirmation dialogs
        if publish_success:
            # Some Fiverr flows show a confirmation modal
            for confirm_sel in [
                'button:has-text("Confirm")',
                'button:has-text("Yes")',
                'button:has-text("OK")',
                'button:has-text("Got it")',
            ]:
                _wait_and_click(page, confirm_sel, timeout=2000)

            time.sleep(2)
            page.screenshot(path=str(ss_dir / f"publish_gig_{gig_idx:02d}_done.png"))
            state["gigs"][gig_key]["status"] = "published"
            state["gigs"][gig_key]["published_at"] = datetime.now(timezone.utc).isoformat()
            _save_state(state)
            published.append(gig_idx)
            print(f"    Published!")
        else:
            failed.append(gig_idx)
            print(f"    Could not find publish button — may need manual publish")
            page.screenshot(path=str(ss_dir / f"publish_gig_{gig_idx:02d}_failed.png"))

    # Summary
    print(f"\n{'='*60}")
    print(f"  PUBLISH COMPLETE")
    for g in published:
        print(f"  + Gig {g}: published")
    for g in failed:
        print(f"  x Gig {g}: needs manual publish")
    print(f"{'='*60}\n")

    # Keep browser open for review
    print("  Browser stays open 60s for review...")
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass

    _save_cookies(context)
    context.close()
    browser.close()
    pw.stop()


def _find_gig_image(gig_index: int) -> Path | None:
    """Find the generated image for a gig index."""
    if not IMAGE_DIR.exists():
        return None
    pattern = f"gig_{gig_index:02d}_*"
    matches = list(IMAGE_DIR.glob(pattern))
    return matches[0] if matches else None


# ── CLIPBOARD-GUIDED MODE ──────────────────────────────────────

def guided_deploy(gig_indices: list[int] = None):
    """Step-by-step guided gig creation with clipboard copy.

    Opens the browser and walks through each field,
    copying the right content to clipboard for paste.
    """
    import pyperclip
    import webbrowser

    if gig_indices is None:
        gig_indices = DEFAULT_TOP_4

    gig_indices = [i for i in gig_indices if 1 <= i <= len(FIVERR_GIGS)]
    if not gig_indices:
        print("  No valid gig indices.")
        return

    print(f"\n{'='*60}")
    print(f"  GUIDED FIVERR GIG CREATION — {len(gig_indices)} gigs")
    print(f"  Mode: Clipboard copy + manual paste")
    print(f"{'='*60}")

    state = _load_state()

    for idx in gig_indices:
        gig = FIVERR_GIGS[idx - 1]
        print(f"\n{'─'*60}")
        print(f"  GIG {idx}: {gig['title'][:70]}")
        print(f"{'─'*60}")

        # Open gig creation page
        input(f"\n  Press Enter to open Fiverr gig creation page...")
        webbrowser.open(f"{FIVERR_BASE}/seller_dashboard/gigs/create")
        time.sleep(2)

        # STEP 1: Title
        print(f"\n  ── STEP 1: TITLE ──")
        pyperclip.copy(gig["title"])
        print(f"  📋 Copied to clipboard: {gig['title'][:80]}")
        print(f"  → Paste into the 'Gig title' field")
        input(f"  Press Enter when done...")

        # Category
        print(f"\n  ── STEP 1b: CATEGORY ──")
        cat_parts = gig.get("category", "").split(" > ")
        print(f"  Select: {' → '.join(cat_parts)}")
        input(f"  Press Enter when done...")

        # Tags
        print(f"\n  ── STEP 1c: TAGS ──")
        tags = gig.get("tags", [])[:5]
        for i, tag in enumerate(tags, 1):
            pyperclip.copy(tag)
            print(f"  📋 Tag {i}/5 copied: {tag}")
            print(f"  → Paste and press Enter")
            if i < len(tags):
                input(f"  Press Enter for next tag...")
        input(f"  Press Enter and click 'Save & Continue'...")

        # STEP 2: Pricing
        print(f"\n  ── STEP 2: PRICING ──")
        packages = gig.get("packages", {})
        for pkg_name, pkg_desc in packages.items():
            price_match = re.search(r'\$(\d+)', pkg_name)
            price = price_match.group(1) if price_match else "?"
            tier = pkg_name.split("(")[0].strip()
            print(f"\n  {tier} — ${price}")
            pyperclip.copy(pkg_desc)
            print(f"  📋 Description copied: {pkg_desc[:60]}...")
            print(f"  → Set price to ${price}")
            print(f"  → Paste description")
            input(f"  Press Enter for next package...")
        input(f"  Press Enter and click 'Save & Continue'...")

        # STEP 3: Description
        print(f"\n  ── STEP 3: DESCRIPTION ──")
        desc = gig.get("description", "")
        # Clean for Fiverr (no markdown)
        clean_desc = re.sub(r'#{1,3}\s+', '\n', desc)
        clean_desc = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_desc)
        pyperclip.copy(clean_desc)
        print(f"  📋 Full description copied ({len(clean_desc)} chars)")
        print(f"  → Paste into the Description field")
        input(f"  Press Enter when done...")

        # FAQ
        faq = gig.get("faq", [])
        if faq:
            print(f"\n  ── STEP 3b: FAQ ──")
            for i, (q, a) in enumerate(faq, 1):
                print(f"\n  FAQ {i}:")
                pyperclip.copy(q)
                print(f"  📋 Question copied: {q}")
                input(f"  Paste question, then press Enter...")
                pyperclip.copy(a)
                print(f"  📋 Answer copied: {a[:60]}...")
                input(f"  Paste answer, click 'Add', then press Enter...")
        input(f"  Press Enter and click 'Save & Continue'...")

        # STEP 4: Requirements
        print(f"\n  ── STEP 4: REQUIREMENTS ──")
        print(f"  → You can skip this or add custom requirements")
        input(f"  Press Enter and click 'Save & Continue'...")

        # STEP 5: Gallery
        print(f"\n  ── STEP 5: GALLERY ──")
        img_path = _find_gig_image(idx)
        if img_path:
            print(f"  Image ready: {img_path}")
            pyperclip.copy(str(img_path))
            print(f"  📋 Image path copied to clipboard")
            print(f"  → Click 'Upload' and navigate to the image file")
        else:
            print(f"  ⚠ No image generated. Run: --images first")
        input(f"  Press Enter and click 'Save & Continue'...")

        # STEP 6: Publish
        print(f"\n  ── STEP 6: PUBLISH ──")
        print(f"  → Review everything looks correct")
        print(f"  → Click 'Publish Gig'")
        result = input(f"  Did you publish? (y/n): ").strip().lower()

        state["gigs"][str(idx)] = {
            "status": "published" if result == "y" else "draft",
            "deployed_at": datetime.now(timezone.utc).isoformat(),
            "method": "guided",
        }
        _save_state(state)

        if result == "y":
            print(f"  ✓ Gig {idx} published!")
        else:
            print(f"  → Saved as draft. You can publish later.")

    print(f"\n{'='*60}")
    print(f"  GUIDED DEPLOYMENT COMPLETE")
    print(f"{'='*60}\n")


# ── STATUS DASHBOARD ───────────────────────────────────────────

def show_status():
    """Show deployment status of all gigs."""
    state = _load_state()

    print(f"\n{'='*60}")
    print(f"  FIVERR DEPLOYMENT STATUS")
    if state.get("last_run"):
        print(f"  Last run: {state['last_run']}")
    print(f"{'='*60}\n")

    print(f"  {'#':>3}  {'Status':<12}  {'Image':>5}  Title")
    print(f"  {'─'*3}  {'─'*12}  {'─'*5}  {'─'*40}")

    deployed = 0
    for i, gig in enumerate(FIVERR_GIGS, 1):
        gig_state = state.get("gigs", {}).get(str(i), {})
        status = gig_state.get("status", "not_started")
        has_image = "✓" if _find_gig_image(i) else "✗"
        short = gig["title"][:50]

        icon = {"published": "🟢", "draft": "🟡", "not_started": "⬜"}.get(status, "⬜")
        print(f"  {i:3d}  {icon} {status:<10}  {has_image:>5}  {short}")
        if status == "published":
            deployed += 1

    print(f"\n  Deployed: {deployed}/20  |  New seller limit: 4 gigs")
    print(f"  Images: {sum(1 for i in range(1, 21) if _find_gig_image(i))}/20")
    print()

    # Recommendations
    if deployed == 0:
        print(f"  Recommended first 4 gigs: {DEFAULT_TOP_4}")
        print(f"  → Content Repurpose, SEO Blog, Social Media, Ad Copy")
        print(f"  → These are highest-demand Fiverr categories")
    elif deployed < 4:
        remaining = [i for i in DEFAULT_TOP_4 if state.get("gigs", {}).get(str(i), {}).get("status") != "published"]
        if remaining:
            print(f"  Remaining to hit 4-gig limit: {remaining}")


# ── BULK DATA EXPORT ───────────────────────────────────────────

def export_all_gig_data():
    """Export all 20 gigs as individual ready-to-paste files."""
    export_dir = PROJECT_ROOT / "output" / "fiverr_ready"
    export_dir.mkdir(parents=True, exist_ok=True)

    for i, gig in enumerate(FIVERR_GIGS, 1):
        # Clean description (no markdown)
        desc = gig.get("description", "")
        clean_desc = re.sub(r'#{1,3}\s+', '\n', desc)
        clean_desc = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_desc)

        content = []
        content.append(f"{'='*60}")
        content.append(f"GIG {i}")
        content.append(f"{'='*60}")
        content.append(f"")
        content.append(f"TITLE:")
        content.append(gig["title"])
        content.append(f"")
        content.append(f"CATEGORY:")
        content.append(gig.get("category", "Programming & Tech > AI Services > AI Agents"))
        content.append(f"")
        content.append(f"TAGS (copy one at a time):")
        for tag in gig.get("tags", [])[:5]:
            content.append(f"  {tag}")
        content.append(f"")
        content.append(f"DESCRIPTION:")
        content.append(clean_desc.strip())
        content.append(f"")
        content.append(f"PACKAGES:")
        for pkg_name, pkg_desc in gig.get("packages", {}).items():
            price_match = re.search(r'\$(\d+)', pkg_name)
            price = price_match.group(1) if price_match else "?"
            tier = pkg_name.split("(")[0].strip()
            content.append(f"")
            content.append(f"  {tier} — ${price}")
            content.append(f"  {pkg_desc}")
        content.append(f"")
        content.append(f"FAQ:")
        for q, a in gig.get("faq", []):
            content.append(f"")
            content.append(f"  Q: {q}")
            content.append(f"  A: {a}")

        # Image reference
        img_path = _find_gig_image(i)
        if img_path:
            content.append(f"")
            content.append(f"IMAGE: {img_path}")

        filepath = export_dir / f"gig_{i:02d}.txt"
        filepath.write_text("\n".join(content), encoding="utf-8")

    print(f"\n  Exported {len(FIVERR_GIGS)} gig files to {export_dir}")

    # Also export a master JSON for programmatic use
    master = []
    for i, gig in enumerate(FIVERR_GIGS, 1):
        entry = dict(gig)
        entry["gig_number"] = i
        img_path = _find_gig_image(i)
        entry["image_path"] = str(img_path) if img_path else None
        master.append(entry)

    master_path = export_dir / "all_gigs.json"
    master_path.write_text(json.dumps(master, indent=2, default=str), encoding="utf-8")
    print(f"  Master JSON: {master_path}")


# ── CLI ────────────────────────────────────────────────────────

def _parse_gig_list(s: str) -> list[int]:
    """Parse comma-separated gig numbers."""
    if not s:
        return DEFAULT_TOP_4
    try:
        return [int(x.strip()) for x in s.split(",") if x.strip().isdigit()]
    except ValueError:
        return DEFAULT_TOP_4


def main():
    args = sys.argv[1:]

    if not args or "--help" in args:
        print(__doc__)
        return

    if "--images" in args:
        generate_all_images()
        return

    if "--login" in args:
        login_flow()
        return

    if "--status" in args:
        show_status()
        return

    if "--export" in args:
        export_all_gig_data()
        return

    # Parse --gigs flag
    gig_list = None
    if "--gigs" in args:
        idx = args.index("--gigs")
        if idx + 1 < len(args):
            gig_list = _parse_gig_list(args[idx + 1])

    if "--deploy" in args:
        deploy_all_browser(gig_list)
        return

    if "--publish" in args:
        publish_drafts(gig_list)
        return

    if "--guided" in args:
        guided_deploy(gig_list)
        return

    print(__doc__)


if __name__ == "__main__":
    main()
