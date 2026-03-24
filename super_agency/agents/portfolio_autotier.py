#!/usr/bin/env python3
"""Portfolio auto-tiering: assigns tier + risk_tier based on activity, project config, and repo signals."""
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PORT = ROOT / 'portfolio.json'
PROJECTS_FILE = ROOT / 'config' / 'research_projects.json'

portfolio = json.loads(PORT.read_text(encoding='utf-8')
                       ) if PORT.exists() else {'repositories': []}
now = datetime.now(timezone.utc)

CORE_L = {'ResonanceEnergy_SuperAgency',
    'Super-Agency', 'NCC', 'NCL', 'AZ', 'NCC-Doctrine'}
PRIO_RANK = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}

# Build project lookup: repo_name -> highest project priority
project_priority = {}
if PROJECTS_FILE.exists():
    projects = json.loads(PROJECTS_FILE.read_text(encoding='utf-8'))
    for p in projects.get('projects', []):
        prio = p.get('priority', 'low')
        for repo_name in p.get('repos', []):
            if repo_name not in project_priority or PRIO_RANK.get(
                prio, 0) >PRIO_RANK.get(
                project_priority[repo_name],
                0):
                project_priority[repo_name] = prio


def compute_risk(name: str, days_since_update: int, visibility: str,
                 has_local: bool) ->str:
    """Assign risk tier based on staleness, visibility, project priority, and local presence."""
    if name in CORE_L:
        return 'CRITICAL'
    prio = project_priority.get(name, '')
    if prio == 'critical':
        return 'CRITICAL'
    if prio == 'high' and days_since_update < 90:
        return 'HIGH'
    if visibility == 'public' and days_since_update > 180:
        return 'HIGH'  # public + stale = risky
    if prio in ('high', 'medium'):
        return 'MEDIUM'
    if days_since_update > 365:
        return 'LOW'
    return 'MEDIUM'


for r in portfolio.get('repositories', []):
    updated = r.get('updatedAt')
    try:
        dt = datetime.fromisoformat(updated.replace(
            'Z', '+00:00')) if updated else None
    except Exception:
        dt = None
    days = (now - dt).days if dt else 999
    activity = max(0, 100 - min(100, days))
    visibility = r.get('visibility', 'private')
    repo_dir = ROOT / 'repos' / r['name']
    has_local = repo_dir.is_dir()

    # Tier assignment
    if r['name'] in CORE_L:
        tier = 'L'
    else:
        tier = 'L' if activity >= 60 else ('M' if activity >= 20 else 'S')

    # Risk assignment
    risk = compute_risk(r['name'], days, visibility, has_local)
    if risk in (
        'CRITICAL', 'HIGH') and tier =='L' and r['name'] not in CORE_L:
        tier = 'M'  # high-risk non-core repos get downgraded from auto-L

    r['tier'] = tier
    r['risk_tier'] = risk
    r['autonomy_level'] = 'L2' if risk in ('LOW', 'MEDIUM') else 'L1'

    # Track scan count for graduation eligibility
    r['clean_scans'] = r.get('clean_scans', 0) + 1

PORT.write_text(json.dumps(portfolio, indent=2), encoding='utf-8')

# Check graduation eligibility for L1 repos
try:
    from autonomy_mode import check_graduation_eligibility, graduate_repo
    for r in portfolio.get('repositories', []):
        if r.get('autonomy_level') == 'L1':
            stats = {
                'clean_scans': r.get('clean_scans', 0),
                'incidents': 0,
                'days_at_current': 14,  # default; real tracking requires event log
                'heal_success_rate': 1.0,
            }
            result = check_graduation_eligibility(r['name'], stats)
            if result.get('eligible') and not result.get(
                'reason', '').startswith('eligible — requires council'):
                graduate_repo(r['name'], result['target'])
                print(f"  [GRAD] {r['name']}: L1 -> {result['target']}")
except ImportError:
    pass

print('[OK] Auto-tiering + risk assessment complete.')
