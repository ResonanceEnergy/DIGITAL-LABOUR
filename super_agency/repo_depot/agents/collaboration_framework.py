# REPO DEPOT AGENTS - Collaboration Framework

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from .agent_registry import AgentRegistry, AgentSpecialization

logger = logging.getLogger(__name__)


class MessageType(Enum):
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    COLLABORATION_OFFER = "collaboration_offer"
    COLLABORATION_ACCEPT = "collaboration_accept"
    COLLABORATION_REJECT = "collaboration_reject"
    STATUS_UPDATE = "status_update"
    KNOWLEDGE_SHARE = "knowledge_share"
    CONFLICT_RESOLUTION = "conflict_resolution"


class CollaborationMode(Enum):
    SEQUENTIAL = "sequential"  # Agents work in sequence
    PARALLEL = "parallel"  # Agents work simultaneously
    HIERARCHICAL = "hierarchical"  # Master-slave relationship
    CONSENSUS = "consensus"  # Democratic decision making


@dataclass
class AgentMessage:
    """Message between agents"""

    message_id: str
    sender_id: str
    receiver_id: str
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # For request-response pairs
    priority: int = 1  # 1-5, higher is more urgent


@dataclass
class CollaborationSession:
    """Session for multi-agent collaboration"""

    session_id: str
    initiator_id: str
    participants: Set[str]
    mode: CollaborationMode
    objective: str
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    messages: List[AgentMessage] = field(default_factory=list)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    consensus_required: bool = False
    consensus_threshold: float = 0.66  # 2/3 majority


@dataclass
class TaskDependency:
    """Dependency between tasks in a collaborative workflow"""

    dependent_task: str
    dependency_task: str
    dependency_type: str  # "requires_output", "requires_review", "parallel_ok"


