#!/usr/bin/env python3
"""
Swarm Intelligence — parallel agent teams for complex analysis.

Spawns multiple analysis agents in parallel threads, collects results,
and synthesises a unified report. Each worker runs independently with
its own task context, and a coordinator merges the outputs.

Usage::

    python tools/swarm_intelligence.py --task "Audit ..."
    python tools/swarm_intelligence.py  # default analysis
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.common import (  # noqa: E402
    CONFIG, Log, ensure_dir, now_iso, get_portfolio,
)

REPORTS_DIR = ROOT / (CONFIG.get("reports_dir", "reports"))
ensure_dir(REPORTS_DIR)


# ── Worker Definition ────────────────────────────────────────────────────

class SwarmWorker:
    """A single unit of parallel work."""

    def __init__(
        self, name: str, fn: Callable,
        args: tuple = (), kwargs: dict | None = None,
    ):
        self.name = name
        self.fn = fn
        self.args = args
        self.kwargs = kwargs or {}
        self.result: dict[str, Any] | None = None
        self.error: str | None = None
        self.elapsed_ms: float = 0

    def run(self) -> dict[str, Any]:
        t0 = time.monotonic()
        try:
            self.result = self.fn(*self.args, **self.kwargs)
            self.elapsed_ms = (time.monotonic() - t0) * 1000
            return {
                "worker": self.name, "status": "ok",
                "result": self.result,
                "elapsed_ms": round(self.elapsed_ms, 1),
            }
        except Exception as exc:
            self.error = str(exc)
            self.elapsed_ms = (time.monotonic() - t0) * 1000
            return {
                "worker": self.name, "status": "error",
                "error": self.error,
                "elapsed_ms": round(self.elapsed_ms, 1),
            }


# ── Swarm Coordinator ────────────────────────────────────────────────────

class Swarm:
    """Coordinate parallel worker teams."""

    def __init__(self, name: str = "default", max_workers: int = 4):
        self.name = name
        self.max_workers = max_workers
        self.workers: list[SwarmWorker] = []
        self.results: list[dict] = []

    def add(self, name: str, fn: Callable, *args, **kwargs) -> "Swarm":
        self.workers.append(SwarmWorker(name, fn, args, kwargs))
        return self

    def run(self) -> list[dict]:
        """Execute all workers in parallel, return results."""
        Log.info(f"[Swarm:{self.name}] Launching {len(self.workers)} workers "
                 f"(max_workers={self.max_workers})")
        t0 = time.monotonic()

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(w.run): w for w in self.workers}
            for future in as_completed(futures):
                worker = futures[future]
                try:
                    self.results.append(future.result())
                except Exception as exc:
                    self.results.append({
                        "worker": worker.name,
                        "status": "error",
                        "error": str(exc),
                        "elapsed_ms": 0,
                    })

        elapsed = round((time.monotonic() - t0) * 1000, 1)
        ok = sum(1 for r in self.results if r["status"] == "ok")
        Log.info(
            f"[Swarm:{self.name}] Done — "
            f"{ok}/{len(self.results)} succeeded "
            f"in {elapsed}ms"
        )
        return self.results

    def report(self) -> dict:
        """Generate a summary report of swarm execution."""
        ok = [r for r in self.results if r["status"] == "ok"]
        errors = [r for r in self.results if r["status"] != "ok"]
        total_ms = sum(r.get("elapsed_ms", 0) for r in self.results)
        return {
            "swarm": self.name,
            "timestamp": now_iso(),
            "total_workers": len(self.workers),
            "succeeded": len(ok),
            "failed": len(errors),
            "total_worker_ms": round(total_ms, 1),
            "results": self.results,
        }


# ── Built-in Analysis Workers ───────────────────────────────────────────

def _worker_repo_health(repo_name: str, repo_path: Path) -> dict:
    """Check basic health indicators for a repo."""
    issues = []
    has_readme = (repo_path / "README.md").exists()
    has_tests = (
        any(repo_path.rglob("test_*.py"))
        or (repo_path / "tests").is_dir()
    )
    has_ci = (repo_path / ".github" / "workflows").is_dir()
    has_requirements = (
        (repo_path / "requirements.txt").exists()
        or (repo_path / "package.json").exists()
    )

    if not has_readme:
        issues.append("missing README")
    if not has_tests:
        issues.append("no tests detected")
    if not has_ci:
        issues.append("no CI workflows")
    if not has_requirements:
        issues.append("no dependency manifest")

    return {
        "repo": repo_name, "issues": issues,
        "score": max(0, 4 - len(issues)),
    }


def _worker_activity(repo_name: str, repo_path: Path) -> dict:
    """Check recent activity in a repo via git log."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-10", "--format=%ci"],
            cwd=str(repo_path), capture_output=True, text=True, timeout=10
        )
        dates = result.stdout.strip().splitlines()
        return {"repo": repo_name, "recent_commits": len(dates),
                "latest": dates[0] if dates else "none"}
    except Exception:
        return {"repo": repo_name, "recent_commits": 0, "latest": "unknown"}


