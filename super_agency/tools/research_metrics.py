#!/usr/bin/env python3
"""
Research Metrics & KPIs — Intelligence Cycle Measurement System
================================================================
Implements the 5-phase Intelligence Cycle (Direction → Collection →
Processing → Analysis → Dissemination) with measurable KPIs at
each phase.

Inspired by the OODA loop (Observe-Orient-Decide-Act) and OSINT
best practices from NATO/SCIP frameworks.

KPI categories:
  - Collection: ingestion throughput, source coverage, freshness
  - Processing: enrichment quality, pipeline latency
  - Analysis: correlation density, trend detection accuracy
  - Synthesis: idea generation rate, cross-pollination score
  - Dissemination: actionable recommendation rate, brief quality
  - System: uptime, cycle frequency, agent effectiveness

Usage::

    python tools/research_metrics.py              # full dashboard
    python tools/research_metrics.py snapshot      # quick snapshot
    python tools/research_metrics.py history       # trend over time
"""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Optional, cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    Log, ensure_dir, now_iso, get_portfolio,
)

KNOWLEDGE_DIR = ROOT / "knowledge" / "secondbrain"
TOPIC_INDEX = KNOWLEDGE_DIR / "topic_index.json"
RESEARCH_DIR = ROOT / "reports" / "research"
INTEL_DIR = ROOT / "reports" / "intelligence"
METRICS_DIR = ROOT / "reports" / "metrics"
WATCHLIST = ROOT / "config" / "intelligence_watchlist.json"
PROJECTS_FILE = ROOT / "config" / "research_projects.json"
METRICS_HISTORY = METRICS_DIR / "metrics_history.json"

ensure_dir(METRICS_DIR)
ensure_dir(INTEL_DIR)

# Message bus (best-effort)
_bus: Any = None
try:
    from agents.message_bus import bus
    _bus = bus
except Exception:
    pass


def _emit(topic: str, payload: Optional[dict] = None):
    if _bus:
        _bus.publish(  # type: ignore[union-attr]
            topic, payload or {}, source="research_metrics",
        )


# ── Data Loaders ────────────────────────────────────────────

def _count_ingested_videos() -> int:
    """Count total ingested Second Brain entries."""
    count = 0
    if not KNOWLEDGE_DIR.exists():
        return 0
    for year_dir in KNOWLEDGE_DIR.iterdir():
        if not year_dir.is_dir() or year_dir.name.startswith("."):
            continue
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir():
                continue
            for vid_dir in month_dir.iterdir():
                if vid_dir.is_dir():
                    count += 1
    return count


def _count_enriched_videos() -> int:
    """Count entries that have been enriched."""
    count = 0
    if not KNOWLEDGE_DIR.exists():
        return 0
    for year_dir in KNOWLEDGE_DIR.iterdir():
        if not year_dir.is_dir() or year_dir.name.startswith("."):
            continue
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir():
                continue
            for vid_dir in month_dir.iterdir():
                if (vid_dir / "enrich.json").exists():
                    count += 1
    return count


def _load_watchlist() -> dict:
    if WATCHLIST.exists():
        try:
            return cast(
                dict,
                json.loads(
                    WATCHLIST.read_text(
                        encoding="utf-8",
                    ),
                ),
            )
        except (json.JSONDecodeError, OSError):
            pass
    return {"sources": []}


def _load_topic_index() -> dict:
    if TOPIC_INDEX.exists():
        try:
            return cast(
                dict,
                json.loads(
                    TOPIC_INDEX.read_text(
                        encoding="utf-8",
                    ),
                ),
            )
        except (json.JSONDecodeError, OSError):
            pass
    return {"entries": [], "keywords": {}}


def _load_projects() -> list[dict]:
    if PROJECTS_FILE.exists():
        data = json.loads(
            PROJECTS_FILE.read_text(encoding="utf-8")
        )
        return cast(
            list[dict], data.get("projects", []),
        )
    return []


