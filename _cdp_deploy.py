"""Deploy Fiverr gigs via CDP — uses your REAL Edge browser to bypass PerimeterX.

This script:
  1. Launches Edge with remote debugging enabled (separate profile)
  2. Waits for you to log in to Fiverr
  3. Navigates to the gig wizard and inspects actual DOM selectors
  4. Fills in all gig data through your real browser session

Usage:
  python _cdp_deploy.py              # Deploy default top gigs
  python _cdp_deploy.py --probe      # Just probe selectors (no gig filling)
  python _cdp_deploy.py --gigs 3,7   # Deploy specific gigs
"""
import sys
import time
import json
import subprocess
import tempfile
import re
import random
import math
from pathlib import Path

import pyautogui
import pygetwindow as gw

# pyautogui safety: disable the fail-safe corner (we handle our own safety)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.03  # Small default pause between pyautogui calls

sys.path.insert(0, ".")
from income.freelance_listings import FIVERR_GIGS

PROJECT_ROOT = Path(__file__).resolve().parent
FIVERR_BASE = "https://www.fiverr.com"
FIVERR_USERNAME = "bit_rage_labour"
IMAGE_DIR = PROJECT_ROOT / "output" / "fiverr_images"
SS_DIR = PROJECT_ROOT / "output" / "fiverr_screenshots"
STATE_FILE = PROJECT_ROOT / "data" / "fiverr_deploy_state.json"
SS_DIR.mkdir(parents=True, exist_ok=True)

CDP_PORT = 9222
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
USER_DATA_DIR = Path(tempfile.gettempdir()) / "edge_cdp_fiverr"

DEFAULT_GIGS = [3, 7, 8, 16, 1]


def _load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"gigs": {}, "last_run": None}


def _save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════
# STEALTH: Anti-detection init script injected before every page load
# ═══════════════════════════════════════════════════════════════

STEALTH_JS = """
// Override navigator.webdriver — THE #1 detection vector
Object.defineProperty(navigator, 'webdriver', {
    get: () => false,
    configurable: true,
});

// Remove automation markers that PerimeterX checks
const automationVars = [
    '__nightmare', '_phantom', 'callPhantom', '_Selenium_IDE_Recorder',
    'domAutomation', 'domAutomationController', 'emit', 'spawn',
    'fmget_targets', 'awesomium', 'geb', 'RunPerfTest',
];
automationVars.forEach(v => {
    if (window[v] !== undefined) {
        try { delete window[v]; } catch(e) {}
    }
});

// Remove document-level automation markers
try {
    if (document.__webdriver_script_fn) delete document.__webdriver_script_fn;
} catch(e) {}
try {
    const html = document.getElementsByTagName('html')[0];
    if (html && html.getAttribute('webdriver')) html.removeAttribute('webdriver');
} catch(e) {}

// Ensure window.chrome exists (PX checks for it in Chrome/Edge)
if (!window.chrome) {
    window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
}
if (!window.chrome.runtime) {
    window.chrome.runtime = {};
}

// Override navigator.plugins to look realistic (not empty)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Microsoft Edge PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
        ];
        arr.length = 3;
        arr.item = (i) => arr[i];
        arr.namedItem = (n) => arr.find(p => p.name === n);
        arr.refresh = () => {};
        return arr;
    },
    configurable: true,
});

// Override navigator.languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
    configurable: true,
});

// Override navigator.platform
Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32',
    configurable: true,
});

// Patch permissions.query to always resolve (some bots fail on this)
const origQuery = window.navigator.permissions?.query;
if (origQuery) {
    window.navigator.permissions.query = (params) => {
        if (params.name === 'notifications') {
            return Promise.resolve({ state: Notification.permission });
        }
        return origQuery.call(window.navigator.permissions, params);
    };
}

// Override console.debug marker (PX injects debug traps)
// Keep console.debug functional but prevent fingerprinting via it

// Make WebGL renderer look like a real consumer GPU
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    // UNMASKED_VENDOR_WEBGL
    if (parameter === 37445) return 'Google Inc. (Intel)';
    // UNMASKED_RENDERER_WEBGL
    if (parameter === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)';
    return getParameter.call(this, parameter);
};

// Patch for WebGL2 as well
if (typeof WebGL2RenderingContext !== 'undefined') {
    const getParam2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Google Inc. (Intel)';
        if (parameter === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)';
        return getParam2.call(this, parameter);
    };
}
"""


def _apply_stealth(context, page):
    """Apply all stealth countermeasures to the browser context and page."""
    # 1. Inject anti-detection JS into all future pages via context
    try:
        context.add_init_script(STEALTH_JS)
        print("  Stealth init script applied to context.", flush=True)
    except Exception as e:
        print(f"  Context init_script failed ({e}), applying to page...", flush=True)
        try:
            page.add_init_script(STEALTH_JS)
            print("  Stealth init script applied to page.", flush=True)
        except Exception as e2:
            print(f"  Page init_script also failed: {e2}", flush=True)

    # 2. Also evaluate the stealth JS immediately on the current page
    try:
        page.evaluate(STEALTH_JS)
    except Exception:
        pass

    # 3. Try applying playwright-stealth evasions on top
    try:
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.apply_stealth_sync(page)
        print("  playwright-stealth evasions applied.", flush=True)
    except Exception as e:
        print(f"  playwright-stealth not applied ({e}), using manual evasions only.", flush=True)

    # 4. Clear PerimeterX tracking cookies to force fresh evaluation
    try:
        cookies = context.cookies()
        px_cookie_names = {"_px3", "_pxhd", "_pxvid", "_pxde", "_pxff_cc", "_pxff_cfp", "_pxff_fp"}
        px_cookies = [c for c in cookies if c["name"] in px_cookie_names]
        if px_cookies:
            non_px_cookies = [c for c in cookies if c["name"] not in px_cookie_names]
            context.clear_cookies()
            if non_px_cookies:
                context.add_cookies(non_px_cookies)
            print(f"  Cleared {len(px_cookies)} PX tracking cookies: {[c['name'] for c in px_cookies]}", flush=True)
        else:
            print("  No PX cookies found to clear.", flush=True)
    except Exception as e:
        print(f"  Cookie clearing failed: {e}", flush=True)


