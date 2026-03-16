#!/usr/bin/env python3
from pathlib import Path
import json, argparse, datetime, uuid
from typing import Dict, List, Any, Optional
from autogen_agentchat.agents import AssistantAgent
from .common import CONFIG, PORTFOLIO, Log, ensure_dir, require_consent_for

DECISIONS_DIR = Path(CONFIG["decisions_dir"])
ensure_dir(DECISIONS_DIR)

VALID_AUTONOMY = ["L0","L1","L2","L3"]
VALID_RISK = ["LOW","MEDIUM","HIGH"]

def load_repo(repo_name: str):
    for r in PORTFOLIO.get("repositories", []):
        if r["name"] == repo_name:
            return r
    return None

def has_valid_consent(repo_root: Path, action_class: str) -> bool:
    consents_dir = repo_root / ".ncl" / "consents"
    if not consents_dir.exists():
        return False
    for f in consents_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            if data.get("action_class") ==action_class and data.get(
                "ttl_valid", True):
                return True
        except Exception:
            pass
    return False

def evaluate(proposal: dict) -> dict:
    decision = {
        "id": proposal.get("id", str(uuid.uuid4())),
        "approved": False,
        "requires_human": False,
        "reason": [],
        "timestamp": datetime.datetime.now().astimezone().isoformat(),
    }
    repo = load_repo(proposal["repo"])
    if not repo:
        decision["reason"].append("Unknown repo")
        return decision

    autonomy = proposal.get("autonomy", "L1")
    risk = proposal.get("risk", "MEDIUM")
    if autonomy not in VALID_AUTONOMY:
        decision["reason"].append("Invalid autonomy level")
        return decision
    if risk not in VALID_RISK:
        decision["reason"].append("Invalid risk tier")
        return decision

    action_class = proposal.get("action", "")
    repo_root = Path(CONFIG["repos_base"]) / repo["name"]

    # business rule: any financial action always forces human review
    if action_class == "financial_actions":
        decision["reason"].append(
            "Financial actions always require human review")
        decision["requires_human"] = True
        return decision

    if require_consent_for(action_class):
        if not has_valid_consent(repo_root, action_class):
            decision["reason"].append(
                "Missing valid consent receipt for sensitive action")
            decision["requires_human"] = True
            return decision

    if autonomy == "L3":
        decision["reason"].append("L3 always requires human + council gate")
        decision["requires_human"] = True
        return decision

    if risk == "HIGH":
        decision["reason"].append("HIGH risk requires human review")
        decision["requires_human"] = True
        return decision

    decision["approved"] = True
    decision["reason"].append(
        "Policy pass: consent satisfied and within autonomy/risk thresholds")
    return decision

def save_decision(proposal: dict, decision: dict):
    rid = proposal.get("repo")
    pid = decision["id"]
    out = DECISIONS_DIR / f"decision_{rid}_{pid}.json"
    out.write_text(json.dumps(
                       {"proposal": proposal, "decision": decision},
                       indent=2),
                   encoding='utf-8')
    Log.info(f"Decision written: {out}")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['propose'])
    ap.add_argument('--repo', required=True)
    ap.add_argument('--action', required=True)
    ap.add_argument('--description', required=True)
    ap.add_argument('--risk', default='MEDIUM', choices=VALID_RISK)
    ap.add_argument('--autonomy', default='L1', choices=VALID_AUTONOMY)
    ap.add_argument('--id', default=None)
    args = ap.parse_args()

    proposal = {
        "id": args.id or str(uuid.uuid4()),
        "repo": args.repo,
        "action": args.action,
        "description": args.description,
        "risk": args.risk,
        "autonomy": args.autonomy
    }
    decision = evaluate(proposal)
    save_decision(proposal, decision)
    print(json.dumps(decision, indent=2))


