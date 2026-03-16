#!/usr/bin/env python3
"""
Intelligence Products — generates trend analysis, cross-repo correlations,
and actionable recommendations from Second Brain content and portfolio data.

Builds on topic_index and weekly_digest to create higher-order intelligence.

Usage::

    python tools/intelligence_products.py trends      # trend detection
    python tools/intelligence_products.py correlate    # cross-repo correlation
    python tools/intelligence_products.py recommend    # repo recommendations
    python tools/intelligence_products.py all    # full report
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    get_portfolio, Log, ensure_dir, now_iso,
)

KNOWLEDGE_DIR = ROOT / "knowledge" / "secondbrain"
TOPIC_INDEX = KNOWLEDGE_DIR / "topic_index.json"
REPORTS_DIR = ROOT / "reports" / "intelligence"
_cfg = json.loads(
    (ROOT / "config" / "settings.json").read_text(encoding="utf-8"),
)
REPOS_BASE = (ROOT / _cfg["repos_base"]).resolve()
ensure_dir(REPORTS_DIR)


# ── Trend Detection ─────────────────────────────────────────────────────

def _load_topic_index() -> dict[str, Any]:
    if TOPIC_INDEX.exists():
        try:
            data: dict[str, Any] = json.loads(
                TOPIC_INDEX.read_text(encoding="utf-8"),
            )
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"entries": [], "keywords": {}}


def _load_all_entries() -> list[dict[str, Any]]:
    """Load all enriched Second Brain entries with timestamps."""
    entries: list[dict[str, Any]] = []
    if not KNOWLEDGE_DIR.exists():
        return entries
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
                    data["_year"] = year_dir.name
                    data["_month"] = month_dir.name
                    data["_vid"] = vid_dir.name
                    entries.append(data)
                except (json.JSONDecodeError, OSError):
                    continue
    return entries


def detect_trends(window_days: int = 30) -> dict[str, Any]:
    """Detect trending topics across ingested content.

    Compares keyword frequency in recent content vs older content
    to identify rising and falling topics.
    """
    index = _load_topic_index()
    entries = index.get("entries", [])

    if not entries:
        return {
            "trends": [], "rising": [], "falling": [],
            "steady": [], "generated_at": now_iso(),
        }

    # Split entries by time (using year/month)
    cutoff = datetime.now() - timedelta(days=window_days)
    cutoff_ym = cutoff.strftime("%Y-%m")

    recent_kw: Counter[str] = Counter()
    older_kw: Counter[str] = Counter()

    for entry in entries:
        ym = f"{entry.get('year', '2026')}-{entry.get('month', '01')}"
        keywords = entry.get("keywords", [])
        if ym >= cutoff_ym:
            recent_kw.update(keywords)
        else:
            older_kw.update(keywords)

    # Calculate trend scores
    all_keywords = set(recent_kw.keys()) | set(older_kw.keys())
    trends: list[dict[str, Any]] = []
    for kw in all_keywords:
        recent_count = recent_kw.get(kw, 0)
        older_count = older_kw.get(kw, 0)
        total = recent_count + older_count
        if total < 2:
            continue
        # Trend score: positive = rising, negative = falling
        score: float
        if older_count == 0:
            score = float(recent_count)
        else:
            score = (recent_count - older_count) / older_count
        trends.append({
            "keyword": kw,
            "recent": recent_count,
            "older": older_count,
            "total": total,
            "trend_score": round(score, 2),
        })

    trends.sort(
        key=lambda t: float(t["trend_score"]),
        reverse=True,
    )
    rising = [
        t for t in trends
        if float(t["trend_score"]) > 0.5
    ][:10]
    falling = [
        t for t in trends
        if float(t["trend_score"]) < -0.3
    ][:10]
    steady = [
        t for t in trends
        if -0.3 <= float(t["trend_score"]) <= 0.5
        and int(t["total"]) >= 3
    ][:10]

    result = {
        "trends": trends[:20], "rising": rising, "falling": falling,
        "steady": steady, "total_keywords": len(all_keywords),
        "window_days": window_days, "generated_at": now_iso(),
    }

    out = REPORTS_DIR / f"trends_{datetime.now().strftime('%Y%m%d')}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    Log.info(
        f"Trends: {len(rising)} rising, "
        f"{len(falling)} falling, {len(steady)} steady",
    )
    return result


# ── Cross-Repository Insight Correlation ─────────────────────────────────

def _get_repo_languages() -> dict[str, str]:
    """Get primary language for each repo from portfolio."""
    langs = {}
    for repo in get_portfolio().get("repositories", []):
        langs[repo["name"]] = repo.get("language_hint", "unknown") or "unknown"
    return langs


def _get_repo_readme_keywords(repo_name: str, top_n: int = 20) -> list[str]:
    """Extract keywords from a repo's README."""
    repo_path = REPOS_BASE / repo_name
    readme_names = (
        "README.md", "readme.md", "README.rst",
        "README.txt", "README",
    )
    for readme_name in readme_names:
        readme = repo_path / readme_name
        if readme.exists():
            try:
                text = readme.read_text(encoding="utf-8", errors="replace")
                words = re.findall(r"[a-z]{3,}", text.lower())
                stop = {
                    "the", "and", "for", "this", "that",
                    "with", "from", "are", "was", "has",
                    "have", "not", "but", "can", "will",
                    "our", "your", "you", "all", "been",
                    "more", "its", "also",
                }
                filtered = [w for w in words if w not in stop]
                return [w for w, _ in Counter(filtered).most_common(top_n)]
            except OSError:
                pass
    return []