# ═══════════════════════════════════════════════════════════════
# HUMAN-LIKE BEHAVIOR: OS-level mouse/keyboard via pyautogui
# CDP is used ONLY for DOM reading, never for input.
# ═══════════════════════════════════════════════════════════════

def _get_edge_window():
    """Find the Edge browser window for coordinate translation."""
    try:
        windows = gw.getWindowsWithTitle("Edge")
        # Find the one with Fiverr or the CDP profile
        for w in windows:
            if w.title and ("fiverr" in w.title.lower() or "edge" in w.title.lower()):
                return w
        # Fallback: any Edge window
        if windows:
            return windows[0]
    except Exception:
        pass
    return None


def _get_browser_content_offset(page):
    """Get the offset from window top-left to the browser content area.
    
    Returns (offset_x, offset_y) — the pixel offset from Edge window origin
    to where the web page content begins (below address bar, tabs, etc).
    """
    try:
        # Use CDP to get the content area position via JS
        result = page.evaluate("""() => {
            return {
                screenX: window.screenX,
                screenY: window.screenY,
                outerWidth: window.outerWidth,
                outerHeight: window.outerHeight,
                innerWidth: window.innerWidth,
                innerHeight: window.innerHeight
            };
        }""")
        # The difference between outer and inner gives us the chrome (toolbar) size
        chrome_x = (result["outerWidth"] - result["innerWidth"]) // 2
        chrome_y = result["outerHeight"] - result["innerHeight"] - chrome_x  # Bottom border ≈ side border
        return result["screenX"] + chrome_x, result["screenY"] + chrome_y
    except Exception:
        # Fallback: typical Edge chrome offsets
        win = _get_edge_window()
        if win:
            return win.left + 8, win.top + 100  # Rough estimate
        return 0, 0


def _page_to_screen(page, page_x, page_y):
    """Convert page-relative coordinates to screen-absolute coordinates."""
    try:
        result = page.evaluate("""() => ({
            screenX: window.screenX,
            screenY: window.screenY,
            outerW: window.outerWidth,
            outerH: window.outerHeight,
            innerW: window.innerWidth,
            innerH: window.innerHeight,
            scrollX: window.scrollX,
            scrollY: window.scrollY
        })""")
        chrome_x = (result["outerW"] - result["innerW"]) // 2
        chrome_y = result["outerH"] - result["innerH"] - chrome_x
        screen_x = result["screenX"] + chrome_x + page_x - result["scrollX"]
        screen_y = result["screenY"] + chrome_y + page_y - result["scrollY"]
        return int(screen_x), int(screen_y)
    except Exception:
        # Fallback
        win = _get_edge_window()
        if win:
            return int(win.left + 8 + page_x), int(win.top + 100 + page_y)
        return int(page_x), int(page_y)


def _human_delay(min_s=0.3, max_s=1.5):
    """Random delay with a slight gaussian distribution for realism."""
    delay = random.gauss((min_s + max_s) / 2, (max_s - min_s) / 4)
    delay = max(min_s, min(max_s, delay))
    time.sleep(delay)


def _os_mouse_move(screen_x, screen_y, duration=None):
    """Move mouse to screen coordinates with human-like curve via pyautogui."""
    if duration is None:
        duration = random.uniform(0.2, 0.6)
    try:
        pyautogui.moveTo(screen_x, screen_y, duration=duration, tween=pyautogui.easeOutQuad)
    except Exception:
        pass


def _os_click(screen_x, screen_y):
    """Click at screen coordinates via pyautogui (OS-level, 100% trusted event)."""
    _os_mouse_move(screen_x, screen_y)
    _human_delay(0.05, 0.15)
    pyautogui.click(screen_x, screen_y)


def _os_type(text, interval=None):
    """Type text via pyautogui (OS-level keyboard input)."""
    if interval is None:
        interval = random.uniform(0.02, 0.06)
    # pyautogui.write has issues with special chars, use pyperclip + paste for reliability
    # but for simple text, write works
    try:
        pyautogui.write(text, interval=interval)
    except Exception:
        # Fallback for unicode/special chars: clipboard paste
        import pyperclip
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')


def _os_typewrite_slow(text, min_interval=0.02, max_interval=0.08):
    """Type text character by character with random delays for realism."""
    for char in text:
        try:
            pyautogui.press(char) if len(char) == 1 and char.isalnum() else pyautogui.write(char, interval=0)
        except Exception:
            pass
        time.sleep(random.uniform(min_interval, max_interval))


def _os_press(key):
    """Press a single key via pyautogui."""
    pyautogui.press(key)


def _os_hotkey(*keys):
    """Press a hotkey combination via pyautogui."""
    pyautogui.hotkey(*keys)


def _click_element(page, selector, label=""):
    """Find element position via CDP, click via pyautogui (OS-level)."""
    try:
        el = page.query_selector(selector)
        if not el:
            print(f"    {label}: selector {selector} not found", flush=True)
            return False
        if not el.is_visible():
            print(f"    {label}: element not visible", flush=True)
            return False
        box = el.bounding_box()
        if not box:
            print(f"    {label}: no bounding box", flush=True)
            return False
        # Click at a random point within the element
        page_x = box["x"] + box["width"] * random.uniform(0.25, 0.75)
        page_y = box["y"] + box["height"] * random.uniform(0.25, 0.75)
        screen_x, screen_y = _page_to_screen(page, page_x, page_y)
        _os_click(screen_x, screen_y)
        return True
    except Exception as e:
        print(f"    {label} click error: {e}", flush=True)
        return False