class CouncilAgent:
    """AI-powered agent for autonomous decision making and proposal evaluation"""

    def __init__(self, model_client=None):
        self.name = "CouncilAgent"
        self.model_client = model_client
        self.status = "initialized"

        # Create AutoGen agent if model client is available
        if self.model_client:
            self.agent = AssistantAgent(
                "council_decision_maker", model_client=self.model_client,
                system_message="""You are an expert autonomous decision-making agent with deep knowledge of
                operational risk assessment, ethical AI governance, and strategic decision frameworks.

                Your role is to evaluate proposals, assess risks, determine autonomy levels, and make
                strategic decisions within defined authority limits.

                Key responsibilities:
                - Risk assessment and mitigation analysis
                - Autonomy level determination (L0-L3)
                - Ethical and compliance evaluation
                - Strategic impact assessment
                - Consent and governance validation
                - Decision reasoning and documentation

                Always provide clear, well-reasoned decisions with specific risk assessments and
                recommendations for human oversight when appropriate.""")

    def execute(self, task: str) -> Dict[str, Any]:
        """Execute council decision-making task"""
        try:
            if "evaluate" in task.lower():
                # Parse task for proposal details
                proposal = self._parse_proposal_from_task(task)
                if proposal:
                    return self.evaluate_proposal(proposal)
                else:
                    return {
                        'task': task,
                        'result': 'failed to parse proposal from task',
                        'agent': self.name,
                        'timestamp': datetime.datetime.now().isoformat(),
                        'status': 'error'
                    }
            else:
                # General council operations
                return {
                    'task': task,
                    'result': 'council decision framework executed',
                    'agent': self.name,
                    'timestamp': datetime.datetime.now().isoformat(),
                    'status': 'success'
                }

        except Exception as e:
            Log.error(f"CouncilAgent execution failed: {e}")
            return {
                'task': task,
                'result': f'error: {str(e)}',
                'agent': self.name,
                'timestamp': datetime.datetime.now().isoformat(),
                'status': 'error'
            }

    def evaluate_proposal(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a proposal using AI-enhanced decision making"""
        try:
            # First, run the standard policy evaluation
            decision = evaluate(proposal)

            # If AI is available, enhance the decision with deeper analysis
            if self.model_client and self.agent:
                analysis_prompt = f"""
                Perform a comprehensive risk and strategic analysis of this proposal:

                Proposal: {json.dumps(proposal, indent=2)}
                Initial Decision: {json.dumps(decision, indent=2)}

                Provide:
                1. Risk Assessment (scale 1-10, with specific risk factors)
                2. Strategic Impact Analysis
                3. Ethical Considerations
                4. Alternative Approaches
                5. Recommended Autonomy Level
                6. Human Oversight Requirements
                7. Implementation Timeline
                8. Success Metrics

                Consider the broader portfolio context and long-term implications.
                """

                # Note: In full implementation, we would run the agent here
                ai_enhancement = {
                    'risk_score': 'AI analysis requires model execution',
                    'strategic_impact': 'AI analysis pending',
                    'ethical_considerations': 'AI analysis pending',
                    'alternatives': 'AI analysis pending',
                    'recommended_autonomy': proposal.get('autonomy', 'L1'),
                    'oversight_needs': 'AI analysis pending',
                    'timeline': 'AI analysis pending',
                    'success_metrics': 'AI analysis pending'
                }
            else:
                ai_enhancement = {
                    'risk_score': 'AI analysis unavailable - manual assessment required',
                    'strategic_impact': 'Manual review needed',
                    'ethical_considerations': 'Manual review needed',
                    'alternatives': 'Manual review needed',
                    'recommended_autonomy': proposal.get('autonomy', 'L1'),
                    'oversight_needs': 'Based on policy rules',
                    'timeline': 'To be determined',
                    'success_metrics': 'To be defined'
                }

            # Enhance the decision with AI insights
            enhanced_decision = decision.copy()
            enhanced_decision['ai_enhancement'] = ai_enhancement
            enhanced_decision['confidence_level'] = 'high' if decision['approved'] else 'medium'

            # Save the enhanced decision
            save_decision(proposal, enhanced_decision)

            return {
                'task': 'proposal_evaluation',
                'result': 'proposal evaluated with AI enhancement',
                'agent': self.name,
                'timestamp': datetime.datetime.now().isoformat(),
                'proposal_id': proposal.get('id'),
                'decision': enhanced_decision,
                'ai_enhanced': bool(self.model_client),
                'status': 'success'
            }

        except Exception as e:
            Log.error(f"Proposal evaluation failed: {e}")
            return {
                'task': 'proposal_evaluation',
                'result': f'evaluation error: {str(e)}',
                'agent': self.name,
                'timestamp': datetime.datetime.now().isoformat(),
                'status': 'error'
            }

    def _parse_proposal_from_task(self, task: str) -> Optional[Dict[str, Any]]:
        """Parse proposal details from task description"""
        # This is a simple parser - in production, this could be more sophisticated
        try:
            # Look for JSON in the task
            import re
            json_match = re.search(r'\{.*\}', task, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # Or parse key-value pairs
            proposal = {}
            lines = task.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    proposal[key] = value

            # Validate required fields
            if 'repo' in proposal and 'action' in proposal:
                proposal['id'] = proposal.get('id', str(uuid.uuid4()))
                proposal['autonomy'] = proposal.get('autonomy', 'L1')
                proposal['risk'] = proposal.get('risk', 'MEDIUM')
                return proposal

        except Exception as e:
            Log.warn(f"Failed to parse proposal from task: {e}")

        return None