def _latest_research_report() -> dict | None:
    """Load most recent parallel research JSON."""
    if not RESEARCH_DIR.exists():
        return None
    reports = sorted(RESEARCH_DIR.glob(
        "parallel_research_*.json"
    ))
    if not reports:
        return None
    try:
        return cast(
            dict,
            json.loads(
                reports[-1].read_text(
                    encoding="utf-8",
                ),
            ),
        )
    except (json.JSONDecodeError, OSError):
        return None


# ── KPI Calculations ────────────────────────────────────────

def _collection_kpis() -> dict[str, Any]:
    """Phase 1: Collection — source coverage & throughput."""
    watchlist = _load_watchlist()
    sources = watchlist.get("sources", [])
    ingested = _count_ingested_videos()
    enriched = _count_enriched_videos()

    enrichment_rate = (
        round(enriched / ingested * 100, 1)
        if ingested > 0 else 0
    )

    return {
        "total_sources": len(sources),
        "total_ingested": ingested,
        "total_enriched": enriched,
        "enrichment_rate_pct": enrichment_rate,
        "source_health": (
            "HEALTHY" if len(sources) >= 5
            else "LOW" if len(sources) >= 1
            else "EMPTY"
        ),
    }


def _processing_kpis() -> dict[str, Any]:
    """Phase 2: Processing — pipeline health & quality."""
    idx = _load_topic_index()
    entries = idx.get("entries", [])
    keywords = idx.get("keywords", {})

    entry_count = (
        len(entries) if isinstance(entries, list)
        else len(entries.values()) if isinstance(entries, dict)
        else 0
    )
    kw_count = len(keywords) if isinstance(keywords, dict) else 0

    return {
        "topic_index_entries": entry_count,
        "unique_keywords": kw_count,
        "index_density": (
            round(kw_count / max(entry_count, 1), 1)
        ),
    }


def _analysis_kpis() -> dict[str, Any]:
    """Phase 3: Analysis — research depth & coverage."""
    projects = _load_projects()
    report = _latest_research_report()

    total_repos = sum(len(p.get("repos", [])) for p in projects)
    analysed_repos = 0
    total_knowledge_links = 0
    total_next_actions = 0

    if report:
        for p in report.get("projects", []):
            analysed_repos += p.get("repos_analysed", 0)
            total_knowledge_links += len(
                p.get("knowledge_links", [])
            )
            total_next_actions += len(
                p.get("next_actions", [])
            )

    # Milestone progress
    done_ms = 0
    total_ms = 0
    for p in projects:
        for m in p.get("milestones", []):
            total_ms += 1
            if m.get("status") == "done":
                done_ms += 1

    return {
        "total_projects": len(projects),
        "total_repos": total_repos,
        "repos_analysed": analysed_repos,
        "coverage_pct": (
            round(analysed_repos / max(total_repos, 1) * 100)
        ),
        "knowledge_links": total_knowledge_links,
        "next_actions": total_next_actions,
        "milestones_done": done_ms,
        "milestones_total": total_ms,
        "milestone_pct": (
            round(done_ms / max(total_ms, 1) * 100)
        ),
    }


def _synthesis_kpis() -> dict[str, Any]:
    """Phase 4: Synthesis — idea generation & cross-pollination."""
    ideas_dir = ROOT / "reports" / "ideas"
    idea_count = 0
    cross_links = 0
    if ideas_dir.exists():
        idea_files = list(ideas_dir.glob("ideas_*.json"))
        idea_count = len(idea_files)
        for f in idea_files:
            try:
                data = json.loads(
                    f.read_text(encoding="utf-8")
                )
                cross_links += len(
                    data.get("cross_pollinations", [])
                )
            except (json.JSONDecodeError, OSError):
                pass

    return {
        "idea_reports_generated": idea_count,
        "cross_pollinations": cross_links,
    }


