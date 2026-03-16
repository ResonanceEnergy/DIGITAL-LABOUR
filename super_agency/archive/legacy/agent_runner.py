#!/usr/bin/env python3
"""
AGENT RUNNER - Persistent Agent Execution
Runs Agent Optimus and Agent Gasket as continuous background processes
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir / "agents"))

from agents.agent_optimus import AgentOptimus
from agents.agent_gasket import AgentGasket

class AgentRunner:
    """Manages persistent execution of agents"""

    def __init__(self):
        self.logger = logging.getLogger("AgentRunner")
        logging.basicConfig(level=logging.INFO)

        self.optimus = None
        self.gasket = None
        self.running = True

    async def start_agents(self):
        """Start both agents and keep them running"""
        self.logger.info("🚀 Starting Agent Runner...")

        try:
            # Initialize agents (they will start their own operational loops)
            self.logger.info("🤖 Initializing Agent Optimus...")
            self.optimus = AgentOptimus()

            self.logger.info("⚙️ Initializing Agent Gasket...")
            self.gasket = AgentGasket()

            # Explicitly start operational work
            self.logger.info("🔄 Starting Agent Optimus operational work...")
            await self.optimus.start_operational_work()

            self.logger.info("🔄 Starting Agent Gasket operational work...")
            await self.gasket.start_operational_work()

            self.logger.info("✅ Agents initialized and operational loops started")

            # Keep the runner alive and monitor agents
            while self.running:
                # Check if agents are still active
                if hasattr(self.optimus, 'logger'):
                    self.logger.info("🔄 Agent Optimus: ACTIVE")
                if hasattr(self.gasket, 'logger'):
                    self.logger.info("🔄 Agent Gasket: ACTIVE")

                await asyncio.sleep(300)  # Log every 5 minutes

        except Exception as e:
            self.logger.error(f"Agent Runner error: {e}")
            raise

    def stop_agents(self):
        """Stop all agents"""
        self.logger.info("🛑 Stopping Agent Runner...")
        self.running = False

async def main():
    """Main entry point"""
    runner = AgentRunner()

    # Handle shutdown signals
    def signal_handler(signum, frame):
        runner.stop_agents()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await runner.start_agents()
    except KeyboardInterrupt:
        runner.stop_agents()
    except Exception as e:
        logging.error(f"Agent Runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