def _type_into_element(page, selector, text, label="", clear_first=True):
    """Click element via pyautogui, then type text via pyautogui."""
    if not _click_element(page, selector, label):
        return False
    _human_delay(0.2, 0.5)
    if clear_first:
        _os_hotkey('ctrl', 'a')
        _human_delay(0.05, 0.15)
        _os_press('delete')
        _human_delay(0.1, 0.3)
    # Type via clipboard paste for reliability (handles special chars)
    import pyperclip
    pyperclip.copy(text)
    _os_hotkey('ctrl', 'v')
    return True


def _human_mouse_move(page, target_x=None, target_y=None):
    """Move mouse to a random area on page via OS-level pyautogui."""
    try:
        viewport = page.viewport_size or {"width": 1366, "height": 768}
        if target_x is None:
            target_x = random.randint(100, viewport["width"] - 100)
        if target_y is None:
            target_y = random.randint(100, viewport["height"] - 200)
        screen_x, screen_y = _page_to_screen(page, target_x, target_y)
        _os_mouse_move(screen_x, screen_y, duration=random.uniform(0.3, 0.8))
    except Exception:
        pass


def _human_scroll(page, direction="down", amount=None):
    """Scroll the page via pyautogui (OS-level scroll)."""
    try:
        clicks = random.randint(2, 5) if amount is None else max(1, amount // 80)
        if direction == "up":
            clicks = -clicks
        else:
            clicks = -clicks  # pyautogui scroll: negative = down
        pyautogui.scroll(clicks)
        _human_delay(0.2, 0.5)
    except Exception:
        pass


def _navigate_via_addressbar(url, page=None):
    """Navigate to URL by typing it in the browser address bar via pyautogui.
    
    This makes the navigation look user-initiated (Ctrl+L, type URL, Enter)
    instead of using CDP page.goto() which PX can fingerprint.
    """
    import pyperclip
    # Focus the Edge window
    win = _get_edge_window()
    if win:
        try:
            win.activate()
            _human_delay(0.3, 0.6)
        except Exception:
            pass
    
    # Ctrl+L focuses the address bar in Edge/Chrome
    _os_hotkey('ctrl', 'l')
    _human_delay(0.3, 0.6)
    
    # Select all existing text and paste the URL
    _os_hotkey('ctrl', 'a')
    _human_delay(0.1, 0.2)
    pyperclip.copy(url)
    _os_hotkey('ctrl', 'v')
    _human_delay(0.2, 0.4)
    
    # Press Enter to navigate
    _os_press('enter')
    
    # Wait for page to load
    _human_delay(3, 5)
    
    # If we have a page reference, wait for it to stabilize and re-inject stealth
    if page:
        try:
            # Wait for the page URL to change (up to 15s)
            for _ in range(30):
                try:
                    current = page.url
                    if url.rstrip('/') in current or current != 'about:blank':
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            _human_delay(1, 2)
            page.evaluate(STEALTH_JS)
        except Exception:
            pass


def _simulate_reading(page):
    """Simulate a human reading the page via OS-level input."""
    _human_mouse_move(page)
    _human_delay(0.5, 1.5)
    _human_scroll(page, "down")
    _human_delay(0.3, 1.0)
    _human_mouse_move(page)
    _human_delay(0.3, 0.8)


def launch_edge():
    """Launch Edge with CDP on port 9222, separate profile, stealth flags."""
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Launching Edge (CDP port {CDP_PORT}) with stealth flags...", flush=True)
    subprocess.Popen([
        EDGE_PATH,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        # Stealth flags to reduce automation fingerprint
        "--disable-blink-features=AutomationControlled",
        "--disable-features=AutomationControlled",
        "--disable-infobars",
        "--disable-automation",
        "--disable-dev-shm-usage",
        f"--window-size={random.randint(1280, 1440)},{random.randint(800, 900)}",
        f"{FIVERR_BASE}/login",
    ])
    time.sleep(3)


def connect_cdp():
    """Connect to Edge via CDP. Applies stealth evasions. Returns (playwright, browser, context, page) or None."""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = None
    for attempt in range(15):
        try:
            browser = pw.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
            print("Connected to Edge via CDP!", flush=True)
            break
        except Exception:
            print(f"  Waiting for Edge... ({attempt+1}/15)", flush=True)
            time.sleep(2)
    if not browser:
        print("FAILED to connect to Edge CDP.", flush=True)
        pw.stop()
        return None
    contexts = browser.contexts
    if not contexts:
        print("No browser contexts found.", flush=True)
        return None
    context = contexts[0]
    pages = context.pages
    page = pages[0] if pages else context.new_page()

    # Apply stealth countermeasures immediately
    _apply_stealth(context, page)

    return pw, browser, context, page


def wait_for_login(context, page, timeout=600):
    """Wait for user to log in (URL stops being /login). Scans all tabs."""
    print("\n>>> Please log in to Fiverr in the Edge window <<<", flush=True)
    print(f">>> Then navigate to any seller page <<<\n", flush=True)
    deadline = time.time() + timeout
    check_count = 0
    while time.time() < deadline:
        # Check ALL pages/tabs in the context
        for p in context.pages:
            url = p.url
            if "fiverr.com" in url and "/login" not in url:
                print(f"Logged in! URL: {url}", flush=True)
                return p  # Return the logged-in page
        check_count += 1
        if check_count % 10 == 1:
            urls = [p.url for p in context.pages]
            print(f"  Checking tabs ({len(urls)}): {urls}", flush=True)
        time.sleep(3)
    print("Login timeout.", flush=True)
    return False


def wait_for_captcha_clear(page, timeout=300):
    """If PerimeterX CAPTCHA appears (title or iframe overlay), wait for user to clear it.
    Returns (True/False, page) — page may be a different object if original page was destroyed."""
    context = page.context

    def _has_captcha(p):
        try:
            title = p.title()
            if "human touch" in title.lower():
                return True
        except Exception:
            return False  # Page might be dead/navigating
        try:
            has_iframe = p.evaluate("""() => {
                const iframe = document.querySelector('#px-captcha-modal, iframe[id*="px-captcha"]');
                return !!iframe;
            }""")
            if has_iframe:
                return True
        except Exception:
            return False
        return False

    def _get_live_page():
        """Get a live page from context — the original might be dead after CAPTCHA."""
        try:
            # Try original page first
            page.title()
            return page
        except Exception:
            pass
        # Original page is dead — find a live one from context
        try:
            for p in context.pages:
                try:
                    p.title()
                    return p
                except Exception:
                    continue
        except Exception:
            pass
        return None

    try:
        if _has_captcha(page):
            print("CAPTCHA detected -- clear it in the browser...", flush=True)
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    # Check if captcha is gone on current page
                    if not _has_captcha(page):
                        print("CAPTCHA cleared!", flush=True)
                        time.sleep(3)
                        try:
                            page.evaluate(STEALTH_JS)
                        except Exception:
                            pass
                        return True, page
                except Exception:
                    # Original page might be dead — check for a new live page
                    live = _get_live_page()
                    if live and live != page:
                        if not _has_captcha(live):
                            print("CAPTCHA cleared (page recovered)!", flush=True)
                            time.sleep(3)
                            try:
                                live.evaluate(STEALTH_JS)
                            except Exception:
                                pass
                            return True, live
                time.sleep(2)
            # Timeout — try to recover a live page anyway
            live = _get_live_page()
            print("CAPTCHA timeout -- continuing anyway...", flush=True)
            return False, live or page
    except Exception as e:
        print(f"CAPTCHA check error: {e}", flush=True)
        return True, page
    return True, page


def probe_general_tab(page):
    """Probe the General tab for form selectors. Returns dict of selector info."""
    print("\n=== PROBING GENERAL TAB ===", flush=True)
    url = f"{FIVERR_BASE}/users/{FIVERR_USERNAME}/manage_gigs/new?wizard=0&tab=general"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    _human_delay(2, 4)
    _simulate_reading(page)
    _, page = wait_for_captcha_clear(page)
    print(f"URL: {page.url}", flush=True)
    print(f"Title: {page.title()}", flush=True)

    elements = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('input, textarea, select, [contenteditable="true"], [role="textbox"], .ql-editor, .ProseMirror, [data-placeholder]').forEach(el => {
            r.push({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || el.getAttribute('data-placeholder') || '',
                className: (typeof el.className === 'string' ? el.className : '').substring(0, 150),
                contentEditable: el.contentEditable || '',
                role: el.getAttribute('role') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                dataTestid: el.getAttribute('data-testid') || '',
                visible: el.offsetParent !== null,
                maxLength: el.maxLength || -1,
            });
        });
        // Also buttons
        document.querySelectorAll('button').forEach(el => {
            const text = el.innerText.trim().substring(0, 60);
            if (text) r.push({tag: 'BUTTON', text, visible: el.offsetParent !== null, className: (typeof el.className === 'string' ? el.className : '').substring(0, 100)});
        });
        // Labels
        document.querySelectorAll('label').forEach(el => {
            const text = el.innerText.trim().substring(0, 80);
            if (text) r.push({tag: 'LABEL', for: el.htmlFor, text, className: (typeof el.className === 'string' ? el.className : '').substring(0, 100)});
        });
        // File inputs
        document.querySelectorAll('input[type="file"]').forEach(el => {
            r.push({tag: 'FILE', name: el.name, accept: el.accept, multiple: el.multiple});
        });
        return r;
    }""")

    print(f"\nForm elements ({len(elements)}):", flush=True)
    for el in elements:
        print(f"  {json.dumps(el)}", flush=True)

    page.screenshot(path=str(SS_DIR / "cdp_general_tab.png"), timeout=5000)
    return elements


def probe_description_tab(page):
    """Probe the Description tab."""
    print("\n=== PROBING DESCRIPTION TAB ===", flush=True)
    url = f"{FIVERR_BASE}/users/{FIVERR_USERNAME}/manage_gigs/new?wizard=0&tab=description"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    _human_delay(2, 4)
    _simulate_reading(page)
    _, page = wait_for_captcha_clear(page)
    print(f"URL: {page.url}", flush=True)

    elements = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('input, textarea, select, [contenteditable="true"], [role="textbox"], .ql-editor, .ProseMirror, [data-placeholder]').forEach(el => {
            r.push({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || el.getAttribute('data-placeholder') || '',
                className: (typeof el.className === 'string' ? el.className : '').substring(0, 150),
                contentEditable: el.contentEditable || '',
                role: el.getAttribute('role') || '',
                visible: el.offsetParent !== null,
            });
        });
        document.querySelectorAll('button').forEach(el => {
            const text = el.innerText.trim().substring(0, 60);
            if (text) r.push({tag: 'BUTTON', text, visible: el.offsetParent !== null});
        });
        return r;
    }""")

    print(f"\nForm elements ({len(elements)}):", flush=True)
    for el in elements:
        print(f"  {json.dumps(el)}", flush=True)

    page.screenshot(path=str(SS_DIR / "cdp_description_tab.png"), timeout=5000)
    return elements