def _dissemination_kpis() -> dict[str, Any]:
    """Phase 5: Dissemination — output quality & reach."""
    intel_reports = 0
    if INTEL_DIR.exists():
        intel_reports = len(list(INTEL_DIR.glob("*.json")))

    research_reports = 0
    if RESEARCH_DIR.exists():
        research_reports = len(list(RESEARCH_DIR.glob("*.md")))

    return {
        "intelligence_reports": intel_reports,
        "research_reports": research_reports,
        "total_outputs": intel_reports + research_reports,
    }


def _system_kpis() -> dict[str, Any]:
    """System health KPIs."""
    portfolio = get_portfolio()
    repos = portfolio.get("repositories", [])

    # Count by tier
    tiers: Counter[str] = Counter()
    for r in repos:
        tiers[r.get("risk_tier", "UNKNOWN")] += 1

    return {
        "total_portfolio_repos": len(repos),
        "tiers": dict(tiers),
    }


# ── Dashboard ────────────────────────────────────────────────

def generate_dashboard() -> dict[str, Any]:
    """Generate full research KPI dashboard."""
    t0 = time.monotonic()

    collection = _collection_kpis()
    processing = _processing_kpis()
    analysis = _analysis_kpis()
    synthesis = _synthesis_kpis()
    dissemination = _dissemination_kpis()
    system = _system_kpis()

    # Overall health score (0-100)
    scores = []
    # Collection: sources populated?
    scores.append(
        min(collection["total_sources"] * 10, 25)
    )
    # Processing: enrichment working?
    scores.append(
        min(collection["enrichment_rate_pct"] / 4, 25)
    )
    # Analysis: coverage
    scores.append(
        min(analysis["coverage_pct"] / 4, 25)
    )
    # Dissemination: producing outputs?
    scores.append(
        min(dissemination["total_outputs"] * 5, 25)
    )
    health_score = round(sum(scores))

    health_label = (
        "EXCELLENT" if health_score >= 80
        else "GOOD" if health_score >= 60
        else "FAIR" if health_score >= 40
        else "POOR" if health_score >= 20
        else "CRITICAL"
    )

    elapsed_ms = round(
        (time.monotonic() - t0) * 1000, 1
    )

    dashboard = {
        "generated_at": now_iso(),
        "elapsed_ms": elapsed_ms,
        "health_score": health_score,
        "health_label": health_label,
        "intelligence_cycle": {
            "1_collection": collection,
            "2_processing": processing,
            "3_analysis": analysis,
            "4_synthesis": synthesis,
            "5_dissemination": dissemination,
        },
        "system": system,
    }

    # Save dashboard
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out = METRICS_DIR / f"dashboard_{stamp}.json"
    out.write_text(
        json.dumps(dashboard, indent=2), encoding="utf-8",
    )

    # Append to history
    _append_history(dashboard)

    _emit("metrics.dashboard.generated", {
        "health_score": health_score,
        "health_label": health_label,
    })

    Log.info(
        f"[Metrics] Dashboard: {health_label} "
        f"({health_score}/100) in {elapsed_ms}ms"
    )
    return dashboard


