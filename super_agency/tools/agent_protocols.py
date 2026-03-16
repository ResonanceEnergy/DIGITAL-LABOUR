#!/usr/bin/env python3
"""
Agent Communication Protocols — formal interaction patterns for multi-agent systems.

Implements structured agent-to-agent communication patterns from research:
- Multi-Agent Debate — agents argue positions, mediator synthesizes consensus
- Consensus Protocol — voting-based decision making with confidence weighting
- Delegation Protocol — hierarchical task assignment with capability matching
- A2A (Agent-to-Agent) — structured message exchange with request/response
- Escalation Protocol — chain of responsibility with severity routing

Based on:
- "AutoGen: Multi-Agent Conversation Framework" (Wu et al., 2023)
- "MetaGPT: Multi-Agent Collaborative Framework" (Hong et al., 2023)
- "CAMEL: Communicative Agents for Mind Exploration" (Li et al., 2023)
- "AgentVerse: Facilitating Multi-Agent Collaboration" (Chen et al., 2023)

Usage:
    from tools.agent_protocols import (
        DebateProtocol, ConsensusProtocol, DelegationProtocol,
        EscalationProtocol, AgentMessage
    )

    debate = DebateProtocol(mediator="ceo")
    result = debate.run(topic="Should we invest in quantum computing?",
                        agents={"cto": cto_argue, "cfo": cfo_argue})
"""

import json
import logging
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_LOG_DIR = ROOT / "logs" / "protocols"
PROTOCOL_LOG_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
#  ENUMS & DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════

class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    PROPOSAL = "proposal"
    VOTE = "vote"
    ARGUMENT = "argument"
    COUNTER = "counter_argument"
    CONSENSUS = "consensus"
    ESCALATION = "escalation"
    DELEGATION = "delegation"
    ACK = "acknowledgment"
    REJECT = "rejection"


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class DecisionMethod(Enum):
    MAJORITY = "majority"
    SUPERMAJORITY = "supermajority"  # 2/3
    UNANIMOUS = "unanimous"
    WEIGHTED = "weighted"
    MEDIATOR = "mediator"


@dataclass
class AgentMessage:
    """Structured message for inter-agent communication."""
    sender: str
    receiver: str
    msg_type: MessageType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    confidence: float = 0.5
    reply_to: Optional[str] = None
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "msg_type": self.msg_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "priority": self.priority.value,
            "confidence": self.confidence,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
        }


@dataclass
class DebatePosition:
    """An agent's position in a debate."""
    agent: str
    stance: str  # "for", "against", "neutral"
    argument: str
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.5
    rebuttals: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "stance": self.stance,
            "argument": self.argument,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "rebuttals": self.rebuttals,
        }


@dataclass
class Vote:
    """A vote in a consensus protocol."""
    voter: str
    choice: str
    confidence: float = 0.5
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "voter": self.voter,
            "choice": self.choice,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


