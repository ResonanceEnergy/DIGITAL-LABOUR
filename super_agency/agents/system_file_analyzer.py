#!/usr/bin/env python3
"""
System File Analyzer — scans Python source files and produces actionable recommendations.

Checks performed per file:
- Missing module-level docstring
- Missing docstrings on public functions and classes
- Bare ``except`` clauses
- TODO / FIXME comments
- Files exceeding a configurable line-count threshold
- Functions missing a return-type annotation
"""

import ast
import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import CONFIG, Log, ensure_dir, now_iso

# ---------------------------------------------------------------------------
# defaults
# ---------------------------------------------------------------------------
_DEFAULT_MAX_LINES = int(CONFIG.get(
    "system_analyzer", {}).get("max_lines", 500))
_DEFAULT_EXCLUDE_DIRS = {"__pycache__",
    ".git", ".venv", "venv", "node_modules"}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _has_module_docstring(tree: ast.Module) -> bool:
    """Return True when *tree* starts with a module-level string literal."""
    if not tree.body:
        return False
    first = tree.body[0]
    return isinstance(
        first, ast.Expr) and isinstance(
        first.value, ast.Constant)


# ---------------------------------------------------------------------------
# per-file analysis
# ---------------------------------------------------------------------------


def analyze_file(path: Path, max_lines: int = _DEFAULT_MAX_LINES) -> Dict[str, Any]:
    """Analyze a single Python source file and return a structured report.

    Args:
        path: Path to the ``.py`` file.
        max_lines: Threshold above which a file is flagged as too long.

    Returns:
        A dict with keys ``path``, ``issues``, and ``line_count``.
    """
    issues: List[str] = []
    source = path.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines()
    line_count = len(lines)

    if line_count > max_lines:
        issues.append(
            f"File exceeds {max_lines} lines ({line_count} lines) — consider splitting into smaller modules."
        )

    # TODO/FIXME scan
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") and any(
            tag in stripped.upper() for tag in ("TODO", "FIXME", "HACK", "XXX")
        ):
            issues.append(f"Line {i}: unresolved annotation — {stripped}")

    # AST-based checks
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        issues.append(f"Syntax error — {exc}")
        return {"path": str(path), "issues": issues, "line_count": line_count}

    # Module docstring
    if not _has_module_docstring(tree):
        issues.append("Missing module-level docstring.")

    for node in ast.walk(tree):
        # function / class docstrings
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
            if not name.startswith("_"):  # public only
                if not (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                ):
                    kind = "class" if isinstance(
                        node, ast.ClassDef) else "function"
                    issues.append(
                        f"Line {node.lineno}: public {kind} '{name}' is missing a docstring."
                    )

        # bare except
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(
                f"Line {node.lineno}: bare 'except' clause — specify the exception type."
            )

        # missing return annotation on public functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_") and node.returns is None:
                issues.append(
                    f"Line {node.lineno}: function '{node.name}' is missing a return-type annotation."
                )

    return {"path": str(path), "issues": issues, "line_count": line_count}


# ---------------------------------------------------------------------------
# directory scan
# ---------------------------------------------------------------------------


def analyze_directory(
    root: Path,
    exclude_dirs: Optional[set] = None,
    max_lines: int = _DEFAULT_MAX_LINES,
) -> List[Dict[str, Any]]:
    """Recursively analyze all Python files under *root*.

    Args:
        root: Directory to scan.
        exclude_dirs: Directory names to skip (defaults to common non-source dirs).
        max_lines: Passed through to :func:`analyze_file`.

    Returns:
        List of per-file analysis dicts.
    """
    if exclude_dirs is None:
        exclude_dirs = _DEFAULT_EXCLUDE_DIRS

    results: List[Dict[str, Any]] = []
    for py_file in sorted(root.rglob("*.py")):
        if any(part in exclude_dirs for part in py_file.parts):
            continue
        try:
            results.append(analyze_file(py_file, max_lines=max_lines))
        except (OSError, UnicodeDecodeError) as exc:
            Log.warn(f"Could not analyze {py_file}: {exc}")
    return results


# ---------------------------------------------------------------------------
# recommendations
# ---------------------------------------------------------------------------

_ISSUE_RECOMMENDATIONS: List[tuple] = [
    ("exceeds", "Break large files into smaller, focused modules."),
    ("docstring",
     "Add docstrings to all public modules, classes, and functions."),
    ("bare 'except'",
     "Replace bare 'except' with specific exception types to improve error handling."),
    ("return-type annotation",
     "Add return-type annotations to public functions for better type safety."),
    ("TODO", "Resolve or create tracked issues for all TODO/FIXME comments."),
    ("FIXME", "Resolve or create tracked issues for all TODO/FIXME comments."),
    ("Syntax error",
     "Fix syntax errors before deploying or running the affected files."),]


def generate_recommendations(file_reports: List[Dict[str, Any]]) -> List[str]:
    """Derive a de-duplicated, prioritised list of recommendations.

    Args:
        file_reports: Output of :func:`analyze_directory`.

    Returns:
        List of recommendation strings ordered by frequency.
    """
    counts: Dict[str, int] = {}
    for report in file_reports:
        for issue in report.get("issues", []):
            for keyword, rec in _ISSUE_RECOMMENDATIONS:
                if keyword.lower() in issue.lower():
                    counts[rec] = counts.get(rec, 0) + 1
                    break

    if not counts:
        return ["No issues detected — system files look healthy."]

    return [rec for rec, _ in sorted(counts.items(), key=lambda x: -x[1])]


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------


def run(
    root: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    max_lines: int = _DEFAULT_MAX_LINES,
) -> Dict[str, Any]:
    """Run the full system-file analysis and persist results.

    Args:
        root: Root directory to scan (defaults to repository root).
        output_dir: Where to write the JSON report (defaults to ``reports/``).
        max_lines: Passed through to :func:`analyze_file`.

    Returns:
        Full analysis report dict.
    """
    if root is None:
        root = Path(__file__).resolve().parents[1]
    if output_dir is None:
        output_dir = root / CONFIG.get("reports_dir", "reports")

    ensure_dir(output_dir)

    Log.info(f"SystemFileAnalyzer: scanning {root}")
    file_reports = analyze_directory(root, max_lines=max_lines)
    recommendations = generate_recommendations(file_reports)

    total_issues = sum(len(r["issues"]) for r in file_reports)
    report = {
        "timestamp": now_iso(),
        "root": str(root),
        "files_analyzed": len(file_reports),
        "total_issues": total_issues,
        "recommendations": recommendations,
        "file_reports": file_reports,
    }

    today = datetime.date.today().isoformat()
    out_path = output_dir / f"system_file_analysis_{today}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    Log.info(
        f"SystemFileAnalyzer: {len(file_reports)} files, {total_issues} issues → {out_path}"
    )
    return report


if __name__ == "__main__":
    run()
