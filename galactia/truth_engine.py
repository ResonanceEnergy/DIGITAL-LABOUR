"""Truth & Credibility Engine — LLM-powered scoring for Galactia.

Every piece of content that enters Galactia gets scored on three axes:
  - TRUTH (0-100): Factual accuracy, verifiability, logical consistency
  - CREDIBILITY (0-100): Source reliability, track record, expertise
  - ACCOUNTABILITY (0-100): Transparency, willingness to be proven wrong, sourcing

The combined OVERALL score establishes a baseline of truth that NCL uses
to weight knowledge in its memory and decide what warrants deeper research.

Usage:
    from galactia.truth_engine import score_post, score_batch
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm

DATA_DIR = Path(__file__).parent / "data"
SCORES_DB = DATA_DIR / "scored_posts.jsonl"
FEED_ARCHIVE = DATA_DIR / "x_feed_archive.jsonl"

TRUTH_SYSTEM = """You are VERITAS — the truth-scoring engine for NCL Galactia, the functioning memory
of Natrix Command & Control (NCC). Your job is to evaluate content for truth, credibility,
and accountability so NCL can build a reliable knowledge base.

You score every post/claim on THREE axes (0-100 each):

1. TRUTH SCORE (0-100):
   - 90-100: Verifiable fact with clear evidence, established science, or mathematical certainty
   - 70-89: Strong evidence, multiple sources, widely accepted, testable
   - 50-69: Plausible but unverified, single source, requires more evidence
   - 30-49: Speculative, anecdotal, could go either way
   - 10-29: Unlikely, contradicts established evidence, logical fallacies present
   - 0-9: Demonstrably false, debunked, or pure fabrication

2. CREDIBILITY SCORE (0-100):
   - Based on: author expertise, source quality, track record, peer review status
   - 90+: Peer-reviewed research, established expert in field
   - 70-89: Credible journalist/analyst, reputable institution
   - 50-69: Industry insider, mixed track record
   - 30-49: Anonymous source, unverified credentials
   - 0-29: Known bad actor, propaganda source, bot-like behavior

3. ACCOUNTABILITY SCORE (0-100):
   - Based on: transparency about sources, willingness to be corrected, cites evidence
   - 90+: Full citations, open methodology, invites scrutiny
   - 70-89: Some sourcing, generally transparent
   - 50-69: Opinion stated as opinion, some hedging
   - 30-49: No sources, claims presented as absolute
   - 0-29: Deliberately misleading framing, refuses correction

Also extract:
- TOPICS: Key topics/themes (list of strings)
- KEY_CLAIMS: Specific falsifiable claims made (list of strings)
- REASONING: 2-3 sentence explanation of your scoring

Output ONLY valid JSON:
{
    "truth_score": <int 0-100>,
    "credibility_score": <int 0-100>,
    "accountability_score": <int 0-100>,
    "overall_score": <int 0-100>,
    "topics": ["topic1", "topic2"],
    "key_claims": ["claim1", "claim2"],
    "reasoning": "<explanation>",
    "confidence": "<HIGH|MEDIUM|LOW>"
}

The OVERALL score is your weighted assessment: truth*0.5 + credibility*0.3 + accountability*0.2

Be rigorous but fair. Do not penalize unconventional ideas — penalize lack of evidence.
A wild theory with transparent reasoning scores higher than a mainstream claim with no sources.
"""


def score_post(post: dict, provider: str | None = None) -> dict:
    """Score a single post for truth, credibility, and accountability."""
    text = post.get("clean_text") or post.get("text", "")
    author = post.get("author", "unknown")
    context = post.get("context", "")
    topic_hint = post.get("topic_hint", "")

    user_msg = f"""Score this content for truth, credibility, and accountability:

