"""Codebase audit — finds errors, warnings, gaps, and stubs."""
import os
import ast
import json
import re
import sys

SKIP_DIRS = {'.venv', '__pycache__', '.git', 'node_modules', 'output', 'data', '.mypy_cache'}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

errors = []
warnings = []
gaps = []
stats = {"files": 0, "lines": 0, "functions": 0, "classes": 0}


def scan_py(path):
    rel = os.path.relpath(path, ROOT)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()
    lines = source.strip().split('\n')
    stats["files"] += 1
    stats["lines"] += len(lines)

    # Syntax check
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as e:
        errors.append(("SYNTAX", rel, str(e)))
        return

    basename = os.path.basename(path)

    # Stub detection
    if basename != '__init__.py' and len(lines) < 5 and 'pass' in source:
        gaps.append(("STUB", rel, f"{len(lines)} lines — likely stub"))

    # Count functions/classes
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            stats["functions"] += 1
        elif isinstance(node, ast.ClassDef):
            stats["classes"] += 1

    # Bare excepts
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            warnings.append(("BARE_EXCEPT", rel, f"L{node.lineno}"))

    # Line-level checks
    for i, line in enumerate(lines, 1):
        upper = line.upper().strip()

        # TODOs
        if 'TODO' in upper or 'FIXME' in upper or 'HACK' in upper:
            warnings.append(("TODO", rel, f"L{i}: {line.strip()[:80]}"))

        # Hardcoded secrets
        low = line.lower()
        if any(p in low for p in ['api_key = "', 'password = "', 'secret = "', "api_key = '"]):
            if 'os.getenv' not in line and 'environ' not in line and not line.strip().startswith('#'):
                errors.append(("HARDCODED", rel, f"L{i}: possible hardcoded secret"))

        # Print statements in non-test/non-script files
        # (skip — too noisy for this project)

    # Import gaps — modules importing things that don't exist
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            # Check for common broken imports
            if mod.startswith('utils.') or mod.startswith('agents.') or mod.startswith('automation.'):
                pass  # would need runtime check

    # Missing runner.py in agent dirs
    if '/agents/' in rel.replace('\\', '/') and basename == '__init__.py':
        agent_dir = os.path.dirname(path)
        if not os.path.exists(os.path.join(agent_dir, 'runner.py')):
            gaps.append(("MISSING_RUNNER", os.path.relpath(agent_dir, ROOT), "No runner.py"))

    # Empty files (not __init__)
    if basename != '__init__.py' and len(lines) <= 2 and not source.strip():
        gaps.append(("EMPTY", rel, "Empty file"))

    # Functions with pass-only body
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            # Check if body is just 'pass' or docstring + pass
            real_stmts = [s for s in body if not isinstance(s, ast.Expr) or not isinstance(s.value, ast.Constant)]
            if len(real_stmts) == 1 and isinstance(real_stmts[0], ast.Pass):
                if not node.name.startswith('_'):
                    gaps.append(("EMPTY_FUNC", rel, f"L{node.lineno}: {node.name}() — pass-only"))


def scan_agents():
    """Check each agent dir for completeness."""
    agents_dir = os.path.join(ROOT, 'agents')
    if not os.path.isdir(agents_dir):
        return
    for name in sorted(os.listdir(agents_dir)):
        agent_path = os.path.join(agents_dir, name)
        if not os.path.isdir(agent_path) or name.startswith('_'):
            continue
        has_runner = os.path.exists(os.path.join(agent_path, 'runner.py'))
        has_init = os.path.exists(os.path.join(agent_path, '__init__.py'))
        has_prompts = any(f.endswith('.md') for f in os.listdir(agent_path))

        if not has_runner:
            gaps.append(("AGENT_GAP", f"agents/{name}", "Missing runner.py"))
        if not has_init:
            gaps.append(("AGENT_GAP", f"agents/{name}", "Missing __init__.py"))
        if not has_prompts:
            gaps.append(("AGENT_GAP", f"agents/{name}", "No prompt .md files"))


def main():
    # Walk all Python files
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith('.py'):
                scan_py(os.path.join(root, f))

    # Agent completeness
    scan_agents()

    # Report
    print("=" * 70)
    print("  DIGITAL LABOUR — CODEBASE AUDIT")
    print("=" * 70)
    print(f"\n  Files: {stats['files']} | Lines: {stats['lines']:,} | Functions: {stats['functions']} | Classes: {stats['classes']}")
    print(f"\n  ERRORS:   {len(errors)}")
    print(f"  WARNINGS: {len(warnings)}")
    print(f"  GAPS:     {len(gaps)}")

    if errors:
        print(f"\n{'─' * 70}")
        print("  ERRORS")
        print(f"{'─' * 70}")
        for t, p, m in errors:
            print(f"  [{t}] {p}: {m}")

    if warnings:
        print(f"\n{'─' * 70}")
        print("  WARNINGS")
        print(f"{'─' * 70}")
        for t, p, m in warnings[:50]:
            print(f"  [{t}] {p}: {m}")
        if len(warnings) > 50:
            print(f"  ... and {len(warnings) - 50} more")

    if gaps:
        print(f"\n{'─' * 70}")
        print("  GAPS")
        print(f"{'─' * 70}")
        for t, p, m in gaps[:80]:
            print(f"  [{t}] {p}: {m}")
        if len(gaps) > 80:
            print(f"  ... and {len(gaps) - 80} more")

    # Save full report
    report = {"errors": errors, "warnings": warnings, "gaps": gaps, "stats": stats}
    report_path = os.path.join(ROOT, "tests", "results", "audit_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n  Full report → {os.path.relpath(report_path, ROOT)}")


if __name__ == "__main__":
    main()
