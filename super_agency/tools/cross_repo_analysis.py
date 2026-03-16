#!/usr/bin/env python3
"""
Cross-repo code analysis — detect duplication, shared patterns,
and reuse opportunities across portfolio repositories.

Usage::

    python tools/cross_repo_analysis.py          # full analysis
    python tools/cross_repo_analysis.py --top 10 # show top 10 duplicate groups
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.common import (  # noqa: E402
    CONFIG, Log, ensure_dir, now_iso, get_portfolio,
)

REPORTS_DIR = ROOT / (CONFIG.get("reports_dir", "reports"))
ensure_dir(REPORTS_DIR)

# File extensions to analyse
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cs", ".go",
    ".rb", ".rs", ".cpp", ".c", ".h", ".swift", ".kt",
}

# Minimum lines for a block to be considered meaningful
MIN_BLOCK_LINES = 6


# ── Hashing ──────────────────────────────────────────────────────────────

def _normalise_line(line: str) -> str:
    """Normalise whitespace for comparison."""
    return line.strip()


def _hash_block(lines: list[str]) -> str:
    """Hash a block of normalised lines."""
    content = "\n".join(lines)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# ── Analysis ─────────────────────────────────────────────────────────────

def _scan_file(file_path: Path, repo_name: str) -> list[dict]:
    """Extract code blocks from a file for duplicate detection."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    lines = [_normalise_line(ln) for ln in text.splitlines()]
    blocks = []

    # Sliding window of MIN_BLOCK_LINES
    for i in range(len(lines) - MIN_BLOCK_LINES + 1):
        window = lines[i:i + MIN_BLOCK_LINES]
        # Skip blocks that are mostly empty/comments
        non_empty = [
            ln for ln in window
            if ln
            and not ln.startswith("#")
            and not ln.startswith("//")
        ]
        if len(non_empty) < MIN_BLOCK_LINES // 2:
            continue
        h = _hash_block(window)
        blocks.append({
            "hash": h,
            "repo": repo_name,
            "file": str(file_path),
            "line": i + 1,
            "preview": window[0][:80] if window else "",
        })

    return blocks


def _find_shared_imports(
    repos: list[tuple[str, Path]],
) -> dict[str, list[str]]:
    """Find imports/dependencies used across multiple repos."""
    import_map: dict[str, set[str]] = defaultdict(set)

    for repo_name, repo_path in repos:
        # Python imports
        for py_file in repo_path.rglob("*.py"):
            if ".git" in py_file.parts:
                continue
            try:
                src = py_file.read_text(
                    encoding="utf-8", errors="ignore",
                )
                for line in src.splitlines():
                    stripped = line.strip()
                    if (
                        stripped.startswith("import ")
                        or stripped.startswith("from ")
                    ):
                        # Extract top-level module
                        parts = stripped.split()
                        if len(parts) >= 2:
                            module = parts[1].split(".")[0]
                            if module and not module.startswith("_"):
                                import_map[module].add(repo_name)
            except Exception:
                continue

        # Node.js dependencies
        pkg = repo_path / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                deps = list(
                    data.get("dependencies", {})
                ) + list(
                    data.get("devDependencies", {})
                )
                for dep in deps:
                    import_map[dep].add(repo_name)
            except Exception:
                pass

    # Only keep imports shared across 2+ repos
    return {mod: sorted(repos_set) for mod, repos_set in import_map.items()
            if len(repos_set) >= 2}


def _detect_similar_files(repos: list[tuple[str, Path]]) -> list[dict]:
    """Find files with identical content across repos."""
    file_hashes: dict[str, list[dict]] = defaultdict(list)

    for repo_name, repo_path in repos:
        for ext in CODE_EXTENSIONS:
            for code_file in repo_path.rglob(f"*{ext}"):
                if (
                    ".git" in code_file.parts
                    or "node_modules"
                    in code_file.parts
                ):
                    continue
                try:
                    content = code_file.read_bytes()
                    if len(content) < 100:
                        continue
                    h = hashlib.sha256(content).hexdigest()[:16]
                    rel = str(code_file.relative_to(repo_path))
                    file_hashes[h].append({
                        "repo": repo_name,
                        "file": rel,
                        "size": len(content),
                    })
                except Exception:
                    continue

    # Only keep files duplicated across repos
    return [{"hash": h, "copies": entries}
            for h, entries in file_hashes.items()
            if len(entries) > 1 and len({e["repo"] for e in entries}) > 1]


