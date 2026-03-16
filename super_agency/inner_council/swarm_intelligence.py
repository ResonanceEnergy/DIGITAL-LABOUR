#!/usr/bin/env python3
"""
Swarm Intelligence Coordinator
Creates and manages temporary swarms of agents to tackle specialized tasks
"""

import threading
import uuid
import logging
import time
from typing import Dict, List, Any

from inner_council.agents.agent_marketplace import global_marketplace
from inner_council.agents.base_agent import MessageBus, BaseCouncilAgent

logger = logging.getLogger(__name__)


class SwarmCoordinator:
    """Orchestrates swarms of agents for parallel problem solving"""

    def __init__(self, message_bus: MessageBus = None):
        self.message_bus = message_bus or MessageBus()
        self.active_swarms: Dict[str, List[BaseCouncilAgent]] = {}

    def initiate_swarm(
            self, task_description: str, agent_classes: List[str],
            swarm_id: str=None) ->str:
        """Create a new swarm of agents specified by class names"""
        if swarm_id is None:
            swarm_id = str(uuid.uuid4())

        members: List[BaseCouncilAgent] = []
        for cls_name in agent_classes:
            try:
                agent = global_marketplace.create_agent(cls_name)
                # tag agent to swarm
                agent.name = f"{agent.name}-swarm-{swarm_id}"
                agent.start()
                members.append(agent)
            except Exception as e:
                logger.error(f"Failed to create swarm member {cls_name}: {e}")

        self.active_swarms[swarm_id] = members
        logger.info(
            f"Swarm {swarm_id} initiated with {len(members)} members for task '{task_description}'")
        return swarm_id

    def terminate_swarm(self, swarm_id: str) -> bool:
        """Shutdown all agents in a swarm"""
        if swarm_id not in self.active_swarms:
            logger.warning(f"Swarm {swarm_id} not found")
            return False

        for agent in self.active_swarms[swarm_id]:
            try:
                agent.stop()
            except Exception as e:
                logger.error(f"Error stopping swarm agent {agent.name}: {e}")
        del self.active_swarms[swarm_id]
        logger.info(f"Swarm {swarm_id} terminated")
        return True

    def collect_results(self, swarm_id: str) -> Dict[str, Any]:
        """Aggregate results from swarm members"""
        results = {}
        members = self.active_swarms.get(swarm_id, [])
        for agent in members:
            try:
                insights = agent.get_status().get("latest_insights", [])
                results[agent.name] = insights
            except Exception:
                results[agent.name] = None
        return results

    def list_swarms(self) -> List[str]:
        """List active swarm identifiers"""
        return list(self.active_swarms.keys())