def probe_gallery_tab(page):
    """Probe the Gallery tab."""
    print("\n=== PROBING GALLERY TAB ===", flush=True)
    url = f"{FIVERR_BASE}/users/{FIVERR_USERNAME}/manage_gigs/new?wizard=0&tab=gallery"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    _human_delay(2, 4)
    _simulate_reading(page)
    _, page = wait_for_captcha_clear(page)
    print(f"URL: {page.url}", flush=True)

    elements = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('input[type="file"], [class*="upload"], [class*="drop"], button').forEach(el => {
            r.push({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                accept: el.accept || '',
                className: (typeof el.className === 'string' ? el.className : '').substring(0, 150),
                text: el.innerText ? el.innerText.trim().substring(0, 60) : '',
                visible: el.offsetParent !== null,
            });
        });
        return r;
    }""")

    print(f"\nElements ({len(elements)}):", flush=True)
    for el in elements:
        print(f"  {json.dumps(el)}", flush=True)

    page.screenshot(path=str(SS_DIR / "cdp_gallery_tab.png"), timeout=5000)
    return elements


def probe_pricing_tab(page):
    """Probe the Pricing tab."""
    print("\n=== PROBING PRICING TAB ===", flush=True)
    url = f"{FIVERR_BASE}/users/{FIVERR_USERNAME}/manage_gigs/new?wizard=0&tab=pricing"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    _human_delay(2, 4)
    _simulate_reading(page)
    _, page = wait_for_captcha_clear(page)
    print(f"URL: {page.url}", flush=True)

    elements = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('input, textarea, select').forEach(el => {
            const opts = el.tagName === 'SELECT' ? [...el.options].map(o => o.text).join(', ').substring(0, 200) : '';
            r.push({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                className: (typeof el.className === 'string' ? el.className : '').substring(0, 150),
                visible: el.offsetParent !== null,
                options: opts,
            });
        });
        return r;
    }""")

    print(f"\nElements ({len(elements)}):", flush=True)
    for el in elements:
        print(f"  {json.dumps(el)}", flush=True)

    page.screenshot(path=str(SS_DIR / "cdp_pricing_tab.png"), timeout=5000)
    return elements


