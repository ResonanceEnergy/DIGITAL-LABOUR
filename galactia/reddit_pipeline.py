"""Reddit Pipeline — Live ingestion from Reddit into NCL Galactia.

Pulls posts from configured subreddits using Reddit's public JSON API
(no authentication required) and normalizes them into Galactia's standard
post format for truth-scoring, correlation, and research.

Subreddits are grouped by NCL division relevance:
  ALPHA  — AI, automation, SaaS, digital labour
  BRAVO  — Insurance, claims, regulatory
  CHARLIE — Construction, permits, trades
  DELTA  — Municipal, government, public sector

Usage:
    from galactia.reddit_pipeline import ingest_feed, feed_stats
    results = ingest_feed(max_posts=100)
"""

import json
import os
import re
import sys
import hashlib
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FEED_ARCHIVE = DATA_DIR / "reddit_feed_archive.jsonl"
INGEST_STATE = DATA_DIR / "reddit_ingest_state.json"

# ── Subreddit Configuration ───────────────────────────────────
# Grouped by NCL division relevance

SUBREDDITS = {
    # ALPHA — Digital Labour / AI / Automation
    "artificial": {"division": "ALPHA", "priority": "high"},
    "MachineLearning": {"division": "ALPHA", "priority": "high"},
    "LocalLLaMA": {"division": "ALPHA", "priority": "high"},
    "ChatGPT": {"division": "ALPHA", "priority": "medium"},
    "OpenAI": {"division": "ALPHA", "priority": "high"},
    "ClaudeAI": {"division": "ALPHA", "priority": "high"},
    "SaaS": {"division": "ALPHA", "priority": "medium"},
    "automation": {"division": "ALPHA", "priority": "medium"},
    "freelance": {"division": "ALPHA", "priority": "medium"},
    "Entrepreneur": {"division": "ALPHA", "priority": "medium"},

    # BRAVO — Insurance Operations
    "Insurance": {"division": "BRAVO", "priority": "high"},
    "HealthInsurance": {"division": "BRAVO", "priority": "high"},
    "InsuranceProfessional": {"division": "BRAVO", "priority": "high"},
    "personalfinance": {"division": "BRAVO", "priority": "medium"},

    # CHARLIE — Construction Intelligence
    "Construction": {"division": "CHARLIE", "priority": "high"},
    "Roofing": {"division": "CHARLIE", "priority": "high"},
    "HomeImprovement": {"division": "CHARLIE", "priority": "medium"},
    "Contractors": {"division": "CHARLIE", "priority": "high"},
    "OSHA": {"division": "CHARLIE", "priority": "medium"},

    # DELTA — Municipal / Government
    "govfire": {"division": "DELTA", "priority": "high"},
    "publicadministration": {"division": "DELTA", "priority": "high"},
    "urbanplanning": {"division": "DELTA", "priority": "medium"},
    "GovTech": {"division": "DELTA", "priority": "high"},
    "LocalGovernment": {"division": "DELTA", "priority": "medium"},
}

# Rate limit: Reddit allows ~1 req/sec for unauthenticated
REQUEST_DELAY = 1.5  # seconds between subreddit fetches


def _post_id(text: str, author: str, timestamp: str) -> str:
    """Generate deterministic ID for a post to prevent duplicates."""
    raw = f"reddit:{author}:{timestamp}:{text[:100]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_ingest_state() -> dict:
    if INGEST_STATE.exists():
        return json.loads(INGEST_STATE.read_text(encoding="utf-8"))
    return {
        "last_ingest": None,
        "total_ingested": 0,
        "seen_ids": [],
        "subreddit_state": {},
    }


def _save_ingest_state(state: dict):
    state["seen_ids"] = state["seen_ids"][-10000:]  # Bound
    INGEST_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Reddit Public JSON API ────────────────────────────────────

