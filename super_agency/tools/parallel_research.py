#!/usr/bin/env python3
"""
Parallel Research Engine
========================
Runs research analysis across all 8 projects / 36 repos simultaneously
using the Swarm engine (ThreadPoolExecutor).

Two levels of parallelism:
  1. All projects run in parallel
  2. Within each project, all repos are analysed in parallel

Research lenses per repo:
  - Health: README, tests, CI, dependencies
  - Activity: recent git commits
  - Delta plan: latest sentry-generated delta
  - Code metrics: file count, size, languages
  - Knowledge links: cross-reference with Second Brain topics

Usage::

    python tools/parallel_research.py              # full run
    python tools/parallel_research.py --workers 8  # more threads
    python tools/parallel_research.py --project energy-research
"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    CONFIG, Log, ensure_dir, now_iso, get_portfolio,
)
from swarm_intelligence import Swarm  # noqa: E402

PROJECTS_FILE = ROOT / "config" / "research_projects.json"
REPOS_BASE = Path(CONFIG.get("repos_base", "repos"))
if not REPOS_BASE.is_absolute():
    REPOS_BASE = (ROOT / REPOS_BASE).resolve()
REPORTS_DIR = Path(CONFIG.get("reports_dir", "reports"))
if not REPORTS_DIR.is_absolute():
    REPORTS_DIR = (ROOT / REPORTS_DIR).resolve()
RESEARCH_DIR = REPORTS_DIR / "research"
ensure_dir(RESEARCH_DIR)

# Topic index for knowledge cross-referencing
TOPIC_INDEX = (
    ROOT / "knowledge" / "secondbrain" / "topic_index.json"
)

# Message bus (best-effort)
try:
    from agents.message_bus import bus as _bus
except Exception:
    _bus = None


def _emit(topic: str, payload: dict | None = None):
    if _bus:
        _bus.publish(
            topic, payload or {}, source="parallel_research",
        )


# ── Data loaders ────────────────────────────────────────────

def _load_projects() -> list[dict]:
    if PROJECTS_FILE.exists():
        data = json.loads(
            PROJECTS_FILE.read_text(encoding="utf-8")
        )
        return data.get("projects", [])
    return []


def _load_topic_index() -> dict:
    if TOPIC_INDEX.exists():
        try:
            return json.loads(
                TOPIC_INDEX.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            pass
    return {}


# ── Per-repo research workers ──────────────────────────────

def _research_repo(
    repo_name: str,
    repo_path: Path,
    topic_keywords: set[str],
) -> dict[str, Any]:
    """Run all research lenses on a single repo.

    This function executes inside a thread worker.
    """
    result: dict[str, Any] = {
        "repo": repo_name,
        "exists": repo_path.is_dir(),
    }

    if not repo_path.is_dir():
        result["status"] = "missing"
        return result

    # ── Health ──────────────────────────────────
    has_readme = (repo_path / "README.md").exists()
    has_tests = (
        any(repo_path.rglob("test_*.py"))
        or (repo_path / "tests").is_dir()
    )
    has_ci = (repo_path / ".github" / "workflows").is_dir()
    has_deps = (
        (repo_path / "requirements.txt").exists()
        or (repo_path / "package.json").exists()
    )
    health_issues = []
    if not has_readme:
        health_issues.append("missing README")
    if not has_tests:
        health_issues.append("no tests")
    if not has_ci:
        health_issues.append("no CI")
    if not has_deps:
        health_issues.append("no dependency manifest")
    result["health"] = {
        "score": max(0, 4 - len(health_issues)),
        "issues": health_issues,
    }

    # ── Activity (git log) ─────────────────────
    try:
        cp = subprocess.run(
            [
                "git", "log", "--oneline", "-10",
                "--format=%ci",
            ],
            cwd=str(repo_path),
            capture_output=True, text=True, timeout=10,
        )
        dates = cp.stdout.strip().splitlines()
        result["activity"] = {
            "recent_commits": len(dates),
            "latest": dates[0] if dates else "none",
        }
    except Exception:
        result["activity"] = {
            "recent_commits": 0, "latest": "unknown",
        }

    # ── Code metrics ───────────────────────────
    total_files = 0
    total_bytes = 0
    lang_counts: dict[str, int] = {}
    ext_map = {
        ".py": "Python", ".js": "JavaScript",
        ".ts": "TypeScript", ".java": "Java",
        ".cs": "C#", ".go": "Go", ".rs": "Rust",
        ".md": "Markdown", ".json": "JSON",
        ".html": "HTML", ".css": "CSS",
    }
    for f in repo_path.rglob("*"):
        if f.is_file() and ".git" not in f.parts:
            total_files += 1
            try:
                total_bytes += f.stat().st_size
            except OSError:
                pass
            lang = ext_map.get(f.suffix.lower())
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
    result["metrics"] = {
        "files": total_files,
        "size_mb": round(total_bytes / (1024 * 1024), 2),
        "languages": lang_counts,
    }

    # ── Delta plan (latest) ────────────────────
    delta_dir = repo_path / "reports"
    latest_delta = None
    if delta_dir.is_dir():
        deltas = sorted(delta_dir.glob("delta_plan_*.json"))
        if deltas:
            try:
                latest_delta = json.loads(
                    deltas[-1].read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                pass
    if latest_delta:
        s = latest_delta.get("summary", {})
        result["delta"] = {
            "date": latest_delta.get("date"),
            "head": latest_delta.get("head"),
            "code": s.get("code", 0),
            "tests": s.get("tests", 0),
            "docs": s.get("docs", 0),
            "next_actions": latest_delta.get(
                "next_actions", []
            ),
        }
    else:
        result["delta"] = None

    # ── Knowledge links ────────────────────────
    # Match repo README keywords against topic index
    readme_path = repo_path / "README.md"
    repo_keywords: set[str] = set()
    if readme_path.exists():
        try:
            text = readme_path.read_text(
                encoding="utf-8", errors="ignore"
            ).lower()
            words = set(text.split())
            repo_keywords = words & topic_keywords
        except OSError:
            pass
    result["knowledge_links"] = sorted(repo_keywords)

    result["status"] = "ok"
    return result


# ── Project-level worker ───────────────────────────────────

def _research_project(
    project: dict,
    topic_keywords: set[str],
    max_repo_workers: int,
) -> dict[str, Any]:
    """Research all repos in a project in parallel.

    Runs inside the outer project-level Swarm thread.
    Uses a nested Swarm for repo-level parallelism.
    """
    project_id = project["id"]
    repos = project.get("repos", [])
    milestones = project.get("milestones", [])

    # Nested swarm for repo-level parallelism
    repo_swarm = Swarm(
        f"project:{project_id}",
        max_workers=max_repo_workers,
    )
    for repo_name in repos:
        rp = REPOS_BASE / repo_name
        repo_swarm.add(
            repo_name, _research_repo,
            repo_name, rp, topic_keywords,
        )

    repo_swarm.run()
    repo_report = repo_swarm.report()

    repo_results = [
        r["result"] for r in repo_report["results"]
        if r["status"] == "ok" and r.get("result")
    ]

    # Aggregate project-level metrics
    total_code = 0
    total_tests = 0
    total_docs = 0
    all_next_actions: list[str] = []
    all_knowledge: set[str] = set()
    total_files = 0
    total_size = 0.0
    all_languages: dict[str, int] = {}

    for rr in repo_results:
        d = rr.get("delta")
        if d:
            total_code += d.get("code", 0)
            total_tests += d.get("tests", 0)
            total_docs += d.get("docs", 0)
            for a in d.get("next_actions", []):
                all_next_actions.append(
                    f"[{rr['repo']}] {a}"
                )
        m = rr.get("metrics", {})
        total_files += m.get("files", 0)
        total_size += m.get("size_mb", 0)
        for lang, cnt in m.get("languages", {}).items():
            all_languages[lang] = (
                all_languages.get(lang, 0) + cnt
            )
        for kw in rr.get("knowledge_links", []):
            all_knowledge.add(kw)

    done = sum(
        1 for m in milestones if m.get("status") == "done"
    )
    total_ms_count = len(milestones) if milestones else 1

    return {
        "project_id": project_id,
        "project_name": project["name"],
        "status": project.get("status", "unknown"),
        "priority": project.get("priority", "medium"),
        "description": project.get("description", ""),
        "progress_pct": round(done / total_ms_count * 100),
        "milestones_done": done,
        "milestones_total": len(milestones),
        "repos_analysed": len(repo_results),
        "repos_total": len(repos),
        "aggregate": {
            "code_changes": total_code,
            "test_changes": total_tests,
            "doc_changes": total_docs,
            "total_files": total_files,
            "total_size_mb": round(total_size, 2),
            "languages": all_languages,
        },
        "knowledge_links": sorted(all_knowledge),
        "next_actions": all_next_actions,
        "goals": project.get("goals", []),
        "repos": repo_results,
        "swarm_stats": {
            "workers": repo_report["total_workers"],
            "succeeded": repo_report["succeeded"],
            "failed": repo_report["failed"],
            "worker_ms": repo_report["total_worker_ms"],
        },
    }


# ── Main entry point ──────────────────────────────────────

def run_parallel_research(
    max_project_workers: int = 4,
    max_repo_workers: int = 4,
    project_filter: str | None = None,
) -> str:
    """Execute parallel research across all projects.

    Args:
        max_project_workers: threads for project-level
        max_repo_workers: threads per project for repos
        project_filter: optional project ID to run only one

    Returns:
        Path to the generated markdown report.
    """
    t0 = __import__("time").monotonic()
    date = datetime.date.today().isoformat()

    _emit("research.parallel.start", {
        "date": date,
        "max_project_workers": max_project_workers,
        "max_repo_workers": max_repo_workers,
        "filter": project_filter,
    })

    # Load data
    projects = _load_projects()
    if project_filter:
        projects = [
            p for p in projects if p["id"] == project_filter
        ]

    topic_idx = _load_topic_index()
    topic_keywords: set[str] = set()
    entries = topic_idx.get("entries", [])
    if isinstance(entries, list):
        for entry in entries:
            for kw in entry.get("keywords", []):
                topic_keywords.add(kw.lower())
    elif isinstance(entries, dict):
        for entry in entries.values():
            for kw in entry.get("keywords", []):
                topic_keywords.add(kw.lower())

    if not projects:
        Log.warn("[ParallelResearch] No projects found")
        return ""

    Log.info(
        f"[ParallelResearch] Launching {len(projects)} projects "
        f"({max_project_workers} project workers, "
        f"{max_repo_workers} repo workers each)"
    )

    # Project-level Swarm
    project_swarm = Swarm(
        "parallel-research", max_workers=max_project_workers,
    )
    for proj in projects:
        project_swarm.add(
            proj["id"], _research_project,
            proj, topic_keywords, max_repo_workers,
        )

    project_swarm.run()
    swarm_report = project_swarm.report()

    project_results = [
        r["result"] for r in swarm_report["results"]
        if r["status"] == "ok" and r.get("result")
    ]

    elapsed_s = round(
        (__import__("time").monotonic() - t0), 2
    )

    # ── Generate reports ─────────────────────────
    report_data = {
        "date": date,
        "generated_at": now_iso(),
        "elapsed_seconds": elapsed_s,
        "projects_total": len(projects),
        "projects_analysed": len(project_results),
        "execution": {
            "project_workers": max_project_workers,
            "repo_workers_per_project": max_repo_workers,
            "total_swarm_workers": swarm_report[
                "total_workers"
            ],
            "swarm_succeeded": swarm_report["succeeded"],
            "swarm_failed": swarm_report["failed"],
        },
        "projects": project_results,
    }

    # JSON
    json_path = RESEARCH_DIR / (
        f"parallel_research_{date}.json"
    )
    json_path.write_text(
        json.dumps(report_data, indent=2, default=str),
        encoding="utf-8",
    )

    # Markdown
    md = _render_markdown(report_data)
    md_path = RESEARCH_DIR / (
        f"parallel_research_{date}.md"
    )
    md_path.write_text(md, encoding="utf-8")

    Log.info(
        f"[ParallelResearch] Done in {elapsed_s}s — "
        f"{len(project_results)}/{len(projects)} projects "
        f"→ {md_path}"
    )

    _emit("research.parallel.done", {
        "date": date,
        "elapsed_s": elapsed_s,
        "projects": len(project_results),
        "report": str(md_path),
    })

    return str(md_path)


# ── Markdown renderer ─────────────────────────────────────

def _render_markdown(data: dict) -> str:
    lines = [
        "# Parallel Research Report",
        f"*Generated {data['generated_at']} "
        f"in {data['elapsed_seconds']}s*",
        "",
        f"**Projects:** {data['projects_analysed']}"
        f"/{data['projects_total']} | "
        f"**Workers:** "
        f"{data['execution']['total_swarm_workers']} | "
        f"**Succeeded:** "
        f"{data['execution']['swarm_succeeded']} | "
        f"**Failed:** {data['execution']['swarm_failed']}",
        "",
    ]

    projects = data.get("projects", [])

    # Overview table
    lines += [
        "## Overview",
        "",
        "| Project | Priority | Progress | Files "
        "| Size | Actions |",
        "|---------|----------|----------|-------"
        "|------|---------|",
    ]
    icons = {
        "critical": "\U0001f534",
        "high": "\U0001f7e0",
        "medium": "\U0001f7e1",
        "low": "\u26aa",
    }
    for p in projects:
        icon = icons.get(p.get("priority", ""), "\u26aa")
        pbar = (
            f"{p['progress_pct']}% "
            f"({p['milestones_done']}"
            f"/{p['milestones_total']})"
        )
        agg = p.get("aggregate", {})
        lines.append(
            f"| {icon} {p['project_name']} "
            f"| {p['priority']} "
            f"| {pbar} "
            f"| {agg.get('total_files', 0)} "
            f"| {agg.get('total_size_mb', 0)} MB "
            f"| {len(p.get('next_actions', []))} |"
        )
    lines.append("")

    # Per-project detail
    for p in projects:
        lines += [
            "---",
            f"## {p['project_name']}",
            f"*{p.get('description', '')}*",
            "",
            f"**Status:** {p['status']} | "
            f"**Priority:** {p['priority']} | "
            f"**Repos:** {p['repos_analysed']}"
            f"/{p['repos_total']}",
            "",
        ]

        # Languages
        langs = p.get("aggregate", {}).get("languages", {})
        if langs:
            top = sorted(
                langs.items(), key=lambda x: x[1],
                reverse=True,
            )[:5]
            lines.append(
                "**Languages:** "
                + ", ".join(
                    f"{l} ({c})" for l, c in top
                )
            )
            lines.append("")

        # Knowledge links
        kl = p.get("knowledge_links", [])
        if kl:
            lines.append(
                "**Knowledge Links:** "
                + ", ".join(kl[:10])
            )
            lines.append("")

        # Repo table
        repos = p.get("repos", [])
        if repos:
            lines += [
                "| Repo | Health | Commits "
                "| Files | Size |",
                "|------|--------|---------|"
                "-------|------|",
            ]
            for r in repos:
                h = r.get("health", {})
                a = r.get("activity", {})
                m = r.get("metrics", {})
                score = h.get("score", "?")
                commits = a.get("recent_commits", 0)
                files = m.get("files", 0)
                size = m.get("size_mb", 0)
                lines.append(
                    f"| {r['repo']} | {score}/4 "
                    f"| {commits} "
                    f"| {files} | {size} MB |"
                )
            lines.append("")

        # Next actions
        actions = p.get("next_actions", [])
        if actions:
            lines.append("**Next Actions:**")
            for a in actions[:10]:
                lines.append(f"- {a}")
            if len(actions) > 10:
                lines.append(
                    f"- *...and {len(actions) - 10} more*"
                )
            lines.append("")

    return "\n".join(lines) + "\n"


# ── CLI ──────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Parallel Research Engine",
    )
    parser.add_argument(
        "--workers", type=int, default=4,
        help="Max parallel workers per level (default: 4)",
    )
    parser.add_argument(
        "--project", default=None,
        help="Run only a specific project ID",
    )
    args = parser.parse_args()
    path = run_parallel_research(
        max_project_workers=args.workers,
        max_repo_workers=args.workers,
        project_filter=args.project,
    )
    if path:
        print(f"Report: {path}")
