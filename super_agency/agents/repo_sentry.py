#!/usr/bin/env python3
import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.tools import AgentTool

from .common import (
    CONFIG,
    PORTFOLIO,
    Log,
    categorize_file,
    ensure_dir,
    get_head_commit,
    is_git_repo,
    list_changed_files,
    load_mandate,
    now_iso,
)

REPOS_BASE = Path(CONFIG["repos_base"])

def process_repo(repo_name: str):
    repo_root = REPOS_BASE / repo_name
    if not repo_root.exists():
        Log.warn(f"Repo not found locally: {repo_name} ({repo_root})")
        return

    reports_dir = repo_root / "reports"
    ensure_dir(reports_dir)

    state_dir = repo_root / ".ncl" / "state"
    ensure_dir(state_dir)
    last_file = state_dir / "last_commit.txt"
    last = last_file.read_text().strip() if last_file.exists() else None

    head = get_head_commit(repo_root) if is_git_repo(repo_root) else None
    if head is None:
        Log.warn(f"Not a git repo or git missing: {repo_name}")
        changed = []
    else:
        changed = list_changed_files(repo_root, last)

    by_cat = {"ncl": [], "tests": [], "docs": [], "code": []}
    for status, fn in changed:
        by_cat[categorize_file(fn)].append({"status": status, "file": fn})

    mandate = load_mandate(repo_root)

    plan = {
        "repo": repo_name,
        "timestamp": now_iso(),
        "head": head,
        "since": last,
        "summary": {k: len(v) for k,v in by_cat.items()},
        "changes": by_cat,
        "mandate_snapshot": mandate,
        "next_actions": []
    }

    if plan["summary"] ["tests"] <max(
        1, int(0.1 * max(1, plan["summary"] ["code"]))):
        plan["next_actions"].append(
            "Increase test coverage for modified code.")
    if plan["summary"]["ncl"] > 0:
        plan["next_actions"].append(
            "Review .ncl changes with Gatekeeper before autonomy lift.")
    if plan["summary"]["docs"] < 1 and plan["summary"]["code"] > 0:
        plan["next_actions"].append(
            "Update documentation for notable code changes.")

    json_path = reports_dir / \
        f"delta_plan_{datetime.date.today().isoformat()}.json"
    json_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    md = [f"# Delta Plan — {repo_name}", "", f"**Time:** {plan['timestamp']}",
        f"**HEAD:** {head}", f"**Since:** {last}", ""]
    md.append("## Summary")
    for k,v in plan["summary"].items():
        md.append(f"- {k}: {v}")
    md.append("\n## Next Actions")
    if plan["next_actions"]:
        for a in plan["next_actions"]:
            md.append(f"- {a}")
    else:
        md.append("- None")
    md.append("\n## Changed Files")
    for k in ["ncl","tests","docs","code"]:
        if plan["changes"][k]:
            md.append(f"### {k}")
            for item in plan["changes"][k]:
                md.append(f"- {item['status']} {item['file']}")
    (reports_dir / f"delta_plan_{datetime.date.today().isoformat()}.md").write_text(
        "\n".join(md), encoding='utf-8')

    if head:
        last_file.write_text(head, encoding='utf-8')

    return plan


def analyze_file_content(content: str, file_type: str = "python") -> Dict[str, Any]:
    """
    Analyze file content and return insights for intelligent updates.
    Used by IntelligentRepoBuilder for autonomous repo maintenance.
    """
    analysis = {
        "file_type": file_type,
        "lines": len(content.splitlines()),
        "recommendations": [],
        "quality_score": 1.0,
    }

    if file_type == "python":
        # Check for common patterns
        if "import " in content:
            analysis["has_imports"] = True
        if "def " in content or "class " in content:
            analysis["has_definitions"] = True
        if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
            analysis["recommendations"].append("Add module docstring")
            analysis["quality_score"] -= 0.1

    return analysis


