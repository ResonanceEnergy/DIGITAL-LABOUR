"""Knowledge Store & Correlation Engine — Galactia's memory cortex.

This is the core of NCL Galactia — the functioning memory. It:
  1. Stores all scored knowledge in topic-grouped clusters
  2. Finds correlations between high-scored content across topics
  3. Identifies convergence patterns (multiple credible sources saying similar things)
  4. Maintains a ranked knowledge graph that evolves with every ingestion
  5. Surfaces research-worthy correlations for the Research Generator

Usage:
    from galactia.knowledge_store import store_scored, find_correlations, get_knowledge_graph
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

KNOWLEDGE_DB = DATA_DIR / "knowledge_graph.json"
CLUSTERS_DIR = DATA_DIR / "clusters"
CLUSTERS_DIR.mkdir(parents=True, exist_ok=True)
CORRELATIONS_DB = DATA_DIR / "correlations.jsonl"


# ── Knowledge Graph ────────────────────────────────────────────

def _load_graph() -> dict:
    """Load the knowledge graph."""
    if KNOWLEDGE_DB.exists():
        return json.loads(KNOWLEDGE_DB.read_text(encoding="utf-8"))
    return {
        "version": 1,
        "created": datetime.now(timezone.utc).isoformat(),
        "last_updated": None,
        "topics": {},        # topic -> {score, count, posts, claims}
        "claims": {},        # claim_hash -> {text, score, sources, corroborations}
        "correlations": [],  # list of correlation events
        "stats": {"total_posts": 0, "total_topics": 0, "total_correlations": 0},
    }


def _save_graph(graph: dict):
    graph["last_updated"] = datetime.now(timezone.utc).isoformat()
    KNOWLEDGE_DB.write_text(json.dumps(graph, indent=2), encoding="utf-8")


def _claim_hash(claim: str) -> str:
    """Short deterministic hash for a claim."""
    import hashlib
    return hashlib.sha256(claim.lower().strip().encode()).hexdigest()[:12]


# ── Store Scored Content ───────────────────────────────────────

def store_scored(scored_posts: list[dict]):
    """Ingest scored posts into the knowledge graph and topic clusters."""
    graph = _load_graph()

    for post in scored_posts:
        post_id = post.get("id", "")
        overall = post.get("overall_score", 0)
        topics = post.get("topics", [])
        claims = post.get("key_claims", [])
        text = post.get("clean_text") or post.get("text", "")

        # Only store content above noise threshold (score >= 30)
        if overall < 30:
            continue

        # Update topic clusters
        for topic in topics:
            topic_key = topic.lower().strip()
            if topic_key not in graph["topics"]:
                graph["topics"][topic_key] = {
                    "name": topic,
                    "avg_score": overall,
                    "count": 0,
                    "post_ids": [],
                    "top_claims": [],
                    "first_seen": datetime.now(timezone.utc).isoformat(),
                    "last_updated": None,
                }
            entry = graph["topics"][topic_key]
            entry["count"] += 1
            # Rolling average
            entry["avg_score"] = round(
                (entry["avg_score"] * (entry["count"] - 1) + overall) / entry["count"], 1
            )
            entry["post_ids"].append(post_id)
            entry["post_ids"] = entry["post_ids"][-200:]  # Bound
            entry["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Store in topic cluster file
            _append_to_cluster(topic_key, post)

        # Track claims
        for claim_text in claims:
            ch = _claim_hash(claim_text)
            if ch not in graph["claims"]:
                graph["claims"][ch] = {
                    "text": claim_text,
                    "avg_score": overall,
                    "source_count": 0,
                    "post_ids": [],
                    "topics": [],
                    "first_seen": datetime.now(timezone.utc).isoformat(),
                }
            claim_entry = graph["claims"][ch]
            claim_entry["source_count"] += 1
            claim_entry["avg_score"] = round(
                (claim_entry["avg_score"] * (claim_entry["source_count"] - 1) + overall) / claim_entry["source_count"], 1
            )
            claim_entry["post_ids"].append(post_id)
            claim_entry["post_ids"] = claim_entry["post_ids"][-100:]
            for t in topics:
                if t.lower() not in claim_entry["topics"]:
                    claim_entry["topics"].append(t.lower())

            # Also add to topic's top claims
            for topic in topics:
                topic_key = topic.lower().strip()
                if topic_key in graph["topics"]:
                    top_claims = graph["topics"][topic_key]["top_claims"]
                    if claim_text not in top_claims:
                        top_claims.append(claim_text)
                        graph["topics"][topic_key]["top_claims"] = top_claims[-20:]

        graph["stats"]["total_posts"] += 1

    graph["stats"]["total_topics"] = len(graph["topics"])
    _save_graph(graph)
    print(f"[KNOWLEDGE] Stored {len(scored_posts)} posts across {len(graph['topics'])} topics")


def _append_to_cluster(topic_key: str, post: dict):
    """Append a post to a topic cluster file."""
    safe_name = re.sub(r'[^\w\-]', '_', topic_key)[:50]
    cluster_file = CLUSTERS_DIR / f"cluster_{safe_name}.jsonl"
    with open(cluster_file, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "id": post.get("id"),
            "text": post.get("clean_text") or post.get("text", ""),
            "author": post.get("author"),
            "overall_score": post.get("overall_score"),
            "truth_score": post.get("truth_score"),
            "topics": post.get("topics", []),
            "key_claims": post.get("key_claims", []),
            "timestamp": post.get("timestamp"),
        }) + "\n")


# ── Correlation Engine ─────────────────────────────────────────

CORRELATION_PROMPT = """You are the CORRELATION ENGINE for NCL Galactia — the functioning memory of NCC.

