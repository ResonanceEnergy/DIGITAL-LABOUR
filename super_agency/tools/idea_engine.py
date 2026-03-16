#!/usr/bin/env python3
"""
Idea Generation Engine — Cross-Pollination & Hypothesis Discovery
==================================================================
Implements automated idea generation across the research portfolio:

  1. Cross-Pollination: finds unexpected connections between repos
     in different projects (e.g. energy concepts × health research)
  2. Gap Analysis: identifies under-explored areas & missing links
  3. Hypothesis Generation: "if X in project A, then maybe Y in B"
  4. Research Questions: generates actionable questions from data
  5. Contradiction Detection: flags conflicting claims across repos

Runs as a standalone tool or as an orchestrator stage.

Usage::

    python tools/idea_engine.py               # full generation
    python tools/idea_engine.py pollinate      # cross-pollination only
    python tools/idea_engine.py gaps           # gap analysis only
    python tools/idea_engine.py hypotheses     # hypothesis gen only
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from datetime import datetime
from itertools import combinations
from pathlib import Path
import sys
from typing import Any, Optional, cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    Log, ensure_dir, now_iso,
)

KNOWLEDGE_DIR = ROOT / "knowledge" / "secondbrain"
TOPIC_INDEX = KNOWLEDGE_DIR / "topic_index.json"
PROJECTS_FILE = ROOT / "config" / "research_projects.json"
IDEAS_DIR = ROOT / "reports" / "ideas"
RESEARCH_DIR = ROOT / "reports" / "research"
SETTINGS = json.loads(
    (ROOT / "config" / "settings.json").read_text(encoding="utf-8"),
)
REPOS_BASE = (ROOT / SETTINGS.get("repos_base", "repos")).resolve()
ensure_dir(IDEAS_DIR)

# Message bus (best-effort)
_bus: Any = None  # noqa: N816
try:
    from agents.message_bus import bus
    _bus = bus
except Exception:
    pass


def _emit(topic: str, payload: Optional[dict] = None):
    if _bus:
        _bus.publish(  # type: ignore[union-attr]
            topic, payload or {}, source="idea_engine",
        )


# ── Data Loaders ────────────────────────────────────────────

def _load_projects() -> list[dict]:
    if PROJECTS_FILE.exists():
        data = json.loads(
            PROJECTS_FILE.read_text(encoding="utf-8")
        )
        return cast(
            list[dict], data.get("projects", []),
        )
    return []


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


def _repo_keywords(repo_name: str, top_n: int = 30) -> set[str]:
    """Extract keywords from repo README and code files."""
    repo_path = REPOS_BASE / repo_name
    words: list[str] = []

    # README
    for name in ("README.md", "readme.md", "README.rst"):
        readme = repo_path / name
        if readme.exists():
            try:
                text = readme.read_text(
                    encoding="utf-8", errors="ignore"
                ).lower()
                words.extend(re.findall(r"[a-z]{4,}", text))
            except OSError:
                pass
            break

    # Scan a few Python files for docstrings
    py_files = list(repo_path.glob("*.py"))[:10]
    for pf in py_files:
        try:
            text = pf.read_text(
                encoding="utf-8", errors="ignore"
            ).lower()
            words.extend(re.findall(r"[a-z]{4,}", text))
        except OSError:
            pass

    # Filter stopwords
    stop = {
        "the", "and", "for", "this", "that", "with",
        "from", "are", "was", "has", "have", "not",
        "but", "can", "will", "our", "your", "you",
        "all", "been", "more", "its", "also", "into",
        "each", "then", "than", "some", "other", "such",
        "when", "what", "where", "which", "while", "how",
        "about", "would", "could", "should", "just",
        "like", "only", "over", "very", "they", "them",
        "their", "there", "here", "these", "those",
        "self", "none", "true", "false", "return",
        "import", "class", "def", "if", "else", "elif",
        "try", "except", "pass", "yield", "raise",
        "print", "path", "file", "name", "data",
        "list", "dict", "str", "int", "float", "bool",
    }
    filtered = [w for w in words if w not in stop]
    counts = Counter(filtered)
    return {w for w, _ in counts.most_common(top_n)}


def _latest_research() -> dict | None:
    """Load latest parallel research report."""
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


# ── Cross-Pollination ───────────────────────────────────────

def cross_pollinate() -> list[dict]:
    """Find unexpected connections between repos in different
    projects by keyword overlap analysis.

    The most valuable discoveries come from distant domains
    sharing concepts (e.g. "resonance" in both energy and
    health research).
    """
    projects = _load_projects()
    if len(projects) < 2:
        return []

    # Build per-project keyword profiles
    project_profiles: dict[str, dict[str, set[str]]] = {}
    for proj in projects:
        pid = proj["id"]
        project_profiles[pid] = {}
        for repo_name in proj.get("repos", []):
            kw = _repo_keywords(repo_name)
            if kw:
                project_profiles[pid][repo_name] = kw

    # Find cross-project keyword overlaps
    cross_links: list[dict] = []
    project_ids = list(project_profiles.keys())

    for p1, p2 in combinations(project_ids, 2):
        for r1, kw1 in project_profiles.get(p1, {}).items():
            for r2, kw2 in project_profiles.get(p2, {}).items():
                overlap = kw1 & kw2
                # Filter common programming terms
                overlap -= {
                    "python", "json", "yaml",
                    "config", "test", "setup",
                    "main", "init", "run",
                    "base", "type", "value",
                    "error", "result", "output",
                    "input", "source", "system",
                }
                if len(overlap) >= 3:
                    relevance = round(
                        len(overlap)
                        / min(len(kw1), len(kw2))
                        * 100, 1,
                    )
                    cross_links.append({
                        "project_a": p1,
                        "repo_a": r1,
                        "project_b": p2,
                        "repo_b": r2,
                        "shared_concepts": sorted(overlap),
                        "concept_count": len(overlap),
                        "relevance_pct": relevance,
                    })

    # Sort by concept count descending
    cross_links.sort(
        key=lambda x: x["concept_count"], reverse=True,
    )

    Log.info(
        f"[IdeaEngine] Cross-pollination: "
        f"{len(cross_links)} connections found"
    )
    return cross_links[:50]  # top 50


# ── Gap Analysis ────────────────────────────────────────────

def analyse_gaps() -> list[dict]:
    """Identify under-explored areas in the research portfolio.

    Checks for:
    - Projects with incomplete milestones
    - Repos with no knowledge links
    - Topic areas with low coverage
    - Projects with few repos relative to scope
    """
    projects = _load_projects()
    research = _latest_research()
    gaps: list[dict] = []

    for proj in projects:
        pid = proj["id"]
        repos = proj.get("repos", [])
        milestones = proj.get("milestones", [])

        # Milestone gaps
        not_started = [
            m for m in milestones
            if m.get("status") == "not-started"
        ]
        if not_started:
            gaps.append({
                "type": "incomplete_milestones",
                "project": pid,
                "severity": "HIGH",
                "detail": (
                    f"{len(not_started)}/{len(milestones)} "
                    "milestones not started"
                ),
                "milestones": [
                    m["name"] for m in not_started
                ],
            })

        # Repos without knowledge links
        if research:
            for p_result in research.get("projects", []):
                if p_result.get("project_id") != pid:
                    continue
                for repo in p_result.get("repos", []):
                    kl = repo.get("knowledge_links", [])
                    if not kl and repo.get("status") == "ok":
                        gaps.append({
                            "type": "no_knowledge_links",
                            "project": pid,
                            "repo": repo["repo"],
                            "severity": "MEDIUM",
                            "detail": (
                                f"{repo['repo']} has no "
                                "knowledge links to "
                                "Second Brain content"
                            ),
                        })

        # Small project (fewer than 2 repos)
        if len(repos) < 2:
            gaps.append({
                "type": "small_project",
                "project": pid,
                "severity": "LOW",
                "detail": (
                    f"{pid} has only {len(repos)} repo(s)"
                    " — consider expanding scope"
                ),
            })

    # Sort by severity
    sev_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    gaps.sort(key=lambda g: sev_order.get(g["severity"], 9))

    Log.info(
        f"[IdeaEngine] Gap analysis: {len(gaps)} gaps found"
    )
    return gaps


# ── Hypothesis Generation ──────────────────────────────────

def generate_hypotheses() -> list[dict]:
    """Generate research hypotheses from cross-project data.

    Uses pattern:
      "If [concept] works in [project_A/repo_A],
       then it might apply to [project_B/repo_B] because
       they share [shared_concepts]."
    """
    cross_links = cross_pollinate()
    hypotheses: list[dict] = []

    for link in cross_links[:20]:
        shared = link["shared_concepts"][:5]
        concept_str = ", ".join(shared)

        hypothesis = {
            "hypothesis": (
                f"If concepts ({concept_str}) are "
                f"relevant in {link['repo_a']} "
                f"({link['project_a']}), they may "
                f"also apply to {link['repo_b']} "
                f"({link['project_b']})"
            ),
            "basis": link,
            "confidence": (
                "high" if link["concept_count"] >= 8
                else "medium" if link["concept_count"] >= 5
                else "low"
            ),
            "suggested_action": (
                f"Cross-reference findings from "
                f"{link['repo_a']} with {link['repo_b']}; "
                f"look for overlapping experiments or data "
                f"on: {concept_str}"
            ),
        }
        hypotheses.append(hypothesis)

    Log.info(
        f"[IdeaEngine] Hypotheses generated: {len(hypotheses)}"
    )
    return hypotheses


# ── Research Questions ──────────────────────────────────────

def generate_research_questions() -> list[dict]:
    """Generate actionable research questions from gaps and
    cross-pollination data.
    """
    gaps = analyse_gaps()
    questions: list[dict] = []

    for gap in gaps:
        if gap["type"] == "incomplete_milestones":
            for ms in gap.get("milestones", [])[:3]:
                questions.append({
                    "question": (
                        f"What blockers prevent milestone "
                        f"'{ms}' in {gap['project']}?"
                    ),
                    "source": "gap_analysis",
                    "priority": gap["severity"],
                })
        elif gap["type"] == "no_knowledge_links":
            questions.append({
                "question": (
                    f"What Second Brain content is "
                    f"relevant to {gap['repo']}? "
                    f"Are we missing ingestion sources?"
                ),
                "source": "gap_analysis",
                "priority": gap["severity"],
            })
        elif gap["type"] == "small_project":
            questions.append({
                "question": (
                    f"Should {gap['project']} be expanded "
                    f"with additional repos, or merged "
                    f"into another project?"
                ),
                "source": "gap_analysis",
                "priority": gap["severity"],
            })

    Log.info(
        f"[IdeaEngine] Research questions: {len(questions)}"
    )
    return questions


# ── Full Report ─────────────────────────────────────────────

def generate_ideas() -> dict[str, Any]:
    """Generate complete idea report."""
    t0 = time.monotonic()

    cross = cross_pollinate()
    gaps = analyse_gaps()
    hypotheses = generate_hypotheses()
    questions = generate_research_questions()

    elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

    report = {
        "generated_at": now_iso(),
        "elapsed_ms": elapsed_ms,
        "cross_pollinations": cross,
        "gaps": gaps,
        "hypotheses": hypotheses,
        "research_questions": questions,
        "summary": {
            "total_cross_links": len(cross),
            "total_gaps": len(gaps),
            "high_severity_gaps": sum(
                1 for g in gaps if g["severity"] == "HIGH"
            ),
            "total_hypotheses": len(hypotheses),
            "total_questions": len(questions),
        },
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    json_path = IDEAS_DIR / f"ideas_{stamp}.json"
    json_path.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )

    md = _render_ideas_md(report)
    md_path = IDEAS_DIR / f"ideas_{stamp}.md"
    md_path.write_text(md, encoding="utf-8")

    _emit("ideas.generated", {
        "cross_links": len(cross),
        "gaps": len(gaps),
        "hypotheses": len(hypotheses),
        "questions": len(questions),
    })

    Log.info(
        f"[IdeaEngine] Report generated in {elapsed_ms}ms "
        f"→ {md_path}"
    )
    return report


def _render_ideas_md(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# Idea Generation Report",
        f"*Generated {report['generated_at']}*",
        "",
        f"**Cross-pollinations:** {s['total_cross_links']} | "
        f"**Gaps:** {s['total_gaps']} "
        f"({s['high_severity_gaps']} HIGH) | "
        f"**Hypotheses:** {s['total_hypotheses']} | "
        f"**Questions:** {s['total_questions']}",
        "",
    ]

    # Cross-pollinations
    lines += ["## Cross-Pollination Discoveries", ""]
    for cp in report["cross_pollinations"][:10]:
        concepts = ", ".join(cp["shared_concepts"][:5])
        lines.append(
            f"- **{cp['repo_a']}** ({cp['project_a']}) "
            f"\u2194 **{cp['repo_b']}** ({cp['project_b']}) "
            f"— *{concepts}* "
            f"({cp['concept_count']} shared, "
            f"{cp['relevance_pct']}%)"
        )
    lines.append("")

    # Gaps
    lines += ["## Research Gaps", ""]
    sev_icon = {
        "HIGH": "\U0001f534", "MEDIUM": "\U0001f7e1",
        "LOW": "\u26aa",
    }
    for gap in report["gaps"][:15]:
        icon = sev_icon.get(gap["severity"], "\u2753")
        lines.append(
            f"- {icon} [{gap['severity']}] {gap['detail']}"
        )
    lines.append("")

    # Hypotheses
    lines += ["## Generated Hypotheses", ""]
    for i, h in enumerate(report["hypotheses"][:10], 1):
        lines.append(
            f"{i}. [{h['confidence'].upper()}] "
            f"{h['hypothesis']}"
        )
        lines.append(
            f"   - *Action:* {h['suggested_action']}"
        )
    lines.append("")

    # Questions
    lines += ["## Research Questions", ""]
    for q in report["research_questions"][:15]:
        lines.append(
            f"- [{q['priority']}] {q['question']}"
        )

    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Idea Generation Engine",
    )
    parser.add_argument(
        "command", nargs="?", default="all",
        choices=[
            "all", "pollinate", "gaps", "hypotheses",
        ],
    )
    args = parser.parse_args()

    if args.command == "all":
        report = generate_ideas()
        s = report["summary"]
        print(
            f"Ideas: {s['total_cross_links']} cross-links, "
            f"{s['total_gaps']} gaps, "
            f"{s['total_hypotheses']} hypotheses, "
            f"{s['total_questions']} questions"
        )
    elif args.command == "pollinate":
        links = cross_pollinate()
        for lk in links[:10]:
            print(
                f"  {lk['repo_a']} <-> {lk['repo_b']}: "
                f"{lk['concept_count']} shared concepts"
            )
    elif args.command == "gaps":
        gaps = analyse_gaps()
        for g in gaps[:15]:
            print(f"  [{g['severity']}] {g['detail']}")
    elif args.command == "hypotheses":
        hyps = generate_hypotheses()
        for h in hyps[:10]:
            print(f"  [{h['confidence']}] {h['hypothesis']}")


if __name__ == "__main__":
    main()
