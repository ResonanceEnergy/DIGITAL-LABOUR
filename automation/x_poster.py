"""X/Twitter Daily Poster — Automated content posting for @agentbravo069.

Posts pre-written tweets from campaign/SOCIAL_CONTENT.md on a rotation.
Tracks what's been posted to avoid duplicates. Supports LLM-generated content fallback.

Usage:
    python -m automation.x_poster --post           # Post next tweet in rotation
    python -m automation.x_poster --status          # Show posting status
    python -m automation.x_poster --preview         # Preview next tweet without posting
    python -m automation.x_poster --daemon          # Run daily posting daemon
"""

import argparse
import base64
import hashlib
import hmac
import io
import json
import os
import re
import sys
import time
import urllib.parse
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ── UTF-8 stdout fix for Windows ──────────────────────────────
if sys.stdout and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

STATE_FILE = PROJECT_ROOT / "data" / "x_poster_state.json"
CONTENT_FILE = PROJECT_ROOT / "campaign" / "SOCIAL_CONTENT.md"

# X API v2 endpoints
X_API_BASE = "https://api.twitter.com/2"
X_TWEET_URL = f"{X_API_BASE}/tweets"


# ── Content Loading ────────────────────────────────────────────

def _load_tweets() -> list[str]:
    """Extract tweet content blocks from SOCIAL_CONTENT.md."""
    if not CONTENT_FILE.exists():
        return []

    content = CONTENT_FILE.read_text(encoding="utf-8")

    # Find the TWITTER/X POSTS section
    match = re.search(r"## TWITTER/X POSTS.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if not match:
        return []

    section = match.group(1)

    # Extract code blocks (``` ... ```)
    tweets = re.findall(r"```\n(.*?)```", section, re.DOTALL)
    # Clean up whitespace
    tweets = [t.strip() for t in tweets if t.strip()]
    return tweets


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


# ── X API Posting ──────────────────────────────────────────────

def _has_oauth1a_creds() -> bool:
    """Check if OAuth 1.0a user-context credentials are configured."""
    return all(os.getenv(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"))


def _oauth1a_sign(method: str, url: str, body_params: dict | None = None) -> dict:
    """Build OAuth 1.0a Authorization header using HMAC-SHA1 signing.
    Returns headers dict ready for requests."""
    api_key = os.getenv("X_API_KEY", "")
    api_secret = os.getenv("X_API_SECRET", "")
    access_token = os.getenv("X_ACCESS_TOKEN", "")
    access_secret = os.getenv("X_ACCESS_SECRET", "")

    oauth_params = {
        "oauth_consumer_key": api_key,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }

    # Combine all params for signature base string
    all_params = {**oauth_params}
    if body_params:
        all_params.update(body_params)

    # Sort and percent-encode
    param_string = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted(all_params.items())
    )

    base_string = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_string, safe='')}"
    signing_key = f"{urllib.parse.quote(api_secret, safe='')}&{urllib.parse.quote(access_secret, safe='')}"

    signature = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()

    oauth_params["oauth_signature"] = signature

    auth_header = "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(oauth_params.items())
    )

    return {
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }


def _get_auth_headers() -> dict:
    """Build OAuth headers for X API v2 using Bearer token (read-only fallback)."""
    token = os.getenv("X_BEARER_TOKEN", "")
    if not token:
        raise RuntimeError("X_BEARER_TOKEN not set in .env")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _post_tweet_api(text: str) -> dict:
    """Post a tweet using X API v2. Prefers OAuth 1.0a, falls back to Bearer."""
    payload = {"text": text}

    if _has_oauth1a_creds():
        # OAuth 1.0a User Context — can create tweets
        # For JSON body posts, the body params are NOT included in the signature base string
        headers = _oauth1a_sign("POST", X_TWEET_URL)
        resp = requests.post(X_TWEET_URL, headers=headers, json=payload, timeout=30)
    else:
        # Bearer token — read-only, will get 403
        headers = _get_auth_headers()
        resp = requests.post(X_TWEET_URL, headers=headers, json=payload, timeout=30)

    if resp.status_code == 201:
        data = resp.json()
        tweet_id = data.get("data", {}).get("id", "")
        print(f"  [X] Posted tweet {tweet_id}")
        return {"success": True, "tweet_id": tweet_id, "data": data}
    elif resp.status_code == 403:
        return {
            "success": False,
            "error": "403 Forbidden — Bearer token is read-only. Set X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_SECRET for OAuth 1.0a.",
            "status_code": resp.status_code,
            "queued": True,
        }
    else:
        return {
            "success": False,
            "error": resp.text[:500],
            "status_code": resp.status_code,
        }


def _queue_tweet(text: str, reason: str = "api_fallback") -> dict:
    """Queue a tweet for manual posting when API fails."""
    queue_dir = PROJECT_ROOT / "data" / "x_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    queue_file = queue_dir / f"tweet_{ts}_{content_hash}.json"

    entry = {
        "text": text,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "status": "queued",
        "char_count": len(text),
    }
    queue_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    print(f"  [X] Queued tweet to {queue_file.name} ({len(text)} chars)")
    return {"queued": True, "file": str(queue_file)}


# ── Public API ─────────────────────────────────────────────────

def get_next_tweet() -> str | None:
    """Get the next tweet in rotation."""
    tweets = _load_tweets()
    if not tweets:
        return None

    state = _load_state()
    idx = state.get("next_index", 0) % len(tweets)
    return tweets[idx]


