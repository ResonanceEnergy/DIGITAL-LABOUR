#!/usr/bin/env python3
import subprocess, sys, json, shutil
from pathlib import Path
from datetime import datetime
ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads(
    (ROOT/'config'/'settings.json').read_text(encoding='utf-8'))
PORTFOLIO_JSON = ROOT/'portfolio.json'
PORTFOLIO_YAML = ROOT/'portfolio.yaml'
ORG = CONFIG.get('org','ResonanceEnergy')
if shutil.which('gh') is None:
    print('[ERROR] gh not found. Run gh auth login.',
          file=sys.stderr); sys.exit(2)
cmd = ['gh','repo','list', ORG,'--json',
    'name,visibility,updatedAt,primaryLanguage,isPrivate','-L','500']
cp = subprocess.run(cmd, capture_output=True, text=True)
if cp.returncode != 0:
    print(cp.stderr or cp.stdout); sys.exit(cp.returncode)
repos = json.loads(cp.stdout)
portfolio = json.loads(PORTFOLIO_JSON.read_text(
    encoding='utf-8')) if PORTFOLIO_JSON.exists() else {'repositories':[]}
existing = {r['name']: r for r in portfolio.get('repositories', [])}
updated = []
for r in repos:
    name = r['name']
    vis = 'private' if r.get('isPrivate') else (
        r.get('visibility') or 'public')
    row = existing.get(name) or {'name': name}
    row.update(
        {'name': name, 'visibility': vis,
         'language_hint': (r.get('primaryLanguage') or{}).get('name'),
         'updatedAt': r.get('updatedAt')})
    row.setdefault('tier','TBD'); row.setdefault(
        'autonomy_level','L1'); row.setdefault('risk_tier','TBD')
    updated.append(row)
portfolio['repositories'] = sorted(updated, key=lambda x: (
    (x.get('visibility','public')!='public'), x['name'].lower()))
portfolio['generated'] = datetime.now().isoformat()
PORTFOLIO_JSON.write_text(json.dumps(portfolio, indent=2), encoding='utf-8')
PORTFOLIO_YAML.write_text('# ResonanceEnergy Portfolio Registry\n'+ \
                          json.dumps(portfolio, indent=2), encoding='utf-8')
print(f'[OK] Discovered {len(updated)} repos and updated portfolio.')
