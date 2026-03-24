#!/usr/bin/env python3
"""
Inner Council Agent Framework
Base classes and protocols for autonomous council member agents
"""

import asyncio
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import queue
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AgentMessage:
    """Message structure for inter-agent communication"""
    message_id: str
    sender: str
    recipient: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    priority: str = "normal"  # low, normal, high, urgent
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class AgentCapabilities:
    """Agent capabilities and specializations"""
    content_analysis: bool = True
    strategic_planning: bool = False
    risk_assessment: bool = False
    policy_recommendation: bool = False
    real_time_monitoring: bool = True
    autonomous_decision_making: bool = False
    cross_agent_coordination: bool = True

class MessageBus:
    """Central message bus for agent communication"""

    def __init__(self):
        self.agents: Dict[str, 'BaseCouncilAgent'] = {}
        self.message_queue = queue.Queue()
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def register_agent(self, agent: 'BaseCouncilAgent'):
        """Register an agent with the message bus"""
        self.agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.name} ({agent.agent_id})")

    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")

    def send_message(self, message: AgentMessage):
        """Send a message to the bus"""
        self.message_queue.put(message)

    def broadcast(self, message_dict: Dict[str, Any]):
        """Broadcast a message to all agents"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=message_dict.get("sender", "system"),
            recipient="broadcast",
            message_type=message_dict.get("type", "broadcast"),
            payload=message_dict.get("payload", {}),
            timestamp=datetime.now(),
            priority=message_dict.get("priority", "normal")
        )
        self.send_message(message)

    def start(self):
        """Start the message processing thread"""
        self.running = True
        self.thread = threading.Thread(
            target=self._process_messages, daemon=True)
        self.thread.start()
        logger.info("Message bus started")

    def stop(self):
        """Stop the message processing"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Message bus stopped")

    def get_status(self) -> Dict[str, Any]:
        """Return current status of the message bus for monitoring"""
        return {
            "running": self.running,
            "registered_agents": list(self.agents.keys()),
            "queue_size": self.message_queue.qsize(),
        }

    def _process_messages(self):
        """Process messages from the queue"""
        while self.running:
            try:
                message = self.message_queue.get(timeout=1)

                # Route message to recipient
                if message.recipient in self.agents:
                    agent = self.agents[message.recipient]
                    # Run in thread pool to avoid blocking
                    threading.Thread(
                        target=self._deliver_message,
                        args=(agent, message),
                        daemon=True
                    ).start()
                elif message.recipient == "broadcast":
                    # Broadcast to all agents
                    for agent in self.agents.values():
                        threading.Thread(
                            target=self._deliver_message,
                            args=(agent, message),
                            daemon=True
                        ).start()
                else:
                    logger.warning(
                        f"No recipient found for message: {message.recipient}")

                self.message_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    def _deliver_message(self, agent: 'BaseCouncilAgent',
                          message: AgentMessage):
        """Deliver message to agent"""
        try:
            agent.receive_message(message)
        except Exception as e:
            logger.error(f"Error delivering message to {agent.name}: {e}")

# Global message bus instance
message_bus = MessageBus()

