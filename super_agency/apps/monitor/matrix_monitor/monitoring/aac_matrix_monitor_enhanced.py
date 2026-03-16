#!/usr/bin/env python3
"""
AAC Matrix Monitor Enhanced
Advanced UI/UX adapted from the AAC repository. Provides a richer dashboard
and agent status visualization for the Matrix Monitor.
"""

import threading
import time
import json
import logging
from typing import Dict, Any

from inner_council.deploy_agents import InnerCouncilDeployment
from global_intelligence_network import global_network
from decision_optimizer import DecisionOptimizer

logger = logging.getLogger(__name__)

class AACMatrixMonitor:
    """Enhanced monitor that replaces default output"""

    def __init__(self, deployment: InnerCouncilDeployment):
        self.deployment = deployment
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info("AAC Matrix Monitor started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("AAC Matrix Monitor stopped")

    def _loop(self):
        while self.running:
            try:
                status = self.deployment.get_system_status()
                self._render(status)
                time.sleep(3)
            except Exception as e:
                logger.error(f"AACMatrixMonitor error: {e}")
                time.sleep(3)

    def _render(self, status: Dict[str, Any]):
        # example enhanced formatting
        print("\n=== AAC MATRIX MONITOR ===")
        print("Agents:")
        for name, s in status.get('agents', {}).items():
            print(
                f" - {name}: active={s.get('is_active')} last={s.get('last_activity')}")
        print("Global nodes:", global_network.list_nodes())
        print("Swarm count:", len(getattr(self.deployment, 'swarm_coordinator', {
              }).active_swarms if hasattr(self.deployment, 'swarm_coordinator') else []))
        print("---")


# end of enhanced monitor