Given a set of topic clusters with their scored claims, identify MEANINGFUL CORRELATIONS
between different topics. A correlation exists when:

1. Multiple credible sources (score >= 70) from DIFFERENT topics reference related phenomena
2. Claims in one topic logically imply or reinforce claims in another
3. Patterns emerge that no single topic reveals alone
4. Temporal convergence — multiple topics surging at the same time
5. Cross-domain evidence — a claim in physics corroborates a claim in economics, etc.

IMPORTANT: Only flag correlations that are GENUINELY significant. Not everything is connected.
Low-confidence correlations waste resources.

For each correlation found, specify:
- The topics involved
- The specific claims that correlate
- WHY this correlation matters
- A RESEARCH_WORTHY score (0-100): would a deep investigation yield valuable new knowledge?
- A suggested research direction

Output ONLY valid JSON:
{
    "correlations": [
        {
            "id": "<short unique id>",
            "topics": ["topic1", "topic2"],
            "claims": ["related claim from topic1", "related claim from topic2"],
            "explanation": "<why this correlation matters>",
            "research_worthy": <0-100>,
            "research_direction": "<what should be investigated>",
            "confidence": "<HIGH|MEDIUM|LOW>"
        }
    ],
    "meta": {
        "topics_analyzed": <int>,
        "correlations_found": <int>,
        "strongest_signal": "<brief description>"
    }
}
"""


def find_correlations(min_topic_score: int = 50, min_posts: int = 2) -> list[dict]:
    """Analyze the knowledge graph for cross-topic correlations."""
    graph = _load_graph()
    topics = graph.get("topics", {})

    # Filter to topics with enough data and quality
    eligible = {
        k: v for k, v in topics.items()
        if v["count"] >= min_posts and v["avg_score"] >= min_topic_score
    }

    if len(eligible) < 2:
        print("[CORRELATION] Not enough eligible topics for correlation analysis.")
        return []

    # Build context for LLM
    topic_summaries = []
    for key, topic in eligible.items():
        claims = topic.get("top_claims", [])[:5]
        topic_summaries.append({
            "topic": topic["name"],
            "avg_score": topic["avg_score"],
            "post_count": topic["count"],
            "top_claims": claims,
        })

    user_msg = f"""Analyze these {len(topic_summaries)} knowledge clusters for meaningful correlations:

{json.dumps(topic_summaries, indent=2)}

Find cross-topic correlations where credible claims in different domains reinforce each other.
Only flag correlations that would yield genuine insight if researched deeper.
"""

    print(f"[CORRELATION] Analyzing {len(eligible)} topics for cross-correlations...")

    try:
        raw = call_llm(
            system_prompt=CORRELATION_PROMPT,
            user_message=user_msg,
            json_mode=True,
            temperature=0.4,
        )
        result = json.loads(raw)
        correlations = result.get("correlations", [])

        # Filter to research-worthy
        worthy = [c for c in correlations if c.get("research_worthy", 0) >= 60]

        # Persist
        for corr in worthy:
            corr["found_at"] = datetime.now(timezone.utc).isoformat()
            corr["status"] = "pending"
            with open(CORRELATIONS_DB, "a", encoding="utf-8") as f:
                f.write(json.dumps(corr) + "\n")

        # Update graph
        graph["correlations"].extend(worthy)
        graph["correlations"] = graph["correlations"][-200:]  # Bound
        graph["stats"]["total_correlations"] += len(worthy)
        _save_graph(graph)

        if worthy:
            print(f"[CORRELATION] Found {len(worthy)} research-worthy correlations:")
            for c in worthy:
                print(f"  [{c.get('research_worthy', 0)}] {' <-> '.join(c.get('topics', []))}: {c.get('explanation', '')[:80]}")
        else:
            print("[CORRELATION] No research-worthy correlations found this cycle.")

        return worthy

    except Exception as e:
        print(f"[CORRELATION] Analysis failed: {e}")
        return []


# ── Queries ────────────────────────────────────────────────────

def get_knowledge_graph() -> dict:
    """Get the full knowledge graph."""
    return _load_graph()


def get_top_topics(limit: int = 20) -> list[dict]:
    """Get highest-scoring topics."""
    graph = _load_graph()
    topics = list(graph.get("topics", {}).values())
    topics.sort(key=lambda x: x["avg_score"], reverse=True)
    return topics[:limit]


def get_topic_detail(topic: str) -> dict | None:
    """Get detailed info about a specific topic."""
    graph = _load_graph()
    return graph.get("topics", {}).get(topic.lower().strip())


def get_pending_correlations() -> list[dict]:
    """Get correlations pending research project creation."""
    if not CORRELATIONS_DB.exists():
        return []
    pending = []
    with open(CORRELATIONS_DB, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            corr = json.loads(line)
            if corr.get("status") == "pending":
                pending.append(corr)
    return pending


def knowledge_stats() -> dict:
    """Get knowledge store statistics."""
    graph = _load_graph()
    stats = graph.get("stats", {})

    # Topic distribution
    topics = graph.get("topics", {})
    if topics:
        scores = [t["avg_score"] for t in topics.values()]
        stats["avg_topic_score"] = round(sum(scores) / len(scores), 1)
        stats["highest_topic"] = max(topics.items(), key=lambda x: x[1]["avg_score"])[1]["name"] if topics else None
        stats["most_active_topic"] = max(topics.items(), key=lambda x: x[1]["count"])[1]["name"] if topics else None

    # Claims
    claims = graph.get("claims", {})
    stats["total_claims"] = len(claims)
    multi_source = [c for c in claims.values() if c["source_count"] >= 2]
    stats["multi_source_claims"] = len(multi_source)

    return stats
