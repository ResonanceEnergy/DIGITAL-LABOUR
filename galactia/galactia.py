"""GALACTIA — NCL's Unified Intelligence Engine.

The master daemon that runs the full Galactia pipeline in a continuous loop:
  PARALLEL Ingestion (X + Reddit + YouTube)
  → VERITAS Truth Scoring
  → ML Statistical Scoring
  → Context Governance
  → Knowledge Store
  → Correlation Analysis
  → Research Generation
  → Feedback Loop
  → Repeat

Unified architecture merging:
  - Galactia memory brain (original)
  - ML Intelligence Framework (anomaly detection, trend forecasting, TF-IDF)
  - Context Governor (TTL freshness, pruning, memory pressure)

Usage:
    python -m galactia.galactia                    # Run one full cycle
    python -m galactia.galactia --daemon           # Run 24/7
    python -m galactia.galactia --status           # Full status report
    python -m galactia.galactia --ingest-file X    # Ingest posts from JSON file
"""

import argparse
import json
import os
import sys
import time
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "galactia_state.json"
CYCLE_LOG_DIR = DATA_DIR / "cycle_logs"
CYCLE_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Timing ─────────────────────────────────────────────────────
CYCLE_INTERVAL_MINUTES = 30     # Full pipeline every 30 min
SCORE_BATCH_SIZE = 20           # Posts to score per cycle
CORRELATION_INTERVAL_CYCLES = 3 # Run correlation every N cycles
RESEARCH_INTERVAL_CYCLES = 6   # Run research every N cycles
GOVERNANCE_INTERVAL_CYCLES = 2  # Run context governance every N cycles


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "cycles_run": 0,
        "started_at": None,
        "last_cycle": None,
        "total_ingested": 0,
        "total_scored": 0,
        "total_ml_scored": 0,
        "total_correlations": 0,
        "total_research_projects": 0,
        "total_feedback_claims": 0,
        "total_governance_actions": 0,
        "ingestion_mode": "parallel",
    }


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ══════════════════════════════════════════════════════════════
#  PHASE 1: PARALLEL INGESTION
# ══════════════════════════════════════════════════════════════

def _ingest_x(max_posts: int = 50) -> dict:
    """Ingest from X/Twitter — runs in its own thread."""
    try:
        from galactia.x_pipeline import ingest_feed as x_ingest, feed_stats as x_stats
        if os.getenv("X_BEARER_TOKEN"):
            posts = x_ingest(max_posts=max_posts)
            return {"source": "x", "count": len(posts), "mode": "api", "posts": posts}
        else:
            stats = x_stats()
            return {"source": "x", "count": 0, "mode": "no_token", "archive": stats.get("archive_count", 0)}
    except Exception as e:
        return {"source": "x", "count": 0, "error": str(e)}


def _ingest_reddit(max_posts: int = 100) -> dict:
    """Ingest from Reddit — runs in its own thread."""
    try:
        from galactia.reddit_pipeline import ingest_feed as reddit_ingest
        posts = reddit_ingest(max_posts=max_posts, sort="hot")
        return {"source": "reddit", "count": len(posts), "mode": "public_json", "posts": posts}
    except Exception as e:
        return {"source": "reddit", "count": 0, "error": str(e)}


def _ingest_youtube(max_videos: int = 50) -> dict:
    """Ingest from YouTube — runs in its own thread."""
    try:
        from galactia.youtube_pipeline import ingest_feed as yt_ingest
        posts = yt_ingest(max_videos=max_videos)
        mode = "api" if os.getenv("YOUTUBE_API_KEY") else "rss"
        return {"source": "youtube", "count": len(posts), "mode": mode, "posts": posts}
    except Exception as e:
        return {"source": "youtube", "count": 0, "error": str(e)}


def _parallel_ingest() -> dict:
    """Run all 3 ingestion pipelines in parallel threads."""
    ingestion_report = {"sources": {}, "total_new": 0, "mode": "parallel", "timing": {}}
    start = time.time()

    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="galactia-ingest") as executor:
        futures = {
            executor.submit(_ingest_x, 50): "x",
            executor.submit(_ingest_reddit, 100): "reddit",
            executor.submit(_ingest_youtube, 50): "youtube",
        }

        for future in as_completed(futures):
            source_name = futures[future]
            try:
                result = future.result(timeout=120)
                ingestion_report["sources"][source_name] = {
                    k: v for k, v in result.items() if k != "posts"
                }
                ingestion_report["total_new"] += result.get("count", 0)
                if result.get("error"):
                    print(f"    [{source_name.upper()}] Error: {result['error']}")
                else:
                    print(f"    [{source_name.upper()}] {result['count']} posts ({result.get('mode', '?')})")
            except Exception as e:
                ingestion_report["sources"][source_name] = {"error": str(e), "count": 0}
                print(f"    [{source_name.upper()}] Thread error: {e}")

    elapsed = time.time() - start
    ingestion_report["timing"]["parallel_seconds"] = round(elapsed, 1)
    return ingestion_report


