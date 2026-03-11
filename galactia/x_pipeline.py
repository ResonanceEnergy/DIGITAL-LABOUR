"""X Pipeline — Live ingestion from X (Twitter) feed into NCL Galactia.

Pulls posts from a configured X account feed and ingests them into
Galactia's knowledge store for truth-scoring, correlation, and research.

Supports two modes:
  1. API mode: Uses X API v2 (requires Bearer Token)
  2. Manual mode: Reads from a curated JSON feed file

Usage:
    from galactia.x_pipeline import ingest_feed, ingest_manual
    results = ingest_feed(max_posts=50)
"""

import json
import os
import re
import sys
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FEED_ARCHIVE = DATA_DIR / "x_feed_archive.jsonl"
INGEST_STATE = DATA_DIR / "x_ingest_state.json"


def _post_id(text: str, author: str, timestamp: str) -> str:
    """Generate deterministic ID for a post to prevent duplicates."""
    raw = f"{author}:{timestamp}:{text[:100]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_ingest_state() -> dict:
    if INGEST_STATE.exists():
        return json.loads(INGEST_STATE.read_text(encoding="utf-8"))
    return {"last_ingest": None, "total_ingested": 0, "seen_ids": []}


def _save_ingest_state(state: dict):
    # Keep seen_ids bounded
    state["seen_ids"] = state["seen_ids"][-5000:]
    INGEST_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── X API v2 Ingestion ─────────────────────────────────────────

