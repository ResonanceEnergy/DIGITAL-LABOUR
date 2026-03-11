"""GALACTIA — NCL's Functioning Memory Orchestrator.

The master daemon that runs the full Galactia pipeline in a continuous loop:
  X Feed → Truth Scoring → Knowledge Store → Correlation → Research → Feedback → Repeat

Galactia is NCL's living brain — constantly ingesting, evaluating, connecting,
and deepening its understanding of reality. Every cycle it gets smarter.

Usage:
    python -m galactia.galactia                    # Run one full cycle
    python -m galactia.galactia --daemon           # Run 24/7
    python -m galactia.galactia --status           # Full status report
    python -m galactia.galactia --ingest-file X    # Ingest posts from JSON file
"""

import argparse
import json
import sys
import time
import traceback
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


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "cycles_run": 0,
        "started_at": None,
        "last_cycle": None,
        "total_ingested": 0,
        "total_scored": 0,
        "total_correlations": 0,
        "total_research_projects": 0,
        "total_feedback_claims": 0,
    }


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Single Galactia Cycle ──────────────────────────────────────

def run_cycle() -> dict:
    """Execute one full Galactia memory cycle."""
    state = _load_state()
    cycle_num = state.get("cycles_run", 0) + 1
    now = datetime.now(timezone.utc)

    print(f"\n{'='*70}")
    print(f"  GALACTIA CYCLE #{cycle_num} — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  NCL's Functioning Memory")
    print(f"{'='*70}")

    report = {
        "cycle": cycle_num,
        "started": now.isoformat(),
        "phases": {},
    }

    # ── Phase 1: X Feed Ingestion ──────────────────────────────
    print(f"\n[PHASE 1] X Feed Ingestion...")
    try:
        from galactia.x_pipeline import ingest_feed, get_unscored_posts, feed_stats

        # Try API ingestion if configured
        import os
        if os.getenv("X_BEARER_TOKEN"):
            posts = ingest_feed(max_posts=50)
            report["phases"]["ingestion"] = {"source": "x_api", "count": len(posts)}
            state["total_ingested"] += len(posts)
        else:
            stats = feed_stats()
            report["phases"]["ingestion"] = {"source": "manual_only", "archive": stats.get("archive_count", 0)}
            print(f"  No X_BEARER_TOKEN set. Using manual ingestion mode.")
            print(f"  Archive: {stats.get('archive_count', 0)} posts")
    except Exception as e:
        print(f"  [ERROR] Ingestion failed: {e}")
        report["phases"]["ingestion"] = {"error": str(e)}

    # ── Phase 2: Truth Scoring ─────────────────────────────────
    print(f"\n[PHASE 2] Truth Scoring...")
    try:
        from galactia.x_pipeline import get_unscored_posts
        from galactia.truth_engine import score_batch, scoring_stats

        unscored = get_unscored_posts(limit=SCORE_BATCH_SIZE)
        if unscored:
            print(f"  Scoring {len(unscored)} unscored posts...")
            scored = score_batch(unscored)
            state["total_scored"] += len(scored)
            report["phases"]["scoring"] = {"scored": len(scored)}

            # Store scored content in knowledge store
            from galactia.knowledge_store import store_scored
            store_scored(scored)
        else:
            print(f"  No unscored posts. Feed is current.")
            report["phases"]["scoring"] = {"scored": 0, "note": "feed_current"}
    except Exception as e:
        print(f"  [ERROR] Scoring failed: {e}")
        report["phases"]["scoring"] = {"error": str(e)}

    # ── Phase 3: Correlation Analysis (every N cycles) ─────────
    run_correlation = (cycle_num % CORRELATION_INTERVAL_CYCLES == 0)
    if run_correlation:
        print(f"\n[PHASE 3] Correlation Analysis...")
        try:
            from galactia.knowledge_store import find_correlations

            correlations = find_correlations(min_topic_score=50, min_posts=2)
            state["total_correlations"] += len(correlations)
            report["phases"]["correlation"] = {"found": len(correlations)}

            # If correlations found, create research projects
            if correlations:
                from galactia.research_gen import create_research
                for corr in correlations[:3]:  # Max 3 new projects per cycle
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
            from galactia.research_gen import get_active_projects, run_research as exec_research, feed_back_to_galactia

            active = get_active_projects()
            if active:
                print(f"  {len(active)} active research projects")
                for proj in active[:2]:  # Max 2 research cycles per Galactia cycle
                    pid = proj.get("id") or list(proj.keys())[0] if isinstance(proj, dict) else str(proj)
                    # Get the actual project ID from the index
                    from galactia.research_gen import _load_index
                    index = _load_index()
                    for proj_id, proj_data in index.get("projects", {}).items():
                        if proj_data.get("status") == "active":
                            exec_research(proj_id)
                            fed = feed_back_to_galactia(proj_id)
                            state["total_feedback_claims"] += fed
                            break
                report["phases"]["research"] = {"active": len(active)}
            else:
                print(f"  No active research projects.")
                report["phases"]["research"] = {"active": 0}
        except Exception as e:
            print(f"  [ERROR] Research failed: {e}")
            report["phases"]["research"] = {"error": str(e)}
    else:
        print(f"\n[PHASE 4] Research — skipped (runs every {RESEARCH_INTERVAL_CYCLES} cycles)")
        report["phases"]["research"] = {"skipped": True}

    # ── Phase 5: Memory Status ─────────────────────────────────
    print(f"\n[PHASE 5] Memory Status...")
    try:
        from galactia.knowledge_store import knowledge_stats
        from galactia.truth_engine import scoring_stats
        from galactia.research_gen import research_stats

        k_stats = knowledge_stats()
        s_stats = scoring_stats()
        r_stats = research_stats()

        print(f"  Knowledge: {k_stats.get('total_topics', 0)} topics, {k_stats.get('total_claims', 0)} claims")
        print(f"  Scoring: {s_stats.get('total_scored', 0)} scored, avg {s_stats.get('avg_overall', 'N/A')}")
        print(f"  Research: {r_stats.get('active', 0)} active, {r_stats.get('completed', 0)} completed")

        report["phases"]["status"] = {
            "knowledge": k_stats,
            "scoring": s_stats,
            "research": r_stats,
        }
    except Exception as e:
        print(f"  [ERROR] Status check failed: {e}")

    # ── Finalize ───────────────────────────────────────────────
    report["finished"] = datetime.now(timezone.utc).isoformat()
    elapsed = (datetime.now(timezone.utc) - now).total_seconds()
    report["elapsed_seconds"] = round(elapsed, 1)

    # Save cycle log
    log_file = CYCLE_LOG_DIR / f"galactia_cycle_{cycle_num:04d}.json"
    log_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Update state
    state["cycles_run"] = cycle_num
    state["last_cycle"] = now.isoformat()
    if not state.get("started_at"):
        state["started_at"] = now.isoformat()
    _save_state(state)

    print(f"\n{'='*70}")
    print(f"  GALACTIA CYCLE #{cycle_num} COMPLETE — {elapsed:.1f}s")
    print(f"  Total: {state['total_ingested']} ingested | {state['total_scored']} scored | {state['total_correlations']} correlations | {state['total_research_projects']} projects")
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
    print(f"  NCL's Functioning Memory — Online")
    print(f"  Cycle: {CYCLE_INTERVAL_MINUTES} min | Score batch: {SCORE_BATCH_SIZE}")
    print(f"  Correlation every {CORRELATION_INTERVAL_CYCLES} cycles")
    print(f"  Research every {RESEARCH_INTERVAL_CYCLES} cycles")
    print(f"  Press Ctrl+C to stop")
    print(f"{'#'*70}")

    consecutive_failures = 0
    while True:
        try:
            run_cycle()
            consecutive_failures = 0
        except KeyboardInterrupt:
            print("\n\n[GALACTIA] Memory daemon stopped by operator.")
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
    """Display full Galactia status."""
    state = _load_state()

    print(f"\n{'='*70}")
    print(f"  GALACTIA — NCL's Functioning Memory")
    print(f"{'='*70}")
    print(f"  Cycles run: {state.get('cycles_run', 0)}")
    print(f"  First started: {state.get('started_at', 'never')}")
    print(f"  Last cycle: {state.get('last_cycle', 'never')}")
    print(f"\n── Pipeline Totals ──")
    print(f"  Posts ingested: {state.get('total_ingested', 0)}")
    print(f"  Posts scored: {state.get('total_scored', 0)}")
    print(f"  Correlations found: {state.get('total_correlations', 0)}")
    print(f"  Research projects: {state.get('total_research_projects', 0)}")
    print(f"  Feedback claims: {state.get('total_feedback_claims', 0)}")

    # Knowledge stats
    try:
        from galactia.knowledge_store import knowledge_stats, get_top_topics
        k = knowledge_stats()
        print(f"\n── Knowledge Graph ──")
        print(f"  Topics: {k.get('total_topics', 0)}")
        print(f"  Claims: {k.get('total_claims', 0)}")
        print(f"  Multi-source claims: {k.get('multi_source_claims', 0)}")
        if k.get("highest_topic"):
            print(f"  Highest scored topic: {k['highest_topic']}")
        if k.get("most_active_topic"):
            print(f"  Most active topic: {k['most_active_topic']}")

        top = get_top_topics(limit=10)
        if top:
            print(f"\n── Top Topics ──")
            for t in top:
                print(f"  [{t['avg_score']:.0f}] {t['name']} ({t['count']} posts)")
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

    # Scoring stats
    try:
        from galactia.truth_engine import scoring_stats
        s = scoring_stats()
        if s.get("total_scored", 0) > 0:
            print(f"\n── Truth Engine ──")
            print(f"  Total scored: {s['total_scored']}")
            print(f"  Avg truth: {s.get('avg_truth', 'N/A')}")
            print(f"  Avg credibility: {s.get('avg_credibility', 'N/A')}")
            print(f"  Avg overall: {s.get('avg_overall', 'N/A')}")
            if s.get("top_topics"):
                print(f"  Top topics: {s['top_topics']}")
    except Exception:
        pass


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GALACTIA — NCL's Functioning Memory")
    parser.add_argument("--daemon", action="store_true", help="Run 24/7 memory daemon")
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
