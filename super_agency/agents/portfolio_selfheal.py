#!/usr/bin/env python3
"""
Portfolio Self-Heal — ensures every repo has required scaffolding,
detects common issues, and creates fix proposals.
"""
import json, shutil, subprocess, logging
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads(
    (ROOT / 'config' / 'settings.json').read_text(encoding='utf-8'))
PORT = ROOT / 'portfolio.json'
portfolio = json.loads(PORT.read_text(encoding='utf-8')
                       ) if PORT.exists() else {'repositories': []}
repos_base = Path(CONFIG.get('repos_base', './repos')).resolve()
T = ROOT / 'templates' / 'ncl'
HEAL_LOG = ROOT / 'logs' / 'selfheal.ndjson'
HEAL_LOG.parent.mkdir(parents=True, exist_ok=True)
PROPOSALS_DIR = ROOT / 'proposals' / 'L1'
PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)


def _log_heal(repo: str, action: str, detail: str = ""):
    """Append structured heal record."""
    import datetime
    entry = {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
             "repo": repo, "action": action, "detail": detail}
    try:
        with open(HEAL_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def heal_repo(repo_name: str, repo_path: Path) -> list[str]:
    """Run all heal checks on a single repo. Returns list of actions taken."""
    actions = []

    # 1. Ensure required directories
    ncl = repo_path / '.ncl'
    for p in [ncl, repo_path / 'playbooks', repo_path / 'adr', repo_path / 'tests']:
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            actions.append(f"created dir {p.relative_to(repo_path)}")

    # 2. Scaffold NCL templates
    files = {
        ncl / 'mandate.yaml': T / 'mandate.template.yaml',
        ncl / 'agents.json': T / 'agents.template.json',
        ncl / 'events.schema.json': T / 'events.schema.json',
        ncl / 'policies.md': T / 'policies.md',
        repo_path / 'playbooks' / 'Incident.md': None,
        repo_path / 'adr' / 'ADR-000-template.md': None,
    }
    for dst, src in files.items():
        if not dst.exists():
            if src and src.exists():
                shutil.copyfile(src, dst)
            else:
                dst.write_text('# TODO: fill', encoding='utf-8')
            actions.append(f"created {dst.relative_to(repo_path)}")

    # 3. Check for README
    if not (repo_path / 'README.md').exists() and not (repo_path / 'readme.md').exists():
        (repo_path / \
         'README.md').write_text(f'# {repo_name}\n', encoding='utf-8')
        actions.append("created README.md")

    # 4. Detect stale default branch
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ci'],
            capture_output=True, text=True, cwd=str(repo_path), timeout=10)
        if result.returncode == 0:
            from datetime import datetime, timedelta, timezone
            last_commit = result.stdout.strip()
            if last_commit:
                # Parse git date (e.g. "2025-01-15 10:30:00 -0500")
                dt = datetime.strptime(last_commit[:19], "%Y-%m-%d %H:%M:%S")
                age_days = (datetime.now() - dt).days
                if age_days > 90:
                    actions.append(f"STALE: last commit {age_days} days ago")
    except Exception:
        pass

    # 5. Check for CI config
    ci_patterns = ['.github/workflows',
        '.gitlab-ci.yml', 'Jenkinsfile', '.circleci']
    has_ci = any((repo_path / p).exists() for p in ci_patterns)
    if not has_ci:
        actions.append("MISSING: no CI/CD config detected")

    # 6. Check for dependency manifest
    dep_patterns = ['requirements.txt', 'pyproject.toml',
        'package.json', 'Cargo.toml', 'go.mod', 'Gemfile']
    has_deps = any((repo_path / p).exists() for p in dep_patterns)
    if not has_deps:
        actions.append("MISSING: no dependency manifest found")

    # 7. Check for LICENSE
    if not any(
        (repo_path / f).exists()
        for f in ['LICENSE', 'LICENSE.md', 'LICENSE.txt']):
        actions.append("MISSING: no LICENSE file")

    for a in actions:
        _log_heal(repo_name, a)

    # Create L1 fix proposals for actionable issues
    warnings = [a for a in actions if a.startswith(("STALE", "MISSING"))]
    if warnings:
        _create_fix_proposal(repo_name, warnings)

    return actions


def _create_fix_proposal(repo_name: str, issues: list[str]):
    """Write an L1 fix proposal JSON for the council to review."""
    import datetime
    proposal_id = f"selfheal-{repo_name} -{
        datetime.datetime.now().strftime('%Y%m%d%H%M%S')} "
    proposal = {
        "id": proposal_id,
        "type": "remediation",
        "proposed_by": "portfolio_selfheal",
        "title": f"Fix issues in {repo_name}",
        "repo_name": repo_name,
        "issues": issues,
        "risk": "LOW",
        "autonomy_required": "L1",
        "suggested_actions": [],
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    for issue in issues:
        if issue.startswith("MISSING: no CI/CD"):
            proposal["suggested_actions"].append(
                "Add GitHub Actions CI workflow")
        elif issue.startswith("MISSING: no dependency manifest"):
            proposal["suggested_actions"].append(
                "Create requirements.txt or package.json")
        elif issue.startswith("MISSING: no LICENSE"):
            proposal["suggested_actions"].append("Add MIT LICENSE file")
        elif issue.startswith("STALE"):
            proposal["suggested_actions"].append(
                "Review and update stale repo")

    out_file = PROPOSALS_DIR / f"{proposal_id}.json"
    out_file.write_text(json.dumps(proposal, indent=2), encoding="utf-8")


def main():
    """Run self-heal across the entire portfolio."""
    created = []
    missing = []
    issues = []

    for r in portfolio.get('repositories', []):
        name = r['name']
        rr = repos_base / name
        if not rr.exists():
            missing.append(name)
            continue
        repo_actions = heal_repo(name, rr)
        if repo_actions:
            issues.append((name, repo_actions))
        created.extend(repo_actions)

    # Print summary
    scaffolded = [a for a in created if a.startswith("created")]
    warnings = [a for a in created if a.startswith(("STALE", "MISSING"))]
    print(
        f"[OK] Self-heal complete. Scaffolded: {len(scaffolded)} items. Warnings: {len(warnings)}. Missing clones: {len(missing)}.")

    if warnings:
        print(f"\n  Warnings across repos:")
        for name, acts in issues:
            warns = [a for a in acts if a.startswith(("STALE", "MISSING"))]
            if warns:
                print(f"    {name}:")
                for w in warns:
                    print(f"      - {w}")

    return {"scaffolded": len(scaffolded), "warnings": len(warnings), "missing": missing}


if __name__ == '__main__':
    main()