class CollaborationFramework:
    """
    Framework for multi-agent collaboration, communication, and coordination.
    Enables agents to work together on complex tasks.
    """

    def __init__(self, agent_registry: AgentRegistry):
        self.registry = agent_registry
        self.active_sessions: Dict[str, CollaborationSession] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.task_dependencies: Dict[str, List[TaskDependency]] = {}

        # Register default message handlers
        self._register_default_handlers()

        # Start message processing
        self.processing_task = None

    async def start(self):
        """Start the collaboration framework"""
        self.processing_task = asyncio.create_task(self._process_messages())
        logger.info("Collaboration framework started")

    async def stop(self):
        """Stop the collaboration framework"""
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Collaboration framework stopped")

    def _register_default_handlers(self):
        """Register default message handlers"""
        self.message_handlers = {
            MessageType.TASK_REQUEST: self._handle_task_request,
            MessageType.TASK_RESPONSE: self._handle_task_response,
            MessageType.COLLABORATION_OFFER: self._handle_collaboration_offer,
            MessageType.COLLABORATION_ACCEPT: self._handle_collaboration_accept,
            MessageType.COLLABORATION_REJECT: self._handle_collaboration_reject,
            MessageType.STATUS_UPDATE: self._handle_status_update,
            MessageType.KNOWLEDGE_SHARE: self._handle_knowledge_share,
            MessageType.CONFLICT_RESOLUTION: self._handle_conflict_resolution,
        }

    async def send_message(self, message: AgentMessage):
        """Send a message to the queue"""
        await self.message_queue.put(message)
        logger.debug(
            f"Message queued: {message.message_type.value} from {message.sender_id} to {message.receiver_id}"
        )

    async def _process_messages(self):
        """Process messages from the queue"""
        while True:
            try:
                message = await self.message_queue.get()
                await self._handle_message(message)
                self.message_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def _handle_message(self, message: AgentMessage):
        """Handle a single message"""
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error in message handler for {message.message_type.value}: {e}")
        else:
            logger.warning(f"No handler for message type: {message.message_type.value}")

    async def initiate_collaboration(
        self,
        initiator_id: str,
        participants: List[str],
        objective: str,
        mode: CollaborationMode = CollaborationMode.SEQUENTIAL,
    ) -> str:
        """Initiate a new collaboration session"""
        session_id = str(uuid.uuid4())

        session = CollaborationSession(
            session_id=session_id,
            initiator_id=initiator_id,
            participants=set([initiator_id] + participants),
            mode=mode,
            objective=objective,
        )

        self.active_sessions[session_id] = session

        # Send collaboration offers to participants
        for participant in participants:
            offer_message = AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=initiator_id,
                receiver_id=participant,
                message_type=MessageType.COLLABORATION_OFFER,
                content={
                    "session_id": session_id,
                    "objective": objective,
                    "mode": mode.value,
                    "participants": list(session.participants),
                },
            )
            await self.send_message(offer_message)

        logger.info(
            f"Initiated collaboration session {session_id} with {len(participants)} participants"
        )
        return session_id

    async def _handle_collaboration_offer(self, message: AgentMessage):
        """Handle collaboration offer"""
        session_id = message.content.get("session_id")
        objective = message.content.get("objective")

        # Auto-accept for now (could be made configurable)
        accept_message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=message.receiver_id,
            receiver_id=message.sender_id,
            message_type=MessageType.COLLABORATION_ACCEPT,
            content={"session_id": session_id},
            correlation_id=message.message_id,
        )
        await self.send_message(accept_message)

        logger.info(
            f"Agent {message.receiver_id} accepted collaboration offer for session {session_id}"
        )

    async def _handle_collaboration_accept(self, message: AgentMessage):
        """Handle collaboration acceptance"""
        session_id = message.content.get("session_id")
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.messages.append(message)
            logger.info(f"Collaboration acceptance recorded for session {session_id}")

    async def _handle_collaboration_reject(self, message: AgentMessage):
        """Handle collaboration rejection"""
        session_id = message.content.get("session_id")
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.messages.append(message)
            # Could implement session cancellation logic here
            logger.warning(f"Collaboration rejected for session {session_id}")

    async def request_task_assistance(
        self,
        requester_id: str,
        task_description: str,
        required_specializations: List[AgentSpecialization],
    ) -> List[str]:
        """Request assistance from other agents for a task"""
        available_agents = []

        for agent_id, agent in self.registry.agents.items():
            if agent.status.name == "ACTIVE" and agent.specialization in required_specializations:
                available_agents.append(agent_id)

        if not available_agents:
            logger.warning(
                f"No agents available for specializations: {[s.value for s in required_specializations]}"
            )
            return []

        # Send task requests
        responses = []
        for agent_id in available_agents:
            request_message = AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=requester_id,
                receiver_id=agent_id,
                message_type=MessageType.TASK_REQUEST,
                content={
                    "task_description": task_description,
                    "required_specializations": [s.value for s in required_specializations],
                },
            )
            await self.send_message(request_message)

            # Wait for response (simplified - in real implementation would use correlation_id)
            await asyncio.sleep(0.1)  # Brief delay for processing

        return available_agents

    async def _handle_task_request(self, message: AgentMessage):
        """Handle task request"""
        task_description = message.content.get("task_description", "")

        # Auto-accept for now (could evaluate capability)
        response_message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=message.receiver_id,
            receiver_id=message.sender_id,
            message_type=MessageType.TASK_RESPONSE,
            content={"accepted": True, "estimated_duration": 300, "confidence": 0.8},  # 5 minutes
            correlation_id=message.message_id,
        )
        await self.send_message(response_message)

    async def _handle_task_response(self, message: AgentMessage):
        """Handle task response"""
        # Store response for coordination
        logger.debug(f"Task response received from {message.sender_id}")

    async def share_knowledge(
        self, sender_id: str, knowledge_type: str, knowledge_data: Dict[str, Any]
    ):
        """Share knowledge with other agents"""
        # Broadcast knowledge to all active agents
        for agent_id, agent in self.registry.agents.items():
            if agent.status.name == "ACTIVE" and agent_id != sender_id:
                knowledge_message = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    sender_id=sender_id,
                    receiver_id=agent_id,
                    message_type=MessageType.KNOWLEDGE_SHARE,
                    content={"knowledge_type": knowledge_type, "data": knowledge_data},
                )
                await self.send_message(knowledge_message)

        logger.info(f"Knowledge shared: {knowledge_type} from {sender_id}")

    async def _handle_knowledge_share(self, message: AgentMessage):
        """Handle knowledge sharing"""
        knowledge_type = message.content.get("knowledge_type")
        # In a real implementation, this would update the agent's knowledge base
        logger.debug(f"Knowledge received: {knowledge_type} from {message.sender_id}")

    async def _handle_status_update(self, message: AgentMessage):
        """Handle status update"""
        # Update agent status in registry if needed
        logger.debug(f"Status update from {message.sender_id}: {message.content}")

    async def _handle_conflict_resolution(self, message: AgentMessage):
        """Handle conflict resolution request"""
        # Implement conflict resolution logic
        logger.info(f"Conflict resolution requested: {message.content}")

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a collaboration session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "status": session.status,
            "participants": list(session.participants),
            "mode": session.mode.value,
            "objective": session.objective,
            "message_count": len(session.messages),
            "created_at": session.created_at.isoformat(),
            "shared_context_keys": list(session.shared_context.keys()),
        }

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active collaboration sessions"""
        return [self.get_session_status(session_id) for session_id in self.active_sessions.keys()]

    async def resolve_conflict(
        self, session_id: str, conflict_description: str, options: List[str]
    ) -> Optional[str]:
        """Resolve a conflict through agent consensus"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None

        # Send conflict resolution request to all participants
        votes = {}

        for participant in session.participants:
            conflict_message = AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id="system",  # System-initiated
                receiver_id=participant,
                message_type=MessageType.CONFLICT_RESOLUTION,
                content={
                    "session_id": session_id,
                    "conflict": conflict_description,
                    "options": options,
                },
            )
            await self.send_message(conflict_message)

            # Simplified voting - in real implementation would collect actual votes
            votes[participant] = options[0]  # Auto-vote for first option

        # Simple majority vote
        vote_counts = {}
        for vote in votes.values():
            vote_counts[vote] = vote_counts.get(vote, 0) + 1

        winner = max(vote_counts.items(), key=lambda x: x[1])
        return winner[0]


# Global collaboration framework instance
collaboration_framework = CollaborationFramework(AgentRegistry())