@dataclass
class ProtocolResult:
    """Result of protocol execution."""
    protocol: str
    topic: str
    decision: Optional[str] = None
    confidence: float = 0.0
    participants: List[str] = field(default_factory=list)
    rounds: int = 0
    messages: List[dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "protocol": self.protocol,
            "topic": self.topic,
            "decision": self.decision,
            "confidence": round(self.confidence, 3),
            "participants": self.participants,
            "rounds": self.rounds,
            "messages": self.messages,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════
#  MULTI-AGENT DEBATE PROTOCOL
# ═══════════════════════════════════════════════════════════════════════

class DebateProtocol:
    """
    Structured multi-agent debate for decision-making.

    Agents present arguments for/against, then a mediator synthesizes.

    Phases:
    1. Opening: Each agent states initial position
    2. Rebuttal: Agents respond to opposing arguments
    3. Synthesis: Mediator weighs evidence and decides

    Based on "Improving Factuality through Multiagent Debate" (Du et al., 2023)
    """

    def __init__(self, mediator: str = "ceo", max_rounds: int = 3):
        self.mediator = mediator
        self.max_rounds = max_rounds

    def run(self, topic: str,
            agents: Dict[str, Callable[[str, List[DebatePosition]], DebatePosition]],
            mediator_fn: Optional[Callable[[str, List[DebatePosition]], str]] = None
            ) -> ProtocolResult:
        """
        Execute a debate.

        Parameters
        ----------
        topic : str
            The question to debate.
        agents : dict
            {agent_name: debate_fn} where debate_fn(topic, positions) → DebatePosition
        mediator_fn : callable, optional
            (topic, all_positions) → decision string
        """
        result = ProtocolResult(
            protocol="debate",
            topic=topic,
            participants=list(agents.keys()) + [self.mediator],
        )

        all_positions: List[DebatePosition] = []

        for round_num in range(self.max_rounds):
            result.rounds += 1
            round_positions = []

            for agent_name, agent_fn in agents.items():
                try:
                    position = agent_fn(topic, all_positions)
                    round_positions.append(position)
                    result.messages.append({
                        "round": round_num + 1,
                        "agent": agent_name,
                        "position": position.to_dict(),
                    })
                except Exception as e:
                    logger.error("Debate error from %s: %s", agent_name, e)

            all_positions.extend(round_positions)

            # Check for early consensus
            stances = [p.stance for p in round_positions]
            if len(set(stances)) == 1:
                logger.info("Debate consensus reached in round %d", round_num + 1)
                break

        # Mediator synthesis
        if mediator_fn:
            decision = mediator_fn(topic, all_positions)
        else:
            decision = self._default_mediate(topic, all_positions)

        avg_conf = (
            sum(p.confidence for p in all_positions) / len(all_positions)
            if all_positions else 0.0
        )
        result.decision = decision
        result.confidence = avg_conf
        result.metadata = {
            "stance_distribution": dict(Counter(p.stance for p in all_positions)),
            "total_positions": len(all_positions),
        }

        self._log_result(result)
        return result

    def _default_mediate(self, topic: str,
                         positions: List[DebatePosition]) -> str:
        """Default mediation: majority stance wins."""
        if not positions:
            return "No positions presented"

        stance_counts = Counter(p.stance for p in positions)
        weighted_scores: Dict[str, float] = {}
        for p in positions:
            weighted_scores[p.stance] = (
                weighted_scores.get(p.stance, 0) + p.confidence
            )

        best = max(weighted_scores, key=weighted_scores.get)  # type: ignore[arg-type]
        return f"Decision: {best} (confidence-weighted majority)"

    def _log_result(self, result: ProtocolResult):
        log_file = PROTOCOL_LOG_DIR / "debate_log.ndjson"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result.to_dict(), default=str) + "\n")


# ═══════════════════════════════════════════════════════════════════════
#  CONSENSUS PROTOCOL
# ═══════════════════════════════════════════════════════════════════════

class ConsensusProtocol:
    """
    Formal voting-based consensus mechanism.

    Supports:
    - Majority vote (>50%)
    - Supermajority (>66%)
    - Unanimous (100%)
    - Confidence-weighted voting

    Includes quorum requirements and tie-breaking rules.
    """

    def __init__(self, method: DecisionMethod = DecisionMethod.WEIGHTED,
                 quorum: float = 0.5):
        self.method = method
        self.quorum = quorum  # fraction of eligible voters required

    def vote(self, topic: str, options: List[str],
             voters: Dict[str, Callable[[str, List[str]], Vote]]
             ) -> ProtocolResult:
        """
        Execute a voting round.

        Parameters
        ----------
        topic : str
            The question being voted on.
        options : list
            Available choices.
        voters : dict
            {voter_name: vote_fn} where vote_fn(topic, options) → Vote
        """
        result = ProtocolResult(
            protocol="consensus",
            topic=topic,
            participants=list(voters.keys()),
        )

        votes: List[Vote] = []
        for voter_name, vote_fn in voters.items():
            try:
                v = vote_fn(topic, options)
                v.voter = voter_name  # ensure correct attribution
                votes.append(v)
                result.messages.append(v.to_dict())
            except Exception as e:
                logger.error("Vote error from %s: %s", voter_name, e)

        result.rounds = 1

        # Check quorum
        if len(votes) < len(voters) * self.quorum:
            result.decision = "QUORUM_NOT_MET"
            result.confidence = 0.0
            return result

        # Tally
        decision, confidence = self._tally(votes, options)
        result.decision = decision
        result.confidence = confidence
        result.metadata = {
            "method": self.method.value,
            "vote_count": len(votes),
            "eligible_voters": len(voters),
            "tally": dict(Counter(v.choice for v in votes)),
        }

        self._log_result(result)
        return result

    def _tally(self, votes: List[Vote], options: List[str]
               ) -> tuple:
        if self.method == DecisionMethod.WEIGHTED:
            return self._weighted_tally(votes)
        elif self.method == DecisionMethod.MAJORITY:
            return self._majority_tally(votes, threshold=0.5)
        elif self.method == DecisionMethod.SUPERMAJORITY:
            return self._majority_tally(votes, threshold=2.0 / 3.0)
        elif self.method == DecisionMethod.UNANIMOUS:
            return self._unanimous_tally(votes)
        return "UNKNOWN_METHOD", 0.0

    def _weighted_tally(self, votes: List[Vote]) -> tuple:
        scores: Dict[str, float] = {}
        for v in votes:
            scores[v.choice] = scores.get(v.choice, 0) + v.confidence
        if not scores:
            return "NO_VOTES", 0.0
        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        total = sum(scores.values())
        confidence = scores[best] / total if total else 0.0
        return best, confidence

    def _majority_tally(self, votes: List[Vote], threshold: float) -> tuple:
        counts = Counter(v.choice for v in votes)
        total = len(votes)
        for choice, count in counts.most_common():
            if count / total >= threshold:
                avg_conf = sum(
                    v.confidence for v in votes if v.choice == choice
                ) / count
                return choice, avg_conf
        return "NO_MAJORITY", 0.0

    def _unanimous_tally(self, votes: List[Vote]) -> tuple:
        choices = set(v.choice for v in votes)
        if len(choices) == 1:
            avg_conf = sum(v.confidence for v in votes) / len(votes)
            return choices.pop(), avg_conf
        return "NO_UNANIMITY", 0.0

    def _log_result(self, result: ProtocolResult):
        log_file = PROTOCOL_LOG_DIR / "consensus_log.ndjson"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result.to_dict(), default=str) + "\n")


