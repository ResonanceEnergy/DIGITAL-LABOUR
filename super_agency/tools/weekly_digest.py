#!/usr/bin/env python3
"""
Weekly Intelligence Digest.

Aggregates ingested Second Brain content and topic index
into a formatted weekly digest report (Markdown) suitable
for the daily brief or standalone reading.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SECONDBRAIN_DIR = ROOT / "knowledge" / "secondbrain"
TOPIC_INDEX = SECONDBRAIN_DIR / "topic_index.json"
REPORTS_DIR = ROOT / "reports"


def _load_topic_index() -> dict[str, Any]:
    if TOPIC_INDEX.exists():
        try:
            return json.loads(
                TOPIC_INDEX.read_text(encoding="utf-8"),
            )
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _recent_entries(days: int = 7) -> list[dict]:
    """Return Second Brain entries ingested within the last N days."""
    cutoff = datetime.now() - timedelta(days=days)
    entries = []
    for f in sorted(SECONDBRAIN_DIR.glob("*.json")):
        if f.name in ("topic_index.json", "pending.json"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            ts = data.get("ingested_at") or data.get("timestamp")
            if ts:
                dt = datetime.fromisoformat(ts)
                if dt >= cutoff:
                    data["_file"] = f.name
                    entries.append(data)
        except Exception:
            continue
    return entries


def generate_digest(days: int = 7) -> str:
    """Generate a Markdown intelligence digest for the last N days."""
    entries = _recent_entries(days)
    topic_index = _load_topic_index()
    now = datetime.now()

    lines = [
        "# Weekly Intelligence Digest",
        (
            f"*Generated {now.strftime('%Y-%m-%d %H:%M')}"
            f" \u2014 covering last {days} days*\n"
        ),
    ]

    # Summary stats
    lines.append("## Summary")
    lines.append(f"- **Sources ingested:** {len(entries)}")
    lines.append(f"- **Topics indexed:** {len(topic_index)}")

    # Top topics by frequency
    if topic_index:
        topic_counts: Counter[str] = Counter()
        for topic, refs in topic_index.items():
            if isinstance(refs, list):
                topic_counts[topic] = len(refs)
            else:
                topic_counts[topic] = 1
        top = topic_counts.most_common(10)
        lines.append("\n## Trending Topics")
        for topic, count in top:
            lines.append(f"- **{topic}** ({count} sources)")

    # Recent entries
    if entries:
        lines.append("\n## Recent Ingestions")
        for e in entries[-20:]:
            title = e.get("title", e.get("_file", "untitled"))
            url = e.get("url", "")
            ts = e.get("ingested_at", e.get("timestamp", ""))
            summary = e.get("summary", "")[:200]
            lines.append(f"\n### {title}")
            if url:
                lines.append(f"- URL: {url}")
            if ts:
                lines.append(f"- Ingested: {ts}")
            if summary:
                lines.append(f"- {summary}...")
    else:
        lines.append(f"\n*No new content ingested in the last {days} days.*")

    # Cross-reference insights
    if len(entries) >= 2:
        lines.append("\n## Cross-Reference Opportunities")
        lines.append(
            "- Review trending topics above for"
            " patterns across multiple sources",
        )
        lines.append(
            "- Topics appearing in 3+ sources"
            " may indicate emerging trends",
        )

    return "\n".join(lines) + "\n"


def save_digest(days: int = 7) -> str:
    """Generate and save the digest to reports/."""
    digest = generate_digest(days)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"intelligence_digest_{datetime.now().strftime('%Y%m%d')}.md"
    path = REPORTS_DIR / filename
    path.write_text(digest, encoding="utf-8")
    print(f"[OK] Digest saved to {path}")
    return str(path)


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    if "--save" in sys.argv:
        save_digest(days)
    else:
        print(generate_digest(days))
