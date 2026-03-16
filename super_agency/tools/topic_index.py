#!/usr/bin/env python3
"""
Second Brain Topic Index — keyword extraction + tagging for ingested content.

Scans knowledge/secondbrain/ for enriched content, extracts keywords and tags,
and builds a searchable JSON topic index at knowledge/secondbrain/topic_index.json.

Usage:
    python tools/topic_index.py             # rebuild index
    python tools/topic_index.py search AI   # search for keyword
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge" / "secondbrain"
INDEX_PATH = KNOWLEDGE_DIR / "topic_index.json"

# Common stop words to exclude from keyword extraction
_STOP_WORDS = frozenset(
    "the a an and or but in on at to for of is it this that with from by as be "
    "are was were been have has had do does did will would can could may might shall "
    "should not no so if its they them their he she we you i my your our than also "
    "very just about more most some any all each every".split())


def _extract_keywords(text: str, top_n: int = 15) -> list[str]:
    """Extract top keywords from text by frequency, excluding stop words."""
    words = re.findall(r"[a-z]{3,}", text.lower())
    filtered = [w for w in words if w not in _STOP_WORDS]
    return [word for word, _ in Counter(filtered).most_common(top_n)]


def _derive_tags(data: dict) -> list[str]:
    """Derive tags from enrichment data: key_insights, claims, action items."""
    tags = set()
    # Use existing enrichment fields
    for insight in data.get("key_insights", []):
        tags.update(re.findall(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", insight))
    for claim in data.get("claims", []):
        tags.update(re.findall(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", claim))
    # Also pull from abstract
    abstract = data.get("abstract_120w", "")
    tags.update(re.findall(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", abstract))
    return sorted(tags)


def build_index() -> dict:
    """Scan all enriched content and build a topic index."""
    entries: list[dict] = []
    keyword_map: dict[str, list[str]] = {}  # keyword -> list of video_ids

    if not KNOWLEDGE_DIR.exists():
        return {"entries": [], "keywords": {}, "built_at": datetime.now().isoformat()}

    for year_dir in sorted(KNOWLEDGE_DIR.iterdir()):
        if not year_dir.is_dir() or year_dir.name.startswith("."):
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            for vid_dir in sorted(month_dir.iterdir()):
                if not vid_dir.is_dir():
                    continue
                enrich_file = vid_dir / "enrich.json"
                if not enrich_file.exists():
                    continue
                try:
                    data = json.loads(enrich_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue

                vid = vid_dir.name
                abstract = data.get("abstract_120w", "")
                keywords = _extract_keywords(abstract)
                tags = _derive_tags(data)

                entry = {
                    "video_id": vid,
                    "year": year_dir.name,
                    "month": month_dir.name,
                    "abstract": abstract[:300],
                    "keywords": keywords,
                    "tags": tags,
                    "confidence": data.get("confidence", "unknown"),
                }
                entries.append(entry)

                for kw in keywords:
                    keyword_map.setdefault(kw, []).append(vid)

    index = {
        "entries": entries,
        "keywords": keyword_map,
        "total_entries": len(entries),
        "total_keywords": len(keyword_map),
        "built_at": datetime.now().isoformat(),
    }

    # Persist index
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def search(query: str) -> list[dict]:
    """Search the topic index for a query term. Returns matching entries."""
    if not INDEX_PATH.exists():
        build_index()
    if not INDEX_PATH.exists():
        return []

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    q = query.lower()
    results = []
    for entry in index.get("entries", []):
        # Match against keywords, tags, abstract
        if (
            q in entry.get("keywords", [])
            or any(q in t.lower() for t in entry.get("tags", []))
            or q in entry.get("abstract", "").lower()
        ):
            results.append(entry)
    return results


def get_index() -> dict:
    """Load existing index or build it."""
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return build_index()


if __name__ == "__main__":
    import sys as _sys

    if len(_sys.argv) > 1 and _sys.argv[1] == "search":
        q = " ".join(_sys.argv[2:])
        hits = search(q)
        print(f"Found {len(hits)} result(s) for '{q}':")
        for h in hits:
            print(f"  [{h['video_id']}] {h['abstract'][:80]}...")
    else:
        idx = build_index()
        print(
            f"Built topic index: {idx['total_entries']} entries, {idx['total_keywords']} keywords")
        print(f"Saved to {INDEX_PATH}")