def _worker_size(repo_name: str, repo_path: Path) -> dict:
    """Estimate repo size (file count, total bytes)."""
    total_files = 0
    total_bytes = 0
    for f in repo_path.rglob("*"):
        if f.is_file() and ".git" not in f.parts:
            total_files += 1
            try:
                total_bytes += f.stat().st_size
            except OSError:
                pass
    return {"repo": repo_name, "files": total_files,
            "size_mb": round(total_bytes / (1024 * 1024), 2)}


# ── Full-Spectrum Analysis ───────────────────────────────────────────────

def full_spectrum_analysis(max_workers: int = 4) -> str:
    """Run health, activity, and size analysis
    across all portfolio repos in parallel.
    """
    repos_base = Path(CONFIG.get("repos_base", "repos")).resolve()
    portfolio_data = get_portfolio().get(
        "repositories", []
    )

    swarm = Swarm("full-spectrum", max_workers=max_workers)

    for entry in portfolio_data:
        name = entry.get("name", "")
        rp = repos_base / name
        if not rp.is_dir():
            continue
        swarm.add(f"health:{name}", _worker_repo_health, name, rp)
        swarm.add(f"activity:{name}", _worker_activity, name, rp)
        swarm.add(f"size:{name}", _worker_size, name, rp)

    swarm.run()
    report = swarm.report()

    # Synthesise
    health_results = [r["result"] for r in report["results"]
                      if r["status"] == "ok"
                      and r["worker"].startswith("health:")]
    activity_results = [
        r["result"] for r in report["results"]
        if r["status"] == "ok"
        and r["worker"].startswith("activity:")
    ]
    size_results = [r["result"] for r in report["results"]
                    if r["status"] == "ok" and r["worker"].startswith("size:")]

    lines = [
        "# Swarm Intelligence — Full-Spectrum Analysis",
        f"*Generated {now_iso()}*",
        f"Workers: {report['total_workers']} | "
        f"Succeeded: {report['succeeded']} | "
        f"Failed: {report['failed']} | "
        f"Total worker time: {report['total_worker_ms']}ms",
        "",
        "## Repo Health Scores",
        "| Repo | Score | Issues |",
        "|------|-------|--------|",
    ]
    for h in sorted(health_results, key=lambda x: x.get("score", 0)):
        issues_str = ", ".join(h.get("issues", [])) or "none"
        lines.append(f"| {h['repo']} | {h.get('score', 0)}/4 | {issues_str} |")

    lines += [
        "", "## Activity (Last 10 Commits)",
        "| Repo | Commits | Latest |",
        "|------|---------|--------|",
    ]
    for a in activity_results:
        lines.append(
            f"| {a['repo']} | {a['recent_commits']}"
            f" | {a['latest']} |"
        )

    lines += ["", "## Size", "| Repo | Files | Size (MB) |",
              "|------|-------|-----------|"]
    for s in sorted(
        size_results,
        key=lambda x: x.get("size_mb", 0),
        reverse=True,
    ):
        lines.append(f"| {s['repo']} | {s['files']} | {s['size_mb']} |")

    md = "\n".join(lines) + "\n"
    out = REPORTS_DIR / "swarm_analysis.md"
    out.write_text(md, encoding="utf-8")
    Log.info(f"[Swarm] Report saved to {out}")
    return md


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Swarm Intelligence")
    parser.add_argument(
        "--task", default="full",
        help="Task to run (default: full)",
    )
    parser.add_argument(
        "--workers", type=int, default=4,
        help="Max parallel workers",
    )
    args = parser.parse_args()

    if args.task == "full":
        print(full_spectrum_analysis(max_workers=args.workers))
    else:
        # Custom swarm — single worker as demonstration
        swarm = Swarm("custom")
        swarm.add("echo", lambda t: {"echo": t}, args.task)
        swarm.run()
        print(json.dumps(swarm.report(), indent=2))
