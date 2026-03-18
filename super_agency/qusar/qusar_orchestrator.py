#!/usr/bin/env python3
"""
QUSAR Orchestrator - Orchestration Layer for BIT RAGE LABOUR
Handles feedback loops, goal formulation, and high-level coordination
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import SASP components with fallback
try:
    from sasp_protocol import (
        SASPClient,
        SASPMessage,
        SASPNetworkManager,
        SASPNode,
        SASPProtocol,
        SASPSecurityManager,
        get_sasp_network,
        get_sasp_protocol,
    )
    SASP_AVAILABLE = True
except ImportError:
    SASP_AVAILABLE = False
    logging.info("SASP Protocol not available - running in standalone mode")

    # Stub classes for standalone mode
    class SASPSecurityManager:
        def __init__(self, key): self.key = key
        def sign_message(self, msg): return "stub-signature"
        def verify_signature(self, msg, sig): return True

    class SASPClient:
        def __init__(self, host, port, security_manager, use_tls=False):
            self.host = host
            self.port = port
            self.connected = False
        def connect(self): self.connected = True
        def send_message(self, msg): pass
        def receive_response(self, timeout=5.0): return None
        def close(self): self.connected = False

    class SASPMessage:
        def __init__(self, msg_type, payload, msg_id=None):
            self.message_type = msg_type
            self.payload = payload
        def to_dict(self): return {
                    'message_type': self.message_type, 'payload': self.payload}
        @classmethod
        def from_dict(cls, data): return cls(
            data.get('message_type'), data.get('payload'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - QUSAR - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackLoopManager:
    """Manages feedback loops for continuous improvement"""

    def __init__(self):
        self.feedback_history = []
        self.learning_patterns = {}
        self.performance_metrics = {}

    def process_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming feedback and extract learning patterns"""
        self.feedback_history.append({
            'timestamp': time.time(),
            'data': feedback_data
        })

        # Extract patterns from feedback
        patterns = self._extract_patterns(feedback_data)

        # Update learning patterns
        for pattern, confidence in patterns.items():
            if pattern not in self.learning_patterns:
                self.learning_patterns[pattern] = confidence
            else:
                # Weighted average for pattern confidence
                self.learning_patterns[pattern] = (
                    self.learning_patterns[pattern] * 0.7 + confidence * 0.3
                )

        return {
            'patterns_learned': len(patterns),
            'confidence_improved': sum(patterns.values()) / len(patterns) if patterns else 0
        }

    def _extract_patterns(self, feedback_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract learning patterns from feedback data"""
        patterns = {}

        # Simple pattern extraction based on feedback type
        feedback_type = feedback_data.get('type', 'unknown')

        if feedback_type == 'performance':
            success_rate = feedback_data.get('success_rate', 0.5)
            patterns['performance_optimization'] = min(success_rate + 0.1, 1.0)

        elif feedback_type == 'error':
            error_type = feedback_data.get('error_type', 'unknown')
            patterns[f'error_handling_{error_type}'] = 0.8

        elif feedback_type == 'goal_completion':
            completion_rate = feedback_data.get('completion_rate', 0.5)
            patterns['goal_formulation'] = completion_rate

        return patterns

    def get_learning_insights(self) -> Dict[str, Any]:
        """Get current learning insights from feedback history"""
        return {
            'total_feedback_processed': len(self.feedback_history),
            'active_patterns': len(self.learning_patterns),
            'top_patterns': sorted(
                self.learning_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

class GoalFormulator:
    """Formulates goals based on feedback and system state"""

    def __init__(self):
        self.active_goals = []
        self.goal_templates = {
            'optimization': 'Optimize {component} for {metric} improvement',
            'expansion': 'Expand {component} capabilities in {domain}',
            'integration': 'Integrate {component} with {target_system}',
            'monitoring': 'Enhance monitoring for {component} {aspect}'
        }

    def formulate_goal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Formulate a new goal based on current context"""
        goal_type = context.get('goal_type', 'optimization')
        template = self.goal_templates.get(
            goal_type, self.goal_templates['optimization'])

        goal = {
            'id': f"goal_{int(time.time())}_{len(self.active_goals)}",
            'type': goal_type,
            'description': template.format(**context),
            'priority': context.get('priority', 'medium'),
            'created_at': time.time(),
            'context': context,
            'status': 'formulated'
        }

        self.active_goals.append(goal)
        return goal

    def prioritize_goals(self) -> List[Dict[str, Any]]:
        """Prioritize active goals based on various factors"""
        priority_weights = {'high': 3, 'medium': 2, 'low': 1}

        prioritized = sorted(
            self.active_goals,
            key=lambda g: priority_weights.get(g['priority'], 1),
            reverse=True
        )

        return prioritized[:10]  # Return top 10 goals

class QUSAROrchestrator:
    """Main QUSAR orchestration coordinator"""

    def __init__(self, qforge_host: str = None, qforge_port: int = None):
        self.feedback_manager = FeedbackLoopManager()
        self.goal_formulator = GoalFormulator()
        self.device_state = {}
        self.is_running = False
        self.initialized = False

        # SASP communication
        self.security = SASPSecurityManager(
            'qforge-secret-key-change-in-production')
        self.qforge_client = None

        # Configuration
        self.config = self._load_config()

        # Override with explicit host/port if provided
        if qforge_host:
            self.config.setdefault('communication', {})['host'] = qforge_host
        if qforge_port:
            self.config.setdefault('communication', {})['port'] = qforge_port

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from global config file"""
        config_path = Path(__file__).parent.parent / "config" / "global.yaml"
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load config: {e}, using defaults")
            return {
                'communication': {'host': '127.0.0.1', 'port': 8888, 'use_tls': False},
                'system': {'name': 'BIT RAGE LABOUR'}
            }

    def start(self):
        """Start QUSAR orchestration services"""
        logger.info("Starting QUSAR orchestration services")

        # Initialize SASP client for QFORGE communication
        comm_config = self.config.get('communication', {})
        self.qforge_client = SASPClient(
            host=comm_config.get('host', '127.0.0.1'),
            port=comm_config.get('port', 8888),
            security_manager=self.security,
            use_tls=comm_config.get('use_tls', False)
        )

        # Connect to QFORGE
        try:
            self.qforge_client.connect()
            logger.info("Connected to QFORGE execution layer")
        except Exception as e:
            logger.warning(f"Failed to connect to QFORGE: {e}")
            self.qforge_client = None

        self.is_running = True
        logger.info("QUSAR orchestration services started")

    def stop(self):
        """Stop QUSAR orchestration services"""
        logger.info("Stopping QUSAR orchestration services")
        self.is_running = False

        if self.qforge_client:
            self.qforge_client.close()

    async def run_maintenance_cycle(self):
        """Run the main orchestration maintenance cycle"""
        logger.info("Starting QUSAR maintenance cycle")

        cycle_count = 0
        while self.is_running:
            try:
                cycle_count += 1
                logger.debug(f"Maintenance cycle {cycle_count}")

                # Process feedback loops
                await self._process_feedback_loops()

                # Formulate new goals
                await self._formulate_goals()

                # Coordinate with QFORGE
                await self._coordinate_with_qforge()

                # Update device state
                await self._update_device_state()

                # Brief pause between cycles
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in maintenance cycle: {e}")
                await asyncio.sleep(10)  # Longer pause on error

    async def _process_feedback_loops(self):
        """Process feedback from various sources"""
        # Simulate feedback processing (in real implementation, this would
        # collect feedback from QFORGE and other components)
        feedback_data = {
            'type': 'performance',
            'success_rate': 0.85,
            'timestamp': time.time()
        }

        result = self.feedback_manager.process_feedback(feedback_data)
        logger.debug(f"Processed feedback: {result}")

    async def _formulate_goals(self):
        """Formulate new goals based on current state"""
        # Check if we need new goals
        if len(self.goal_formulator.active_goals) < 3:
            context = {
                'goal_type': 'optimization',
                'component': 'task_execution',
                'metric': 'efficiency',
                'priority': 'medium'
            }

            goal = self.goal_formulator.formulate_goal(context)
            logger.info(f"Formulated new goal: {goal['description']}")

    async def _coordinate_with_qforge(self):
        """Coordinate with QFORGE execution layer"""
        if not self.qforge_client:
            return

        try:
            # Send status update to QFORGE
            status_message = self.feedback_manager.create_feedback_message({
                'orchestrator_status': 'active',
                'active_goals': len(self.goal_formulator.active_goals),
                'feedback_processed': len(self.feedback_manager.feedback_history)
            })

            self.qforge_client.send_message(status_message)
            logger.debug("Sent status update to QFORGE")

        except Exception as e:
            logger.warning(f"Failed to coordinate with QFORGE: {e}")

    async def _update_device_state(self):
        """Update device state information"""
        # Simulate device state updates
        self.device_state.update({
            'last_update': time.time(),
            'goals_active': len(self.goal_formulator.active_goals),
            'feedback_count': len(self.feedback_manager.feedback_history)
        })

    def get_status(self) -> Dict[str, Any]:
        """Get current QUSAR status"""
        return {
            'is_running': self.is_running,
            'initialized': self.initialized,
            'active_goals': len(self.goal_formulator.active_goals),
            'feedback_processed': len(self.feedback_manager.feedback_history),
            'learning_insights': self.feedback_manager.get_learning_insights(),
            'device_state': self.device_state
        }

    async def initialize(self):
        """Initialize QUSAR orchestration services (async version of start)"""
        logger.info("Initializing QUSAR orchestration services")
        self.start()
        self.initialized = True
        logger.info("QUSAR orchestration services initialized")

    async def orchestrate_cycle(self):
        """Run a single orchestration cycle"""
        if not self.is_running:
            logger.warning("Orchestrator not running, starting...")
            self.start()

        logger.debug("Running single orchestration cycle")

        # Process feedback loops
        await self._process_feedback_loops()

        # Formulate new goals
        await self._formulate_goals()

        # Coordinate with QFORGE
        await self._coordinate_with_qforge()

        # Update device state
        await self._update_device_state()

        return self.get_status()

    async def add_goal(self, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new goal to the orchestrator"""
        logger.info(
            f"Adding new goal: {goal_data.get('description', 'unnamed')}")

        goal = self.goal_formulator.formulate_goal(goal_data)
        logger.info(f"Goal added: {goal['id']}")

        return goal

    async def shutdown(self):
        """Shutdown QUSAR orchestration services (async version of stop)"""
        logger.info("Shutting down QUSAR orchestration services")
        self.stop()
        self.initialized = False
        logger.info("QUSAR orchestration services shutdown complete")