def correlate_insights() -> dict[str, Any]:
    """Correlate Second Brain insights with portfolio repos.

    Matches topic keywords from ingested content against repo readmes,
    languages, and descriptions to find relevant connections.
    """
    index = _load_topic_index()
    entries = index.get("entries", [])
    # Build repo keyword profiles
    repo_profiles: dict[str, set[str]] = {}
    repo_langs = _get_repo_languages()

    for repo in get_portfolio().get("repositories", []):
        name = repo["name"]
        keywords = set(_get_repo_readme_keywords(name))
        lang = repo_langs.get(name, "").lower()
        if lang and lang != "unknown":
            keywords.add(lang)
        keywords.add(name.lower().replace("-", " ").replace("_", " "))
        repo_profiles[name] = keywords

    # Correlate: find which intelligence entries match which repos
    correlations: list[dict] = []
    for entry in entries:
        entry_kw = set(entry.get("keywords", []))
        for repo_name, repo_kw in repo_profiles.items():
            overlap = entry_kw & repo_kw
            if len(overlap) >= 2:
                correlations.append({
                    "content_id": entry.get("video_id", "?"),
                    "repo": repo_name,
                    "matching_keywords": sorted(overlap),
                    "relevance_score": len(overlap) / max(len(entry_kw), 1),
                    "abstract": entry.get("abstract", "")[:200],
                })

    # Sort by relevance
    correlations.sort(key=lambda c: c["relevance_score"], reverse=True)

    # Group by repo
    by_repo: dict[str, list] = defaultdict(list)
    for c in correlations:
        by_repo[c["repo"]].append(c)

    result = {
        "correlations": correlations[:50],
        "by_repo": {k: v[:5] for k, v in by_repo.items()},
        "total_correlations": len(correlations),
        "repos_with_insights": len(by_repo),
        "generated_at": now_iso(),
    }

    stamp = datetime.now().strftime("%Y%m%d")
    out = REPORTS_DIR / f"correlations_{stamp}.json"
    out.write_text(
        json.dumps(result, indent=2), encoding="utf-8",
    )
    Log.info(
        f"Correlations: {len(correlations)} across "
        f"{len(by_repo)} repos",
    )
    return result


# ── Actionable Recommendations ───────────────────────────────────────────

def _days_since_update(updated_at: str) -> int:
    """Calculate days since last update."""
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return (datetime.now(dt.tzinfo) - dt).days
    except (ValueError, TypeError):
        return 999


