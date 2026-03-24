#!/usr/bin/env python3
"""
Portfolio Intelligence System - LIVE DEMONSTRATION
Shows the system actually working on all 24 repositories
"""
import os
import json
import re
from pathlib import Path
from datetime import datetime

# Configuration
ROOT = Path(__file__).parent / "ResonanceEnergy_BitRageLabour"
CONFIG = json.loads((ROOT/'config'/'settings.json').read_text(encoding='utf-8'))
REPOS_BASE = Path("../../repos").resolve()  # Relative to ResonanceEnergy_BitRageLabour
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def read_simple_yaml(p: Path):
    """Read simple YAML format"""
    data = {}
    if not p.exists():
        return data
    try:
        key = None
        for line in p.read_text(encoding='utf-8', errors='ignore').splitlines():
            s = line.rstrip('\n')
            if not s or s.strip().startswith('#'):
                continue
            if re.match(r'^[A-Za-z0-9_]+:\s*$', s):
                key = s.split(':')[0].strip()
                data[key] = None
            elif ':' in s and not s.lstrip().startswith('-'):
                k, v = s.split(':', 1)
                data[k.strip()] = v.strip().strip('"')
                key = k.strip()
            elif s.lstrip().startswith('- ') and key:
                if data.get(key) is None or not isinstance(data.get(key), list):
                    data[key] = []
                data[key].append(s.strip()[2:])
        return data
    except Exception:
        return {}

def read_json(p: Path):
    """Read JSON file"""
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None

def parse_readme(p: Path):
    """Parse README file for intelligence"""
    info = {'exists': p.exists(), 'size': 0, 'headings': []}
    if not p.exists():
        return info
    txt = p.read_text(encoding='utf-8', errors='ignore')
    info['size'] = len(txt)
    heads = []
    for line in txt.splitlines():
        if line.startswith('#'):
            heads.append(line.strip().lstrip('#').strip())
    info['headings'] = heads[:15]
    return info

def analyze_repository(repo_name: str):
    """Analyze a single repository for intelligence"""
    repo_root = REPOS_BASE / repo_name

    # README analysis
    readme = None
    for cand in [repo_root/'README.md', repo_root/'readme.md', repo_root/'README.MD']:
        if cand.exists():
            readme = cand
            break
    readme_info = parse_readme(readme) if readme else {'exists': False, 'size': 0, 'headings': []}

    # Mandate analysis
    mandate_yaml = repo_root/'.ncl'/'mandate.yaml'
    mandate_json = repo_root/'.ncl'/'mandate.json'
    mandate = read_json(mandate_json) or read_simple_yaml(mandate_yaml)

    # Agents analysis
    agents_json = read_json(repo_root/'.ncl'/'agents.json') or {}

    # Goals/mission signals
    mission = (mandate or {}).get('mission') or ''
    goals = []
    if mission:
        goals.append(mission.strip())
    for h in readme_info.get('headings', []):
        if re.search(r'goal|mission|roadmap|vision|plan|kpi', h, re.I):
            goals.append(h)

    return {
        'repo': repo_name,
        'readme': readme_info,
        'mandate_present': bool(mandate),
        'mandate': mandate,
        'agents_present': bool(agents_json),
        'agents': agents_json,
        'goals_signals': goals,
    }

def main():
    """main handler."""
    print('🚀 PORTFOLIO INTELLIGENCE SYSTEM - LIVE DEMONSTRATION')
    print('=' * 70)
    print(f'Analyzing {REPOS_BASE}')
    print(f'Reports will be saved to {REPORTS_DIR}')
    print()

    if not REPOS_BASE.exists():
        print(f'[ERROR] Repository base not found: {REPOS_BASE}')
        return

    # Get all repositories
    repo_dirs = [d for d in REPOS_BASE.iterdir() if d.is_dir()]
    print(f'[INFO] Found {len(repo_dirs)} repositories to analyze')

    # Analyze each repository
    inventory = []
    for repo_dir in sorted(repo_dirs):
        repo_name = repo_dir.name
        print(f'[ANALYZING] {repo_name}...', end=' ')

        try:
            analysis = analyze_repository(repo_name)
            inventory.append(analysis)
            status = '✅'
        except Exception as e:
            print(f'❌ Error: {e}')
            continue

        print(status)

    # Generate reports
    print()
    print('📊 GENERATING INTELLIGENCE REPORTS...')

    # JSON report
    out_json = REPORTS_DIR / 'portfolio_inventory.json'
    json_data = {
        'generated': datetime.now().isoformat(),
        'repos_base': str(REPOS_BASE),
        'total_repos': len(inventory),
        'inventory': inventory
    }
    out_json.write_text(json.dumps(json_data, indent=2), encoding='utf-8')

    # Markdown report
    out_md = REPORTS_DIR / 'portfolio_inventory.md'
    lines = [f'# Portfolio Inventory - {datetime.now().date().isoformat()}', '']
    lines.append(f'**Total Repositories Analyzed**: {len(inventory)}')
    lines.append(f'**Generated**: {datetime.now().isoformat()}')
    lines.append('')

    for r in inventory:
        lines.append(f"## {r['repo']}")
        lines.append(f"- **README**: {'✅ Present' if r['readme']['exists'] else '❌ Missing'} | Size: {r['readme']['size']} bytes")
        if r['readme']['headings']:
            lines.append(f"  - **Headings**: {', '.join(r['readme']['headings'][:5])}")
        lines.append(f"- **Mandate**: {'✅ Present' if r['mandate_present'] else '❌ Missing'}")
        if r['mandate']:
            tier = r['mandate'].get('tier') or 'TBD'
            lines.append(f"  - **Tier**: {tier}")
        lines.append(f"- **Agents**: {'✅ Present' if r['agents_present'] else '❌ Missing'}")
        if r['goals_signals']:
            lines.append(f"- **Goals/Mission**: {', '.join(sorted(set(r['goals_signals'])))}")
        lines.append('')

    out_md.write_text('\n'.join(lines), encoding='utf-8')

    print('✅ Intelligence gathering complete!')
    print(f'📄 JSON Report: {out_json}')
    print(f'📄 Markdown Report: {out_md}')
    print()

    # Summary statistics
    total_repos = len(inventory)
    readme_present = sum(1 for r in inventory if r['readme']['exists'])
    mandate_present = sum(1 for r in inventory if r['mandate_present'])
    agents_present = sum(1 for r in inventory if r['agents_present'])

    print('📊 PORTFOLIO INTELLIGENCE SUMMARY')
    print('=' * 40)
    print(f'Total Repositories: {total_repos}')
    print(f'README Coverage: {readme_present}/{total_repos} ({readme_present/total_repos*100:.1f}%)')
    print(f'Mandate Coverage: {mandate_present}/{total_repos} ({mandate_present/total_repos*100:.1f}%)')
    print(f'Agent Coverage: {agents_present}/{total_repos} ({agents_present/total_repos*100:.1f}%)')
    print()

    # Show sample analysis
    if inventory:
        print('🔍 SAMPLE REPOSITORY ANALYSIS')
        print('=' * 40)
        sample = inventory[0]  # Show first repo analysis
        print(f"Repository: {sample['repo']}")
        print(f"README: {'Present' if sample['readme']['exists'] else 'Missing'}")
        print(f"Mandate: {'Present' if sample['mandate_present'] else 'Missing'}")
        print(f"Agents: {'Present' if sample['agents_present'] else 'Missing'}")
        if sample['goals_signals']:
            print(f"Goals: {sample['goals_signals'][0][:100]}...")

if __name__ == "__main__":
    main()