# ══════════════════════════════════════════════════════════════
#  PHASE 2: UNIFIED SCORING (VERITAS + ML + GOVERNANCE)
# ══════════════════════════════════════════════════════════════

def _gather_unscored() -> list[dict]:
    """Collect unscored posts from all pipelines."""
    unscored = []
    try:
        from galactia.x_pipeline import get_unscored_posts as x_unscored
        unscored.extend(x_unscored(limit=SCORE_BATCH_SIZE))
    except Exception:
        pass
    try:
        from galactia.reddit_pipeline import get_unscored_posts as reddit_unscored
        unscored.extend(reddit_unscored(limit=SCORE_BATCH_SIZE))
    except Exception:
        pass
    try:
        from galactia.youtube_pipeline import get_unscored_posts as yt_unscored
        unscored.extend(yt_unscored(limit=SCORE_BATCH_SIZE))
    except Exception:
        pass
    # Sort by recency, take top batch
    unscored.sort(key=lambda p: p.get("ingested_at", ""), reverse=True)
    return unscored[:SCORE_BATCH_SIZE]


def _phase2_scoring(state: dict) -> dict:
    """Phase 2: Three-pass scoring — VERITAS + ML + Governance."""
    phase_report = {"veritas": {}, "ml": {}, "governance": {}}

    unscored = _gather_unscored()

    # ── 2a: VERITAS Truth Scoring (LLM) ──────────────────────
    print(f"\n  [2a] VERITAS Truth Scoring...")
    scored_posts = []
    if unscored:
        try:
            from galactia.truth_engine import score_batch
            print(f"       Scoring {len(unscored)} posts via LLM...")
            scored_posts = score_batch(unscored)
            state["total_scored"] += len(scored_posts)
            phase_report["veritas"] = {"scored": len(scored_posts)}
        except Exception as e:
            print(f"       [ERROR] VERITAS failed: {e}")
            phase_report["veritas"] = {"error": str(e)}
    else:
        print(f"       No unscored posts — feed is current.")
        phase_report["veritas"] = {"scored": 0, "note": "feed_current"}

    # ── 2b: ML Statistical Scoring ───────────────────────────
    print(f"\n  [2b] ML Statistical Scoring...")
    try:
        from galactia.ml_scorer import score_ml_batch, get_ml_insights
        # Score the same batch we just VERITAS-scored (or unscored if VERITAS failed)
        ml_targets = scored_posts if scored_posts else unscored
        if ml_targets:
            ml_results = score_ml_batch(ml_targets)
            state["total_ml_scored"] += len(ml_results)
            # Generate insights snapshot
            insights = get_ml_insights()
            phase_report["ml"] = {
                "scored": len(ml_results),
                "anomaly_sources": list(insights.get("anomalies", {}).keys()),
                "trends": {s: t.get("direction") for s, t in insights.get("trends", {}).items()},
                "top_keywords": [k["word"] for k in insights.get("top_keywords", [])[:10]],
            }
        else:
            phase_report["ml"] = {"scored": 0}
    except Exception as e:
        print(f"       [ERROR] ML scoring failed: {e}")
        phase_report["ml"] = {"error": str(e)}

    # ── 2c: Context Governance ───────────────────────────────
    cycle_num = state.get("cycles_run", 0) + 1
    run_gov = (cycle_num % GOVERNANCE_INTERVAL_CYCLES == 0)
    if run_gov:
        print(f"\n  [2c] Context Governance...")
        try:
            from galactia.context_governor import run_governance
            gov_report = run_governance()
            state["total_governance_actions"] += len(gov_report.get("actions", []))
            phase_report["governance"] = {
                "actions": len(gov_report.get("actions", [])),
                "topics_after": gov_report.get("topics_after", 0),
                "claims_after": gov_report.get("claims_after", 0),
                "memory_pressure": gov_report.get("memory_pressure", "unknown"),
                "storage_mb": gov_report.get("storage", {}).get("total_size_mb", 0),
            }
        except Exception as e:
            print(f"       [ERROR] Governance failed: {e}")
            phase_report["governance"] = {"error": str(e)}
    else:
        phase_report["governance"] = {"skipped": True, "next_in": GOVERNANCE_INTERVAL_CYCLES - (cycle_num % GOVERNANCE_INTERVAL_CYCLES)}

    # ── Store scored content in knowledge store ──────────────
    if scored_posts:
        try:
            from galactia.knowledge_store import store_scored
            store_scored(scored_posts)
        except Exception as e:
            print(f"       [ERROR] Knowledge store failed: {e}")

    return phase_report