AUTHOR: {author}
CONTENT: {text}
"""
    if context:
        user_msg += f"ADDITIONAL CONTEXT: {context}\n"
    if topic_hint:
        user_msg += f"TOPIC HINT: {topic_hint}\n"
    if post.get("metrics"):
        m = post["metrics"]
        user_msg += f"ENGAGEMENT: {m.get('like_count', 0)} likes, {m.get('retweet_count', 0)} RTs, {m.get('reply_count', 0)} replies\n"

    try:
        raw = call_llm(
            system_prompt=TRUTH_SYSTEM,
            user_message=user_msg,
            provider=provider,
            json_mode=True,
            temperature=0.3,
        )

        scores = json.loads(raw)

        # Validate scores are in range
        for key in ["truth_score", "credibility_score", "accountability_score", "overall_score"]:
            val = scores.get(key, 50)
            scores[key] = max(0, min(100, int(val)))

        # Recalculate overall to ensure consistency
        scores["overall_score"] = round(
            scores["truth_score"] * 0.5 +
            scores["credibility_score"] * 0.3 +
            scores["accountability_score"] * 0.2
        )

        scores["scored_at"] = datetime.now(timezone.utc).isoformat()
        scores["post_id"] = post.get("id", "")

        return scores

    except json.JSONDecodeError as e:
        return _fallback_score(post, f"JSON parse error: {e}")
    except Exception as e:
        return _fallback_score(post, str(e))


def _fallback_score(post: dict, error: str) -> dict:
    """Return a neutral score when LLM scoring fails."""
    return {
        "truth_score": 50,
        "credibility_score": 50,
        "accountability_score": 50,
        "overall_score": 50,
        "topics": [],
        "key_claims": [],
        "reasoning": f"Scoring failed: {error}. Defaulting to neutral.",
        "confidence": "LOW",
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "post_id": post.get("id", ""),
        "error": error,
    }


def score_batch(posts: list[dict], provider: str | None = None) -> list[dict]:
    """Score a batch of posts. Returns scored results."""
    import time

    results = []
    for i, post in enumerate(posts, 1):
        print(f"  [SCORING {i}/{len(posts)}] {post.get('clean_text', post.get('text', ''))[:60]}...")
        scores = score_post(post, provider=provider)
        result = {**post, **scores}
        results.append(result)

        # Persist to scored DB
        with open(SCORES_DB, "a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")

        # Update archive with scores
        _update_archive_scores(post.get("id", ""), scores)

        if i < len(posts):
            time.sleep(2)  # Rate limit

    # Summary
    if results:
        avg_truth = sum(r["truth_score"] for r in results) / len(results)
        avg_cred = sum(r["credibility_score"] for r in results) / len(results)
        avg_overall = sum(r["overall_score"] for r in results) / len(results)
        print(f"\n  [BATCH COMPLETE] {len(results)} posts scored")
        print(f"  Avg Truth: {avg_truth:.1f} | Avg Credibility: {avg_cred:.1f} | Avg Overall: {avg_overall:.1f}")

    return results


def _update_archive_scores(post_id: str, scores: dict):
    """Update the feed archive with scores for a specific post."""
    if not FEED_ARCHIVE.exists() or not post_id:
        return

    lines = FEED_ARCHIVE.read_text(encoding="utf-8").strip().split("\n")
    updated = False
    new_lines = []

    for line in lines:
        if not line.strip():
            continue
        post = json.loads(line)
        if post.get("id") == post_id:
            post["truth_score"] = scores.get("truth_score")
            post["credibility_score"] = scores.get("credibility_score")
            post["accountability_score"] = scores.get("accountability_score")
            post["overall_score"] = scores.get("overall_score")
            post["topics"] = scores.get("topics", [])
            updated = True
        new_lines.append(json.dumps(post))

    if updated:
        FEED_ARCHIVE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


# ── Score Queries ──────────────────────────────────────────────

def get_high_scored(min_score: int = 70, limit: int = 50) -> list[dict]:
    """Get posts scoring above threshold — candidates for correlation."""
    if not SCORES_DB.exists():
        return []

    results = []
    with open(SCORES_DB, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            post = json.loads(line)
            if post.get("overall_score", 0) >= min_score:
                results.append(post)

    results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    return results[:limit]


def get_scored_by_topic(topic: str, limit: int = 50) -> list[dict]:
    """Get scored posts matching a topic."""
    if not SCORES_DB.exists():
        return []

    topic_lower = topic.lower()
    results = []
    with open(SCORES_DB, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            post = json.loads(line)
            post_topics = [t.lower() for t in post.get("topics", [])]
            if any(topic_lower in t for t in post_topics):
                results.append(post)

    results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    return results[:limit]


def scoring_stats() -> dict:
    """Get truth engine statistics."""
    if not SCORES_DB.exists():
        return {"total_scored": 0}

    total = 0
    sum_truth = 0
    sum_cred = 0
    sum_overall = 0
    high_count = 0
    low_count = 0
    topic_counts: dict[str, int] = {}

    with open(SCORES_DB, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            post = json.loads(line)
            total += 1
            sum_truth += post.get("truth_score", 0)
            sum_cred += post.get("credibility_score", 0)
            sum_overall += post.get("overall_score", 0)
            if post.get("overall_score", 0) >= 70:
                high_count += 1
            if post.get("overall_score", 0) < 30:
                low_count += 1
            for t in post.get("topics", []):
                topic_counts[t] = topic_counts.get(t, 0) + 1

    if total == 0:
        return {"total_scored": 0}

    # Top topics
    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:15]

    return {
        "total_scored": total,
        "avg_truth": round(sum_truth / total, 1),
        "avg_credibility": round(sum_cred / total, 1),
        "avg_overall": round(sum_overall / total, 1),
        "high_score_count": high_count,
        "low_score_count": low_count,
        "top_topics": dict(top_topics),
    }
