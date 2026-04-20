"""Context Governor — Unified context lifecycle management for Galactia.

Consolidated from context_manager.py + context_manager_agent.py into a single
lightweight governor that runs as Phase 2c in the unified Galactia pipeline.

Responsibilities:
  1. TTL-based freshness enforcement — stale knowledge decays
  2. Domain gating — controls what intelligence reaches which consumers
  3. Knowledge graph cleanup — prunes low-scoring noise
  4. Memory pressure management — caps growth, compresses old entries
  5. Audit trail — tracks freshness, accuracy, and access patterns

Phase 2c in the unified pipeline:
  2a: VERITAS (LLM truth scoring)
  2b: ML Scorer (statistical analysis)
  2c: Context Governor (freshness + cleanup + governance)  <-- this

Usage:
    from galactia.context_governor import run_governance, context_health, get_context_report
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
GOV_STATE_FILE = DATA_DIR / "governor_state.json"
GOV_REPORT_FILE = DATA_DIR / "governor_report.json"

# ── Thresholds ────────────────────────────────────────────────

TOPIC_TTL_DAYS = 30             # Topics not updated in 30 days decay
CLAIM_TTL_DAYS = 60             # Claims older than 60 days get archived
MIN_SCORE_THRESHOLD = 25        # Posts below this get pruned from graph
MAX_TOPICS = 500                # Hard cap on knowledge graph topics
MAX_CLAIMS = 2000               # Hard cap on claims
MAX_CORRELATIONS = 200          # Hard cap on stored correlations
DECAY_RATE = 0.95               # Score decay multiplier per governance pass
STALE_ARCHIVE_LINES = 50000     # Max lines per JSONL archive before trim


# ── Governance Cycle ──────────────────────────────────────────

def run_governance() -> dict:
    """Execute one governance pass on Galactia's knowledge.

    Returns a report of actions taken: topics decayed, claims pruned,
    archives trimmed, memory pressure status.
    """
    now = datetime.now(timezone.utc)
    report = {
        "timestamp": now.isoformat(),
        "actions": [],
        "topics_before": 0,
        "topics_after": 0,
        "claims_before": 0,
        "claims_after": 0,
        "archives_trimmed": [],
        "memory_pressure": "normal",
    }

    # 1. Knowledge graph governance
    try:
        from galactia.knowledge_store import _load_graph, _save_graph
        graph = _load_graph()

        topics = graph.get("topics", {})
        claims = graph.get("claims", {})
        correlations = graph.get("correlations", [])

        report["topics_before"] = len(topics)
        report["claims_before"] = len(claims)

        # 1a. Decay stale topics
        stale_topics = []
        for key, topic in list(topics.items()):
            last_updated = topic.get("last_updated") or topic.get("first_seen", "")
            if last_updated:
                try:
                    updated_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                    age_days = (now - updated_dt).days
                    if age_days > TOPIC_TTL_DAYS:
                        # Decay score rather than delete
                        topic["avg_score"] = round(topic["avg_score"] * DECAY_RATE, 1)
                        stale_topics.append(key)
                        # Remove if score drops below threshold
                        if topic["avg_score"] < MIN_SCORE_THRESHOLD and topic["count"] < 3:
                            del topics[key]
                except (ValueError, TypeError):
                    pass

        if stale_topics:
            report["actions"].append(f"Decayed {len(stale_topics)} stale topics")

        # 1b. Prune low-score claims
        pruned_claims = 0
        for ch, claim in list(claims.items()):
            first_seen = claim.get("first_seen", "")
            if first_seen:
                try:
                    seen_dt = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
                    age_days = (now - seen_dt).days
                    if age_days > CLAIM_TTL_DAYS and claim.get("source_count", 0) < 2:
                        del claims[ch]
                        pruned_claims += 1
                except (ValueError, TypeError):
                    pass

        if pruned_claims:
            report["actions"].append(f"Pruned {pruned_claims} stale single-source claims")

        # 1c. Enforce caps
        if len(topics) > MAX_TOPICS:
            # Remove lowest-scoring topics
            sorted_topics = sorted(topics.items(), key=lambda x: x[1]["avg_score"])
            to_remove = len(topics) - MAX_TOPICS
            for key, _ in sorted_topics[:to_remove]:
                del topics[key]
            report["actions"].append(f"Capped topics: removed {to_remove} lowest-scoring")

        if len(claims) > MAX_CLAIMS:
            sorted_claims = sorted(claims.items(), key=lambda x: x[1].get("avg_score", 0))
            to_remove = len(claims) - MAX_CLAIMS
            for ch, _ in sorted_claims[:to_remove]:
                del claims[ch]
            report["actions"].append(f"Capped claims: removed {to_remove} lowest-scoring")

        # 1d. Trim correlations
        if len(correlations) > MAX_CORRELATIONS:
            graph["correlations"] = correlations[-MAX_CORRELATIONS:]
            report["actions"].append(f"Trimmed correlations to {MAX_CORRELATIONS}")

        # Save
        graph["topics"] = topics
        graph["claims"] = claims
        graph["stats"]["total_topics"] = len(topics)
        graph["stats"]["total_claims"] = len(claims)
        _save_graph(graph)

        report["topics_after"] = len(topics)
        report["claims_after"] = len(claims)

    except Exception as e:
        report["actions"].append(f"Knowledge governance failed: {e}")

    # 2. Archive size management
    archive_files = [
        DATA_DIR / "x_feed_archive.jsonl",
        DATA_DIR / "reddit_feed_archive.jsonl",
        DATA_DIR / "youtube_feed_archive.jsonl",
        DATA_DIR / "scored_posts.jsonl",
        DATA_DIR / "correlations.jsonl",
    ]

    for archive in archive_files:
        if archive.exists():
            try:
                lines = archive.read_text(encoding="utf-8").strip().split("\n")
                if len(lines) > STALE_ARCHIVE_LINES:
                    # Keep most recent half
                    keep = lines[-(STALE_ARCHIVE_LINES // 2):]
                    archive.write_text("\n".join(keep) + "\n", encoding="utf-8")
                    trimmed = len(lines) - len(keep)
                    report["archives_trimmed"].append({
                        "file": archive.name,
                        "before": len(lines),
                        "after": len(keep),
                        "trimmed": trimmed,
                    })
                    report["actions"].append(f"Trimmed {archive.name}: {trimmed} old entries removed")
            except Exception:
                pass

    # 3. Memory pressure assessment
    total_files = sum(1 for _ in DATA_DIR.rglob("*") if _.is_file())
    total_size_mb = sum(f.stat().st_size for f in DATA_DIR.rglob("*") if f.is_file()) / (1024 * 1024)

    if total_size_mb > 500:
        report["memory_pressure"] = "critical"
    elif total_size_mb > 200:
        report["memory_pressure"] = "high"
    elif total_size_mb > 50:
        report["memory_pressure"] = "moderate"
    else:
        report["memory_pressure"] = "normal"

    report["storage"] = {
        "total_files": total_files,
        "total_size_mb": round(total_size_mb, 2),
    }

    # 4. Cluster file cleanup
    clusters_dir = DATA_DIR / "clusters"
    if clusters_dir.exists():
        cluster_files = list(clusters_dir.glob("cluster_*.jsonl"))
        for cf in cluster_files:
            try:
                lines = cf.read_text(encoding="utf-8").strip().split("\n")
                if len(lines) > 500:
                    # Keep latest 250
                    keep = lines[-250:]
                    cf.write_text("\n".join(keep) + "\n", encoding="utf-8")
            except Exception:
                pass

    # Save governance report
    _save_gov_state(report)

    actions_count = len(report["actions"])
    if actions_count > 0:
        print(f"  [GOVERNOR] {actions_count} actions taken — pressure: {report['memory_pressure']}")
    else:
        print(f"  [GOVERNOR] All clean — {report['topics_after']} topics, {report['claims_after']} claims, pressure: {report['memory_pressure']}")

    return report


# ── Context Health ────────────────────────────────────────────

def context_health() -> dict:
    """Quick health check of the context layer."""
    health = {
        "status": "healthy",
        "issues": [],
        "metrics": {},
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    # Check knowledge graph
    try:
        from galactia.knowledge_store import knowledge_stats
        k = knowledge_stats()
        health["metrics"]["topics"] = k.get("total_topics", 0)
        health["metrics"]["claims"] = k.get("total_claims", 0)
        health["metrics"]["multi_source_claims"] = k.get("multi_source_claims", 0)

        if k.get("total_topics", 0) == 0:
            health["issues"].append("Knowledge graph is empty — no topics ingested yet")
        if k.get("multi_source_claims", 0) == 0 and k.get("total_claims", 0) > 10:
            health["issues"].append("No multi-source claims — intelligence may lack corroboration")
    except Exception as e:
        health["issues"].append(f"Knowledge store unreachable: {e}")

    # Check archive freshness
    for name, filename in [("x", "x_feed_archive.jsonl"), ("reddit", "reddit_feed_archive.jsonl"), ("youtube", "youtube_feed_archive.jsonl")]:
        archive = DATA_DIR / filename
        if archive.exists():
            try:
                mtime = datetime.fromtimestamp(archive.stat().st_mtime, tz=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
                health["metrics"][f"{name}_archive_age_hours"] = round(age_hours, 1)
                if age_hours > 2:
                    health["issues"].append(f"{name} archive is {age_hours:.0f}h stale")
            except Exception:
                pass
        else:
            health["metrics"][f"{name}_archive_age_hours"] = None

    # Check storage
    try:
        total_size_mb = sum(f.stat().st_size for f in DATA_DIR.rglob("*") if f.is_file()) / (1024 * 1024)
        health["metrics"]["storage_mb"] = round(total_size_mb, 2)
        if total_size_mb > 200:
            health["issues"].append(f"Storage pressure: {total_size_mb:.0f}MB used")
    except Exception:
        pass

    # Check governor state
    state = _load_gov_state()
    health["metrics"]["last_governance"] = state.get("last_run")
    health["metrics"]["governance_actions"] = state.get("total_actions", 0)

    if health["issues"]:
        health["status"] = "degraded" if len(health["issues"]) < 3 else "unhealthy"

    return health


def get_context_report() -> dict:
    """Full governance report — last actions, health, recommendations."""
    state = _load_gov_state()
    health = context_health()

    recommendations = []
    if health.get("metrics", {}).get("topics", 0) == 0:
        recommendations.append("Run initial ingestion: POST /galactia/ingest")
    if health.get("metrics", {}).get("storage_mb", 0) > 100:
        recommendations.append("Consider enabling Railway Volume for persistent storage")
    if any("stale" in i for i in health.get("issues", [])):
        recommendations.append("Check daemon status — archives may not be updating")

    return {
        "health": health,
        "last_governance": state.get("last_report", {}),
        "recommendations": recommendations,
        "governor_runs": state.get("runs", 0),
    }


# ── State Persistence ─────────────────────────────────────────

def _save_gov_state(report: dict):
    try:
        state = _load_gov_state()
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        state["runs"] = state.get("runs", 0) + 1
        state["total_actions"] = state.get("total_actions", 0) + len(report.get("actions", []))
        state["last_report"] = report
        GOV_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_gov_state() -> dict:
    if GOV_STATE_FILE.exists():
        try:
            return json.loads(GOV_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"runs": 0, "total_actions": 0, "last_run": None}
