"""LinkedIn Poster — Automated content posting from SOCIAL_CONTENT.md.

Posts pre-written LinkedIn content on a rotation. Uses LinkedIn's Share API
when credentials are available, falls back to file-based queue for manual posting.

Usage:
    python -m automation.linkedin_poster --post        # Post next content
    python -m automation.linkedin_poster --preview      # Preview without posting
    python -m automation.linkedin_poster --status        # Show posting status
    python -m automation.linkedin_poster --daemon        # Run daily posting daemon
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

STATE_FILE = PROJECT_ROOT / "data" / "linkedin_poster_state.json"
CONTENT_FILE = PROJECT_ROOT / "campaign" / "SOCIAL_CONTENT.md"

# LinkedIn API
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


# ── Content Loading ────────────────────────────────────────────

def _load_posts() -> list[str]:
    """Extract LinkedIn content blocks from SOCIAL_CONTENT.md."""
    if not CONTENT_FILE.exists():
        return []

    content = CONTENT_FILE.read_text(encoding="utf-8")

    # Find the LINKEDIN POSTS section
    match = re.search(r"## LINKEDIN POSTS.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if not match:
        # Fallback: try any professional content section
        match = re.search(r"## (?:LINKEDIN|PROFESSIONAL).*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        if not match:
            return []

    section = match.group(1)
    posts = re.findall(r"```\n(.*?)```", section, re.DOTALL)
    posts = [p.strip() for p in posts if p.strip()]
    return posts


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "posted": [],
        "next_index": 0,
        "total_posted": 0,
        "last_posted_at": None,
        "errors": [],
    }


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── LinkedIn API ───────────────────────────────────────────────

def _post_linkedin_api(text: str) -> dict:
    """Post content to LinkedIn using the Share API v2.

    Requires LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_ID in .env.
    """
    import urllib.request
    import urllib.error

    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    person_id = os.getenv("LINKEDIN_PERSON_ID", "")

    if not token or not person_id:
        return {
            "success": False,
            "error": "LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_ID not set",
            "queued": True,
        }

    payload = json.dumps({
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{LINKEDIN_API_BASE}/ugcPosts",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            post_id = data.get("id", "")
            return {"success": True, "post_id": post_id}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        return {"success": False, "error": f"HTTP {e.code}: {body}", "status_code": e.code}
    except (urllib.error.URLError, TimeoutError) as e:
        return {"success": False, "error": str(e)}


def _queue_post(text: str, reason: str = "api_fallback") -> dict:
    """Queue a post for manual LinkedIn posting."""
    queue_dir = PROJECT_ROOT / "data" / "linkedin_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    queue_file = queue_dir / f"post_{ts}_{content_hash}.json"

    entry = {
        "text": text,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "status": "queued",
        "char_count": len(text),
    }
    queue_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return {"queued": True, "file": str(queue_file)}


# ── Public API ─────────────────────────────────────────────────

def get_next_post() -> str | None:
    """Get the next LinkedIn post in rotation."""
    posts = _load_posts()
    if not posts:
        return None
    state = _load_state()
    idx = state.get("next_index", 0) % len(posts)
    return posts[idx]


def post_next() -> dict:
    """Post the next LinkedIn content in rotation."""
    posts = _load_posts()
    if not posts:
        return {"success": False, "error": "No LinkedIn posts found in SOCIAL_CONTENT.md"}

    state = _load_state()
    idx = state.get("next_index", 0) % len(posts)
    post_text = posts[idx]

    # Check cooldown (24h between posts)
    last = state.get("last_posted_at")
    if last:
        last_dt = datetime.fromisoformat(last)
        now = datetime.now(timezone.utc)
        if (now - last_dt) < timedelta(hours=22):
            return {
                "success": False,
                "error": f"Already posted at {last_dt.strftime('%H:%M UTC')}. Wait 22h between posts.",
            }

    # LinkedIn post limit: 3000 chars
    if len(post_text) > 3000:
        post_text = post_text[:2997] + "..."

    print(f"\n[LINKEDIN] Posting content {idx + 1}/{len(posts)}:")
    print(f"  {post_text[:100]}...")

    # Try API first, fallback to queue
    result = _post_linkedin_api(post_text)

    if not result.get("success"):
        queue_result = _queue_post(post_text, reason=result.get("error", "api_failed")[:80])
        result["queued"] = True
        result["queue_file"] = queue_result.get("file")
        print(f"  [LINKEDIN] Queued for manual posting")
    else:
        print(f"  [LINKEDIN] Posted: {result.get('post_id', 'OK')}")

    # Update state
    state["next_index"] = (idx + 1) % len(posts)
    state["total_posted"] = state.get("total_posted", 0) + 1
    state["last_posted_at"] = datetime.now(timezone.utc).isoformat()
    state["posted"].append({
        "index": idx,
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "success": result.get("success", False),
        "queued": result.get("queued", False),
    })
    _save_state(state)

    return result


def get_status() -> dict:
    """Get LinkedIn poster status."""
    posts = _load_posts()
    state = _load_state()
    queue_dir = PROJECT_ROOT / "data" / "linkedin_queue"
    queued = len(list(queue_dir.glob("post_*.json"))) if queue_dir.exists() else 0

    return {
        "content_available": len(posts),
        "total_posted": state.get("total_posted", 0),
        "next_index": state.get("next_index", 0),
        "last_posted": state.get("last_posted_at"),
        "queued_for_manual": queued,
    }


def run_daemon():
    """Run daily LinkedIn posting daemon."""
    print(f"\n{'='*60}")
    print(f"  LINKEDIN POSTER DAEMON — Daily posting")
    print(f"{'='*60}\n")

    while True:
        try:
            result = post_next()
            if result.get("success") or result.get("queued"):
                print(f"  [{datetime.now(timezone.utc).strftime('%H:%M')}] Posted/queued")
            else:
                print(f"  [{datetime.now(timezone.utc).strftime('%H:%M')}] Skipped: {result.get('error', '')[:60]}")
            # Sleep 24 hours
            time.sleep(86400)
        except KeyboardInterrupt:
            print("\n  [STOP] LinkedIn poster stopped")
            break
        except Exception as e:
            print(f"  [ERROR] {e}")
            time.sleep(3600)


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LinkedIn Poster")
    parser.add_argument("--post", action="store_true", help="Post next content")
    parser.add_argument("--preview", action="store_true", help="Preview without posting")
    parser.add_argument("--status", action="store_true", help="Show posting status")
    parser.add_argument("--daemon", action="store_true", help="Run daily daemon")
    args = parser.parse_args()

    if args.post:
        post_next()
    elif args.preview:
        text = get_next_post()
        if text:
            print(f"\n  Next LinkedIn post ({len(text)} chars):\n")
            print(f"  {text}")
        else:
            print("\n  No posts available in SOCIAL_CONTENT.md")
    elif args.status:
        st = get_status()
        print(f"\n  LinkedIn Poster Status:")
        print(f"    Content available:  {st['content_available']}")
        print(f"    Total posted:       {st['total_posted']}")
        print(f"    Next index:         {st['next_index']}")
        print(f"    Last posted:        {st['last_posted'] or 'Never'}")
        print(f"    Queued for manual:  {st['queued_for_manual']}")
    elif args.daemon:
        run_daemon()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
