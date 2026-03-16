#!/usr/bin/env python3
import os, json, re
from pathlib import Path
from datetime import datetime
ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads(
    (ROOT/'config'/'settings.json').read_text(encoding='utf-8'))
REPOS_BASE = Path(CONFIG.get('repos_base','./repos')).resolve()
REPORTS_DIR = Path(CONFIG.get('reports_dir','./reports')).resolve()
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def read_simple_yaml(p: Path):
    data = {}
    if not p.exists(): return data
    try:
        key=None
        for line in p.read_text(
            encoding='utf-8', errors='ignore').splitlines():
            s = line.rstrip('\n')
            if not s or s.strip().startswith('#'): continue
            if re.match(r'^[A-Za-z0-9_]+:\s*$', s):
                key = s.split(':')[0].strip(); data[key] = None
            elif ':' in s and not s.lstrip().startswith('-'):
                k,v = s.split(':',1)
                data[k.strip()] = v.strip().strip('"')
                key = k.strip()
            elif s.lstrip().startswith('- ') and key:
                if data.get(key) is None or not isinstance(
                    data.get(key), list): data[key]=[]
                data[key].append(s.strip()[2:])
        return data
    except Exception:
        return {}

def read_json(p: Path):
    if not p.exists(): return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None

def parse_readme(p: Path):
    info = {'exists': p.exists(), 'size': 0, 'headings': []}
    if not p.exists(): return info
    txt = p.read_text(encoding='utf-8', errors='ignore')
    info['size'] = len(txt)
    heads = []
    for line in txt.splitlines():
        if line.startswith('#'):
            heads.append(line.strip().lstrip('#').strip())
    info['headings'] = heads[:15]
    return info

inventory = []
if not REPOS_BASE.exists():
    print(f'[WARN] repos_base not found: {REPOS_BASE}')

for repo_dir in sorted([d for d in REPOS_BASE.iterdir() if d.is_dir()]):
    name = repo_dir.name
    # README
    readme = None
    for cand in [repo_dir/'README.md', repo_dir/'readme.md', repo_dir/'README.MD']:
        if cand.exists(): readme = cand; break
    readme_info = parse_readme(readme) if readme else {
                               'exists': False, 'size': 0, 'headings': []}
    # mandates
    mandate_yaml = repo_dir/'.ncl'/'mandate.yaml'
    mandate_json = repo_dir/'.ncl'/'mandate.json'
    mandate = read_json(mandate_json) or read_simple_yaml(mandate_yaml)
    # agents
    agents_json = read_json(repo_dir/'.ncl'/'agents.json') or {}
    # goals
    mission = (mandate or {}).get('mission') or ''
    goals = []
    if mission: goals.append(mission.strip())
    for h in readme_info.get('headings', []):
        if re.search(r'goal|mission|roadmap|vision|plan|kpi',
                     h, re.I): goals.append(h)
    inventory.append({
        'repo': name,
        'readme': readme_info,
        'mandate_present': bool(mandate),
        'mandate': mandate,
        'agents_present': bool(agents_json),
        'agents': agents_json,
        'goals_signals': goals,
    })

out_json = REPORTS_DIR/'portfolio_inventory.json'
out_md   = REPORTS_DIR/'portfolio_inventory.md'

out_json.write_text(
    json.dumps(
        {'generated': datetime.now().isoformat(),
         'repos_base': str(REPOS_BASE),
         'inventory': inventory},
        indent=2),
    encoding='utf-8')

lines = [f'# Portfolio Inventory - {datetime.now().date().isoformat()}', '']
for r in inventory:
    lines.append(f"## {r['repo']}")
    lines.append(
        f"- README: {'yes' if r['readme']['exists'] else 'no'} | size: {r['readme']['size']} bytes")
    if r['readme']['headings']:
        lines.append('  - Headings: ' + ', '.join(r['readme']['headings']))
    lines.append(
        f"- Mandate: {'present' if r['mandate_present'] else 'missing'}")
    if r['mandate']:
        tier = r['mandate'].get('tier') or 'TBD'
        lvl = (r['mandate'].get('autonomy') or {}).get('default_level') if isinstance(
            r['mandate'].get('autonomy'), dict) else 'L1'
        lines.append(f'  - Tier: {tier} | Autonomy default: {lvl}')
    lines.append(
        f"- Agents: {'present' if r['agents_present'] else 'missing'}")
    if r['goals_signals']:
        lines.append('- Goals/Mission Signals: ' + \
                     ', '.join(sorted(set(r['goals_signals']))))
    lines.append('')

out_md.write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps({'wrote':[str(out_json), str(out_md)]}, indent=2))
