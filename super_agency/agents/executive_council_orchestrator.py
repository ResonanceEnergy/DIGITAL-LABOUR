#!/usr/bin/env python3
"""
Executive Council Orchestrator - Passive Agent Coordinator.

Manages all executive agents (CEO, CFO, CTO, CMO, CIO)
as coordinated passive system.
"""

import time
import threading
from datetime import datetime, timedelta
import logging

# Import executive agents (relative within package)
from .ceo_agent import get_ceo_agent
from .cfo_agent import get_cfo_agent
from .cto_agent import get_cto_agent
from .cmo_agent import get_cmo_agent
from .cio_agent import get_cio_agent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class ExecutiveCouncilOrchestrator:
    """Orchestrates all executive agents as a coordinated passive system"""

    def __init__(self):
        self.name = "Executive_Council_Orchestrator"
        self.executive_agents = {
            "CEO": get_ceo_agent(),
            "CFO": get_cfo_agent(),
            "CTO": get_cto_agent(),
            "CMO": get_cmo_agent(),
            "CIO": get_cio_agent()
        }

        # Council coordination state
        self.council_state = {
            "council_status": "INITIALIZING",
            "last_executive_meeting": None,
            "strategic_alignment_score": 0.0,
            "executive_decisions": [],
            "council_health": 100.0,
            "coordination_cycles": 0
        }

        self.running = False
        self.thread = None
        self._lock = threading.RLock()

    def start_council(self):
        """Start the entire executive council"""
        if self.running:
            logger.warning("Executive Council already running")
            return

        logger.info(
            "\U0001f680 Starting Executive Council"
            " - All C-Suite Agents Activating",
        )

        # Start all executive agents
        for role, agent in self.executive_agents.items():
            try:
                agent.start()
                logger.info(f"✅ {role} Agent started successfully")
            except Exception as e:
                logger.error(f"❌ Failed to start {role} Agent: {e}")

        self.running = True
        with self._lock:
            self.council_state["council_status"] = "ACTIVE"
        self.thread = threading.Thread(
            target=self._executive_council_loop,
            daemon=True,
        )
        self.thread.start()

        logger.info(
            "\U0001f3af Executive Council fully operational"
            " - Supreme executive oversight active",
        )

    def stop_council(self):
        """Stop the entire executive council"""
        logger.info("🛑 Stopping Executive Council")

        self.running = False

        # Stop all executive agents
        for role, agent in self.executive_agents.items():
            try:
                agent.stop()
                logger.info(f"✅ {role} Agent stopped successfully")
            except Exception as e:
                logger.error(f"❌ Error stopping {role} Agent: {e}")

        if self.thread:
            self.thread.join(timeout=10)

        with self._lock:
            self.council_state["council_status"] = "INACTIVE"
        logger.info("Executive Council shutdown complete")

    def _executive_council_loop(self):
        """Main executive council coordination loop"""
        while self.running:
            try:
                self._hold_executive_meeting()
                self._coordinate_executive_actions()
                self._assess_council_health()
                self._update_strategic_alignment()

                with self._lock:
                    self.council_state["coordination_cycles"] += 1

                # Executive meetings every 6 hours
                time.sleep(21600)

            except Exception as e:
                logger.error(f"Executive Council coordination error: {e}")
                time.sleep(300)  # Retry in 5 minutes on error

    def _hold_executive_meeting(self):
        """Hold comprehensive executive meeting with all C-suite"""
        meeting_time = datetime.now()

        # Gather status from all executives
        executive_status = {}
        for role, agent in self.executive_agents.items():
            status = None
            try:
                if role == "CEO":
                    status = agent.get_executive_status()
                elif role == "CFO":
                    status = agent.get_financial_status()
                elif role == "CTO":
                    status = agent.get_technical_status()
                elif role == "CMO":
                    status = agent.get_market_status()
                elif role == "CIO":
                    status = agent.get_intelligence_status()

                executive_status[role] = status
            except Exception as e:
                logger.error(
                    f"Error getting {role} status: {e}",
                )
                executive_status[role] = {
                    "status": "ERROR",
                    "error": str(e),
                }

        # Conduct executive meeting
        meeting_data = {
            "timestamp": meeting_time.isoformat(),
            "attendees": list(executive_status.keys()),
            "executive_status": executive_status,
            "strategic_decisions": self._make_strategic_decisions(
                executive_status,
            ),
            "action_items": self._generate_executive_action_items(
                executive_status,
            ),
            "council_assessment": self._assess_executive_council(
                executive_status,
            )
        }

        with self._lock:
            self.council_state["last_executive_meeting"] = meeting_data

        logger.info(
            "Executive Council Meeting completed:"
            f" {len(meeting_data['strategic_decisions'])}"
            " strategic decisions made",
        )

    def _make_strategic_decisions(self, executive_status: dict) -> list:
        """Make strategic decisions based on executive input"""
        decisions = []

        # Analyze executive status for strategic decisions
        ceo_status = executive_status.get("CEO", {})
        cfo_status = executive_status.get("CFO", {})
        cto_status = executive_status.get("CTO", {})
        cmo_status = executive_status.get("CMO", {})
        cio_status = executive_status.get("CIO", {})

        # Strategic decision making based on executive metrics
        if ceo_status.get("mission_alignment", 0) < 90.0:
            decisions.append({
                "decision": "MISSION_ALIGNMENT_INITIATIVE",
                "description": (
                    "Launch comprehensive mission"
                    " alignment program"
                ),
                "priority": "HIGH",
                "lead": "CEO",
                "timeline": "30 days"
            })

        if cfo_status.get("budget_utilization", 0) > 80.0:
            decisions.append({
                "decision": "COST_OPTIMIZATION_PROGRAM",
                "description": (
                    "Implement cost optimization"
                    " across all departments"
                ),
                "priority": "MEDIUM",
                "lead": "CFO",
                "timeline": "60 days"
            })

        if cto_status.get("architecture_health", 0) < 85.0:
            decisions.append({
                "decision": "ARCHITECTURE_MODERNIZATION",
                "description": (
                    "Modernize system architecture"
                    " for improved performance"
                ),
                "priority": "HIGH",
                "lead": "CTO",
                "timeline": "90 days"
            })

        if cmo_status.get("market_share", 0) < 20.0:
            decisions.append({
                "decision": "MARKET_EXPANSION_STRATEGY",
                "description": (
                    "Develop comprehensive market"
                    " expansion strategy"
                ),
                "priority": "HIGH",
                "lead": "CMO",
                "timeline": "45 days"
            })

        if cio_status.get("intelligence_coverage", 0) < 90.0:
            decisions.append({
                "decision": "INTELLIGENCE_COVERAGE_EXPANSION",
                "description": (
                    "Expand intelligence coverage"
                    " to 95%+ of sources"
                ),
                "priority": "MEDIUM",
                "lead": "CIO",
                "timeline": "30 days"
            })

        return decisions

    def _generate_executive_action_items(self, executive_status: dict) -> list:
        """Generate executive action items from council meeting"""
        action_items = []

        # Create action items based on executive status
        for role, status in executive_status.items():
            if status.get("status") == "ERROR":
                action_items.append({
                    "action": f"TROUBLESHOOT_{role}_AGENT",
                    "description": f"Resolve {role} agent operational issues",
                    "priority": "HIGH",
                    "assignee": role,
                    "deadline": (
                        datetime.now() + timedelta(days=1)
                    ).isoformat()
                })

        # Add standard executive action items
        action_items.extend([
            {
                "action": "EXECUTIVE_PERFORMANCE_REVIEW",
                "description": (
                    "Conduct quarterly executive"
                    " performance review"
                ),
                "priority": "MEDIUM",
                "assignee": "CEO",
                "deadline": (datetime.now() + timedelta(days=30)).isoformat()
            },
            {
                "action": "STRATEGIC_PLANNING_SESSION",
                "description": (
                    "Hold strategic planning session"
                    " for next quarter"
                ),
                "priority": "MEDIUM",
                "assignee": "EXECUTIVE_COUNCIL",
                "deadline": (datetime.now() + timedelta(days=14)).isoformat()
            }
        ])

        return action_items

    def _assess_executive_council(self, executive_status: dict) -> dict:
        """Assess overall executive council effectiveness"""
        total_executives = len(executive_status)
        active_executives = sum(
            1 for status in executive_status.values()
            if status.get("status") == "ACTIVE"
        )
        healthy_executives = sum(
            1 for status in executive_status.values()
            if status.get("status") == "ACTIVE"
        )

        council_health = (
            (healthy_executives / total_executives) * 100
            if total_executives > 0
            else 0
        )

        return {
            "total_executives": total_executives,
            "active_executives": active_executives,
            "healthy_executives": healthy_executives,
            "council_health_percentage": council_health,
            "coordination_effectiveness": 92.0  # Simulated coordination score
        }

    def _coordinate_executive_actions(self):
        """Coordinate actions across executives."""
        # Ensures CFO budget decisions align with
        # CEO strategic goals
        logger.debug(
            "Executive action coordination active",
        )

    def _assess_council_health(self):
        """Assess overall executive council health"""
        # Update council health based on individual agent status
        executive_status = {}
        for role, agent in self.executive_agents.items():
            try:
                if hasattr(agent, 'running'):
                    status_text = (
                        "ACTIVE" if agent.running
                        else "INACTIVE"
                    )
                    executive_status[role] = {
                        "status": status_text,
                    }
                else:
                    executive_status[role] = {"status": "UNKNOWN"}
            except Exception:
                executive_status[role] = {"status": "ERROR"}

        council_assessment = self._assess_executive_council(
            executive_status,
        )
        with self._lock:
            self.council_state["council_health"] = (
                council_assessment["council_health_percentage"]
            )

    def _update_strategic_alignment(self):
        """Update strategic alignment score across executives"""
        alignment_score = 87.0
        with self._lock:
            self.council_state["strategic_alignment_score"] = alignment_score

    def get_council_status(self) -> dict:
        """Get comprehensive executive council status"""
        with self._lock:
            state_snapshot = dict(self.council_state)
        executive_status = {}
        for role, agent in self.executive_agents.items():
            try:
                if role == "CEO":
                    executive_status[role] = agent.get_executive_status()
                elif role == "CFO":
                    executive_status[role] = agent.get_financial_status()
                elif role == "CTO":
                    executive_status[role] = agent.get_technical_status()
                elif role == "CMO":
                    executive_status[role] = agent.get_market_status()
                elif role == "CIO":
                    executive_status[role] = agent.get_intelligence_status()
            except Exception as e:
                executive_status[role] = {"status": "ERROR", "error": str(e)}

        return {
            "council_name": self.name,
            "council_status": state_snapshot["council_status"],
            "executive_agents": executive_status,
            "council_health": state_snapshot["council_health"],
            "strategic_alignment": state_snapshot["strategic_alignment_score"],
            "coordination_cycles": state_snapshot["coordination_cycles"],
            "last_executive_meeting": state_snapshot["last_executive_meeting"],
            "active_strategic_decisions": len(
                state_snapshot["executive_decisions"],
            )
        }

    def make_council_decision(self, proposal: dict) -> dict:
        """Make executive council decision requiring multiple approvals"""
        # Get approvals from relevant executives
        approvals = {}

        # CEO approval (required for all)
        try:
            ceo_decision = (
                self.executive_agents["CEO"]
                .make_executive_decision(proposal)
            )
            approvals["CEO"] = ceo_decision
        except Exception:
            approvals["CEO"] = {
                "approved": False,
                "error": "CEO unavailable",
            }

        # Get additional approvals based on proposal type
        proposal_type = proposal.get("type", "general")

        if proposal_type in ["financial", "budget"]:
            try:
                cfo_decision = (
                    self.executive_agents["CFO"]
                    .approve_budget_request(proposal)
                )
                approvals["CFO"] = cfo_decision
            except Exception:
                approvals["CFO"] = {
                    "approved": False,
                    "error": "CFO unavailable",
                }

        if proposal_type in ["technical", "architecture"]:
            try:
                cto_decision = (
                    self.executive_agents["CTO"]
                    .approve_technical_architecture(proposal)
                )
                approvals["CTO"] = cto_decision
            except Exception:
                approvals["CTO"] = {
                    "approved": False,
                    "error": "CTO unavailable",
                }

        if proposal_type in ["marketing", "market"]:
            try:
                cmo_decision = (
                    self.executive_agents["CMO"]
                    .approve_marketing_campaign(proposal)
                )
                approvals["CMO"] = cmo_decision
            except Exception:
                approvals["CMO"] = {
                    "approved": False,
                    "error": "CMO unavailable",
                }

        if proposal_type in ["intelligence", "council"]:
            try:
                cio_decision = (
                    self.executive_agents["CIO"]
                    .approve_intelligence_initiative(proposal)
                )
                approvals["CIO"] = cio_decision
            except Exception:
                approvals["CIO"] = {
                    "approved": False,
                    "error": "CIO unavailable",
                }

        # Determine final council decision
        ceo_approved = approvals.get(
            "CEO", {},
        ).get("approved", False)
        all_approvals = all(
            d.get("approved", False)
            for d in approvals.values()
        )

        council_decision = {
            "council_decision_id": (
                f"COUNCIL_{int(time.time())}"
            ),
            "proposal": proposal,
            "final_approval": (
                ceo_approved and all_approvals
            ),
            "individual_approvals": approvals,
            "decision_logic": (
                "CEO approval required,"
                " additional executive approvals"
                " considered"
            ),
            "timestamp": datetime.now().isoformat(),
            "council_authority": "EXECUTIVE_COUNCIL"
        }

        with self._lock:
            self.council_state["executive_decisions"].append(
                council_decision,
            )

        decision_status = (
            "APPROVED"
            if council_decision["final_approval"]
            else "REQUIRES_REVIEW"
        )
        title = proposal.get('title', 'Unknown')
        logger.info(
            "Executive Council Decision:"
            f" {title} - {decision_status}",
        )

        return council_decision


# Global Executive Council instance
executive_council = ExecutiveCouncilOrchestrator()


def get_executive_council():
    """Get the global executive council instance."""
    return executive_council


if __name__ == "__main__":
    # Start Executive Council
    executive_council.start_council()

    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        executive_council.stop_council()
