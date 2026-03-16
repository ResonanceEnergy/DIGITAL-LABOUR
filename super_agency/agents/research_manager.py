#!/usr/bin/env python3
"""
Research Project Manager
Reads config/research_projects.json, correlates with repo delta plans,
and generates per-project status reports including progress, recent changes,
and next actions.
"""

import json
import datetime
from pathlib import Path
from typing import Any, Dict, List

from common import ROOT, CONFIG, get_portfolio, Log, ensure_dir


PROJECTS_FILE = ROOT / "config" / "research_projects.json"
REPOS_BASE = Path(CONFIG["repos_base"])
if not REPOS_BASE.is_absolute():
    REPOS_BASE = (ROOT / REPOS_BASE).resolve()
REPORTS_DIR = Path(CONFIG["reports_dir"])
if not REPORTS_DIR.is_absolute():
    REPORTS_DIR = (ROOT / REPORTS_DIR).resolve()
RESEARCH_DIR = REPORTS_DIR / "research"
ensure_dir(RESEARCH_DIR)


def load_projects() -> Dict[str, Any]:
    if PROJECTS_FILE.exists():
        return json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    return {"projects": []}


def get_repo_delta(repo_name: str, date: str) -> Dict[str, Any] | None:
    """Load the delta plan for a repo on a given date."""
    delta_path = REPOS_BASE / repo_name / "reports" / f"delta_plan_{date}.json"
    if delta_path.exists():
        try:
            return json.loads(delta_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def project_status(project: Dict[str, Any], date: str) -> Dict[str, Any]:
    """Build status report for a single research project on a given date."""
    repos = project.get("repos", [])
    milestones = project.get("milestones", [])

    total_code = 0
    total_tests = 0
    total_docs = 0
    total_ncl = 0
    repo_details = []
    next_actions = []

    for repo_name in repos:
        delta = get_repo_delta(repo_name, date)
        detail = {"repo": repo_name, "delta_found": delta is not None}
        if delta:
            s = delta.get("summary", {})
            detail["code"] = s.get("code", 0)
            detail["tests"] = s.get("tests", 0)
            detail["docs"] = s.get("docs", 0)
            detail["ncl"] = s.get("ncl", 0)
            detail["head"] = delta.get("head")
            total_code += detail["code"]
            total_tests += detail["tests"]
            total_docs += detail["docs"]
            total_ncl += detail["ncl"]
            for action in delta.get("next_actions", []):
                next_actions.append(f"[{repo_name}] {action}")
        repo_details.append(detail)

    done = sum(1 for m in milestones if m.get("status") == "done")
    total = len(milestones) if milestones else 1

    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "status": project.get("status", "unknown"),
        "priority": project.get("priority", "medium"),
        "date": date,
        "progress_pct": round(done / total * 100),
        "milestones_done": done,
        "milestones_total": len(milestones),
        "summary": {
            "code": total_code,
            "tests": total_tests,
            "docs": total_docs,
            "ncl": total_ncl,
            "total_changes": total_code + total_tests + total_docs + total_ncl,
        },
        "repos": repo_details,
        "next_actions": next_actions,
        "goals": project.get("goals", []),
    }


def generate_research_report(date: str | None = None) -> str:
    """Generate a full research status report for all projects."""
    if date is None:
        date = datetime.date.today().isoformat()

    data = load_projects()
    projects = data.get("projects", [])

    report_data = {
        "date": date,
        "generated_at": datetime.datetime.now().isoformat(),
        "projects": [],
    }

    md_lines = [f"# Research Projects Report — {date}", ""]

    active_projects = [p for p in projects if p.get(
        "status") in ("active", "in-progress")]
    planned_projects = [p for p in projects if p.get("status") == "planned"]
    paused_projects = [p for p in projects if p.get("status") == "paused"]

    # Summary table
    md_lines.append("## Overview")
    md_lines.append("")
    md_lines.append(f"| Project | Priority | Progress | Changes Today |")
    md_lines.append(f"|---------|----------|----------|---------------|")

    for proj in projects:
        status = project_status(proj, date)
        report_data["projects"].append(status)
        pbar = f"{
            status['progress_pct']} % ({
            status['milestones_done']} /{
            status['milestones_total']}) "
        changes = status["summary"]["total_changes"]
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}.get(
            status["priority"], "⚪"
        )
        md_lines.append(
            f"| {icon} {status['project_name']} | {status['priority']} | {pbar} | {changes} |"
        )

    md_lines.append("")

    # Active projects detail
    if active_projects:
        md_lines.append("---")
        md_lines.append("## Active Projects")
        md_lines.append("")

    for proj in active_projects:
        status = project_status(proj, date)
        md_lines.append(f"### {proj['name']}")
        md_lines.append(f"*{proj.get('description', '')}*")
        md_lines.append("")

        # Milestones
        if proj.get("milestones"):
            md_lines.append("**Milestones:**")
            for m in proj["milestones"]:
                icon = {"done": "✅", "in-progress": "🔄",
                    "not-started": "⬜"}.get( m["status"], "⬜" )
                md_lines.append(f"- {icon} {m['name']}")
            md_lines.append("")

        # Repo activity
        active_repos = [r for r in status["repos"] if r.get(
            "code", 0) + r.get("tests", 0) + r.get("docs", 0) > 0]
        if active_repos:
            md_lines.append("**Active Repos Today:**")
            for r in active_repos:
                md_lines.append(
                    f"- {r['repo']}: code={r['code']}, tests={r['tests']}, docs={r['docs']}"
                )
            md_lines.append("")

        # Next actions
        if status["next_actions"]:
            md_lines.append("**Next Actions:**")
            for a in status["next_actions"]:
                md_lines.append(f"- {a}")
            md_lines.append("")

    # Planned projects
    if planned_projects:
        md_lines.append("---")
        md_lines.append("## Planned Projects")
        md_lines.append("")
        for proj in planned_projects:
            md_lines.append(
                f"- **{proj['name']}** — {proj.get('description', 'No description')}")
        md_lines.append("")

    # Write outputs
    md_path = RESEARCH_DIR / f"research_report_{date}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    json_path = RESEARCH_DIR / f"research_report_{date}.json"
    json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    Log.info(f"Research report written to {md_path}")
    return str(md_path)


def get_all_project_statuses(date: str | None = None) -> List[Dict[str, Any]]:
    """Return status data for all projects (used by API)."""
    if date is None:
        date = datetime.date.today().isoformat()
    data = load_projects()
    return [project_status(p, date) for p in data.get("projects", [])]


if __name__ == "__main__":
    path = generate_research_report()
    print(f"Report: {path}")
