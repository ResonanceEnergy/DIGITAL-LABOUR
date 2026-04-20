"""Bit Rage Intelligence Router — Galactia pipeline status, feeds, knowledge.

Exposes Galactia intelligence engine endpoints. Galactia currently runs
inside this repo but is NCL-bound (see RESONANCE_ENERGY_SOT.md). These
endpoints will migrate to NCL when Galactia moves.

Endpoints:
    GET  /api/v1/intel/galactia/status         — Full Galactia status
    GET  /api/v1/intel/galactia/feed           — Recent intelligence feed
    GET  /api/v1/intel/galactia/knowledge      — Knowledge graph summary
    POST /api/v1/intel/galactia/ingest         — Trigger manual ingestion
    GET  /api/v1/intel/galactia/ml-insights    — ML anomalies, trends, keywords
    GET  /api/v1/intel/galactia/context-health — Context governance health
    GET  /api/v1/intel/galactia/research       — Research projects
    GET  /api/v1/intel/galactia/unified        — Everything in one call
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/intel", tags=["Intelligence (Galactia)"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


# ── GET /galactia/status ──────────────────────────────────────

@router.get("/galactia/status")
async def galactia_status():
    """Get full Galactia brain status — pipelines, knowledge graph, truth engine."""
    result = {"sources": {}, "knowledge": {}, "scoring": {}, "state": {}}

    # Galactia daemon state
    try:
        galactia_state = PROJECT_ROOT / "galactia" / "data" / "galactia_state.json"
        if galactia_state.exists():
            result["state"] = json.loads(galactia_state.read_text(encoding="utf-8"))
    except Exception:
        pass

    # X Pipeline stats
    try:
        from galactia.x_pipeline import feed_stats as x_stats
        result["sources"]["x"] = x_stats()
    except Exception as e:
        result["sources"]["x"] = {"error": str(e)}

    # Reddit Pipeline stats
    try:
        from galactia.reddit_pipeline import feed_stats as reddit_stats
        result["sources"]["reddit"] = reddit_stats()
    except Exception as e:
        result["sources"]["reddit"] = {"error": str(e)}

    # YouTube Pipeline stats
    try:
        from galactia.youtube_pipeline import feed_stats as yt_stats
        result["sources"]["youtube"] = yt_stats()
    except Exception as e:
        result["sources"]["youtube"] = {"error": str(e)}

    # Knowledge store stats
    try:
        from galactia.knowledge_store import knowledge_stats, get_top_topics
        result["knowledge"] = knowledge_stats()
        result["knowledge"]["top_topics"] = get_top_topics(limit=10)
    except Exception as e:
        result["knowledge"] = {"error": str(e)}

    # Truth engine stats
    try:
        from galactia.truth_engine import scoring_stats
        result["scoring"] = scoring_stats()
    except Exception as e:
        result["scoring"] = {"error": str(e)}

    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result


# ── GET /galactia/feed ────────────────────────────────────────

@router.get("/galactia/feed")
async def galactia_feed(source: str = "all", limit: int = 30, scored_only: bool = False):
    """Get recent intelligence feed posts across all sources."""
    posts = []
    galactia_data = PROJECT_ROOT / "galactia" / "data"

    archives = []
    if source in ("all", "x"):
        archives.append(("x", galactia_data / "x_feed_archive.jsonl"))
    if source in ("all", "reddit"):
        archives.append(("reddit", galactia_data / "reddit_feed_archive.jsonl"))
    if source in ("all", "youtube"):
        archives.append(("youtube", galactia_data / "youtube_feed_archive.jsonl"))

    for src_name, archive_path in archives:
        if not archive_path.exists():
            continue
        try:
            with open(archive_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        post = json.loads(line)
                        if scored_only and post.get("overall_score") is None:
                            continue
                        post["_source_pipeline"] = src_name
                        posts.append(post)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue

    posts.sort(key=lambda p: p.get("ingested_at", ""), reverse=True)
    posts = posts[:limit]

    source_counts = {}
    for p in posts:
        s = p.get("_source_pipeline", "unknown")
        source_counts[s] = source_counts.get(s, 0) + 1

    return {
        "posts": posts,
        "count": len(posts),
        "source_breakdown": source_counts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── GET /galactia/knowledge ──────────────────────────────────

@router.get("/galactia/knowledge")
async def galactia_knowledge(limit: int = 20):
    """Get knowledge graph summary — top topics, claims, correlations."""
    try:
        from galactia.knowledge_store import get_knowledge_graph, get_top_topics, get_pending_correlations

        graph = get_knowledge_graph()
        top_topics = get_top_topics(limit=limit)
        pending = get_pending_correlations()

        claims = list(graph.get("claims", {}).values())
        claims.sort(key=lambda c: c.get("avg_score", 0), reverse=True)

        return {
            "top_topics": top_topics,
            "top_claims": claims[:20],
            "recent_correlations": graph.get("correlations", [])[-10:],
            "pending_correlations": pending[:10],
            "stats": graph.get("stats", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "top_topics": [], "top_claims": [], "stats": {}}


# ── POST /galactia/ingest ────────────────────────────────────

@router.post("/galactia/ingest")
async def galactia_trigger_ingest(source: str = "all"):
    """Manually trigger intelligence ingestion from one or all sources."""
    results = {}

    if source in ("all", "reddit"):
        try:
            from galactia.reddit_pipeline import ingest_feed as reddit_ingest
            posts = reddit_ingest(max_posts=50, sort="hot")
            results["reddit"] = {"status": "ok", "ingested": len(posts)}
        except Exception as e:
            results["reddit"] = {"status": "error", "error": str(e)}

    if source in ("all", "youtube"):
        try:
            from galactia.youtube_pipeline import ingest_feed as yt_ingest
            posts = yt_ingest(max_videos=30)
            results["youtube"] = {"status": "ok", "ingested": len(posts)}
        except Exception as e:
            results["youtube"] = {"status": "error", "error": str(e)}

    if source in ("all", "x"):
        try:
            from galactia.x_pipeline import ingest_feed as x_ingest
            posts = x_ingest(max_posts=50)
            results["x"] = {"status": "ok", "ingested": len(posts)}
        except Exception as e:
            results["x"] = {"status": "error", "error": str(e)}

    total = sum(r.get("ingested", 0) for r in results.values() if isinstance(r, dict))
    return {
        "status": "completed",
        "source": source,
        "results": results,
        "total_ingested": total,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── GET /galactia/ml-insights ──────────────────────────────────

@router.get("/galactia/ml-insights")
async def galactia_ml_insights():
    """Get ML intelligence insights — anomalies, trends, keywords, clusters."""
    try:
        from galactia.ml_scorer import get_ml_insights, ml_stats, cluster_posts
        insights = get_ml_insights()
        stats = ml_stats()

        clusters = {}
        try:
            from galactia.truth_engine import get_high_scored
            high_posts = get_high_scored(min_score=30, limit=100)
            if high_posts:
                clusters = cluster_posts(high_posts, k=min(5, len(high_posts)))
        except Exception:
            pass

        return {
            "insights": insights,
            "stats": stats,
            "clusters": clusters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "insights": {}, "stats": {}}


# ── GET /galactia/context-health ───────────────────────────────

@router.get("/galactia/context-health")
async def galactia_context_health():
    """Get context governance health — freshness, storage, issues."""
    try:
        from galactia.context_governor import context_health, get_context_report
        health = context_health()
        report = get_context_report()
        return {
            "health": health,
            "report": report,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "health": {"status": "unknown"}}


# ── GET /galactia/research ─────────────────────────────────────

@router.get("/galactia/research")
async def galactia_research():
    """Get research projects — active, completed, and stats."""
    try:
        from galactia.research_gen import list_projects, research_stats
        projects = list_projects()
        stats = research_stats()
        return {
            "projects": projects,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "projects": [], "stats": {}}


# ── GET /galactia/unified ──────────────────────────────────────

@router.get("/galactia/unified")
async def galactia_unified():
    """Full unified intelligence status — everything in one call."""
    result = {
        "architecture": "unified_v2",
        "pipelines": {},
        "scoring": {},
        "ml": {},
        "context": {},
        "knowledge": {},
        "research": {},
        "state": {},
    }

    try:
        state_file = PROJECT_ROOT / "galactia" / "data" / "galactia_state.json"
        if state_file.exists():
            result["state"] = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        pass

    for name, mod_path, fn_name in [
        ("x", "galactia.x_pipeline", "feed_stats"),
        ("reddit", "galactia.reddit_pipeline", "feed_stats"),
        ("youtube", "galactia.youtube_pipeline", "feed_stats"),
    ]:
        try:
            mod = __import__(mod_path, fromlist=[fn_name])
            result["pipelines"][name] = getattr(mod, fn_name)()
        except Exception as e:
            result["pipelines"][name] = {"error": str(e)}

    try:
        from galactia.truth_engine import scoring_stats
        result["scoring"] = scoring_stats()
    except Exception as e:
        result["scoring"] = {"error": str(e)}

    try:
        from galactia.ml_scorer import ml_stats
        result["ml"] = ml_stats()
    except Exception as e:
        result["ml"] = {"error": str(e)}

    try:
        from galactia.context_governor import context_health
        result["context"] = context_health()
    except Exception as e:
        result["context"] = {"error": str(e)}

    try:
        from galactia.knowledge_store import knowledge_stats, get_top_topics
        k = knowledge_stats()
        k["top_topics"] = get_top_topics(limit=10)
        result["knowledge"] = k
    except Exception as e:
        result["knowledge"] = {"error": str(e)}

    try:
        from galactia.research_gen import research_stats
        result["research"] = research_stats()
    except Exception as e:
        result["research"] = {"error": str(e)}

    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result