def post_next() -> dict:
    """Post the next tweet in the rotation."""
    tweets = _load_tweets()
    if not tweets:
        return {"success": False, "error": "No tweets found in SOCIAL_CONTENT.md"}

    state = _load_state()
    idx = state.get("next_index", 0) % len(tweets)
    tweet_text = tweets[idx]

    # Check if we already posted today
    last = state.get("last_posted_at")
    if last:
        last_dt = datetime.fromisoformat(last)
        now = datetime.now(timezone.utc)
        if (now - last_dt) < timedelta(hours=20):
            return {
                "success": False,
                "error": f"Already posted today at {last_dt.strftime('%H:%M UTC')}. Wait 20h between posts.",
                "last_posted": last,
            }

    # Truncate to 280 chars if needed
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + "..."

    print(f"\n[X POSTER] Posting tweet {idx + 1}/{len(tweets)}:")
    print(f"  {tweet_text[:100]}...")

    # Try API first, fall back to queue
    result = _post_tweet_api(tweet_text)

    if not result.get("success") and result.get("status_code") in (401, 403):
        # Bearer token is read-only — queue for manual posting
        queue_result = _queue_tweet(tweet_text, reason="bearer_readonly")
        result["queued"] = True
        result["queue_file"] = queue_result.get("file")

    # Update state regardless (rotate to next)
    state["next_index"] = (idx + 1) % len(tweets)
    state["total_posted"] = state.get("total_posted", 0) + 1
    state["last_posted_at"] = datetime.now(timezone.utc).isoformat()
    state["posted"].append({
        "index": idx,
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "success": result.get("success", False),
        "tweet_id": result.get("tweet_id"),
        "char_count": len(tweet_text),
    })
    _save_state(state)

    return result


def preview_next() -> dict:
    """Preview the next tweet without posting."""
    tweets = _load_tweets()
    if not tweets:
        return {"error": "No tweets found"}

    state = _load_state()
    idx = state.get("next_index", 0) % len(tweets)
    tweet = tweets[idx]

    return {
        "index": idx + 1,
        "total_tweets": len(tweets),
        "text": tweet,
        "char_count": len(tweet),
        "over_limit": len(tweet) > 280,
    }


def show_status():
    """Display posting status."""
    state = _load_state()
    tweets = _load_tweets()

    print(f"\n{'='*60}")
    print(f"  X/TWITTER POSTER — @{os.getenv('X_USERNAME', 'agentbravo069')}")
    print(f"{'='*60}")
    print(f"  Available tweets: {len(tweets)}")
    print(f"  Total posted:     {state.get('total_posted', 0)}")
    print(f"  Next index:       {state.get('next_index', 0) + 1}/{len(tweets)}")
    print(f"  Last posted:      {state.get('last_posted_at', 'never')}")

    # Check queue
    queue_dir = PROJECT_ROOT / "data" / "x_queue"
    if queue_dir.exists():
        queued = list(queue_dir.glob("tweet_*.json"))
        pending = [q for q in queued if "queued" in q.read_text(encoding="utf-8")]
        print(f"  Queued (pending): {len(pending)}")

    # Show next preview
    if tweets:
        idx = state.get("next_index", 0) % len(tweets)
        preview = tweets[idx][:80] + "..." if len(tweets[idx]) > 80 else tweets[idx]
        print(f"\n  Next tweet: {preview}")


def generate_fresh_tweet() -> str:
    """Generate a fresh tweet using LLM when pre-written ones run out."""
    try:
        from utils.llm_client import call_llm
        prompt = """Write a single tweet (max 270 chars) for @agentbravo069, a B2B AI labor service.

Tone: direct, no fluff, specific numbers.
Services: AI lead research ($12/lead), support triage ($2/ticket), content repurposing ($10/piece).
Include a CTA. No hashtags. No emojis.

Respond with ONLY the tweet text, nothing else."""

        result = call_llm(prompt, provider="openai", max_tokens=100)
        tweet = result.strip().strip('"').strip("'")
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        return tweet
    except Exception as e:
        return f"AI agents doing real work for real money. $12/lead, $2/ticket. DM for a free demo. ({e})"


# ── Daemon ─────────────────────────────────────────────────────

def daemon_loop():
    """Run daily posting loop — posts once per day at ~14:00 UTC."""
    from automation.decision_log import log_decision
    print(f"\n[X POSTER] Daemon started. Posting daily at ~14:00 UTC.")

    while True:
        now = datetime.now(timezone.utc)

        # Post window: 13:00-15:00 UTC (morning Americas, afternoon Europe)
        if 13 <= now.hour <= 15:
            state = _load_state()
            last = state.get("last_posted_at")

            should_post = True
            if last:
                last_dt = datetime.fromisoformat(last)
                if (now - last_dt) < timedelta(hours=20):
                    should_post = False

            if should_post:
                result = post_next()
                log_decision(
                    actor="X_POSTER",
                    action="daily_tweet",
                    reasoning="Scheduled daily X/Twitter post",
                    outcome=f"Success: {result.get('success')}, Tweet ID: {result.get('tweet_id', 'queued')}",
                )

        # Sleep 30 minutes between checks
        time.sleep(1800)


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="X/Twitter Daily Poster")
    parser.add_argument("--post", action="store_true", help="Post next tweet")
    parser.add_argument("--preview", action="store_true", help="Preview next tweet")
    parser.add_argument("--status", action="store_true", help="Show posting status")
    parser.add_argument("--daemon", action="store_true", help="Run daily posting daemon")
    parser.add_argument("--generate", action="store_true", help="Generate fresh tweet with LLM")
    args = parser.parse_args()

    if args.post:
        result = post_next()
        print(json.dumps(result, indent=2, default=str))
    elif args.preview:
        result = preview_next()
        print(json.dumps(result, indent=2))
    elif args.status:
        show_status()
    elif args.daemon:
        daemon_loop()
    elif args.generate:
        tweet = generate_fresh_tweet()
        print(f"\nGenerated tweet ({len(tweet)} chars):")
        print(tweet)
    else:
        show_status()