def _fetch_subreddit(subreddit: str, sort: str = "hot", limit: int = 25) -> list[dict]:
    """Fetch posts from a subreddit using Reddit's public JSON endpoint."""
    import urllib.request
    import urllib.error

    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}&raw_json=1"
    headers = {
        "User-Agent": "NCL-Galactia/1.0 (intelligence pipeline; contact: admin@bitrage.labour)",
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            children = data.get("data", {}).get("children", [])
            return [c.get("data", {}) for c in children if c.get("kind") == "t3"]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  [REDDIT] Rate limited on r/{subreddit}. Backing off.")
            time.sleep(5)
        else:
            print(f"  [REDDIT] HTTP {e.code} on r/{subreddit}: {e.reason}")
        return []
    except Exception as e:
        print(f"  [REDDIT] Failed to fetch r/{subreddit}: {e}")
        return []


def ingest_feed(
    max_posts: int = 100,
    subreddits: dict | None = None,
    sort: str = "hot",
    per_sub_limit: int = 15,
) -> list[dict]:
    """Pull recent posts from configured subreddits.

    Args:
        max_posts: Maximum total posts to ingest across all subreddits.
        subreddits: Override subreddit config. Defaults to SUBREDDITS.
        sort: Reddit sort order (hot, new, rising, top).
        per_sub_limit: Max posts per subreddit fetch.

    Returns:
        List of normalized post dicts ready for truth scoring.
    """
    subs = subreddits or SUBREDDITS
    state = _load_ingest_state()
    seen = set(state.get("seen_ids", []))
    ingested = []

    print(f"[REDDIT PIPELINE] Scanning {len(subs)} subreddits ({sort})...")

    for sub_name, sub_config in subs.items():
        if len(ingested) >= max_posts:
            break

        division = sub_config.get("division", "ALPHA")
        priority = sub_config.get("priority", "medium")

        raw_posts = _fetch_subreddit(sub_name, sort=sort, limit=per_sub_limit)

        sub_count = 0
        for rp in raw_posts:
            if len(ingested) >= max_posts:
                break

            # Build text from title + selftext
            title = rp.get("title", "")
            selftext = rp.get("selftext", "")
            text = f"{title}\n\n{selftext}".strip() if selftext else title

            if not text or len(text) < 10:
                continue

            author = rp.get("author", "deleted")
            created = rp.get("created_utc", 0)
            ts_str = datetime.fromtimestamp(created, tz=timezone.utc).isoformat() if created else datetime.now(timezone.utc).isoformat()

            # Use Reddit's native ID for dedup
            reddit_id = rp.get("id", "")
            pid = f"reddit_{reddit_id}" if reddit_id else _post_id(text, author, ts_str)

            if pid in seen:
                continue

            record = _normalize_post(
                text=text,
                author=f"u/{author}",
                timestamp=ts_str,
                source=f"reddit:r/{sub_name}",
                post_id=pid,
                url=f"https://reddit.com{rp.get('permalink', '')}",
                metrics={
                    "score": rp.get("score", 0),
                    "upvote_ratio": rp.get("upvote_ratio", 0),
                    "num_comments": rp.get("num_comments", 0),
                    "awards": rp.get("total_awards_received", 0),
                },
                subreddit=sub_name,
                division=division,
                priority=priority,
                flair=rp.get("link_flair_text", ""),
                is_self=rp.get("is_self", True),
                domain=rp.get("domain", ""),
            )

            # Archive
            with open(FEED_ARCHIVE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            seen.add(pid)
            ingested.append(record)
            sub_count += 1

        if sub_count > 0:
            print(f"  r/{sub_name}: {sub_count} new posts [{division}]")

        # Update per-subreddit state
        state.setdefault("subreddit_state", {})[sub_name] = {
            "last_fetch": datetime.now(timezone.utc).isoformat(),
            "posts_fetched": len(raw_posts),
            "new_ingested": sub_count,
        }

        # Rate limit between subreddits
        if len(ingested) < max_posts:
            time.sleep(REQUEST_DELAY)

    # Update global state
    state["last_ingest"] = datetime.now(timezone.utc).isoformat()
    state["total_ingested"] = state.get("total_ingested", 0) + len(ingested)
    state["seen_ids"] = list(seen)
    _save_ingest_state(state)

    print(f"[REDDIT PIPELINE] Ingested {len(ingested)} new posts from {len(subs)} subreddits")
    return ingested


# ── Manual Ingestion ──────────────────────────────────────────

def ingest_manual(posts: list[dict]) -> list[dict]:
    """Ingest manually curated Reddit posts.

    Each post dict should have: text, author (optional), subreddit (optional)
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
        sub = post.get("subreddit", "unknown")
        pid = _post_id(text, author, ts)

        if pid in seen:
            continue

        record = _normalize_post(
            text=text,
            author=author,
            timestamp=ts,
            source=f"reddit:r/{sub}",
            post_id=pid,
            url=post.get("url", ""),
            subreddit=sub,
            division=post.get("division", "ALPHA"),
        )

        with open(FEED_ARCHIVE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        seen.add(pid)
        ingested.append(record)

    state["last_ingest"] = datetime.now(timezone.utc).isoformat()
    state["total_ingested"] = state.get("total_ingested", 0) + len(ingested)
    state["seen_ids"] = list(seen)
    _save_ingest_state(state)

    print(f"[REDDIT PIPELINE] Manually ingested {len(ingested)} posts")
    return ingested


# ── Normalization ─────────────────────────────────────────────

def _normalize_post(
    text: str,
    author: str,
    timestamp: str,
    source: str,
    post_id: str = "",
    url: str = "",
    metrics: dict | None = None,
    subreddit: str = "",
    division: str = "ALPHA",
    priority: str = "medium",
    flair: str = "",
    is_self: bool = True,
    domain: str = "",
    topic_hint: str = "",
    context: str = "",
) -> dict:
    """Normalize a Reddit post into Galactia's standard format."""
    # Extract URLs from text
    urls = re.findall(r'https?://\S+', text)

    # Extract hashtags (rare on Reddit but some posts have them)
    hashtags = re.findall(r'#(\w+)', text)

    # Extract mentions (u/username pattern)
    mentions = re.findall(r'u/(\w+)', text)

    # Clean text for analysis
    clean_text = re.sub(r'https?://\S+', '', text).strip()
    clean_text = re.sub(r'\s+', ' ', clean_text)
    # Truncate very long selftext posts
    if len(clean_text) > 2000:
        clean_text = clean_text[:2000] + "..."

    return {
        "id": post_id or _post_id(text, author, timestamp),
        "text": text[:3000],  # Bound raw text
        "clean_text": clean_text,
        "author": author,
        "timestamp": timestamp,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "platform": "reddit",
        "url": url,
        "urls_found": urls,
        "hashtags": hashtags,
        "mentions": mentions,
        "metrics": metrics or {},
        "subreddit": subreddit,
        "division": division,
        "priority": priority,
        "flair": flair,
        "is_self": is_self,
        "domain": domain,
        "topic_hint": topic_hint or flair,
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


# ── Feed Stats ────────────────────────────────────────────────

def feed_stats() -> dict:
    """Get Reddit ingestion statistics."""
    state = _load_ingest_state()
    archive_count = 0
    source_counts = {}
    if FEED_ARCHIVE.exists():
        with open(FEED_ARCHIVE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                archive_count += 1
                try:
                    post = json.loads(line)
                    sub = post.get("subreddit", "unknown")
                    source_counts[sub] = source_counts.get(sub, 0) + 1
                except json.JSONDecodeError:
                    pass

    return {
        "total_ingested": state.get("total_ingested", 0),
        "archive_count": archive_count,
        "last_ingest": state.get("last_ingest"),
        "seen_ids_count": len(state.get("seen_ids", [])),
        "subreddits_configured": len(SUBREDDITS),
        "subreddit_counts": source_counts,
        "subreddit_state": state.get("subreddit_state", {}),
    }


def get_unscored_posts(limit: int = 50) -> list[dict]:
    """Get Reddit posts that haven't been scored by the truth engine yet."""
    if not FEED_ARCHIVE.exists():
        return []

    unscored = []
    with open(FEED_ARCHIVE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                post = json.loads(line)
                if post.get("overall_score") is None:
                    unscored.append(post)
                    if len(unscored) >= limit:
                        break
            except json.JSONDecodeError:
                continue
    return unscored


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Reddit Pipeline — Feed ingestion for Galactia")
    parser.add_argument("--ingest", action="store_true", help="Ingest from Reddit")
    parser.add_argument("--sort", type=str, default="hot", choices=["hot", "new", "rising", "top"],
                        help="Reddit sort order")
    parser.add_argument("--stats", action="store_true", help="Show feed stats")
    parser.add_argument("--max", type=int, default=100, help="Max posts to ingest")
    parser.add_argument("--division", type=str, help="Only scan subreddits for this division")
    args = parser.parse_args()

    if args.stats:
        stats = feed_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")
    elif args.ingest:
        subs = SUBREDDITS
        if args.division:
            subs = {k: v for k, v in SUBREDDITS.items() if v["division"] == args.division.upper()}
        ingest_feed(max_posts=args.max, subreddits=subs, sort=args.sort)
    else:
        parser.print_help()