class BaseCouncilAgent(ABC):
    """Base class for all council member agents"""

    def __init__(self, name: str, channel_id: str, focus_areas: List[str],
                 priority: str, monitoring_frequency: str):
        self.agent_id = str(uuid.uuid4())
        self.name = name
        self.channel_id = channel_id
        self.focus_areas = focus_areas
        self.priority = priority
        self.monitoring_frequency = monitoring_frequency

        # Agent state
        self.is_active = False
        self.last_activity = datetime.now()
        self.message_handlers: Dict[str, Callable] = {}

        # Capabilities
        self.capabilities = AgentCapabilities()

        # Data storage
        self.data_dir = Path(
            f"inner_council/agents/{self.name.lower().replace(' ', '_')}")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Communication
        self.message_bus = message_bus
        self.message_bus.register_agent(self)

        # Setup message handlers
        self._setup_message_handlers()

        logger.info(f"Initialized agent: {self.name} ({self.agent_id})")

    def start(self):
        """Start the agent"""
        self.is_active = True
        self.last_activity = datetime.now()
        logger.info(f"Agent {self.name} started")

    def stop(self):
        """Stop the agent"""
        self.is_active = False
        logger.info(f"Agent {self.name} stopped")

    def receive_message(self, message: AgentMessage):
        """Receive and process a message"""
        self.last_activity = datetime.now()

        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                response = handler(message)
                if response:
                    self._send_response(message, response)
            except Exception as e:
                logger.error(
                    f"Error handling message {message.message_type}: {e}")
                self._send_error_response(message, str(e))
        else:
            logger.warning(
                f"No handler for message type: {message.message_type}")

    def send_message(
            self, recipient: str, message_type: str, payload: Dict[str, Any],
            priority: str="normal", correlation_id: Optional[str]=None):
        """Send a message through the bus"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=self.agent_id,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.now(),
            priority=priority,
            correlation_id=correlation_id
        )
        self.message_bus.send_message(message)

    def _send_response(self, original_message: AgentMessage,
                       response_payload: Dict[str, Any]):
        """Send a response to a message"""
        self.send_message(
            recipient=original_message.sender,
            message_type=f"{original_message.message_type}_response",
            payload=response_payload,
            correlation_id=original_message.message_id
        )

    def _send_error_response(self, original_message: AgentMessage, error: str):
        """Send an error response"""
        self.send_message(
            recipient=original_message.sender,
            message_type="error",
            payload={"error": error,
                "original_message": original_message.message_id},
            priority="high",
            correlation_id=original_message.message_id
        )

    def _setup_message_handlers(self):
        """Setup message handlers - override in subclasses"""
        self.message_handlers.update({
            "ping": self._handle_ping,
            "status_request": self._handle_status_request,
            "shutdown": self._handle_shutdown,
            "analyze_content": self._handle_analyze_content,
            "get_insights": self._handle_get_insights,
            "coordinate_action": self._handle_coordinate_action
        })

    def _handle_ping(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle ping messages"""
        return {"status": "alive", "timestamp": datetime.now().isoformat()}

    def _handle_status_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle status requests"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "is_active": self.is_active,
            "last_activity": self.last_activity.isoformat(),
            "capabilities": asdict(self.capabilities),
            "focus_areas": self.focus_areas,
            "priority": self.priority
        }

    def _handle_shutdown(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle shutdown requests"""
        self.stop()
        return {"status": "shutdown", "timestamp": datetime.now().isoformat()}

    @abstractmethod
    def _handle_analyze_content(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle content analysis requests - must be implemented by subclasses"""
        pass

    @abstractmethod
    def _handle_get_insights(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle insight requests - must be implemented by subclasses"""
        pass

    def _handle_coordinate_action(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle coordination requests"""
        action = message.payload.get("action")
        if action == "sync_insights":
            return self._coordinate_insights_sync()
        elif action == "collaborate_analysis":
            return self._coordinate_analysis_collaboration(message.payload)
        else:
            return {"error": f"Unknown coordination action: {action}"}

    def _coordinate_insights_sync(self) -> Dict[str, Any]:
        """Synchronize insights with other agents"""
        # Get recent insights
        insights = self._get_recent_insights()

        # Send insights to Bit Rage Systems
        self.send_message(
            recipient="super_agency",
            message_type="insights_sync",
            payload={
                "agent_name": self.name,
                "insights": insights,
                "sync_timestamp": datetime.now().isoformat()
            }
        )

        return {"status": "insights_synced", "count": len(insights)}

    def _coordinate_analysis_collaboration(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Collaborate on analysis with other agents"""
        topic = payload.get("topic")
        collaborating_agents = payload.get("agents", [])

        # Request collaboration from other agents
        for agent_id in collaborating_agents:
            self.send_message(
                recipient=agent_id,
                message_type="collaboration_request",
                payload={
                    "topic": topic,
                    "requester": self.name,
                    "collaboration_type": "analysis"
                }
            )

        return {"status": "collaboration_initiated", "topic": topic}

    @abstractmethod
    def _get_recent_insights(self) -> List[Dict[str, Any]]:
        """Get recent insights - must be implemented by subclasses"""
        pass

    def run_monitoring_cycle(self):
        """Run one monitoring cycle - override in subclasses"""
        if not self.is_active:
            return

        try:
            # Monitor channel for new content
            new_content = self._monitor_channel()

            if new_content:
                # Analyze content
                analysis_results = self._analyze_content_batch(new_content)

                # Store results
                self._store_analysis_results(analysis_results)

                # Send to Bit Rage Systems
                self._report_to_super_agency(analysis_results)

                logger.info(
                    f"{self.name}: Processed {len(new_content)} new content items")

        except Exception as e:
            logger.error(f"Error in monitoring cycle for {self.name}: {e}")

    @abstractmethod
    def _monitor_channel(self) -> List[Dict[str, Any]]:
        """Monitor channel for new content - must be implemented by subclasses"""
        pass

    @abstractmethod
    def _analyze_content_batch(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze batch of content - must be implemented by subclasses"""
        pass

    def _store_analysis_results(self, results: List[Dict[str, Any]]):
        """Store analysis results locally"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{timestamp}.json"
        filepath = self.data_dir / filename

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

    def _report_to_super_agency(self, results: List[Dict[str, Any]]):
        """Report analysis results to Bit Rage Systems"""
        self.send_message(
            recipient="super_agency",
            message_type="analysis_complete",
            payload={
                "agent_name": self.name,
                "results": results,
                "timestamp": datetime.now().isoformat()
            },
            priority="normal"
        )

    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "is_active": self.is_active,
            "last_activity": self.last_activity.isoformat(),
            "focus_areas": self.focus_areas,
            "capabilities": asdict(self.capabilities)
        }

class AgentManager:
    """Manager for coordinating multiple agents"""

    def __init__(self):
        self.agents: Dict[str, BaseCouncilAgent] = {}
        self.message_bus = message_bus

    def register_agent(self, agent: BaseCouncilAgent):
        """Register an agent"""
        self.agents[agent.agent_id] = agent
        logger.info(f"Agent manager registered: {agent.name}")

    def start_all_agents(self):
        """Start all registered agents"""
        for agent in self.agents.values():
            agent.start()
        logger.info(f"Started {len(self.agents)} agents")

    def stop_all_agents(self):
        """Stop all registered agents"""
        for agent in self.agents.values():
            agent.stop()
        logger.info(f"Stopped {len(self.agents)} agents")

    def get_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all agents"""
        return {agent_id: agent.get_status() for agent_id, agent in self.agents.items()}

    def broadcast_message(
            self, message_type: str, payload: Dict[str, Any],
            priority: str="normal"):
        """Broadcast message to all agents"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender="agent_manager",
            recipient="broadcast",
            message_type=message_type,
            payload=payload,
            timestamp=datetime.now(),
            priority=priority
        )
        self.message_bus.send_message(message)

    def send_to_agent(
            self, agent_name: str, message_type: str, payload: Dict
            [str, Any]):
        """Send message to specific agent by name"""
        for agent in self.agents.values():
            if agent.name == agent_name:
                agent.send_message(
                    recipient=agent.agent_id,
                    message_type=message_type,
                    payload=payload
                )
                return
        logger.warning(f"Agent not found: {agent_name}")

# Global agent manager instance
agent_manager = AgentManager()