# ══════════════════════════════════════════════════════════════
#  SINGLE GALACTIA CYCLE
# ══════════════════════════════════════════════════════════════

def run_cycle() -> dict:
    """Execute one full unified Galactia intelligence cycle."""
    state = _load_state()
    cycle_num = state.get("cycles_run", 0) + 1
    now = datetime.now(timezone.utc)

    print(f"\n{'='*70}")
    print(f"  GALACTIA UNIFIED CYCLE #{cycle_num} — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  NCL's Intelligence Engine")
    print(f"{'='*70}")

    report = {
        "cycle": cycle_num,
        "started": now.isoformat(),
        "architecture": "unified_v2",
        "phases": {},
    }

    # ── Phase 1: Parallel Ingestion ────────────────────────────
    print(f"\n[PHASE 1] Parallel Intelligence Ingestion...")
    ingestion_report = _parallel_ingest()
    report["phases"]["ingestion"] = ingestion_report
    state["total_ingested"] += ingestion_report["total_new"]
    print(f"\n  [PHASE 1 COMPLETE] {ingestion_report['total_new']} new posts in {ingestion_report['timing'].get('parallel_seconds', '?')}s (parallel)")

    # ── Phase 2: Unified Scoring ───────────────────────────────
    print(f"\n[PHASE 2] Unified Scoring Pipeline...")
    scoring_report = _phase2_scoring(state)
    report["phases"]["scoring"] = scoring_report

    # ── Phase 3: Correlation Analysis (every N cycles) ─────────
    run_correlation = (cycle_num % CORRELATION_INTERVAL_CYCLES == 0)
    if run_correlation:
        print(f"\n[PHASE 3] Correlation Analysis...")
        try:
            from galactia.knowledge_store import find_correlations
            correlations = find_correlations(min_topic_score=50, min_posts=2)
            state["total_correlations"] += len(correlations)
            report["phases"]["correlation"] = {"found": len(correlations)}

            if correlations:
                from galactia.research_gen import create_research
                for corr in correlations[:3]:
                    project = create_research(corr)
                    if project:
                        state["total_research_projects"] += 1
        except Exception as e:
            print(f"  [ERROR] Correlation failed: {e}")
            report["phases"]["correlation"] = {"error": str(e)}
    else:
        print(f"\n[PHASE 3] Correlation — skipped (runs every {CORRELATION_INTERVAL_CYCLES} cycles)")
        report["phases"]["correlation"] = {"skipped": True, "next_in": CORRELATION_INTERVAL_CYCLES - (cycle_num % CORRELATION_INTERVAL_CYCLES)}

    # ── Phase 4: Research Execution (every N cycles) ───────────
    run_research = (cycle_num % RESEARCH_INTERVAL_CYCLES == 0)
    if run_research:
        print(f"\n[PHASE 4] Research Execution...")
        try:
            from galactia.research_gen import get_active_projects, run_research as exec_research, feed_back_to_galactia, _load_index
            active = get_active_projects()
            if active:
                print(f"  {len(active)} active research projects")
                index = _load_index()
                executed = 0
                for proj_id, proj_data in index.get("projects", {}).items():
                    if proj_data.get("status") == "active" and executed < 2:
                        exec_research(proj_id)
                        fed = feed_back_to_galactia(proj_id)
                        state["total_feedback_claims"] += fed
                        executed += 1
                report["phases"]["research"] = {"active": len(active), "executed": executed}
            else:
                print(f"  No active research projects.")
                report["phases"]["research"] = {"active": 0}
        except Exception as e:
            print(f"  [ERROR] Research failed: {e}")
            report["phases"]["research"] = {"error": str(e)}
    else:
        print(f"\n[PHASE 4] Research — skipped (runs every {RESEARCH_INTERVAL_CYCLES} cycles)")
        report["phases"]["research"] = {"skipped": True}

    # ── Phase 5: Memory Status + ML Insights ───────────────────
    print(f"\n[PHASE 5] Unified Memory Status...")
    try:
        from galactia.knowledge_store import knowledge_stats
        from galactia.truth_engine import scoring_stats
        from galactia.research_gen import research_stats

        k_stats = knowledge_stats()
        s_stats = scoring_stats()
        r_stats = research_stats()

        # ML insights
        ml_insights = {}
        try:
            from galactia.ml_scorer import ml_stats
            ml_insights = ml_stats()
        except Exception:
            pass

        # Context health
        ctx_health = {}
        try:
            from galactia.context_governor import context_health
            ctx_health = context_health()
        except Exception:
            pass

        print(f"  Knowledge: {k_stats.get('total_topics', 0)} topics, {k_stats.get('total_claims', 0)} claims")
        print(f"  Scoring: {s_stats.get('total_scored', 0)} scored, avg {s_stats.get('avg_overall', 'N/A')}")
        print(f"  Research: {r_stats.get('active', 0)} active, {r_stats.get('completed', 0)} completed")
        print(f"  ML: {ml_insights.get('documents_indexed', 0)} indexed, trends: {ml_insights.get('trends', {})}")
        print(f"  Context: {ctx_health.get('status', 'unknown')}")

        report["phases"]["status"] = {
            "knowledge": k_stats,
            "scoring": s_stats,
            "research": r_stats,
            "ml": ml_insights,
            "context": ctx_health,
        }
    except Exception as e:
        print(f"  [ERROR] Status check failed: {e}")

    # ── Finalize ───────────────────────────────────────────────
    report["finished"] = datetime.now(timezone.utc).isoformat()
    elapsed = (datetime.now(timezone.utc) - now).total_seconds()
    report["elapsed_seconds"] = round(elapsed, 1)

    log_file = CYCLE_LOG_DIR / f"galactia_cycle_{cycle_num:04d}.json"
    log_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    state["cycles_run"] = cycle_num
    state["last_cycle"] = now.isoformat()
    if not state.get("started_at"):
        state["started_at"] = now.isoformat()
    _save_state(state)

    print(f"\n{'='*70}")
    print(f"  GALACTIA UNIFIED CYCLE #{cycle_num} COMPLETE — {elapsed:.1f}s")
    print(f"  Ingested: {state['total_ingested']} | Scored: {state['total_scored']} | ML: {state['total_ml_scored']}")
    print(f"  Correlations: {state['total_correlations']} | Projects: {state['total_research_projects']} | Gov: {state['total_governance_actions']} actions")
    print(f"{'='*70}")

    return report