def ingest_feed(max_posts: int = 50, username: str | None = None) -> list[dict]:
    """Pull recent posts from X feed via API v2.

    Requires X_BEARER_TOKEN in .env.
    If username is None, uses X_USERNAME from .env.
    """
    import httpx

    bearer = os.getenv("X_BEARER_TOKEN", "")
    if not bearer:
        print("[X PIPELINE] No X_BEARER_TOKEN configured. Use ingest_manual() or set token in .env")
        return []

    username = username or os.getenv("X_USERNAME", "")
    if not username:
        print("[X PIPELINE] No X_USERNAME configured in .env")
        return []

    state = _load_ingest_state()
    seen = set(state.get("seen_ids", []))

    # Step 1: Get user ID from username
    headers = {"Authorization": f"Bearer {bearer}"}
    try:
        resp = httpx.get(
            f"https://api.twitter.com/2/users/by/username/{username}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        user_data = resp.json()
        user_id = user_data["data"]["id"]
    except Exception as e:
        print(f"[X PIPELINE] Failed to lookup user @{username}: {e}")
        return []

    # Step 2: Get recent tweets
    params = {
        "max_results": min(max_posts, 100),
        "tweet.fields": "created_at,public_metrics,entities,referenced_tweets",
        "expansions": "referenced_tweets.id",
    }

    # Use since_id if we have previous state
    if state.get("last_tweet_id"):
        params["since_id"] = state["last_tweet_id"]

    try:
        resp = httpx.get(
            f"https://api.twitter.com/2/users/{user_id}/tweets",
            headers=headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[X PIPELINE] Failed to fetch tweets: {e}")
        return []

    tweets = data.get("data", [])
    if not tweets:
        print("[X PIPELINE] No new tweets found.")
        return []

    # Step 3: Process and archive
    ingested = []
    for tweet in tweets:
        post_id = tweet.get("id", _post_id(tweet["text"], username, tweet.get("created_at", "")))

        if post_id in seen:
            continue

        record = _normalize_post(
            text=tweet["text"],
            author=username,
            timestamp=tweet.get("created_at", datetime.now(timezone.utc).isoformat()),
            source="x_api",
            metrics=tweet.get("public_metrics", {}),
            entities=tweet.get("entities", {}),
            post_id=post_id,
            is_retweet="referenced_tweets" in tweet,
            raw=tweet,
        )

        # Archive
        with open(FEED_ARCHIVE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        seen.add(post_id)
        ingested.append(record)

    # Update state
    if tweets:
        state["last_tweet_id"] = tweets[0]["id"]
    state["last_ingest"] = datetime.now(timezone.utc).isoformat()
    state["total_ingested"] = state.get("total_ingested", 0) + len(ingested)
    state["seen_ids"] = list(seen)
    _save_ingest_state(state)

    print(f"[X PIPELINE] Ingested {len(ingested)} new posts from @{username}")
    return ingested


# ── Manual / File-Based Ingestion ──────────────────────────────

def ingest_manual(posts: list[dict]) -> list[dict]:
    """Ingest manually curated posts.

    Each post dict should have: text, author (optional), timestamp (optional)
    Can also include: url, topic_hint, context
    """
    state = _load_ingest_state()
    seen = set(state.get("seen_ids", []))
    ingested = []

    for post in posts:
        text = post.get("text", "")
        if not text:
            continue

        author = post.get("author", "manual")
        ts = post.get("timestamp", datetime.now(timezone.utc).isoformat())
        pid = _post_id(text, author, ts)

        if pid in seen:
            continue

        record = _normalize_post(
            text=text,
            author=author,
            timestamp=ts,
            source="manual",
            post_id=pid,
            url=post.get("url", ""),
            topic_hint=post.get("topic_hint", ""),
            context=post.get("context", ""),
        )

        with open(FEED_ARCHIVE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        seen.add(pid)
        ingested.append(record)

    state["last_ingest"] = datetime.now(timezone.utc).isoformat()
    state["total_ingested"] = state.get("total_ingested", 0) + len(ingested)
    state["seen_ids"] = list(seen)
    _save_ingest_state(state)

    print(f"[X PIPELINE] Manually ingested {len(ingested)} posts")
    return ingested


def ingest_from_file(filepath: str | Path) -> list[dict]:
    """Ingest posts from a JSON file (array of post objects)."""
    path = Path(filepath)
    if not path.exists():
        print(f"[X PIPELINE] File not found: {path}")
        return []
    posts = json.loads(path.read_text(encoding="utf-8"))
    return ingest_manual(posts)


# ── Normalization ──────────────────────────────────────────────

def _normalize_post(
    text: str,
    author: str,
    timestamp: str,
    source: str,
    post_id: str = "",
    metrics: dict | None = None,
    entities: dict | None = None,
    is_retweet: bool = False,
    raw: dict | None = None,
    url: str = "",
    topic_hint: str = "",
    context: str = "",
) -> dict:
    """Normalize a post into Galactia's standard format."""
    # Extract URLs from text
    urls = re.findall(r'https?://\S+', text)

    # Extract hashtags
    hashtags = re.findall(r'#(\w+)', text)

    # Extract mentions
    mentions = re.findall(r'@(\w+)', text)

    # Clean text for analysis
    clean_text = re.sub(r'https?://\S+', '', text).strip()
    clean_text = re.sub(r'\s+', ' ', clean_text)

    return {
        "id": post_id or _post_id(text, author, timestamp),
        "text": text,
        "clean_text": clean_text,
        "author": author,
        "timestamp": timestamp,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "url": url,
        "urls_found": urls,
        "hashtags": hashtags,
        "mentions": mentions,
        "metrics": metrics or {},
        "entities": entities or {},
        "is_retweet": is_retweet,
        "topic_hint": topic_hint,
        "context": context,
        # Placeholders — filled by truth engine
        "truth_score": None,
        "credibility_score": None,
        "accountability_score": None,
        "overall_score": None,
        "topics": [],
        "correlation_ids": [],
        "research_spawned": None,
    }


# ── Feed Stats ─────────────────────────────────────────────────

def feed_stats() -> dict:
    """Get ingestion statistics."""
    state = _load_ingest_state()
    archive_count = 0
    if FEED_ARCHIVE.exists():
        with open(FEED_ARCHIVE, "r", encoding="utf-8") as f:
            archive_count = sum(1 for line in f if line.strip())

    return {
        "total_ingested": state.get("total_ingested", 0),
        "archive_count": archive_count,
        "last_ingest": state.get("last_ingest"),
        "seen_ids_count": len(state.get("seen_ids", [])),
    }


def get_unscored_posts(limit: int = 50) -> list[dict]:
    """Get posts that haven't been scored by the truth engine yet."""
    if not FEED_ARCHIVE.exists():
        return []

    unscored = []
    with open(FEED_ARCHIVE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            post = json.loads(line)
            if post.get("overall_score") is None:
                unscored.append(post)
                if len(unscored) >= limit:
                    break
    return unscored


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="X Pipeline — Feed ingestion for Galactia")
    parser.add_argument("--ingest", action="store_true", help="Ingest from X API")
    parser.add_argument("--file", type=str, help="Ingest from JSON file")
    parser.add_argument("--stats", action="store_true", help="Show feed stats")
    parser.add_argument("--max", type=int, default=50, help="Max posts to ingest")
    args = parser.parse_args()

    if args.stats:
        stats = feed_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")
    elif args.file:
        ingest_from_file(args.file)
    elif args.ingest:
        ingest_feed(max_posts=args.max)
    else:
        parser.print_help()
