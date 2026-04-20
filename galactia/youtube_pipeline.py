"""YouTube Pipeline — Video intelligence ingestion into NCL Galactia.

Monitors configured YouTube channels for new uploads and ingests video
metadata + descriptions into Galactia's knowledge store for truth-scoring,
correlation, and research.

Supports two modes:
  1. API mode: Uses YouTube Data API v3 (requires YOUTUBE_API_KEY)
  2. RSS mode: Uses YouTube's public RSS feeds (no auth, less data)

Channel config loaded from super_agency/youtube_intelligence_config.json.

Usage:
    from galactia.youtube_pipeline import ingest_feed, feed_stats
    results = ingest_feed(max_videos=50)
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

FEED_ARCHIVE = DATA_DIR / "youtube_feed_archive.jsonl"
INGEST_STATE = DATA_DIR / "youtube_ingest_state.json"
CONFIG_FILE = PROJECT_ROOT / "super_agency" / "youtube_intelligence_config.json"


def _load_channel_config() -> dict:
    """Load YouTube channel configuration."""
    if CONFIG_FILE.exists():
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        # Flatten nested channel structure
        channels = {}
        for category, category_channels in config.get("youtube_channels", {}).items():
            for key, ch in category_channels.items():
                channels[key] = {
                    "channel_id": ch.get("channel_id", ""),
                    "channel_name": ch.get("channel_name", key),
                    "description": ch.get("description", ""),
                    "priority": ch.get("priority", "medium"),
                    "category": category,
                }
        return channels
    # Fallback: key AI/tech channels
    return {
        "ai_explained": {"channel_id": "UCWN3xxRkmTPmbKwht9FuE5A", "channel_name": "AI Explained", "priority": "high", "category": "ai_tech_focus"},
        "fireship": {"channel_id": "UCsBjURrPoezykLs9EqgamOA", "channel_name": "Fireship", "priority": "high", "category": "ai_tech_focus"},
        "two_minute_papers": {"channel_id": "UCbfYPyITQ-7l4upoX8nvctg", "channel_name": "Two Minute Papers", "priority": "high", "category": "ai_tech_focus"},
    }


def _post_id(text: str, author: str, timestamp: str) -> str:
    """Generate deterministic ID for a video to prevent duplicates."""
    raw = f"youtube:{author}:{timestamp}:{text[:100]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_ingest_state() -> dict:
    if INGEST_STATE.exists():
        return json.loads(INGEST_STATE.read_text(encoding="utf-8"))
    return {
        "last_ingest": None,
        "total_ingested": 0,
        "seen_ids": [],
        "channel_state": {},
    }


def _save_ingest_state(state: dict):
    state["seen_ids"] = state["seen_ids"][-10000:]
    INGEST_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── YouTube Data API v3 ──────────────────────────────────────

def _fetch_channel_videos_api(channel_id: str, api_key: str, max_results: int = 10) -> list[dict]:
    """Fetch recent videos from a channel using YouTube Data API v3."""
    import urllib.request
    import urllib.error
    import urllib.parse

    # Search for recent uploads
    params = urllib.parse.urlencode({
        "part": "snippet",
        "channelId": channel_id,
        "maxResults": min(max_results, 50),
        "order": "date",
        "type": "video",
        "key": api_key,
    })
    url = f"https://www.googleapis.com/youtube/v3/search?{params}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("items", [])
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"  [YOUTUBE] API quota exceeded or invalid key for channel {channel_id}")
        else:
            print(f"  [YOUTUBE] HTTP {e.code} for channel {channel_id}: {e.reason}")
        return []
    except Exception as e:
        print(f"  [YOUTUBE] API failed for channel {channel_id}: {e}")
        return []


# ── YouTube RSS Feed (No Auth) ────────────────────────────────

def _fetch_channel_rss(channel_id: str) -> list[dict]:
    """Fetch recent videos using YouTube's public RSS feed (no API key needed)."""
    import urllib.request
    import xml.etree.ElementTree as ET

    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "NCL-Galactia/1.0",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8")

        root = ET.fromstring(xml_data)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "media": "http://search.yahoo.com/mrss/",
        }

        entries = root.findall("atom:entry", ns)
        videos = []
        for entry in entries:
            video_id_el = entry.find("yt:videoId", ns)
            title_el = entry.find("atom:title", ns)
            published_el = entry.find("atom:published", ns)
            author_el = entry.find("atom:author/atom:name", ns)
            media_desc = entry.find("media:group/media:description", ns)

            videos.append({
                "video_id": video_id_el.text if video_id_el is not None else "",
                "title": title_el.text if title_el is not None else "",
                "published": published_el.text if published_el is not None else "",
                "author": author_el.text if author_el is not None else "",
                "description": media_desc.text if media_desc is not None else "",
                "source": "rss",
            })
        return videos

    except Exception as e:
        print(f"  [YOUTUBE] RSS failed for channel {channel_id}: {e}")
        return []