# ═══════════════════════════════════════════════════════════════════════
#  DELEGATION PROTOCOL
# ═══════════════════════════════════════════════════════════════════════

class DelegationProtocol:
    """
    Hierarchical task delegation with capability matching.

    Flow:
    1. Delegator creates task with requirements
    2. Protocol matches capabilities from available agents
    3. Best-fit agent receives delegation
    4. Result reported back through escalation chain
    """

    def __init__(self):
        self._agent_capabilities: Dict[str, Dict[str, Any]] = {}

    def register_agent(self, agent_name: str,
                       capabilities: List[str],
                       capacity: float = 1.0,
                       priority: int = 5):
        """Register an agent's capabilities for delegation matching."""
        self._agent_capabilities[agent_name] = {
            "capabilities": set(capabilities),
            "capacity": capacity,
            "priority": priority,
            "current_load": 0.0,
        }

    def delegate(self, task: str, requirements: List[str],
                 delegator: str,
                 priority: Priority = Priority.MEDIUM) -> AgentMessage:
        """
        Find best agent for a task and create delegation message.

        Matching considers:
        1. Capability overlap (required vs offered)
        2. Current load (prefer less-loaded agents)
        3. Agent priority (tiebreaker)
        """
        req_set = set(requirements)
        candidates = []

        for agent_name, caps in self._agent_capabilities.items():
            if agent_name == delegator:
                continue
            overlap = len(req_set & caps["capabilities"])
            if overlap == 0:
                continue
            coverage = overlap / len(req_set) if req_set else 0
            available_capacity = caps["capacity"] - caps["current_load"]
            score = (coverage * 3.0 +
                     available_capacity * 2.0 +
                     caps["priority"] * 0.1)
            candidates.append((score, agent_name, coverage))

        if not candidates:
            return AgentMessage(
                sender=delegator, receiver="escalation",
                msg_type=MessageType.ESCALATION,
                content=f"No capable agent found for: {task}",
                metadata={"requirements": requirements},
                priority=priority,
            )

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_agent, coverage = candidates[0]

        # Update load
        self._agent_capabilities[best_agent]["current_load"] += 0.1

        return AgentMessage(
            sender=delegator, receiver=best_agent,
            msg_type=MessageType.DELEGATION,
            content=task,
            metadata={
                "requirements": requirements,
                "coverage": round(coverage, 2),
                "score": round(best_score, 2),
            },
            priority=priority,
            confidence=coverage,
        )

    def release_capacity(self, agent_name: str, amount: float = 0.1):
        """Release capacity after task completion."""
        if agent_name in self._agent_capabilities:
            caps = self._agent_capabilities[agent_name]
            caps["current_load"] = max(0, caps["current_load"] - amount)


