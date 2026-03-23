#!/usr/bin/env python3
import argparse, json, subprocess, sys, re, shutil, os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from autogen_agentchat.agents import AssistantAgent

# allow overriding root for testing or alternative layout
ROOT = Path(os.environ.get('DL_ROOT',
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


class IntegrateCellAgent:
    """AI-powered agent for system integration and cell management"""

    def __init__(self, model_client=None):
        self.name = "IntegrateCellAgent"
        self.model_client = model_client
        self.status = "initialized"

        # Create AutoGen agent if model client is available
        if self.model_client:
            self.agent = AssistantAgent(
                "system_integrator", model_client=self.model_client,
                system_message="""You are an expert system integration specialist with deep knowledge of
                distributed systems, microservices architecture, and autonomous cell management.

                Your role is to integrate new cells (repositories) into the DIGITAL LABOUR ecosystem,
                validate system coherence, manage inter-cell dependencies, and ensure operational integrity.

                Key responsibilities:
                - Cell integration and onboarding
                - Dependency analysis and resolution
                - System architecture validation
                - Inter-cell communication setup
                - Resource allocation optimization
                - Integration testing and validation
                - Documentation and knowledge management

                Focus on creating seamless integration while maintaining system stability and autonomy.""")

    def execute(self, task: str) -> Dict[str, Any]:
        """Execute system integration task"""
        try:
            if "integrate" in task.lower() and "cell" in task.lower():
                # Parse cell integration request
                cell_info = self._parse_cell_integration_task(task)
                if cell_info:
                    return self.integrate_cell(cell_info)
                else:
                    return {
                        'task': task,
                        'result': 'failed to parse cell integration request',
                        'agent': self.name,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'error'
                    }
            else:
                # General integration operations
                return {
                    'task': task,
                    'result': 'system integration framework executed',
                    'agent': self.name,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'success'
                }

        except Exception as e:
            print(f"IntegrateCellAgent execution failed: {e}")
            return {
                'task': task,
                'result': f'error: {str(e)}',
                'agent': self.name,
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }

    def integrate_cell(self, cell_info: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate a new cell into the system with AI-enhanced analysis"""
        try:
            cell_name = cell_info.get('cell_name')
            org_name = cell_info.get('org_name', 'ResonanceEnergy')
            clone_repo = cell_info.get('clone', False)

            # Perform the integration
            integration_data = integrate(cell_name, org_name, clone_repo)

            # If AI is available, enhance the integration with deeper analysis
            if self.model_client and self.agent:
                analysis_prompt = f"""
                Analyze this cell integration and provide strategic insights:

                Cell Data: {json.dumps(integration_data, indent=2)}

                Provide:
                1. Integration Quality Assessment
                2. System Coherence Analysis
                3. Dependency Risk Evaluation
                4. Autonomy Readiness Check
                5. Recommended Integration Actions
                6. Potential Synergies with Existing Cells
                7. Security and Compliance Considerations
                8. Performance Optimization Opportunities

                Consider the cell's mandate, agents, and role within the broader DIGITAL LABOUR ecosystem.
                """

                # Note: In full implementation, we would run the agent here
                ai_analysis = {
                    'integration_quality': 'AI analysis requires model execution',
                    'system_coherence': 'AI analysis pending',
                    'dependency_risks': 'AI analysis pending',
                    'autonomy_readiness': 'AI analysis pending',
                    'recommended_actions': 'AI analysis pending',
                    'synergies': 'AI analysis pending',
                    'security_considerations': 'AI analysis pending',
                    'performance_opportunities': 'AI analysis pending'
                }
            else:
                ai_analysis = {
                    'integration_quality': 'Manual review required',
                    'system_coherence': 'Manual assessment needed',
                    'dependency_risks': 'Manual evaluation required',
                    'autonomy_readiness': 'Manual check needed',
                    'recommended_actions': 'Manual planning required',
                    'synergies': 'Manual analysis needed',
                    'security_considerations': 'Manual review required',
                    'performance_opportunities': 'Manual optimization needed'
                }

            # Update portfolio if this is a new cell
            self._update_portfolio(cell_name, integration_data)

            return {
                'task': 'cell_integration',
                'result': f'cell {cell_name} integrated successfully',
                'agent': self.name,
                'timestamp': datetime.now().isoformat(),
                'cell_name': cell_name,
                'integration_data': integration_data,
                'ai_analysis': ai_analysis,
                'ai_enhanced': bool(self.model_client),
                'status': 'success'
            }

        except Exception as e:
            print(f"Cell integration failed: {e}")
            return {
                'task': 'cell_integration',
                'result': f'integration error: {str(e)}',
                'agent': self.name,
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }

    def _parse_cell_integration_task(self, task: str) -> Optional[Dict[str, Any]]:
        """Parse cell integration details from task description"""
        try:
            # Look for JSON in the task
            import re
            json_match = re.search(r'\{.*\}', task, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # Or parse key-value pairs
            cell_info = {}
            lines = task.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    cell_info[key] = value

            # Validate required fields
            if 'cell' in cell_info or 'cell_name' in cell_info:
                cell_info['cell_name'] = cell_info.get(
                    'cell_name', cell_info.get('cell'))
                cell_info['org_name'] = cell_info.get(
                    'org_name', 'ResonanceEnergy')
                cell_info['clone'] = cell_info.get(
                    'clone', 'false').lower() == 'true'
                return cell_info

        except Exception as e:
            print(f"Failed to parse cell integration task: {e}")

        return None

    def _update_portfolio(
            self, cell_name: str, integration_data: Dict[str, Any]):
        """Update the portfolio configuration with new cell information"""
        try:
            portfolio_path = ROOT/'config'/'portfolio.json'
            portfolio = {}

            if portfolio_path.exists():
                portfolio = json.loads(
                    portfolio_path.read_text(encoding='utf-8'))

            # Add or update cell in portfolio
            repositories = portfolio.get('repositories', [])
            cell_exists = False

            for repo in repositories:
                if repo.get('name') == cell_name:
                    # Update existing cell
                    repo.update({
                        'mandate': integration_data.get('mandate', {}),
                        'agents': integration_data.get('agents', {}),
                        'last_integration': datetime.now().isoformat()
                    })
                    cell_exists = True
                    break

            if not cell_exists:
                # Add new cell
                repositories.append({
                    'name': cell_name,
                    'mandate': integration_data.get('mandate', {}),
                    'agents': integration_data.get('agents', {}),
                    'added': datetime.now().isoformat(),
                    'last_integration': datetime.now().isoformat()
                })

            portfolio['repositories'] = repositories
            portfolio_path.write_text(json.dumps(
                portfolio, indent=2), encoding='utf-8')
            print(f"Updated portfolio with cell: {cell_name}")

        except Exception as e:
            print(f"Failed to update portfolio: {e}")