def _append_history(dashboard: dict):
    """Append snapshot to rolling history file."""
    history: list[dict] = []
    if METRICS_HISTORY.exists():
        try:
            history = json.loads(
                METRICS_HISTORY.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            pass

    snapshot = {
        "timestamp": dashboard["generated_at"],
        "health_score": dashboard["health_score"],
        "health_label": dashboard["health_label"],
        "collection_sources": dashboard[
            "intelligence_cycle"
        ]["1_collection"]["total_sources"],
        "ingested": dashboard[
            "intelligence_cycle"
        ]["1_collection"]["total_ingested"],
        "enriched": dashboard[
            "intelligence_cycle"
        ]["1_collection"]["total_enriched"],
        "repos_analysed": dashboard[
            "intelligence_cycle"
        ]["3_analysis"]["repos_analysed"],
        "knowledge_links": dashboard[
            "intelligence_cycle"
        ]["3_analysis"]["knowledge_links"],
        "total_outputs": dashboard[
            "intelligence_cycle"
        ]["5_dissemination"]["total_outputs"],
    }

    history.append(snapshot)
    # Keep last 500 entries
    if len(history) > 500:
        history = history[-500:]

    METRICS_HISTORY.write_text(
        json.dumps(history, indent=2), encoding="utf-8",
    )


def render_dashboard_md(dashboard: dict) -> str:
    """Render dashboard as Markdown."""
    hs = dashboard["health_score"]
    hl = dashboard["health_label"]
    ic = dashboard["intelligence_cycle"]
    c = ic["1_collection"]
    p = ic["2_processing"]
    a = ic["3_analysis"]
    s = ic["4_synthesis"]
    d = ic["5_dissemination"]
    sy = dashboard["system"]

    bar = "\u2588" * (hs // 5) + "\u2591" * (20 - hs // 5)

    lines = [
        "# Research Intelligence Dashboard",
        f"*Generated {dashboard['generated_at']}*",
        "",
        f"## Overall Health: {hl} [{bar}] {hs}/100",
        "",
        "---",
        "## Intelligence Cycle KPIs",
        "",
        "### 1. Collection (OBSERVE)",
        f"- Sources monitored: **{c['total_sources']}**",
        f"- Videos ingested: **{c['total_ingested']}**",
        f"- Videos enriched: **{c['total_enriched']}**",
        f"- Enrichment rate: **{c['enrichment_rate_pct']}%**",
        f"- Source health: **{c['source_health']}**",
        "",
        "### 2. Processing (ORIENT)",
        f"- Topic index entries: **{p['topic_index_entries']}**",
        f"- Unique keywords: **{p['unique_keywords']}**",
        f"- Index density: **{p['index_density']}** kw/entry",
        "",
        "### 3. Analysis (DECIDE)",
        f"- Projects: **{a['total_projects']}**",
        f"- Repos analysed: **{a['repos_analysed']}"
        f"/{a['total_repos']}** "
        f"({a['coverage_pct']}%)",
        f"- Knowledge links: **{a['knowledge_links']}**",
        f"- Next actions: **{a['next_actions']}**",
        f"- Milestones: **{a['milestones_done']}"
        f"/{a['milestones_total']}** "
        f"({a['milestone_pct']}%)",
        "",
        "### 4. Synthesis (ACT)",
        f"- Idea reports: **{s['idea_reports_generated']}**",
        f"- Cross-pollinations: **{s['cross_pollinations']}**",
        "",
        "### 5. Dissemination",
        f"- Intel reports: **{d['intelligence_reports']}**",
        f"- Research reports: **{d['research_reports']}**",
        f"- Total outputs: **{d['total_outputs']}**",
        "",
        "---",
        "## System",
        f"- Portfolio repos: **{sy['total_portfolio_repos']}**",
        f"- Risk tiers: {sy['tiers']}",
    ]

    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Research Metrics & KPIs Dashboard",
    )
    parser.add_argument(
        "command", nargs="?", default="dashboard",
        choices=["dashboard", "snapshot", "history"],
    )
    args = parser.parse_args()

    if args.command == "dashboard":
        d = generate_dashboard()
        md = render_dashboard_md(d)
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        md_path = METRICS_DIR / f"dashboard_{stamp}.md"
        md_path.write_text(md, encoding="utf-8")
        print(md)
    elif args.command == "snapshot":
        d = generate_dashboard()
        hs = d["health_score"]
        hl = d["health_label"]
        print(f"Health: {hl} ({hs}/100)")
    elif args.command == "history":
        if METRICS_HISTORY.exists():
            history = json.loads(
                METRICS_HISTORY.read_text(encoding="utf-8")
            )
            for h in history[-10:]:
                ts = h["timestamp"][:19]
                hs = h["health_score"]
                print(f"  {ts}  {hs}/100")
        else:
            print("No history yet.")


if __name__ == "__main__":
    main()