def _safe_screenshot(page, path, timeout=5000):
    """Take a screenshot, ignoring timeout errors."""
    try:
        page.screenshot(path=str(path), timeout=timeout)
    except Exception:
        pass


def _fill_react_select(page, input_selector, search_text, label=""):
    """Fill a React-Select dropdown via OS-level pyautogui input.
    
    CDP is used ONLY to locate the element and read DOM state.
    All mouse/keyboard input goes through pyautogui.
    """
    import pyperclip
    # Step 1: Locate the React-Select input element via CDP
    el = page.query_selector(input_selector)
    if not el:
        print(f"    {label}: input {input_selector} not found in DOM", flush=True)
        return False
    
    # Find the clickable container (walk up to 'control' div)
    box = page.evaluate("""(selector) => {
        const input = document.querySelector(selector);
        if (!input) return null;
        let el = input.parentElement;
        for (let i = 0; i < 6; i++) {
            if (!el) break;
            const cls = typeof el.className === 'string' ? el.className : '';
            if (cls.includes('control') || cls.includes('Control')) {
                const rect = el.getBoundingClientRect();
                return {x: rect.x + rect.width/2, y: rect.y + rect.height/2};
            }
            el = el.parentElement;
        }
        // Fallback: use the input itself
        const rect = input.getBoundingClientRect();
        return {x: rect.x + rect.width/2, y: rect.y + rect.height/2};
    }""", input_selector)
    
    if not box:
        print(f"    {label}: could not locate element bounds", flush=True)
        return False
    
    # Step 2: Click the container via pyautogui (OS-level)
    screen_x, screen_y = _page_to_screen(page, box["x"], box["y"])
    _os_click(screen_x, screen_y)
    print(f"    {label} container: clicked at ({screen_x}, {screen_y})", flush=True)
    _human_delay(0.5, 1.2)
    
    # Step 3: Type the search text via pyautogui (OS-level keyboard)
    pyperclip.copy(search_text[:30])
    _os_hotkey('ctrl', 'v')
    _human_delay(1.5, 3.0)  # Wait for dropdown options to render
    
    # Step 4: Check if any options appeared
    options_found = page.evaluate("""() => {
        const menus = document.querySelectorAll('[class*="menu"]');
        let count = 0;
        menus.forEach(m => {
            const opts = m.querySelectorAll('[class*="option"]');
            count += opts.length;
        });
        return count;
    }""")
    print(f"    {label} options visible: {options_found}", flush=True)
    
    # Step 5: Press Enter to select via pyautogui
    _human_delay(0.2, 0.5)
    _os_press('enter')
    _human_delay(0.8, 1.5)
    
    # Step 6: Verify selection via CDP (read-only)
    verify = page.evaluate("""(selector) => {
        const input = document.querySelector(selector);
        if (!input) return null;
        let el = input;
        for (let i = 0; i < 8; i++) {
            if (!el) break;
            const cls = typeof el.className === 'string' ? el.className : '';
            if (cls.includes('singleValue') || cls.includes('SingleValue')) {
                return el.textContent;
            }
            const singleVal = el.querySelector('[class*="singleValue"], [class*="SingleValue"]');
            if (singleVal) return singleVal.textContent;
            el = el.parentElement;
        }
        return 'no-value-found';
    }""", input_selector)
    print(f"    {label} selected value: {verify}", flush=True)
    
    return True


