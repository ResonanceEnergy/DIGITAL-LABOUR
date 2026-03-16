#!/usr/bin/env python3
"""
Lint Autofix — scans portfolio repos for lint/formatting issues
and auto-fixes them under L2 autonomy (with receipts).

Supports: Python (ruff/flake8), JS/TS (eslint --fix), generic formatting.
At L1 creates proposals; at L2+ applies fixes and creates receipts.

Usage::

    python tools/lint_autofix.py              # all repos
    python tools/lint_autofix.py <repo>        # specific repo
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    get_portfolio, Log, ensure_dir, now_iso,
)

_cfg = json.loads(
    (ROOT / "config" / "settings.json")
    .read_text(encoding="utf-8"),
)
REPOS_BASE = (ROOT / _cfg["repos_base"]).resolve()
RECEIPTS_DIR = ROOT / "proposals" / "lint_fixes"
ensure_dir(RECEIPTS_DIR)


def _run_cmd(
    args: list[str], cwd: Path, timeout: int = 120,
) -> tuple[int, str, str]:
    """Run a subprocess with timeout."""
    try:
        cp = subprocess.run(
            args, capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=str(cwd), timeout=timeout,
        )
        return (
            cp.returncode,
            (cp.stdout or "").strip(),
            (cp.stderr or "").strip(),
        )
    except FileNotFoundError:
        return 127, "", f"{args[0]} not found"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def _detect_python_issues(repo_path: Path) -> list[dict]:
    """Detect Python lint issues via ruff or basic checks."""
    py_files = list(repo_path.rglob("*.py"))
    if not py_files:
        return []

    # Try ruff first
    ruff_args = [
        sys.executable, "-m", "ruff", "check",
        "--select", "E,W,F",
        "--output-format", "json", ".",
    ]
    rc, out, _ = _run_cmd(ruff_args, repo_path)
    if rc != 127:  # ruff is available
        try:
            issues = json.loads(out) if out else []
            return [
                {
                    "file": i.get("filename", ""),
                    "line": i.get(
                        "location", {},
                    ).get("row", 0),
                    "code": i.get("code", ""),
                    "message": i.get("message", ""),
                    "fixable": i.get("fix") is not None,
                }
                for i in issues[:50]
            ]
        except json.JSONDecodeError:
            pass

    # Fallback: basic checks
    issues = []
    for f in py_files[:20]:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if line.rstrip() != line:
                    rel = str(
                        f.relative_to(repo_path),
                    )
                    issues.append({
                        "file": rel,
                        "line": i,
                        "code": "W291",
                        "message": "trailing whitespace",
                        "fixable": True,
                    })
                if len(line) > 120:
                    rel = str(
                        f.relative_to(repo_path),
                    )
                    issues.append({
                        "file": rel,
                        "line": i,
                        "code": "E501",
                        "message": (
                            f"line too long "
                            f"({len(line)} > 120)"
                        ),
                        "fixable": False,
                    })
            if lines and lines[-1] != "":
                rel = str(
                    f.relative_to(repo_path),
                )
                issues.append({
                    "file": rel,
                    "line": len(lines),
                    "code": "W292",
                    "message": (
                        "no newline at end of file"
                    ),
                    "fixable": True,
                })
        except OSError:
            continue
    return issues[:50]


def _detect_js_issues(repo_path: Path) -> list[dict]:
    """Detect JS/TS lint issues."""
    pkg = repo_path / "package.json"
    if not pkg.exists():
        return []

    # Check for eslint config
    eslint_configs = (
        list(repo_path.glob(".eslintrc*"))
        + list(repo_path.glob("eslint.config.*"))
    )
    if not eslint_configs:
        return []

    eslint_cmd = [
        "npx", "--no-install", "eslint", ".",
        "--format", "json", "--max-warnings", "50",
    ]
    rc, out, _ = _run_cmd(eslint_cmd, repo_path)
    if rc == 127:
        return []
    try:
        results = json.loads(out) if out else []
        issues = []
        for file_result in results:
            for msg in file_result.get("messages", [])[:10]:
                issues.append({
                    "file": file_result.get("filePath", ""),
                    "line": msg.get("line", 0),
                    "code": msg.get("ruleId", ""),
                    "message": msg.get("message", ""),
                    "fixable": msg.get("fix") is not None,
                })
        return issues[:50]
    except json.JSONDecodeError:
        return []


def _apply_python_fixes(repo_path: Path) -> tuple[int, str]:
    """Apply auto-fixable Python lint fixes using ruff."""
    fix_args = [
        sys.executable, "-m", "ruff", "check",
        "--fix", "--select", "E,W,F", ".",
    ]
    rc, out, err = _run_cmd(fix_args, repo_path)
    if rc == 127:
        # Fallback: fix trailing whitespace manually
        fixed = 0
        for f in repo_path.rglob("*.py"):
            try:
                content = f.read_text(encoding="utf-8")
                cleaned = "\n".join(
                    ln.rstrip()
                    for ln in content.splitlines()
                )
                if not cleaned.endswith("\n"):
                    cleaned += "\n"
                if cleaned != content:
                    f.write_text(cleaned, encoding="utf-8")
                    fixed += 1
            except OSError:
                continue
        return fixed, f"Manually fixed trailing whitespace in {fixed} files"
    return 0, out or err


def scan_repo(repo_name: str) -> dict[str, Any]:
    """Scan a repo for lint issues."""
    repo_path = REPOS_BASE / repo_name
    if not repo_path.is_dir():
        return {"repo": repo_name, "error": "not found", "issues": []}

    issues: list[dict] = []
    issues.extend(_detect_python_issues(repo_path))
    issues.extend(_detect_js_issues(repo_path))

    fixable = sum(1 for i in issues if i.get("fixable"))
    return {
        "repo": repo_name, "issues": issues, "total": len(issues),
        "fixable": fixable, "scanned_at": now_iso(),
    }


def fix_repo(repo_name: str) -> dict[str, Any]:
    """Fix lint issues under L2 autonomy."""
    from autonomy_mode import is_action_allowed

    scan = scan_repo(repo_name)
    if not scan["issues"]:
        return {"repo": repo_name, "status": "clean", "fixed": 0}

    if not is_action_allowed(repo_name, "mutate"):
        # L1: create proposal only
        proposal = {
            "repo": repo_name, "action": "lint_fix",
            "risk": "LOW", "autonomy_required": "L2",
            "created_at": now_iso(), "issues": scan["issues"][:20],
            "total_issues": scan["total"], "fixable": scan["fixable"],
            "description": (
                f"Fix {scan['fixable']} auto-fixable"
                f" lint issues in {repo_name}"
            ),
        }
        ts = datetime.now().strftime('%Y%m%d')
        out = RECEIPTS_DIR / f"lint_{repo_name}_{ts}.json"
        out.write_text(
            json.dumps(proposal, indent=2),
            encoding="utf-8",
        )
        Log.info(f"L1 lint proposal created: {out.name}")
        return {
            "repo": repo_name,
            "status": "proposed",
            "fixed": 0,
            "proposal": str(out.name),
        }

    # L2: apply fixes
    repo_path = REPOS_BASE / repo_name
    fixed_count, detail = _apply_python_fixes(repo_path)

    # Create receipt
    receipt = {
        "repo": repo_name, "action": "lint_autofix", "applied_at": now_iso(),
        "issues_before": scan["total"], "fixed": fixed_count,
        "detail": detail, "autonomy_level": "L2",
    }
    ts = datetime.now().strftime('%Y%m%d')
    receipt_path = (
        RECEIPTS_DIR / f"receipt_{repo_name}_{ts}.json"
    )
    receipt_path.write_text(
        json.dumps(receipt, indent=2), encoding="utf-8",
    )
    Log.info(
        f"L2 lint fixes applied to {repo_name}: "
        f"{fixed_count} fixed, receipt: {receipt_path.name}"
    )
    return {"repo": repo_name, "status": "fixed", "fixed": fixed_count}


def scan_all() -> list[dict]:
    """Scan all portfolio repos for lint issues."""
    results = []
    for repo in get_portfolio().get("repositories", []):
        result = scan_repo(repo["name"])
        results.append(result)
    total_issues = sum(r["total"] for r in results)
    total_fixable = sum(r.get("fixable", 0) for r in results)
    Log.info(
        f"Lint scan complete: {len(results)} repos, "
        f"{total_issues} issues ({total_fixable} fixable)"
    )
    return results


def fix_all() -> list[dict]:
    """Fix lint issues across all repos respecting autonomy levels."""
    results = []
    for repo in get_portfolio().get("repositories", []):
        result = fix_repo(repo["name"])
        results.append(result)
    fixed_total = sum(r.get("fixed", 0) for r in results)
    Log.info(
        f"Lint fix complete: {fixed_total} fixes "
        f"applied across {len(results)} repos"
    )
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = fix_repo(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        results = fix_all()
        print(f"\nProcessed {len(results)} repos")
        for r in results:
            if r.get("fixed", 0) > 0 or r.get("status") == "proposed":
                print(
                    f"  {r['repo']}: {r['status']} "
                    f"({r.get('fixed', 0)} fixed)"
                )