# ═══════════════════════════════════════════════════════════════════════
#  ESCALATION PROTOCOL
# ═══════════════════════════════════════════════════════════════════════

class EscalationProtocol:
    """
    Chain-of-responsibility escalation for issues requiring higher authority.

    Default chain: GASKET → OPTIMUS → AZ → CEO

    Escalation triggers:
    - Risk level exceeds agent authority
    - Confidence below threshold
    - Cross-domain decision required
    - Budget threshold exceeded
    """

    DEFAULT_CHAIN = ["gasket", "optimus", "az", "ceo"]

    def __init__(self, chain: Optional[List[str]] = None,
                 confidence_threshold: float = 0.5):
        self.chain = chain or self.DEFAULT_CHAIN
        self.confidence_threshold = confidence_threshold
        self._escalation_log: List[dict] = []

    def escalate(self, issue: str, severity: Priority,
                 source_agent: str,
                 context: Optional[Dict[str, Any]] = None) -> AgentMessage:
        """
        Escalate an issue up the chain.

        The target is determined by:
        1. Source agent's position in chain
        2. Severity level (higher severity may skip levels)
        """
        # Find source position in chain
        try:
            source_idx = self.chain.index(source_agent.lower())
        except ValueError:
            source_idx = -1  # not in chain, start from beginning

        # Determine target
        if severity.value >= Priority.CRITICAL.value:
            target_idx = len(self.chain) - 1  # go straight to top
        elif severity.value >= Priority.HIGH.value:
            target_idx = min(source_idx + 2, len(self.chain) - 1)
        else:
            target_idx = min(source_idx + 1, len(self.chain) - 1)

        target = self.chain[target_idx]

        msg = AgentMessage(
            sender=source_agent,
            receiver=target,
            msg_type=MessageType.ESCALATION,
            content=issue,
            metadata={
                "context": context or {},
                "chain_position": target_idx,
                "severity": severity.value,
            },
            priority=severity,
        )

        self._escalation_log.append({
            "timestamp": msg.timestamp,
            "from": source_agent,
            "to": target,
            "severity": severity.name,
            "issue": issue[:200],
        })

        logger.info("Escalation: %s → %s (severity=%s): %s",
                     source_agent, target, severity.name, issue[:100])
        return msg

    def should_escalate(self, confidence: float,
                        risk_level: str = "low") -> bool:
        """Determine if an issue should be escalated."""
        if risk_level.lower() in ("high", "critical"):
            return True
        return confidence < self.confidence_threshold

    def get_escalation_history(self, limit: int = 20) -> List[dict]:
        return self._escalation_log[-limit:]


# ═══════════════════════════════════════════════════════════════════════
#  PROTOCOL ORCHESTRATOR — Manages all protocol instances
# ═══════════════════════════════════════════════════════════════════════

class ProtocolOrchestrator:
    """
    Central manager for all agent communication protocols.

    Provides unified access to debate, consensus, delegation, and escalation.
    Integrates with the message bus for event distribution.
    """

    def __init__(self):
        self.debate = DebateProtocol()
        self.consensus = ConsensusProtocol()
        self.delegation = DelegationProtocol()
        self.escalation = EscalationProtocol()
        self._message_log: List[AgentMessage] = []

    def send_message(self, msg: AgentMessage,
                     handler: Optional[Callable[[AgentMessage], None]] = None):
        """Send a message and optionally route to handler."""
        self._message_log.append(msg)
        if handler:
            handler(msg)

    def get_message_history(self, agent: Optional[str] = None,
                            msg_type: Optional[MessageType] = None,
                            limit: int = 50) -> List[dict]:
        """Query message history with filters."""
        msgs = self._message_log
        if agent:
            msgs = [m for m in msgs
                    if m.sender == agent or m.receiver == agent]
        if msg_type:
            msgs = [m for m in msgs if m.msg_type == msg_type]
        return [m.to_dict() for m in msgs[-limit:]]

    def status(self) -> dict:
        return {
            "total_messages": len(self._message_log),
            "protocols_available": ["debate", "consensus", "delegation", "escalation"],
            "escalation_chain": self.escalation.chain,
            "registered_agents": list(self.delegation._agent_capabilities.keys()),
        }