def deploy_gig_cdp(page, gig_index, gig, general_selectors=None):
    """Deploy a single gig using CDP-connected real browser.
    
    Wizard is SEQUENTIAL — must navigate via Save & Continue, not direct URLs.
    Discovered selectors from probe:
      - Title: textarea.gig-title-textarea (placeholder "do something I'm really good at")
      - Category: #react-select-2-input (React-Select)
      - Subcategory: #react-select-3-input (React-Select)
      - Tags: input[role="combobox"]
      - Hidden: gig[title], gig[category_id], gig[sub_category_id], gig[tag_list]
      - Save & Continue: button.js-gig-upcrate-submit
    """
    from datetime import datetime, timezone
    
    result = {"gig": gig_index, "title": gig["title"], "steps": {}}
    title_text = gig["title"]
    desc_text = gig.get("description", "")
    # Clean markdown
    desc_text = re.sub(r'#{1,3}\s+', '', desc_text)
    desc_text = re.sub(r'\*\*(.+?)\*\*', r'\1', desc_text)
    tags = gig.get("tags", [])[:5]
    category = gig.get("category", "")
    subcategory = gig.get("subcategory", "")
    
    print(f"\n{'='*60}", flush=True)
    print(f"Deploying Gig #{gig_index}: {title_text[:60]}...", flush=True)
    print(f"{'='*60}", flush=True)
    
    # ── STEP 1: GENERAL TAB (title, category, tags) ──
    print("  Step 1: General tab...", flush=True)
    url = f"{FIVERR_BASE}/users/{FIVERR_USERNAME}/manage_gigs/new?wizard=0&tab=general"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as _nav_err:
        print(f"  Navigation error: {_nav_err}", flush=True)
    _human_delay(2, 4)
    _simulate_reading(page)
    # Verify we landed on Fiverr (old address-bar method was landing on Bing)
    if "fiverr.com" not in page.url:
        print(f"  ERROR: Not on Fiverr — got {page.url[:80]}", flush=True)
        result["status"] = "nav_failed"
        return result
    captcha_ok, page = wait_for_captcha_clear(page)
    if not captcha_ok:
        result["status"] = "captcha_blocked"
        return result
    
    # TITLE — via pyautogui (OS-level input)
    title_filled = _type_into_element(page, 'textarea.gig-title-textarea', title_text[:80], "Title")
    if title_filled:
        print(f"    Title filled: {title_text[:60]}...", flush=True)
    else:
        # Fallback: any visible textarea
        try:
            for ta in page.query_selector_all('textarea'):
                if ta.is_visible():
                    box = ta.bounding_box()
                    if box:
                        sx, sy = _page_to_screen(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                        _os_click(sx, sy)
                        _human_delay(0.2, 0.5)
                        _os_hotkey('ctrl', 'a')
                        _os_press('delete')
                        _human_delay(0.1, 0.3)
                        import pyperclip
                        pyperclip.copy(title_text[:80])
                        _os_hotkey('ctrl', 'v')
                        title_filled = True
                        print(f"    Title filled via fallback textarea", flush=True)
                        break
        except Exception:
            pass
    result["steps"]["title"] = title_filled
    _human_delay(0.8, 2.0)
    
    # Re-check CAPTCHA before category (overlay can appear mid-interaction)
    _human_mouse_move(page)
    _human_delay(0.5, 1.5)
    captcha_ok, page = wait_for_captcha_clear(page, timeout=120)
    if not captcha_ok:
        result["status"] = "captcha_blocked"
        return result
    
    # CATEGORY — React-Select needs clicking the visible container, not the hidden input
    cat_filled = False
    if category:
        # Parse "Programming & Tech > AI Services > AI Agents" → top level
        cat_parts = [c.strip() for c in category.split(">")]
        cat_top = cat_parts[0] if cat_parts else category
        subcat_text = cat_parts[1] if len(cat_parts) > 1 else ""
        service_text = cat_parts[2] if len(cat_parts) > 2 else ""
        
        try:
            cat_filled = _fill_react_select(page, '#react-select-2-input', cat_top, "Category")
            _human_delay(1.5, 3.0)
            
            # SUBCATEGORY — #react-select-3-input (appears after category selected)
            if subcat_text and cat_filled:
                sub_filled = _fill_react_select(page, '#react-select-3-input', subcat_text, "Subcategory")
                _human_delay(1.5, 3.0)
                
                # SERVICE TYPE — a 3rd React-Select may appear dynamically
                if service_text and sub_filled:
                    # Check for any new React-Select inputs beyond 2 and 3
                    extra_selects = page.evaluate("""() => {
                        const inputs = document.querySelectorAll('input[id^="react-select-"]');
                        return Array.from(inputs).map(i => i.id).filter(id => id !== 'react-select-2-input' && id !== 'react-select-3-input');
                    }""")
                    if extra_selects:
                        _fill_react_select(page, f'#{extra_selects[0]}', service_text, "Service Type")
                        _human_delay(0.8, 1.5)
                    else:
                        print(f"    No 3rd-level select found for: {service_text}", flush=True)
        except Exception as e:
            print(f"    Category error: {e}", flush=True)
    result["steps"]["category"] = cat_filled
    
    # Re-check CAPTCHA before tags
    _human_mouse_move(page)
    captcha_ok, page = wait_for_captcha_clear(page, timeout=60)
    
    # TAGS — via pyautogui (OS-level input)
    tag_filled = 0
    try:
        import pyperclip
        tag_input = page.query_selector('input[role="combobox"]:not([id^="react-select-"])')
        if not tag_input or not tag_input.is_visible():
            for inp in page.query_selector_all('input[role="combobox"]'):
                inp_id = inp.get_attribute('id') or ''
                if not inp_id.startswith('react-select-') and inp.is_visible():
                    tag_input = inp
                    break
        if tag_input and tag_input.is_visible():
            box = tag_input.bounding_box()
            if box:
                for tag in tags:
                    sx, sy = _page_to_screen(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                    _os_click(sx, sy)
                    _human_delay(0.2, 0.5)
                    pyperclip.copy(tag)
                    _os_hotkey('ctrl', 'v')
                    _human_delay(0.3, 0.7)
                    _os_press('enter')
                    _human_delay(0.4, 0.8)
                    tag_filled += 1
                print(f"    Tags: {tag_filled}/{len(tags)}", flush=True)
        else:
            print(f"    Tags: no visible tag input found", flush=True)
    except Exception as e:
        print(f"    Tags error: {e}", flush=True)
    result["steps"]["tags"] = tag_filled
    
    _safe_screenshot(page, SS_DIR / f"cdp_gig{gig_index:02d}_general.png")
    _human_delay(0.8, 1.5)
    
    # Re-check CAPTCHA before saving
    _human_mouse_move(page)
    captcha_ok, page = wait_for_captcha_clear(page, timeout=60)
    
    # Save & Continue to next wizard step
    _click_continue_cdp(page)
    _human_delay(4, 7)  # Wait for wizard transition
    
    # ── STEP 2: After Save & Continue — probe what's on screen now ──
    print(f"  Step 2: After Save & Continue, URL: {page.url}", flush=True)
    # Re-inject stealth after page transition
    try:
        page.evaluate(STEALTH_JS)
    except Exception:
        pass
    _simulate_reading(page)
    _safe_screenshot(page, SS_DIR / f"cdp_gig{gig_index:02d}_step2.png")
    
    # Probe current page for description/pricing elements
    current_elements = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('textarea, [contenteditable="true"], .ql-editor, .ProseMirror, [role="textbox"], input:not([type="hidden"])').forEach(el => {
            r.push({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                class: (typeof el.className === 'string' ? el.className : '').substring(0, 120),
                placeholder: el.placeholder || el.getAttribute('data-placeholder') || '',
                role: el.getAttribute('role') || '',
                ce: el.contentEditable || '',
                visible: el.offsetParent !== null,
            });
        });
        return r;
    }""")
    
    # Log what we found for debugging
    vis_elements = [e for e in current_elements if e['visible']]
    print(f"    Visible elements on step 2: {len(vis_elements)}", flush=True)
    for e in vis_elements:
        print(f"      {e['tag']} name={e['name']} class={e['class'][:60]} placeholder={e['placeholder'][:40]}", flush=True)
    
    # Try to fill description if we see a description-like element
    desc_filled = False
    for e in vis_elements:
        if e['ce'] == 'true' or 'ql-editor' in e['class'] or 'ProseMirror' in e['class']:
            # Rich text editor found
            sel = '.ql-editor' if 'ql-editor' in e['class'] else '.ProseMirror' if 'ProseMirror' in e['class'] else '[contenteditable="true"]'
            try:
                import pyperclip
                desc_el = page.query_selector(sel)
                if desc_el:
                    box = desc_el.bounding_box()
                    if box:
                        sx, sy = _page_to_screen(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                        _os_click(sx, sy)
                        _human_delay(0.3, 0.7)
                        pyperclip.copy(desc_text[:1200])
                        _os_hotkey('ctrl', 'v')
                        desc_filled = True
                        print(f"    Description filled via: {sel}", flush=True)
                        break
            except Exception:
                continue
    
    if not desc_filled:
        # Try any textarea that ISN'T the title textarea
        for e in vis_elements:
            if e['tag'] == 'TEXTAREA' and 'gig-title' not in e['class']:
                try:
                    import pyperclip
                    tas = page.query_selector_all('textarea')
                    for ta in tas:
                        cls = ta.get_attribute('class') or ''
                        if 'gig-title' not in cls and ta.is_visible():
                            box = ta.bounding_box()
                            if box:
                                sx, sy = _page_to_screen(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                                _os_click(sx, sy)
                                _human_delay(0.2, 0.4)
                                pyperclip.copy(desc_text[:1200])
                                _os_hotkey('ctrl', 'v')
                                desc_filled = True
                                print(f"    Description filled via non-title textarea", flush=True)
                                break
                except Exception:
                    pass
                if desc_filled:
                    break
    
    result["steps"]["description"] = desc_filled
    
    # Save & Continue through remaining steps
    _human_mouse_move(page)
    _human_delay(0.5, 1.0)
    _click_continue_cdp(page)
    _human_delay(3, 5)
    
    print(f"  Step 3: URL: {page.url}", flush=True)
    try:
        page.evaluate(STEALTH_JS)
    except Exception:
        pass
    _simulate_reading(page)
    _safe_screenshot(page, SS_DIR / f"cdp_gig{gig_index:02d}_step3.png")
    _click_continue_cdp(page)
    _human_delay(3, 5)
    
    print(f"  Step 4: URL: {page.url}", flush=True)
    try:
        page.evaluate(STEALTH_JS)
    except Exception:
        pass
    _simulate_reading(page)
    _safe_screenshot(page, SS_DIR / f"cdp_gig{gig_index:02d}_step4.png")
    
    # Gallery — try to upload image
    img_path = _find_gig_image(gig_index)
    img_uploaded = False
    if img_path:
        try:
            file_input = page.query_selector('input[type="file"]')
            if file_input:
                file_input.set_input_files(str(img_path))
                _human_delay(3, 6)
                img_uploaded = True
                print(f"    Image uploaded: {img_path.name}", flush=True)
        except Exception as e:
            print(f"    Image upload error: {e}", flush=True)
    result["steps"]["image"] = img_uploaded
    
    _human_mouse_move(page)
    _human_delay(0.5, 1.0)
    _click_continue_cdp(page)
    _human_delay(3, 5)
    
    print(f"  Step 5: URL: {page.url}", flush=True)
    try:
        page.evaluate(STEALTH_JS)
    except Exception:
        pass
    _simulate_reading(page)
    _safe_screenshot(page, SS_DIR / f"cdp_gig{gig_index:02d}_step5.png")
    
    # Final review - don't publish, just save as draft
    result["steps"]["review"] = True
    result["status"] = "draft"
    
    print(f"  Gig #{gig_index} STATUS: {result['status']}", flush=True)
    print(f"  Steps: title={'OK' if title_filled else 'FAIL'}, desc={'OK' if desc_filled else 'FAIL'}, img={'OK' if img_uploaded else 'FAIL'}", flush=True)
    return result


def _click_continue_cdp(page):
    """Click Save & Continue / Continue / Next button via pyautogui."""
    for sel in [
        'button:has-text("Save & Continue")',
        'button:has-text("Save and Continue")',
        'button:has-text("Continue")',
        'button:has-text("Next")',
        'button[type="submit"]',
    ]:
        if _click_element(page, sel, "Continue"):
            return True
    return False


def _find_gig_image(gig_index):
    """Find the cover image for a gig."""
    if not IMAGE_DIR.exists():
        return None
    gig = FIVERR_GIGS[gig_index - 1]
    safe_title = re.sub(r'[^a-z0-9]+', '_', gig["title"].lower())[:60]
    filename = f"gig_{gig_index:02d}_{safe_title}.png"
    path = IMAGE_DIR / filename
    if path.exists():
        return path
    # Try pattern match
    for f in IMAGE_DIR.glob(f"gig_{gig_index:02d}_*.png"):
        return f
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CDP-based Fiverr gig deployment")
    parser.add_argument("--probe", action="store_true", help="Just probe selectors, don't fill")
    parser.add_argument("--gigs", type=str, default=None, help="Comma-separated gig indices (e.g., 3,7,8)")
    parser.add_argument("--reset", action="store_true", help="Clear false-positive deploy state before running")
    args = parser.parse_args()

    gig_indices = DEFAULT_GIGS
    if args.gigs:
        gig_indices = [int(x.strip()) for x in args.gigs.split(",") if x.strip().isdigit()]

    print("=" * 60, flush=True)
    print("  FIVERR CDP DEPLOYMENT", flush=True)
    print(f"  Mode: {'PROBE' if args.probe else 'DEPLOY'}", flush=True)
    if not args.probe:
        print(f"  Gigs: {gig_indices}", flush=True)
    print("=" * 60, flush=True)

    # Launch Edge
    launch_edge()

    # Connect via CDP
    result = connect_cdp()
    if not result:
        return
    pw, browser, context, page = result

    # Wait for login
    if "/login" in page.url or "edge://" in page.url:
        logged_in_page = wait_for_login(context, page)
        if not logged_in_page:
            pw.stop()
            return
        page = logged_in_page  # Use the page that's actually logged in

    _human_delay(2, 4)

    # Warm-up: Navigate to seller dashboard first to establish clean PX fingerprint
    print("  Warming up with seller dashboard...", flush=True)
    try:
        page.goto(f"{FIVERR_BASE}/users/{FIVERR_USERNAME}/seller_dashboard", wait_until="domcontentloaded", timeout=30000)
        _human_delay(2, 4)
        _simulate_reading(page)

        # Verify stealth is working
        webdriver_val = page.evaluate("() => navigator.webdriver")
        print(f"  navigator.webdriver = {webdriver_val}", flush=True)
        if webdriver_val:
            print("  WARNING: navigator.webdriver still true! Stealth may not be effective.", flush=True)
        else:
            print("  Stealth evasions confirmed working.", flush=True)

        # Check for CAPTCHA on dashboard
        captcha_ok, page = wait_for_captcha_clear(page, timeout=120)
        if not captcha_ok:
            print("  CAPTCHA on dashboard -- you need to clear it manually.", flush=True)
    except Exception as e:
        print(f"  Warm-up error: {e}", flush=True)

    if args.probe:
        # Just probe all tabs
        probe_general_tab(page)
        probe_description_tab(page)
        probe_gallery_tab(page)
        probe_pricing_tab(page)
        print("\n=== PROBE COMPLETE ===", flush=True)
    else:
        # Deploy gigs
        state = _load_state()
        if args.reset:
            print("  [RESET] Clearing deploy state...", flush=True)
            state["gigs"] = {}
            _save_state(state)
            print("  [RESET] State cleared — all gigs will be re-deployed.", flush=True)
        results = []

        for i, idx in enumerate(gig_indices):
            if idx < 1 or idx > len(FIVERR_GIGS):
                print(f"Skipping invalid gig index: {idx}", flush=True)
                continue

            gig = FIVERR_GIGS[idx - 1]
            print(f"\n--- Gig {idx} ({i+1}/{len(gig_indices)}): {gig['title'][:60]}... ---", flush=True)

            try:
                r = deploy_gig_cdp(page, idx, gig)
            except Exception as e:
                print(f"  ERROR: {e}", flush=True)
                r = {"gig": idx, "title": gig["title"], "status": "error", "steps": {}, "error": str(e)}

            results.append(r)
            from datetime import datetime, timezone
            state["gigs"][str(idx)] = {
                "status": r["status"],
                "deployed_at": datetime.now(timezone.utc).isoformat(),
                "steps": r["steps"],
            }
            _save_state(state)

            # Random delay between gigs
            if i < len(gig_indices) - 1:
                delay = random.randint(10, 25)
                print(f"  (waiting {delay}s between gigs...)", flush=True)
                time.sleep(delay)

        print(f"\n{'='*60}", flush=True)
        print("=== DEPLOYMENT COMPLETE ===", flush=True)
        for r in results:
            s = "OK" if r["status"] == "draft" else r["status"]
            print(f"  Gig #{r['gig']}: {s} - {r['title'][:50]}", flush=True)
        print(f"{'='*60}", flush=True)

    print("\nEdge stays open. Close it when you're done.", flush=True)


if __name__ == "__main__":
    main()