def generate_recommendations() -> dict[str, Any]:
    """Generate actionable recommendations for each active repo."""
    repos = get_portfolio().get("repositories", [])
    recommendations: list[dict] = []

    for repo in repos:
        name = repo["name"]
        repo_path = REPOS_BASE / name
        recs: list[dict] = []

        # 1. Stale repo check
        days = _days_since_update(repo.get("updatedAt", ""))
        if days > 90:
            recs.append({
                "type": "stale_repo", "priority": "HIGH",
                "action": (
                    f"Review {name} — no updates in"
                    f" {days} days. Archive or refresh."
                ),
            })
        elif days > 30:
            recs.append({
                "type": "aging_repo", "priority": "MEDIUM",
                "action": f"Check {name} — last updated {days} days ago.",
            })

        # 2. Missing CI
        if not repo.get("has_ci"):
            has_workflow = (
                (repo_path / ".github" / "workflows").is_dir()
                if repo_path.is_dir() else False
            )
            if not has_workflow:
                recs.append({
                    "type": "no_ci", "priority": "HIGH",
                    "action": (
                        f"Add CI/CD to {name} — "
                        "no GitHub Actions detected."
                    ),
                })

        # 3. Missing tests
        if not repo.get("has_tests"):
            test_dirs = ("tests", "test", "__tests__", "spec")
            has_tests = (
                any((repo_path / d).is_dir() for d in test_dirs)
                if repo_path.is_dir() else False
            )
            if not has_tests:
                recs.append({
                    "type": "no_tests", "priority": "MEDIUM",
                    "action": f"Add tests to {name}.",
                })

        # 4. Low autonomy with good track record
        autonomy = repo.get("autonomy_level", "L0")
        clean = repo.get("clean_scans", 0)
        if autonomy == "L1" and clean >= 10:
            recs.append({
                "type": "graduation_candidate", "priority": "LOW",
                "action": (
                    f"Graduate {name} L1→L2 — "
                    f"{clean} clean scans."
                ),
            })

        # 5. High risk + public
        is_critical = repo.get("risk_tier") == "CRITICAL"
        is_public = repo.get("visibility", "").upper() == "PUBLIC"
        if is_critical and is_public:
            recs.append({
                "type": "high_risk_public", "priority": "HIGH",
                "action": (
                    f"Review {name} — CRITICAL risk, "
                    "PUBLIC visibility."
                ),
            })

        # 6. Missing README
        if repo_path.is_dir():
            has_readme = any(
                (repo_path / f).exists()
                for f in ("README.md", "readme.md", "README.rst")
            )
            if not has_readme:
                recs.append({
                    "type": "no_readme", "priority": "MEDIUM",
                    "action": f"Add README to {name}.",
                })

        if recs:
            recommendations.append({
                "repo": name,
                "recommendations": recs,
                "count": len(recs),
            })

    # Sort by total recommendation count (most needy first)
    recommendations.sort(key=lambda r: r["count"], reverse=True)

    result = {
        "recommendations": recommendations,
        "total_repos": len(repos),
        "repos_with_recommendations": len(recommendations),
        "total_recommendations": sum(r["count"] for r in recommendations),
        "generated_at": now_iso(),
    }

    stamp = datetime.now().strftime("%Y%m%d")
    out = REPORTS_DIR / f"recommendations_{stamp}.json"
    out.write_text(
        json.dumps(result, indent=2), encoding="utf-8",
    )
    n_recs = result["total_recommendations"]
    n_repos = len(recommendations)
    Log.info(f"Recommendations: {n_recs} across {n_repos} repos")
    return result


# ── Full Intelligence Report ─────────────────────────────────────────────

def generate_full_report() -> dict[str, Any]:
    """Generate complete intelligence report."""
    trends = detect_trends()
    correlations = correlate_insights()
    recs = generate_recommendations()

    report = {
        "report_type": "full_intelligence",
        "generated_at": now_iso(),
        "trends": trends,
        "correlations": correlations,
        "recommendations": recs,
    }

    # Also write a Markdown summary
    md_lines = [
        f"# Intelligence Report — {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## Trending Topics",
        "",
    ]
    for t in trends.get("rising", [])[:5]:
        kw = t['keyword']
        sc = t['trend_score']
        rc = t['recent']
        md_lines.append(
            f"- **{kw}** (score: {sc:+.1f}, "
            f"{rc} recent mentions)",
        )
    if not trends.get("rising"):
        md_lines.append(
            "- No rising trends yet (more content needed)",
        )
    md_lines.append("")

    md_lines.append("## Cross-Repo Correlations")
    md_lines.append("")
    for repo, insights in list(correlations.get("by_repo", {}).items())[:5]:
        md_lines.append(f"- **{repo}**: {len(insights)} matching insights")
        for ins in insights[:2]:
            kws = ', '.join(ins['matching_keywords'][:5])
            md_lines.append(f"  - Keywords: {kws}")
    if not correlations.get("by_repo"):
        md_lines.append("- No correlations yet (ingest more content)")
    md_lines.append("")

    md_lines.append("## Recommendations")
    md_lines.append("")
    for r in recs.get("recommendations", [])[:10]:
        md_lines.append(f"### {r['repo']}")
        for rec in r["recommendations"]:
            icons = {
                "HIGH": "!", "MEDIUM": "?", "LOW": "~",
            }
            icon = icons.get(rec["priority"], "-")
            md_lines.append(f"- [{icon}] {rec['action']}")
    md_lines.append("")

    stamp2 = datetime.now().strftime("%Y%m%d")
    md_path = REPORTS_DIR / f"intelligence_{stamp2}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    Log.info(f"Full intelligence report written to {md_path.name}")

    return report


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "trends":
        result = detect_trends()
        print(json.dumps(result, indent=2))
    elif cmd == "correlate":
        result = correlate_insights()
        print(json.dumps(result, indent=2))
    elif cmd == "recommend":
        result = generate_recommendations()
        print(json.dumps(result, indent=2))
    else:
        result = generate_full_report()
        print("\nFull report generated:")
        rising = result['trends'].get('rising', [])
        print(f"  Trends: {len(rising)} rising")
        corr = result['correlations']['total_correlations']
        print(f"  Correlations: {corr}")
        recs_n = result['recommendations']['total_recommendations']
        print(f"  Recommendations: {recs_n}")