def analyse_portfolio(top_n: int = 20) -> str:
    """Run full cross-repo analysis and generate a report."""
    repos_base = Path(CONFIG.get("repos_base", "repos")).resolve()
    portfolio_data = get_portfolio().get(
        "repositories", []
    )

    repos: list[tuple[str, Path]] = []
    for entry in portfolio_data:
        name = entry.get("name", "")
        rp = repos_base / name
        if rp.is_dir():
            repos.append((name, rp))

    Log.info(f"[CrossRepo] Analysing {len(repos)} repositories")

    # 1. Duplicate code blocks
    all_blocks: list[dict] = []
    for repo_name, repo_path in repos:
        for ext in CODE_EXTENSIONS:
            for code_file in repo_path.rglob(f"*{ext}"):
                if (
                    ".git" in code_file.parts
                    or "node_modules"
                    in code_file.parts
                ):
                    continue
                all_blocks.extend(_scan_file(code_file, repo_name))

    # Group by hash, keep only cross-repo duplicates
    hash_groups: dict[str, list[dict]] = defaultdict(list)
    for block in all_blocks:
        hash_groups[block["hash"]].append(block)

    cross_repo_dupes = {
        h: entries for h, entries in hash_groups.items()
        if len({e["repo"] for e in entries}) > 1
    }

    # Sort by number of repos affected
    top_dupes = sorted(
        cross_repo_dupes.items(),
        key=lambda x: len({e["repo"] for e in x[1]}),
        reverse=True,
    )[:top_n]

    # 2. Shared imports
    shared_imports = _find_shared_imports(repos)

    # 3. Identical files
    identical_files = _detect_similar_files(repos)

    # Generate report
    lines = [
        "# Cross-Repository Code Analysis",
        f"*Generated {now_iso()}*",
        f"Repos analysed: {len(repos)}",
        "",
        "## Identical Files Across Repos",
    ]

    if identical_files:
        n = len(identical_files)
        lines.append(
            f"Found {n} files duplicated "
            "across repos:\n"
        )
        for group in identical_files[:top_n]:
            copies = group["copies"]
            repos_involved = ", ".join(sorted({c["repo"] for c in copies}))
            lines.append(
                f"- **{copies[0]['file']}** "
                f"({copies[0]['size']} bytes) "
                f"— in: {repos_involved}"
            )
    else:
        lines.append("No identical files found across repos.\n")

    lines += ["", "## Duplicate Code Blocks (Top Cross-Repo)"]
    if top_dupes:
        n_groups = len(cross_repo_dupes)
        n_top = min(top_n, len(top_dupes))
        lines.append(
            f"Found {n_groups} duplicate block "
            f"groups. Top {n_top}:\n"
        )
        for h, entries in top_dupes:
            repos_list = sorted(
                {e["repo"] for e in entries},
            )
            preview = entries[0].get("preview", "")[:60]
            lines.append(
                f"- **{len(repos_list)} repos** "
                f"| `{preview}...`"
            )
            for repo in repos_list:
                lines.append(f"  - {repo}")
    else:
        lines.append("No cross-repo code duplication detected.\n")

    n_shared = len(shared_imports)
    lines += [
        "", "## Shared Dependencies",
        f"Dependencies used in 2+ repos "
        f"({n_shared} total):\n",
    ]
    top_imports = sorted(
        shared_imports.items(),
        key=lambda x: len(x[1]),
        reverse=True,
    )[:30]
    lines.append("| Dependency | Used In (repos) |")
    lines.append("|------------|-----------------|")
    for mod, repo_list in top_imports:
        lines.append(f"| {mod} | {', '.join(repo_list)} |")

    # Recommendations
    lines += ["", "## Reuse Opportunities"]
    if identical_files:
        n_id = len(identical_files)
        lines.append(
            f"- **{n_id} identical files** could "
            "be extracted into a shared library"
        )
    if len(cross_repo_dupes) > 5:
        n_dup = len(cross_repo_dupes)
        lines.append(
            f"- **{n_dup} duplicate code blocks** "
            "suggest shared utility modules"
        )
    high_share = [m for m, r in shared_imports.items() if len(r) >= 3]
    if high_share:
        lines.append(
            f"- **{len(high_share)} deps** used in "
            "3+ repos — consider standardising"
        )

    md = "\n".join(lines) + "\n"
    out = REPORTS_DIR / "cross_repo_analysis.md"
    out.write_text(md, encoding="utf-8")
    Log.info(f"[CrossRepo] Report saved to {out}")
    return md


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cross-repo code analysis")
    parser.add_argument(
        "--top", type=int, default=20,
        help="Top N duplicate groups to show",
    )
    args = parser.parse_args()
    print(analyse_portfolio(top_n=args.top))