# ── Main Ingestion ────────────────────────────────────────────

def ingest_feed(max_videos: int = 50, channels: dict | None = None) -> list[dict]:
    """Pull recent videos from configured YouTube channels.

    Uses API v3 if YOUTUBE_API_KEY is set, otherwise falls back to RSS.

    Args:
        max_videos: Maximum total videos to ingest.
        channels: Override channel config.

    Returns:
        List of normalized post dicts.
    """
    ch_config = channels or _load_channel_config()
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    use_api = bool(api_key)

    state = _load_ingest_state()
    seen = set(state.get("seen_ids", []))
    ingested = []

    mode = "API v3" if use_api else "RSS"
    print(f"[YOUTUBE PIPELINE] Scanning {len(ch_config)} channels via {mode}...")

    for ch_key, ch_info in ch_config.items():
        if len(ingested) >= max_videos:
            break

        channel_id = ch_info.get("channel_id", "")
        channel_name = ch_info.get("channel_name", ch_key)
        category = ch_info.get("category", "general")

        if not channel_id:
            continue

        # Fetch videos
        if use_api:
            raw_videos = _fetch_channel_videos_api(channel_id, api_key, max_results=10)
            videos = _normalize_api_results(raw_videos, channel_name, category)
        else:
            raw_videos = _fetch_channel_rss(channel_id)
            videos = _normalize_rss_results(raw_videos, category)

        ch_count = 0
        for video in videos:
            if len(ingested) >= max_videos:
                break

            vid_id = video.get("video_id", "")
            pid = f"yt_{vid_id}" if vid_id else _post_id(video["text"], video["author"], video["timestamp"])

            if pid in seen:
                continue

            record = _normalize_post(
                text=video["text"],
                author=video["author"],
                timestamp=video["timestamp"],
                source=f"youtube:{channel_name}",
                post_id=pid,
                url=f"https://youtube.com/watch?v={vid_id}" if vid_id else "",
                video_id=vid_id,
                channel_name=channel_name,
                channel_id=channel_id,
                category=category,
                description=video.get("description", ""),
            )

            with open(FEED_ARCHIVE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            seen.add(pid)
            ingested.append(record)
            ch_count += 1

        if ch_count > 0:
            print(f"  {channel_name}: {ch_count} new videos [{category}]")

        state.setdefault("channel_state", {})[ch_key] = {
            "last_fetch": datetime.now(timezone.utc).isoformat(),
            "videos_found": len(raw_videos),
            "new_ingested": ch_count,
        }

        # Rate limit
        if len(ingested) < max_videos:
            time.sleep(0.5 if use_api else 1.0)

    state["last_ingest"] = datetime.now(timezone.utc).isoformat()
    state["total_ingested"] = state.get("total_ingested", 0) + len(ingested)
    state["seen_ids"] = list(seen)
    _save_ingest_state(state)

    print(f"[YOUTUBE PIPELINE] Ingested {len(ingested)} new videos from {len(ch_config)} channels")
    return ingested


def _normalize_api_results(items: list[dict], channel_name: str, category: str) -> list[dict]:
    """Normalize YouTube API v3 search results."""
    videos = []
    for item in items:
        snippet = item.get("snippet", {})
        vid_id = item.get("id", {}).get("videoId", "")

        title = snippet.get("title", "")
        description = snippet.get("description", "")
        text = f"{title}\n\n{description}".strip()

        videos.append({
            "video_id": vid_id,
            "text": text,
            "author": channel_name,
            "timestamp": snippet.get("publishedAt", datetime.now(timezone.utc).isoformat()),
            "description": description,
            "category": category,
        })
    return videos


def _normalize_rss_results(items: list[dict], category: str) -> list[dict]:
    """Normalize YouTube RSS feed results."""
    videos = []
    for item in items:
        title = item.get("title", "")
        description = item.get("description", "")
        text = f"{title}\n\n{description}".strip() if description else title

        videos.append({
            "video_id": item.get("video_id", ""),
            "text": text,
            "author": item.get("author", "unknown"),
            "timestamp": item.get("published", datetime.now(timezone.utc).isoformat()),
            "description": description,
            "category": category,
        })
    return videos


# ── Normalization ─────────────────────────────────────────────

def _normalize_post(
    text: str,
    author: str,
    timestamp: str,
    source: str,
    post_id: str = "",
    url: str = "",
    video_id: str = "",
    channel_name: str = "",
    channel_id: str = "",
    category: str = "",
    description: str = "",
    topic_hint: str = "",
    context: str = "",
) -> dict:
    """Normalize a YouTube video into Galactia's standard format."""
    urls = re.findall(r'https?://\S+', text)
    hashtags = re.findall(r'#(\w+)', text)
    mentions = re.findall(r'@(\w+)', text)

    clean_text = re.sub(r'https?://\S+', '', text).strip()
    clean_text = re.sub(r'\s+', ' ', clean_text)
    if len(clean_text) > 2000:
        clean_text = clean_text[:2000] + "..."

    return {
        "id": post_id or _post_id(text, author, timestamp),
        "text": text[:3000],
        "clean_text": clean_text,
        "author": author,
        "timestamp": timestamp,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "platform": "youtube",
        "url": url,
        "urls_found": urls,
        "hashtags": hashtags,
        "mentions": mentions,
        "metrics": {},
        "video_id": video_id,
        "channel_name": channel_name,
        "channel_id": channel_id,
        "category": category,
        "topic_hint": topic_hint or category,
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
    """Get YouTube ingestion statistics."""
    state = _load_ingest_state()
    archive_count = 0
    channel_counts = {}
    if FEED_ARCHIVE.exists():
        with open(FEED_ARCHIVE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                archive_count += 1
                try:
                    post = json.loads(line)
                    ch = post.get("channel_name", "unknown")
                    channel_counts[ch] = channel_counts.get(ch, 0) + 1
                except json.JSONDecodeError:
                    pass

    return {
        "total_ingested": state.get("total_ingested", 0),
        "archive_count": archive_count,
        "last_ingest": state.get("last_ingest"),
        "seen_ids_count": len(state.get("seen_ids", [])),
        "channels_configured": len(_load_channel_config()),
        "channel_counts": channel_counts,
        "channel_state": state.get("channel_state", {}),
        "api_mode": bool(os.getenv("YOUTUBE_API_KEY", "")),
    }


def get_unscored_posts(limit: int = 50) -> list[dict]:
    """Get YouTube videos that haven't been scored yet."""
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
    parser = argparse.ArgumentParser(description="YouTube Pipeline — Video intelligence for Galactia")
    parser.add_argument("--ingest", action="store_true", help="Ingest from YouTube")
    parser.add_argument("--stats", action="store_true", help="Show feed stats")
    parser.add_argument("--max", type=int, default=50, help="Max videos to ingest")
    parser.add_argument("--category", type=str, help="Only scan channels in this category")
    args = parser.parse_args()

    if args.stats:
        stats = feed_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")
    elif args.ingest:
        ch = _load_channel_config()
        if args.category:
            ch = {k: v for k, v in ch.items() if v.get("category") == args.category}
        ingest_feed(max_videos=args.max, channels=ch)
    else:
        parser.print_help()
