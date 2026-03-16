#!/usr/bin/env python3
"""
Matrix Maximizer Workstation - QUSAR Operations Interface
Advanced terminal-based dashboard for QUSAR orchestration monitoring

Features:
- Real-time QUSAR orchestration status monitoring
- Interactive terminal UI with chat bot integration
- Goal formulation and feedback loop visualization
- AGENT Z (AZ PRIME) integration for QUSAR operations
"""

import asyncio
import textwrap
from datetime import datetime

# Import QUSAR components
from qusar.qusar_orchestrator import QUSAROrchestrator
from sasp_protocol import SASPClient, SASPSecurityManager


class MatrixMaximizerWorkstation:
    """Terminal-based workstation for QUSAR operations monitoring"""

    def __init__(self):
        self.orchestrator = None
        self.sasp_client = None
        self.running = False
        self.metrics = {}
        self.goals = []
        self.feedback_history = []

        # Initialize chat bot for AGENT Z (AZ PRIME)
        self.agent_z_prime = None
        self._init_agent_z_prime()

    def _init_agent_z_prime(self):
        """Initialize AGENT Z (AZ PRIME) chat bot"""
        try:
            from agent_z_prime import AgentZPrime
            self.agent_z_prime = AgentZPrime()
            self.feedback_history.append({
                'timestamp': datetime.now().isoformat(),
                'sender': 'AGENT Z (AZ PRIME)',
                'message': 'QUSAR Matrix Maximizer initialized. Ready for orchestration and goal formulation.'
            })
        except ImportError:
            self.feedback_history.append({
                'timestamp': datetime.now().isoformat(),
                'sender': 'SYSTEM',
                'message': 'AGENT Z (AZ PRIME) chat interface not available. Using basic terminal interface.'
            })

    async def start_workstation(self):
        """Start the Matrix Maximizer workstation"""
        print("🚀 Starting Matrix Maximizer Workstation (QUSAR Operations)")

        # Initialize QUSAR orchestrator
        self.orchestrator = QUSAROrchestrator(
            qforge_host="127.0.0.1",
            qforge_port=8888
        )
        await self.orchestrator.initialize()

        # Initialize SASP client for communication
        security = SASPSecurityManager('qusar-secret-key-change-in-production')
        self.sasp_client = SASPClient('127.0.0.1', 8888, security, use_tls=False)
        await self.sasp_client.connect()

        self.running = True
        print("✅ Matrix Maximizer Workstation active")
        print("🎯 AGENT Z (AZ PRIME) ready for QUSAR orchestration")

        # Start monitoring loop
        await self.monitoring_loop()

    async def monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Update metrics
                await self.update_metrics()

                # Process feedback and goals
                await self.process_feedback_loops()

                # Display status
                self.display_status()

                await asyncio.sleep(2)  # Update every 2 seconds

            except Exception as e:
                print(f"❌ Matrix Maximizer error: {e}")
                await asyncio.sleep(5)

    async def update_metrics(self):
        """Update workstation metrics"""
        self.metrics = {
            'timestamp': datetime.now().isoformat(),
            'qusar_status': 'active' if self.orchestrator else 'inactive',
            'sasp_connection': 'connected' if self.sasp_client and self.sasp_client.connected else 'disconnected',
            'active_goals': len(self.goals),
            'feedback_items': len(self.feedback_history),
            'system_health': 98.0,
            'memory_usage': 67.0,
            'cpu_usage': 45.0,
            'orchestration_cycles': getattr(self.orchestrator, 'cycle_count', 0) if self.orchestrator else 0
        }

    async def process_feedback_loops(self):
        """Process feedback loops and goal formulation"""
        if not self.orchestrator:
            return

        try:
            # Process any pending feedback
            await self.orchestrator.orchestrate_cycle()

            # Update goals list
            if hasattr(self.orchestrator, 'goals'):
                self.goals = list(self.orchestrator.goals.values())[-5:]  # Last 5 goals

        except Exception as e:
            print(f"⚠️ Feedback processing error: {e}")

    def display_status(self):
        """Display current workstation status"""
        print("\033[2J\033[H")  # Clear screen
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                MATRIX MAXIMIZER WORKSTATION                ║")
        print("║                   QUSAR Operations Interface                ║")
        print("╠══════════════════════════════════════════════════════════════╣")

        # System Status
        print(f"║ QUSAR Status: {'🟢 ACTIVE' if self.orchestrator else '🔴 INACTIVE':<45} ║")
        print(f"║ SASP Connection: {'🟢 CONNECTED' if self.metrics.get('sasp_connection') == 'connected' else '🔴 DISCONNECTED':<40} ║")
        print(f"║ Active Goals: {len(self.goals):<44} ║")
        print(f"║ System Health: {self.metrics.get('system_health', 0):.1f}%{'':<38} ║")
        print(f"║ Orchestration Cycles: {self.metrics.get('orchestration_cycles', 0):<35} ║")
        print("╠══════════════════════════════════════════════════════════════╣")

        # Recent Goals
        print("║ RECENT GOALS:                                                  ║")
        for i, goal in enumerate(self.goals[-3:]):
            status_icon = "🎯"
            goal_text = goal.get('description', 'unknown')[:45] if isinstance(goal, dict) else str(goal)[:45]
            print(f"║ {i+1}. {status_icon} {goal_text:<42} ║")
        if len(self.goals) < 3:
            for i in range(3 - len(self.goals)):
                print(f"║ {len(self.goals)+i+1}. {'':<48} ║")

        print("╠══════════════════════════════════════════════════════════════╣")

        # AGENT Z (AZ PRIME) Chat
        print("║ AGENT Z (AZ PRIME):                                           ║")
        if self.feedback_history:
            last_msg = self.feedback_history[-1]
            wrapped = textwrap.wrap(last_msg.get('message', ''), 52)
            for i, line in enumerate(wrapped[:2]):
                print(f"║ {line:<52} ║")
            if len(wrapped) < 2:
                print(f"║ {'':<52} ║")

        print("╚══════════════════════════════════════════════════════════════╝")

    async def chat_with_agent(self, message: str):
        """Chat with AGENT Z (AZ PRIME)"""
        if self.agent_z_prime:
            try:
                context = {
                    'active_goals': len(self.goals),
                    'system_health': self.metrics.get('system_health', 0),
                    'orchestration_cycles': self.metrics.get('orchestration_cycles', 0),
                    'feedback_items': len(self.feedback_history),
                    'sasp_connection': self.metrics.get('sasp_connection', 'unknown')
                }
                response = await self.agent_z_prime.chat(message, context)
                self.feedback_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'sender': 'AGENT Z (AZ PRIME)',
                    'message': response
                })
                return response
            except Exception as e:
                return f"Chat error: {e}"
        else:
            return "AGENT Z (AZ PRIME) chat interface not available"

    async def create_goal(self, goal_description: str):
        """Create a new goal for QUSAR orchestration"""
        if self.orchestrator:
            # Use AGENT Z (AZ PRIME) to formulate the goal
            if self.agent_z_prime:
                goal_data = self.agent_z_prime.formulate_goal(goal_description, {
                    'priority': 'high',
                    'deadline': None,
                    'success_criteria': ['Goal completion verified by QUSAR orchestrator'],
                    'stakeholders': ['AGENT Z (AZ PRIME)', 'QUSAR Orchestrator'],
                    'resources': ['QUSAR processing capacity', 'SASP communication']
                })
            else:
                goal_data = {
                    'description': goal_description,
                    'priority': 'high',
                    'created_at': datetime.now().isoformat(),
                    'status': 'active'
                }

            await self.orchestrator.add_goal(goal_data)
            self.goals.append(goal_data)

            return f"Goal created: {goal_description}"
        else:
            return "QUSAR orchestrator not available"

    async def shutdown(self):
        """Shutdown the workstation"""
        self.running = False
        if self.sasp_client:
            await self.sasp_client.close()
        if self.orchestrator:
            await self.orchestrator.shutdown()
        print("🛑 Matrix Maximizer Workstation shutdown complete")

async def main():
    """Main workstation function"""
    workstation = MatrixMaximizerWorkstation()

    try:
        await workstation.start_workstation()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Matrix Maximizer Workstation...")
        await workstation.shutdown()
    except Exception as e:
        print(f"❌ Workstation error: {e}")
        await workstation.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
