#!/usr/bin/env python3
"""
Inner Council Agent Deployment System
Deploy and coordinate all council member agents for distributed intelligence gathering
"""

import sys
import os
import time
import signal
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime, timedelta
import argparse

# Add the agents directory to Python path
agents_dir = Path(__file__).parent / "agents"
sys.path.insert(0, str(agents_dir))

from base_agent import MessageBus, AgentManager
from agent_registry import create_all_agents

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('inner_council_deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InnerCouncilDeployment:
    """Deployment system for Inner Council agents"""

    def __init__(self):
        self.message_bus = MessageBus()
        self.agent_manager = AgentManager()
        self.agents: Dict[str, Any] = {}
        self.running = False
        self.threads: List[threading.Thread] = []

    def initialize_agents(self) -> bool:
        """Initialize all council member agents"""
        logger.info("🚀 Initializing Inner Council agents...")

        try:
            # Create all agents
            self.agents = create_all_agents()

            # Register agents with the manager
            for agent_name, agent in self.agents.items():
                self.agent_manager.register_agent(agent)
                logger.info(f"✅ Registered agent: {agent_name}")

            logger.info(
                f"🎯 Successfully initialized {len(self.agents)} agents")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize agents: {e}")
            return False

    def start_agents(self) -> bool:
        """Start all agents in separate threads"""
        logger.info("▶️  Starting Inner Council agents...")

        try:
            self.running = True

            # Start each agent in its own thread
            for agent_name, agent in self.agents.items():
                thread = threading.Thread(
                    target=self._run_agent,
                    args=(agent_name, agent),
                    name=f"Agent-{agent_name}",
                    daemon=True
                )
                thread.start()
                self.threads.append(thread)
                logger.info(f"▶️  Started agent thread: {agent_name}")

            # Start the message bus
            bus_thread = threading.Thread(
                target=self.message_bus.start,
                name="MessageBus",
                daemon=True
            )
            bus_thread.start()
            self.threads.append(bus_thread)
            logger.info("▶️  Started message bus")

            logger.info("🎯 All agents and message bus started successfully")

            # optional UI monitor
            try:
                from matrix_monitor import create_monitor
                self.ui_monitor = create_monitor(self)
                self.ui_monitor.start()
            except Exception:
                logger.warning("Matrix monitor unavailable")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to start agents: {e}")
            return False

    def _run_agent(self, agent_name: str, agent: Any):
        """Run an individual agent"""
        try:
            logger.info(f"🤖 Agent {agent_name} entering operational mode")

            # Start the agent
            agent.start()

            # Main agent loop
            while self.running:
                try:
                    # Run monitoring cycle based on frequency
                    agent.run_monitoring_cycle()

                    # Sleep based on monitoring frequency
                    sleep_time = 86400 if agent.monitoring_frequency == "daily" else 604800  # 24h or 7d
                    # Cap at 1 hour for testing
                    time.sleep(min(sleep_time, 3600))

                except Exception as e:
                    logger.error(f"❌ Error in agent {agent_name} cycle: {e}")
                    time.sleep(60)  # Wait before retry

        except Exception as e:
            logger.error(f"❌ Fatal error in agent {agent_name}: {e}")
        finally:
            logger.info(f"🛑 Agent {agent_name} shutting down")

    def stop_agents(self):
        """Stop all agents and clean up"""
        logger.info("🛑 Stopping Inner Council agents...")

        # stop UI monitor if running
        try:
            if hasattr(self, 'ui_monitor') and self.ui_monitor:
                self.ui_monitor.stop()
        except Exception:
            pass

        self.running = False

        # Stop message bus
        self.message_bus.stop()

        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5.0)

        # Stop individual agents
        for agent_name, agent in self.agents.items():
            try:
                agent.stop()
                logger.info(f"🛑 Stopped agent: {agent_name}")
            except Exception as e:
                logger.error(f"❌ Error stopping agent {agent_name}: {e}")

        logger.info("🎯 All agents stopped")

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "system_running": self.running,
            "total_agents": len(self.agents),
            "active_threads": len([t for t in self.threads if t.is_alive()]),
            "message_bus_status": getattr(self.message_bus, "get_status", lambda: {
                "running": self.message_bus.running,
                "registered_agents": list(self.message_bus.agents.keys()),
                "queue_size": self.message_bus.message_queue.qsize(),
            })(),
            "agents": {}
        }

        for agent_name, agent in self.agents.items():
            try:
                agent_status = agent.get_status()
                status["agents"][agent_name] = agent_status
            except Exception as e:
                status["agents"][agent_name] = {"error": str(e)}

        return status

    def run_coordination_cycle(self):
        """Run a coordination cycle across all agents"""
        logger.info("🔄 Running coordination cycle...")

        try:
            # Request insights from all agents
            insights_request = {
                "type": "get_insights",
                "payload": {"request_type": "coordination_cycle"},
                "timestamp": datetime.now().isoformat()
            }

            # Broadcast to all agents
            self.message_bus.broadcast(insights_request)

            # Collect responses (simplified - in production would wait for responses)
            time.sleep(2)  # Allow time for processing

            logger.info("✅ Coordination cycle completed")

        except Exception as e:
            logger.error(f"❌ Error in coordination cycle: {e}")

    # convenience wrappers for newly implemented features
    def list_market_agents(self):
        """Return list of agent classes available via marketplace"""
        if self.marketplace:
            return self.marketplace.list_available_agents()
        return []

    def initiate_swarm(self, task: str, agent_classes: List[str]) -> str:
        """Create a new swarm using the swarm coordinator"""
        if not self.swarm_coordinator:
            raise RuntimeError("Swarm coordinator not available")
        return self.swarm_coordinator.initiate_swarm(task, agent_classes)

    def terminate_swarm(self, swarm_id: str) -> bool:
        if not self.swarm_coordinator:
            raise RuntimeError("Swarm coordinator not available")
        return self.swarm_coordinator.terminate_swarm(swarm_id)

    def run_simulation_cycle(self):
        """Run a simulation cycle for testing"""
        logger.info("🎭 Running simulation cycle...")

        # Simulate some activity
        for agent_name, agent in self.agents.items():
            try:
                # Run a monitoring cycle
                agent.run_monitoring_cycle()
                logger.info(f"✅ Simulation cycle completed for {agent_name}")
            except Exception as e:
                logger.error(
                    f"❌ Simulation cycle failed for {agent_name}: {e}")

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(
        description="Inner Council Agent Deployment")
    parser.add_argument(
        "--mode", choices=["deploy", "test", "status"],
        default="deploy", help="Deployment mode")
    parser.add_argument("--duration", type=int, default=0,
                       help="Duration to run in seconds (0 = indefinite)")
    parser.add_argument("--coordination-interval", type=int, default=3600,
                       help="Coordination cycle interval in seconds")

    args = parser.parse_args()

    # Initialize deployment system
    deployment = InnerCouncilDeployment()

    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        logger.info("🛑 Shutdown signal received")
        deployment.stop_agents()
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize agents
        if not deployment.initialize_agents():
            logger.error("❌ Agent initialization failed")
            return 1

        if args.mode == "test":
            # Run simulation cycle
            deployment.run_simulation_cycle()

            # Get and display status
            status = deployment.get_system_status()
            print(json.dumps(status, indent=2, default=str))

        elif args.mode == "status":
            # Get and display status
            status = deployment.get_system_status()
            print(json.dumps(status, indent=2, default=str))

        elif args.mode == "deploy":
            # Start agents
            if not deployment.start_agents():
                logger.error("❌ Agent startup failed")
                return 1

            logger.info("🎯 Inner Council deployment active")
            logger.info(
                f"📊 Monitoring {len(deployment.agents)} council members")
            logger.info(
                "💡 Agents will run autonomous intelligence gathering cycles")

            start_time = time.time()
            coordination_next = start_time + args.coordination_interval

            # Main deployment loop
            while deployment.running:
                current_time = time.time()

                # Run coordination cycle if interval reached
                if current_time >= coordination_next:
                    deployment.run_coordination_cycle()
                    coordination_next = current_time + args.coordination_interval

                # Check duration limit
                if args.duration >0 and(
                    current_time -start_time) >=args.duration:
                    logger.info(f"⏰ Duration limit ({args.duration}s) reached")
                    break

                # Periodic status logging
                if int(current_time) % 300 == 0:  # Every 5 minutes
                    status = deployment.get_system_status()
                    active_agents = sum(
                        1 for a in status["agents"].values()
                        if isinstance(a, dict) and a.get("status") =="active")
                    logger.info(
                        f"📊 Status: {active_agents}/{len(deployment.agents)} agents active")

                time.sleep(10)  # Check every 10 seconds

    except KeyboardInterrupt:
        logger.info("🛑 Deployment interrupted by user")
    except Exception as e:
        logger.error(f"❌ Deployment error: {e}")
        return 1
    finally:
        deployment.stop_agents()

    logger.info("🎯 Inner Council deployment completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())