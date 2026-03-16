#!/usr/bin/env python3
"""
Auto-Changelog Generator
Generates a Keep-a-Changelog-style CHANGELOG.md from git commit history.
Groups commits by date and type (feat/fix/refactor/docs/chore).
"""

import subprocess
import re
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = ROOT / "CHANGELOG.md"

# Conventional-commit prefix → section name
PREFIX_MAP = {
    "feat": "Added",
    "fix": "Fixed",
    "refactor": "Changed",
    "perf": "Changed",
    "docs": "Documentation",
    "test": "Tests",
    "ci": "CI/CD",
    "chore": "Maintenance",
    "build": "Build",
    "style": "Style",
}


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.stdout.strip()


def _parse_commits(since: str | None = None) -> list[dict]:
    """Return list of {hash, date, prefix, message} dicts."""
    cmd = ["log", "--pretty=format:%h|%ad|%s", "--date=short"]
    if since:
        cmd.append(f"--since={since}")
    raw = _run_git(*cmd)
    if not raw:
        return []

    commits = []
    for line in raw.splitlines():
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        sha, date, msg = parts
        # Try to parse conventional-commit prefix
        m = re.match(r"^(\w+)(?:\(.+?\))?:\s*(.+)", msg)
        if m:
            prefix = m.group(1).lower()
            body = m.group(2)
        else:
            prefix = "chore"
            body = msg
        commits.append({"hash": sha, "date": date,
                       "prefix": prefix, "message": body})
    return commits


def generate_changelog(since: str | None = None, write: bool = False) -> str:
    """Generate changelog markdown from git history.

    Args:
        since: ISO date string (YYYY-MM-DD) to start from. Defaults to last 90 days.
        write: If True, write to CHANGELOG.md.

    Returns:
        The generated markdown string.
    """
    if since is None:
        since = "90 days ago"

    commits = _parse_commits(since)
    if not commits:
        return "No commits found.\n"

    # Group by date → section
    by_date: dict[str, dict[str, list]] = defaultdict(
        lambda: defaultdict(list))
    for c in commits:
        section = PREFIX_MAP.get(c["prefix"], "Other")
        by_date[c["date"]][section].append(c)

    lines = [
        "# Changelog\n",
        "All notable changes to this project will be documented in this file.",
        "Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)\n",
        f"*Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
    ]

    for date in sorted(by_date.keys(), reverse=True):
        lines.append(f"\n## [{date}]")
        sections = by_date[date]
        for section in sorted(sections.keys()):
            lines.append(f"\n### {section}")
            for c in sections[section]:
                lines.append(f"- {c['message']} (`{c['hash']}`)")

    text = "\n".join(lines) + "\n"

    if write:
        CHANGELOG_PATH.write_text(text, encoding="utf-8")
        print(f"[OK] Wrote {CHANGELOG_PATH}")

    return text


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace")
    write_flag = "--write" in sys.argv
    since_arg = None
    for arg in sys.argv[1:]:
        if arg != "--write":
            since_arg = arg
    print(generate_changelog(since=since_arg, write=write_flag))
