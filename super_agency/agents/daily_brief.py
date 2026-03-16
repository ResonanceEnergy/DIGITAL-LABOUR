#!/usr/bin/env python3
from pathlib import Path
import json, datetime
from .common import CONFIG, PORTFOLIO, Log, ensure_dir
from typing import Dict, List, Any, Optional
from autogen_agentchat.agents import AssistantAgent

REPOS_BASE = Path(CONFIG["repos_base"])
BRIEFS_DIR = Path(CONFIG["reports_dir"]) / "daily"
ensure_dir(BRIEFS_DIR)

def collect_repo_summary(repo_name: str):
    repo_root = REPOS_BASE / repo_name
    reports_dir = repo_root / "reports"
    today = datetime.date.today().isoformat()

    summary = {"repo": repo_name, "today": today, "commits": 0, "delta": None}
    jpath = reports_dir / f"delta_plan_{today}.json"
    if jpath.exists():
        try:
            summary["delta"] = json.loads(jpath.read_text(encoding='utf-8'))
        except Exception:
            pass
    if summary["delta"]:
        code = summary["delta"]["summary"].get("code",0)
        tests = summary["delta"]["summary"].get("tests",0)
        docs = summary["delta"]["summary"].get("docs",0)
        summary["commits"] = code + tests + docs
    return summary

def build_portfolio_brief():
    today = datetime.date.today().isoformat()
    lines = [f"# Daily Ops Brief — {today}", ""]
    focus = []
    for r in PORTFOLIO.get("repositories", []):
        name = r["name"]
        s = collect_repo_summary(name)
        if s["delta"]:
            d = s["delta"]
            lines.append(f"## {name}")
            lines.append(
                f"- Changes — code: {d['summary'].get('code',0)}, tests: {d['summary'].get('tests',0)}, docs: {d['summary'].get('docs',0)}, ncl: {d['summary'].get('ncl',0)}")
            if d.get("next_actions"):
                for a in d["next_actions"]:
                    lines.append(f"  - Next: {a}")
            lines.append("")
            if d['summary'].get('ncl',0) or d['summary'].get('code',0) > 5:
                focus.append(name)
    if focus:
        lines.insert(2, f"**Focus:** {', '.join(focus)}\n")
    out = BRIEFS_DIR / f"brief_{today}.md"
    out.write_text("\n".join(lines), encoding='utf-8')
    Log.info(f"Wrote {out}")

def queue_for_brief(enrich_file: Path) -> bool:
    """Queue enriched content for tomorrow's ops brief"""
    try:
        if not enrich_file.exists():
            Log.error(f"Enrichment file not found: {enrich_file}")
            return False

        enrich_data = json.loads(enrich_file.read_text(encoding='utf-8'))

        # Create a queued item file for tomorrow's brief
        tomorrow = (datetime.date.today() + \
                    datetime.timedelta(days=1)).isoformat()
        queued_dir = BRIEFS_DIR / "queued" / tomorrow
        ensure_dir(queued_dir)

        video_id = enrich_data["video_id"]
        queue_file = queued_dir / f"secondbrain_{video_id}.json"

        queue_item = {
            "type": "second_brain_ingestion",
            "video_id": video_id,
            "source_url": enrich_data.get("source_url"),
            "abstract": enrich_data.get("abstract_120w", "")[:200] + "...",
            "confidence": enrich_data.get("confidence", "unknown"),
            "action_items": enrich_data.get("action_items", []),
            # Top 3 insights
            "key_insights": enrich_data.get("key_insights", [])[:3],
            "doctrine_principles": enrich_data.get("doctrine_map", {}).get("principles", []),
            "queued_at": datetime.datetime.now().isoformat(),
            "enrich_file": str(enrich_file)
        }

        queue_file.write_text(json.dumps(
            queue_item, indent=2), encoding='utf-8')
        Log.info(f"Queued {video_id} for {tomorrow} ops brief")
        return True

    except Exception as e:
        Log.error(f"Failed to queue for brief: {e}")
        return False


