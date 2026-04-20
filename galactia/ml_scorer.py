"""ML Scorer — Statistical intelligence layer for Galactia.

Wraps the ML Intelligence Framework (anomaly detection, trend forecasting,
TF-IDF keyword extraction) into a Galactia-compatible scoring pass that runs
alongside VERITAS truth scoring. Zero external deps — pure Python stats.

Phase 2b in the unified pipeline:
  2a: VERITAS (LLM truth scoring)
  2b: ML Scorer (statistical anomaly + trend + keyword analysis)  <-- this
  2c: Context Governor (freshness + TTL cleanup)

Usage:
    from galactia.ml_scorer import score_ml_batch, get_ml_insights, ml_stats
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from super_agency.tools.ml_intelligence_framework import (
    AnomalyDetector,
    TrendForecaster,
    TextIntelligence,
    KMeansCluster,
)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ML_STATE_FILE = DATA_DIR / "ml_state.json"
ML_INSIGHTS_FILE = DATA_DIR / "ml_insights.json"

# ── Persistent State ──────────────────────────────────────────

# Detectors keyed by source pipeline
_anomaly_detectors: dict[str, AnomalyDetector] = {}
_trend_forecasters: dict[str, TrendForecaster] = {}
_text_intel = TextIntelligence()
_doc_map: dict[int, str] = {}  # doc_id -> post_id


def _get_detector(source: str) -> AnomalyDetector:
    if source not in _anomaly_detectors:
        _anomaly_detectors[source] = AnomalyDetector(window=100, z_threshold=2.0)
    return _anomaly_detectors[source]


def _get_forecaster(source: str) -> TrendForecaster:
    if source not in _trend_forecasters:
        _trend_forecasters[source] = TrendForecaster(alpha=0.3, beta=0.1)
    return _trend_forecasters[source]


# ── ML Scoring ────────────────────────────────────────────────

def score_ml_batch(posts: list[dict]) -> list[dict]:
    """Run ML analysis on a batch of posts. Adds ml_* fields to each post.

    For each post, computes:
      - ml_anomaly_score (0-1): How unusual is the engagement relative to its source?
      - ml_trend_direction: Is this source trending up/down/flat?
      - ml_keywords: Top TF-IDF keywords extracted from content
      - ml_novelty_score (0-100): Combined novelty metric for Galactia weighting

    Returns the same posts list with ml_ fields added.
    """
    if not posts:
        return []

    results = []
    source_volumes: dict[str, int] = Counter()

    for post in posts:
        source = post.get("platform", "unknown")
        text = post.get("clean_text") or post.get("text", "")
        post_id = post.get("id", "")

        # 1. Anomaly detection on engagement metrics
        metrics = post.get("metrics", {})
        engagement = _extract_engagement(metrics)
        detector = _get_detector(source)
        anomaly_score = detector.score(engagement) if engagement > 0 else 0.0

        # 2. Trend forecasting per source
        forecaster = _get_forecaster(source)
        forecaster.update(engagement)
        trend_dir = forecaster.direction()
        forecast = forecaster.forecast(horizon=3)

        # 3. TF-IDF keyword extraction
        keywords = []
        if text and len(text) > 20:
            doc_id = _text_intel.add_document(text)
            _doc_map[doc_id] = post_id
            kw_list = _text_intel.keywords(doc_id, top_n=8)
            keywords = [{"word": w, "score": round(s, 3)} for w, s in kw_list]

        # 4. Composite novelty score (0-100)
        # Anomaly high = novel, trend divergence = interesting
        novelty = min(100, round(
            anomaly_score * 60 +                          # anomaly contributes 60%
            (20 if trend_dir == "up" else 5) +            # trending up adds novelty
            min(20, len(keywords) * 3)                    # keyword diversity adds novelty
        ))

        # Attach to post
        post["ml_anomaly_score"] = round(anomaly_score, 4)
        post["ml_trend_direction"] = trend_dir
        post["ml_trend_forecast"] = forecast
        post["ml_keywords"] = keywords
        post["ml_novelty_score"] = novelty
        post["ml_scored_at"] = datetime.now(timezone.utc).isoformat()

        source_volumes[source] = source_volumes.get(source, 0) + 1
        results.append(post)

    # Save state
    _save_ml_state(source_volumes)

    print(f"  [ML SCORER] {len(results)} posts analyzed — "
          f"avg novelty: {sum(p.get('ml_novelty_score', 0) for p in results) / max(len(results), 1):.0f}")

    return results


def _extract_engagement(metrics: dict) -> float:
    """Extract a single engagement number from platform-specific metrics."""
    # Reddit
    if "score" in metrics:
        return float(metrics["score"])
    # YouTube
    if "view_count" in metrics:
        return float(metrics.get("view_count", 0))
    # X/Twitter
    if "like_count" in metrics:
        return float(
            metrics.get("like_count", 0) +
            metrics.get("retweet_count", 0) * 2 +
            metrics.get("reply_count", 0) * 3
        )
    # Fallback
    return sum(float(v) for v in metrics.values() if isinstance(v, (int, float)))


# ── Insights ──────────────────────────────────────────────────

def get_ml_insights() -> dict:
    """Get current ML intelligence insights — anomalies, trends, keywords."""
    insights = {
        "anomalies": {},
        "trends": {},
        "top_keywords": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Anomalies per source
    for source, detector in _anomaly_detectors.items():
        alerts = detector.recent_alerts(n=10)
        insights["anomalies"][source] = {
            "recent_alerts": len(alerts),
            "alerts": alerts[-5:],
        }

    # Trends per source
    for source, forecaster in _trend_forecasters.items():
        insights["trends"][source] = {
            "direction": forecaster.direction(),
            "forecast": forecaster.forecast(horizon=5),
            "data_points": forecaster._n,
        }

    # Global top keywords across all documents
    if _text_intel._docs:
        global_tf: Counter = Counter()
        for doc_tokens in _text_intel._docs:
            global_tf.update(doc_tokens)
        top = global_tf.most_common(30)
        insights["top_keywords"] = [{"word": w, "count": c} for w, c in top]

    # Persist
    try:
        ML_INSIGHTS_FILE.write_text(json.dumps(insights, indent=2), encoding="utf-8")
    except Exception:
        pass

    return insights


def find_similar_posts(post_id: str, top_n: int = 5) -> list[dict]:
    """Find posts with similar content using TF-IDF cosine similarity."""
    target_doc = None
    for did, pid in _doc_map.items():
        if pid == post_id:
            target_doc = did
            break
    if target_doc is None:
        return []

    similar = _text_intel.similar_docs(target_doc, top_n=top_n)
    results = []
    for doc_id, sim_score in similar:
        results.append({
            "post_id": _doc_map.get(doc_id, "unknown"),
            "similarity": sim_score,
        })
    return results


def cluster_posts(posts: list[dict], k: int = 5) -> dict:
    """Cluster posts by engagement + score features using k-means."""
    if len(posts) < k:
        return {"clusters": [], "note": "not enough posts to cluster"}

    # Build feature vectors: [overall_score, ml_novelty_score, engagement]
    vectors = []
    valid_posts = []
    for p in posts:
        overall = p.get("overall_score") or 50
        novelty = p.get("ml_novelty_score") or 0
        engagement = _extract_engagement(p.get("metrics", {}))
        vectors.append([overall, novelty, min(engagement, 10000)])
        valid_posts.append(p)

    if not vectors:
        return {"clusters": [], "note": "no valid vectors"}

    km = KMeansCluster(k=min(k, len(vectors)))
    labels = km.fit(vectors)

    clusters: dict[int, list] = defaultdict(list)
    for i, label in enumerate(labels):
        clusters[label].append({
            "id": valid_posts[i].get("id", ""),
            "text": (valid_posts[i].get("clean_text") or "")[:80],
            "overall_score": valid_posts[i].get("overall_score", 0),
            "ml_novelty": valid_posts[i].get("ml_novelty_score", 0),
        })

    return {
        "clusters": [
            {"id": cid, "size": len(members), "posts": members[:5]}
            for cid, members in sorted(clusters.items())
        ],
        "centroids": [[round(v, 2) for v in c] for c in km.centroids],
    }


# ── Stats ─────────────────────────────────────────────────────

def ml_stats() -> dict:
    """ML scorer statistics."""
    state = _load_ml_state()
    return {
        "documents_indexed": len(_text_intel._docs),
        "sources_tracked": list(_anomaly_detectors.keys()),
        "total_anomaly_alerts": sum(
            len(d.recent_alerts(100)) for d in _anomaly_detectors.values()
        ),
        "trends": {
            s: f.direction() for s, f in _trend_forecasters.items()
        },
        "source_volumes": state.get("source_volumes", {}),
        "last_run": state.get("last_run"),
    }


def _save_ml_state(source_volumes: dict):
    try:
        state = _load_ml_state()
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        # Accumulate volumes
        for src, count in source_volumes.items():
            state.setdefault("source_volumes", {})[src] = state.get("source_volumes", {}).get(src, 0) + count
        state["total_scored"] = state.get("total_scored", 0) + sum(source_volumes.values())
        ML_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_ml_state() -> dict:
    if ML_STATE_FILE.exists():
        try:
            return json.loads(ML_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"total_scored": 0, "source_volumes": {}, "last_run": None}