# ── 24/7 Daemon ────────────────────────────────────────────────

def daemon_loop():
    """Run Galactia continuously — NCL's ever-evolving memory."""
    print(f"\n{'#'*70}")
    print(f"  ██████   █████  ██       █████   ██████ ████████ ██  █████ ")
    print(f" ██       ██   ██ ██      ██   ██ ██         ██    ██ ██   ██")
    print(f" ██   ███ ███████ ██      ███████ ██         ██    ██ ███████")
    print(f" ██    ██ ██   ██ ██      ██   ██ ██         ██    ██ ██   ██")
    print(f"  ██████  ██   ██ ███████ ██   ██  ██████    ██    ██ ██   ██")
    print(f"")
    print(f"  NCL's Unified Intelligence Engine — Online")
    print(f"  Architecture: Parallel Ingest → VERITAS + ML + Governor → Knowledge → Research")
    print(f"  Cycle: {CYCLE_INTERVAL_MINUTES}min | Batch: {SCORE_BATCH_SIZE} | Correlation: every {CORRELATION_INTERVAL_CYCLES} cycles")
    print(f"  Research: every {RESEARCH_INTERVAL_CYCLES} cycles | Governance: every {GOVERNANCE_INTERVAL_CYCLES} cycles")
    print(f"  Press Ctrl+C to stop")
    print(f"{'#'*70}")

    consecutive_failures = 0
    while True:
        try:
            run_cycle()
            consecutive_failures = 0
        except KeyboardInterrupt:
            print("\n\n[GALACTIA] Intelligence engine stopped by operator.")
            break
        except Exception as e:
            consecutive_failures += 1
            print(f"\n[GALACTIA] Cycle failed: {e}")
            traceback.print_exc()
            if consecutive_failures >= 5:
                print("[GALACTIA] 5 consecutive failures. Pausing 10 minutes...")
                time.sleep(600)
                consecutive_failures = 0
            else:
                time.sleep(60)
                continue

        print(f"\n[GALACTIA] Next cycle in {CYCLE_INTERVAL_MINUTES} minutes...")
        try:
            time.sleep(CYCLE_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("\n[GALACTIA] Stopped.")
            break


# ── Status ─────────────────────────────────────────────────────

def show_status():
    """Display full unified Galactia status."""
    state = _load_state()

    print(f"\n{'='*70}")
    print(f"  GALACTIA — NCL's Unified Intelligence Engine")
    print(f"  Architecture: {state.get('ingestion_mode', 'parallel')} ingestion + VERITAS + ML + Governor")
    print(f"{'='*70}")
    print(f"  Cycles run: {state.get('cycles_run', 0)}")
    print(f"  First started: {state.get('started_at', 'never')}")
    print(f"  Last cycle: {state.get('last_cycle', 'never')}")
    print(f"\n── Pipeline Totals ──")
    print(f"  Posts ingested: {state.get('total_ingested', 0)}")
    print(f"  VERITAS scored: {state.get('total_scored', 0)}")
    print(f"  ML scored: {state.get('total_ml_scored', 0)}")
    print(f"  Correlations found: {state.get('total_correlations', 0)}")
    print(f"  Research projects: {state.get('total_research_projects', 0)}")
    print(f"  Feedback claims: {state.get('total_feedback_claims', 0)}")
    print(f"  Governance actions: {state.get('total_governance_actions', 0)}")

    # Pipeline stats
    for name, mod_path, stats_fn in [
        ("X", "galactia.x_pipeline", "feed_stats"),
        ("Reddit", "galactia.reddit_pipeline", "feed_stats"),
        ("YouTube", "galactia.youtube_pipeline", "feed_stats"),
    ]:
        try:
            mod = __import__(mod_path, fromlist=[stats_fn])
            stats = getattr(mod, stats_fn)()
            print(f"\n── {name} Pipeline ──")
            for k, v in stats.items():
                print(f"  {k}: {v}")
        except Exception:
            pass

    # Knowledge stats
    try:
        from galactia.knowledge_store import knowledge_stats, get_top_topics
        k = knowledge_stats()
        print(f"\n── Knowledge Graph ──")
        print(f"  Topics: {k.get('total_topics', 0)} | Claims: {k.get('total_claims', 0)}")
        print(f"  Multi-source claims: {k.get('multi_source_claims', 0)}")
        if k.get("highest_topic"):
            print(f"  Highest scored: {k['highest_topic']}")

        top = get_top_topics(limit=10)
        if top:
            print(f"\n── Top Topics ──")
            for t in top:
                print(f"  [{t['avg_score']:.0f}] {t['name']} ({t['count']} posts)")
    except Exception:
        pass

    # ML insights
    try:
        from galactia.ml_scorer import ml_stats, get_ml_insights
        m = ml_stats()
        print(f"\n── ML Intelligence ──")
        print(f"  Documents indexed: {m.get('documents_indexed', 0)}")
        print(f"  Sources tracked: {m.get('sources_tracked', [])}")
        print(f"  Anomaly alerts: {m.get('total_anomaly_alerts', 0)}")
        print(f"  Trends: {m.get('trends', {})}")

        insights = get_ml_insights()
        kw = insights.get("top_keywords", [])[:10]
        if kw:
            print(f"  Top keywords: {', '.join(k['word'] for k in kw)}")
    except Exception:
        pass

    # Context health
    try:
        from galactia.context_governor import context_health
        h = context_health()
        print(f"\n── Context Health ──")
        print(f"  Status: {h.get('status', 'unknown')}")
        if h.get("issues"):
            for issue in h["issues"]:
                print(f"  ! {issue}")
        m = h.get("metrics", {})
        print(f"  Storage: {m.get('storage_mb', '?')}MB | Last governance: {m.get('last_governance', 'never')}")
    except Exception:
        pass

    # Research stats
    try:
        from galactia.research_gen import list_projects
        projects = list_projects()
        if projects:
            print(f"\n── Research Projects ──")
            for p in projects:
                print(f"  [{p.get('status', '?')}] {p.get('codename', '?')} — {', '.join(p.get('topics', []))}")
    except Exception:
        pass

    # Truth engine
    try:
        from galactia.truth_engine import scoring_stats
        s = scoring_stats()
        if s.get("total_scored", 0) > 0:
            print(f"\n── Truth Engine ──")
            print(f"  Total scored: {s['total_scored']} | Avg overall: {s.get('avg_overall', 'N/A')}")
    except Exception:
        pass


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GALACTIA — NCL's Unified Intelligence Engine")
    parser.add_argument("--daemon", action="store_true", help="Run 24/7 intelligence daemon")
    parser.add_argument("--status", action="store_true", help="Show full status")
    parser.add_argument("--cycle", action="store_true", help="Run single cycle")
    parser.add_argument("--ingest-file", type=str, help="Ingest posts from JSON file")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.ingest_file:
        from galactia.x_pipeline import ingest_from_file
        ingest_from_file(args.ingest_file)
    elif args.daemon:
        daemon_loop()
    else:
        run_cycle()