class DailyBriefAgent:
    """AI-powered agent for generating intelligent daily operational briefs"""

    def __init__(self, model_client=None):
        self.name = "DailyBriefAgent"
        self.model_client = model_client
        self.status = "initialized"

        # Create AutoGen agent if model client is available
        if self.model_client:
            self.agent = AssistantAgent(
                "daily_brief_synthesizer", model_client=self.model_client,
                system_message="""You are an expert intelligence synthesizer and operational brief generator.
                Your role is to compile comprehensive daily operational intelligence from multiple sources,
                identify patterns, prioritize actions, and provide strategic recommendations.

                Focus on:
                - Synthesizing repository changes across the portfolio
                - Identifying critical issues and opportunities
                - Prioritizing actions based on impact and urgency
                - Providing clear, actionable intelligence
                - Connecting dots between different operational domains

                Structure your output with clear priorities, timelines, and risk assessments.""")

    def execute(self, task: str) -> Dict[str, Any]:
        """Execute daily brief generation and intelligence synthesis"""
        try:
            # Build the basic portfolio brief
            build_portfolio_brief()

            # Collect comprehensive repository intelligence
            repo_intelligence = []
            focus_repos = []
            total_changes = 0

            for repo in PORTFOLIO.get("repositories", []):
                summary = collect_repo_summary(repo["name"])
                if summary["delta"]:
                    repo_intelligence.append(summary)
                    total_changes += summary["commits"]

                    # Identify focus repositories
                    delta = summary["delta"]
                    if (delta['summary'].get('ncl', 0) > 0 or
                        delta['summary'].get('code', 0) > 5):
                        focus_repos.append(repo["name"])

            # Check for queued content
            queued_content = self._collect_queued_content()

            # Generate AI-enhanced brief if model is available
            if self.model_client and self.agent:
                synthesis_prompt = f"""
                Synthesize the following operational intelligence into a comprehensive daily brief:

                Repository Changes: {json.dumps(repo_intelligence, indent=2)}
                Queued Content: {json.dumps(queued_content, indent=2)}
                Total Changes Today: {total_changes}
                Focus Repositories: {focus_repos}

                Provide:
                1. Executive Summary (3-5 key points)
                2. Critical Issues & Risks
                3. Priority Actions (with timelines)
                4. Strategic Opportunities
                5. Resource Recommendations
                6. Tomorrow's Focus Areas
                """

                # Note: In full implementation, we would run the agent here
                ai_analysis = {
                    'executive_summary': 'AI synthesis requires model execution',
                    'critical_issues': 'AI analysis pending',
                    'priority_actions': 'AI analysis pending',
                    'strategic_opportunities': 'AI analysis pending',
                    'resource_recommendations': 'AI analysis pending',
                    'focus_areas': focus_repos
                }
            else:
                ai_analysis = {
                    'executive_summary': f'Portfolio shows {total_changes} changes across {len(repo_intelligence)} repositories',
                    'critical_issues': 'Manual review required for AI analysis',
                    'priority_actions': f'Focus on repositories: {", ".join(focus_repos) if focus_repos else "None"}',
                    'strategic_opportunities': 'AI analysis unavailable',
                    'resource_recommendations': 'Manual assessment required',
                    'focus_areas': focus_repos
                }

            # Generate enhanced brief file
            self._generate_enhanced_brief(
                repo_intelligence, queued_content, ai_analysis)

            return {
                'task': task,
                'result': 'daily brief generated with intelligence synthesis',
                'agent': self.name,
                'timestamp': datetime.datetime.now().isoformat(),
                'repositories_analyzed': len(repo_intelligence),
                'total_changes': total_changes,
                'focus_repositories': focus_repos,
                'queued_content_count': len(queued_content),
                'ai_analysis': ai_analysis,
                'status': 'success'
            }

        except Exception as e:
            Log.error(f"DailyBriefAgent execution failed: {e}")
            return {
                'task': task,
                'result': f'error: {str(e)}',
                'agent': self.name,
                'timestamp': datetime.datetime.now().isoformat(),
                'status': 'error'
            }

    def _collect_queued_content(self) -> List[Dict[str, Any]]:
        """Collect queued content for today's brief"""
        queued_content = []
        today = datetime.date.today().isoformat()
        queued_dir = BRIEFS_DIR / "queued" / today

        if queued_dir.exists():
            for queue_file in queued_dir.glob("*.json"):
                try:
                    content = json.loads(
                        queue_file.read_text(encoding='utf-8'))
                    queued_content.append(content)
                except Exception as e:
                    Log.warn(
                        f"Failed to load queued content {queue_file}: {e}")

        return queued_content

    def _generate_enhanced_brief(
            self, repo_intelligence: List[Dict],
            queued_content: List[Dict],
            ai_analysis: Dict[str, Any]):
        """Generate an enhanced brief with AI insights"""
        today = datetime.date.today().isoformat()
        lines = [f"# Enhanced Daily Ops Brief — {today}", ""]

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append(ai_analysis.get(
            'executive_summary', 'Summary not available'))
        lines.append("")

        # Repository Status
        lines.append("## Repository Intelligence")
        for repo in repo_intelligence:
            if repo["delta"]:
                d = repo["delta"]
                lines.append(f"### {repo['repo']}")
                lines.append(
                    f"- **Changes:** code: {d['summary'].get('code',0)}, tests: {d['summary'].get('tests',0)}, docs: {d['summary'].get('docs',0)}, ncl: {d['summary'].get('ncl',0)}")
                if d.get("next_actions"):
                    lines.append("- **Actions:**")
                    for a in d["next_actions"]:
                        lines.append(f"  - {a}")
                lines.append("")

        # Queued Content
        if queued_content:
            lines.append("## Intelligence Ingestion")
            for item in queued_content:
                lines.append(f"### {item.get('video_id', 'Unknown')}")
                lines.append(f"- **Source:** {item.get('source_url', 'N/A')}")
                lines.append(f"- **Abstract:** {item.get('abstract', 'N/A')}")
                if item.get('action_items'):
                    lines.append("- **Action Items:**")
                    for action in item['action_items'][:3]:  # Top 3
                        lines.append(f"  - {action}")
                lines.append("")

        # AI Analysis
        lines.append("## Strategic Analysis")
        lines.append(
            f"- **Critical Issues:** {ai_analysis.get('critical_issues', 'N/A')}")
        lines.append(
            f"- **Priority Actions:** {ai_analysis.get('priority_actions', 'N/A')}")
        lines.append(
            f"- **Opportunities:** {ai_analysis.get('strategic_opportunities', 'N/A')}")
        lines.append(
            f"- **Resource Needs:** {ai_analysis.get('resource_recommendations', 'N/A')}")
        lines.append("")

        # Focus Areas
        focus_areas = ai_analysis.get('focus_areas', [])
        if focus_areas:
            lines.append("## Focus Areas")
            for area in focus_areas:
                lines.append(f"- {area}")
            lines.append("")

        # Save enhanced brief
        enhanced_file = BRIEFS_DIR / f"enhanced_brief_{today}.md"
        enhanced_file.write_text("\n".join(lines), encoding='utf-8')
        Log.info(f"Enhanced brief written to {enhanced_file}")
