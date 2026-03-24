#!/usr/bin/env python3
"""
Matrix Monitor UI for Bit Rage Systems
Version: 1.1
Adapted from AAC repository; provides a live dashboard of agent state, swarms,
global network and quantum integration status.
"""

import threading
import time
import json
import logging
from typing import Dict, Any

from inner_council.deploy_agents import InnerCouncilDeployment

try:
    from global_intelligence_network import global_network
except ImportError:
    global_network = None

try:
    from decision_optimizer import DecisionOptimizer
except ImportError:
    DecisionOptimizer = None

logger = logging.getLogger(__name__)

class MatrixMonitor:
    """Console-based matrix monitor dashboard

    (enhanced version can delegate to AAC module if available)
    """

    def __init__(self, deployment: InnerCouncilDeployment):
        # deployment reference and basic state
        self.deployment = deployment
        self.running = False
        self.thread = None

        # ensure attributes exist even if early error occurs
        self.use_delegate = False
        self.chatbot = None
        self.chat_available = False

        # try to use AAC enhanced UI if present; log but do not abort
        try:
            from apps.monitor.matrix_monitor.monitoring.aac_matrix_monitor_enhanced import AACMatrixMonitor
            self.delegate = AACMatrixMonitor(deployment)
            self.use_delegate = True
        except ImportError:
            self.use_delegate = False
        except Exception as e:
            logger.warning(f"AAC delegate initialization failed: {e}")
            self.use_delegate = False

        # optionally integrate Azure chatbot interface
        try:
            from az_chatbot import AzureChatbot
            # instantiate with default configuration
            self.chatbot = AzureChatbot()
            self.chat_available = True
        except Exception:
            # any failure simply disables chat
            self.chatbot = None
            self.chat_available = False

    def start(self):
        # if using AAC delegate, hand off entirely
        if getattr(self, "use_delegate", False):
            self.delegate.start()
            return

        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info("Matrix Monitor started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Matrix Monitor stopped")

    def _loop(self):
        while self.running:
            try:
                status = self.deployment.get_system_status()
                self._render(status)
                time.sleep(5)
            except Exception as e:
                logger.error(f"MatrixMonitor error: {e}")
                time.sleep(5)

    def _render(self, status: Dict[str, Any]):
        # clear screen
        print("\n\x1b[2J\x1b[H", end="")
        print("=== Bit Rage Systems MATRIX MONITOR ===")
        print(json.dumps(status, indent=2, default=str))
        if global_network:
            print("Nodes in Global Intelligence Network:",
                  global_network.list_nodes())
        if DecisionOptimizer:
            print("Available optimizer models:", list(
                DecisionOptimizer().models.keys()))
        if self.chat_available:
            print(
                "AZ Chatbot interface: available (use `matrix_monitor.chatbot` to send messages)")
        else:
            print("AZ Chatbot interface: not configured")
        print("(press Ctrl-C to exit)")

# convenience
monitor_instance: MatrixMonitor = None

def create_monitor(deployment: InnerCouncilDeployment) -> MatrixMonitor:
    global monitor_instance
    if monitor_instance is None:
        monitor_instance = MatrixMonitor(deployment)
    return monitor_instance
