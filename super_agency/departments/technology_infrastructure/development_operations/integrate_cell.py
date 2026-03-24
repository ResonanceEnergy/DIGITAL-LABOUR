#!/usr/bin/env python3
import argparse, json, subprocess, sys, re, shutil, os
from pathlib import Path
from datetime import datetime

# allow overriding root for testing or alternative layout
ROOT = Path(os.environ.get('SUPER_AGENCY_ROOT',
            Path(__file__).resolve().parents[1]))
CONFIG = json.loads(
    (ROOT/'config'/'settings.json').read_text(encoding='utf-8'))
REPOS_BASE = Path(CONFIG.get('repos_base','./repos'))
if not REPOS_BASE.is_absolute():
    REPOS_BASE = (ROOT/REPOS_BASE).resolve()
REPORTS_DIR = Path(CONFIG.get('reports_dir','./reports'))
if not REPORTS_DIR.is_absolute():
    REPORTS_DIR = (ROOT/REPORTS_DIR).resolve()
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = ROOT/'docs'; DOCS_DIR.mkdir(parents=True, exist_ok=True)


def read_json(p: Path):
    if not p.exists(): return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None


def read_mandate(p_yaml: Path, p_json: Path):
    j = read_json(p_json)
    if j: return j
    if not p_yaml.exists(): return {}
    data = {}
    key=None
    for line in p_yaml.read_text(encoding='utf-8',
         errors='ignore').splitlines():
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


def integrate(cell: str, org: str, clone: bool=False):
    cell_dir = REPOS_BASE / cell

    if not cell_dir.exists():
        if clone:
            if not shutil.which('gh'):
                print(
                    '[ERROR] gh not found; install GitHub CLI or pre-clone the repo.',
                    file=sys.stderr)
                sys.exit(2)
            cell_dir.parent.mkdir(parents=True, exist_ok=True)
            cmd = ['gh','repo','clone', f'{org}/{cell}', str(cell_dir)]
            print('[RUN]', ' '.join(cmd))
            cp = subprocess.run(cmd)
            if cp.returncode != 0:
                print('[ERROR] clone failed', file=sys.stderr)
                sys.exit(cp.returncode)
        else:
            print(
                f'[ERROR] repo not found locally: {cell_dir}', file=sys.stderr)
            sys.exit(3)

    mandate = read_mandate(cell_dir/'.ncl'/'mandate.yaml',
                           cell_dir/'.ncl'/'mandate.json')
    agents = read_json(cell_dir/'.ncl'/'agents.json') or {}
    readme = None
    for cand in [cell_dir/'README.md', cell_dir/'readme.md', cell_dir/'README.MD']:
        if cand.exists(): readme = cand; break
    readme_headings = []
    if readme:
        for line in readme.read_text(
            encoding='utf-8', errors='ignore').splitlines():
            if line.startswith('#'):
                readme_headings.append(line.strip().lstrip('#').strip())

    out_json = REPORTS_DIR / f'cell_{cell}.json'
    out_md   = DOCS_DIR / f'Cell_{cell}_Report.md'

    data = {
        'repo': cell,
        'generated': datetime.now().isoformat(),
        'paths': {
            'repo_dir': str(cell_dir),
            'mandate_yaml': str(cell_dir/'.ncl'/'mandate.yaml'),
            'mandate_json': str(cell_dir/'.ncl'/'mandate.json'),
            'agents_json': str(cell_dir/'.ncl'/'agents.json'),
            'readme': str(readme) if readme else None,
        },
        'mandate': mandate,
        'agents': agents,
        'readme_headings': readme_headings,
    }

    out_json.write_text(json.dumps(data, indent=2), encoding='utf-8')

    lines = []
    lines.append(f"# Cell Integration Report — {cell}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().date().isoformat()}")
    lines.append("")
    lines.append("## Mandate")
    if mandate:
        tier = mandate.get('tier','TBD')
        owner = mandate.get('owner','Nathan')
        mission = mandate.get('mission','(not set)')
        lines.append(f"- **Tier:** {tier}")
        lines.append(f"- **Owner:** {owner}")
        lines.append(f"- **Mission:**\n\n> {mission}")
    else:
        lines.append("- (no mandate found)")

    lines.append("\n## Agents")
    if agents:
        roles = agents.get('roles',{})
        if roles:
            lines.append("| Role | Quota |")
            lines.append("|---|---|")
            for r, spec in roles.items():
                q = spec.get('quota','1') if isinstance(spec, dict) else spec
                lines.append(f"| {r} | {q} |")
        else:
            lines.append("(no roles listed)")
    else:
        lines.append("(no agents.json found)")

    lines.append("\n## README Headings")
    if readme_headings:
        for h in readme_headings[:20]:
            lines.append(f"- {h}")
    else:
        lines.append("(no README found)")

    sens_path = ROOT/'config'/'sensitivity.json'
    sens = {}
    if sens_path.exists():
        try:
            sens = json.loads(sens_path.read_text(encoding='utf-8'))
        except Exception:
            sens = {}
    sens.setdefault('classes',[])
    if 'neural_data' not in sens['classes']:
        sens['classes'].append('neural_data')
    sens_path.write_text(json.dumps(sens, indent=2), encoding='utf-8')
    lines.append("\n## Sensitivity Classes")
    lines.append(
        "Updated `config/sensitivity.json` to include **neural_data**.")

    if cell.upper() == 'NCL':
        manifest = ROOT/'docs'/'NCL_Digital_Twin_Manifest_v1.md'
        if manifest.exists():
            txt = manifest.read_text(encoding='utf-8')
            footer = "\n\n---\n**Integration status:** Synchronized on " + \
                datetime.now().date().isoformat()
            if 'Integration status:' not in txt:
                manifest.write_text(txt + footer, encoding='utf-8')
            else:
                txt = re.sub(r"\*\*Integration status:\*\*.*",
                             "**Integration status:** Synchronized on " +
                             datetime.now().date().isoformat(),
                             txt)
                manifest.write_text(txt, encoding='utf-8')
            lines.append(
                "\nUpdated NCL Digital Twin Manifest with current integration status.")

    out_md.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'report_md': str(out_md), 'report_json': str(
        out_json), 'repo_dir': str(cell_dir)}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True,
                    help='Repository name (e.g., NCL)')
    ap.add_argument('--org', default=CONFIG.get('org','ResonanceEnergy'))
    ap.add_argument('--clone', action='store_true',
                    help='Clone via gh if missing')
    args = ap.parse_args()
    integrate(args.repo, args.org, args.clone)

if __name__ == '__main__':
    main()