def generate_file_updates(content: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate recommended updates based on file analysis.
    Returns a list of update suggestions for autonomous application.
    """
    updates = []

    for rec in analysis.get("recommendations", []):
        updates.append({
            "type": "recommendation",
            "description": rec,
            "auto_apply": False,  # Requires review
        })

    return updates


def check_repo_status(repo_name: str = None) -> Dict[str, Any]:
    """
    Check the status of a repository or all repositories.
    Returns status information including health, changes, and recommendations.
    """
    results = {
        'timestamp': now_iso(),
        'repositories': [],
        'total_repos': 0,
        'healthy_repos': 0,
        'repos_with_changes': 0
    }

    repos_to_check = []
    if repo_name:
        repos_to_check = [{'name': repo_name}]
    else:
        repos_to_check = PORTFOLIO.get("repositories", [])

    for repo in repos_to_check:
        name = repo.get('name', repo) if isinstance(repo, dict) else repo
        repo_root = REPOS_BASE / name

        repo_status = {
            'name': name,
            'exists': repo_root.exists(),
            'is_git_repo': False,
            'head_commit': None,
            'changes_pending': 0,
            'health': 'unknown'
        }

        if repo_root.exists():
            repo_status['is_git_repo'] = is_git_repo(repo_root)
            if repo_status['is_git_repo']:
                repo_status['head_commit'] = get_head_commit(repo_root)
                changes = list_changed_files(repo_root, None)
                repo_status['changes_pending'] = len(changes)
                repo_status['health'] = 'healthy' if len(
                    changes) < 10 else 'needs_attention'
            else:
                repo_status['health'] = 'not_git'
        else:
            repo_status['health'] = 'not_found'

        results['repositories'].append(repo_status)
        results['total_repos'] += 1
        if repo_status['health'] == 'healthy':
            results['healthy_repos'] += 1
        if repo_status['changes_pending'] > 0:
            results['repos_with_changes'] += 1

    return results


class RepoSentryAgent:
    """AI-powered agent for monitoring and analyzing repository changes"""

    def __init__(self, model_client=None):
        self.name = "RepoSentryAgent"
        self.model_client = model_client
        self.status = "initialized"

        # Create AutoGen agent if model client is available
        if self.model_client:
            self.agent = AssistantAgent(
                "repo_sentry_analyzer", model_client=self.model_client,
                system_message="""You are an expert repository analyst and change detection specialist.
                Your role is to analyze repository changes, identify patterns, assess risks, and provide
                actionable intelligence for autonomous operations.

                Focus on:
                - Code quality and security implications
                - Testing coverage adequacy
                - Documentation completeness
                - Configuration and deployment changes
                - Potential integration impacts

                Provide clear, actionable insights with specific recommendations.""")

    def execute(self, task: str) -> Dict[str, Any]:
        """Execute repository monitoring and analysis task"""
        try:
            # Process all repositories in portfolio
            results = []
            for repo in PORTFOLIO.get("repositories", []):
                repo_result = process_repo(repo["name"])
                if repo_result:
                    results.append(repo_result)

            if not results:
                return {
                    'task': task,
                    'result': 'no repositories processed',
                    'agent': self.name,
                    'timestamp': now_iso(),
                    'status': 'warning'
                }

            # If AI analysis is available, enhance the results
            if self.model_client and self.agent:
                analysis_prompt = f"""
                Analyze the following repository changes and provide strategic insights:

                {json.dumps(results, indent=2)}

                Provide:
                1. Risk assessment for each repository
                2. Integration recommendations
                3. Testing priorities
                4. Documentation needs
                5. Autonomy level recommendations
                """

                # Note: In a full implementation, we would run the agent here
                # For now, return the processed data with AI-ready structure
                ai_insights = {
                    'risk_assessment': 'Analysis requires AI model',
                    'integration_recommendations': 'AI analysis pending',
                    'testing_priorities': 'AI analysis pending',
                    'documentation_needs': 'AI analysis pending',
                    'autonomy_recommendations': 'AI analysis pending'
                }
            else:
                ai_insights = {
                    'risk_assessment': 'AI analysis unavailable',
                    'integration_recommendations': 'Manual review required',
                    'testing_priorities': 'Check test coverage manually',
                    'documentation_needs': 'Review documentation manually',
                    'autonomy_recommendations': 'Manual assessment required'
                }

            return {
                'task': task,
                'result': 'repository analysis completed',
                'agent': self.name,
                'timestamp': now_iso(),
                'repositories_processed': len(results),
                'data': results,
                'ai_insights': ai_insights,
                'status': 'success'
            }

        except Exception as e:
            Log.error(f"RepoSentryAgent execution failed: {e}")
            return {
                'task': task,
                'result': f'error: {str(e)}',
                'agent': self.name,
                'timestamp': now_iso(),
                'status': 'error'
            }
