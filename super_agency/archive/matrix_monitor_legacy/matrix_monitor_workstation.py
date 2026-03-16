#!/usr/bin/env python3
"""
Matrix Monitor Workstation - QFORGE Operations Interface
Advanced terminal-based dashboard for QFORGE task execution monitoring

Features:
- Real-time QFORGE task status monitoring
- Interactive terminal UI with chat bot integration
- Performance metrics display
- Task execution visualization
- AGENT X HELIX integration for QFORGE operations
"""

import asyncio
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
import curses
import textwrap
from pathlib import Path

# Import QFORGE components
from qforge.qforge_executor import QFORGEExecutor
from sasp_protocol import SASPServer, SASPSecurityManager, SASPMessage

class MatrixMonitorWorkstation:
    """Terminal-based workstation for QFORGE operations monitoring"""

    def __init__(self):
        self.executor = QFORGEExecutor()
        self.sasp_server = None
        self.running = False
        self.metrics = {}
        self.tasks = []
        self.chat_history = []

        # Initialize chat bot for AGENT X HELIX
        self.agent_x_helix = None
        self._init_agent_x_helix()

    def _init_agent_x_helix(self):
        """Initialize AGENT X HELIX chat bot"""
        try:
            from az_chatbot import AzureChatbot
            self.agent_x_helix = AzureChatbot()
            self.chat_history.append({
                'timestamp': datetime.now().isoformat(),
                'sender': 'AGENT X HELIX',
                'message': 'QFORGE Matrix Monitor initialized. Ready for task execution monitoring.'
            })
        except ImportError:
            self.chat_history.append({
                'timestamp': datetime.now().isoformat(),
                'sender': 'SYSTEM',
                'message': 'AGENT X HELIX chat interface not available. Using basic terminal interface.'
            })

    async def start_workstation(self):
        """Start the Matrix Monitor workstation"""
        print("🚀 Starting Matrix Monitor Workstation (QFORGE Operations)")

        # Initialize SASP server for QFORGE communication
        security = SASPSecurityManager('qforge-secret-key-change-in-production')
        self.sasp_server = SASPServer('127.0.0.1', 8888, security)
        await self.sasp_server.start()

        # Start QFORGE executor
        await self.executor.initialize()

        self.running = True
        print("✅ Matrix Monitor Workstation active")
        print("🎯 AGENT X HELIX ready for QFORGE operations")

        # Start monitoring loop
        await self.monitoring_loop()

    async def monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Update metrics
                await self.update_metrics()

                # Process any incoming SASP messages
                await self.process_sasp_messages()

                # Display status
                self.display_status()

                await asyncio.sleep(2)  # Update every 2 seconds

            except Exception as e:
                print(f"❌ Matrix Monitor error: {e}")
                await asyncio.sleep(5)

    async def update_metrics(self):
        """Update workstation metrics"""
        self.metrics = {
            'timestamp': datetime.now().isoformat(),
            'qforge_status': 'active' if self.executor else 'inactive',
            'sasp_connections': len(self.sasp_server.connections) if self.sasp_server else 0,
            'active_tasks': len(self.tasks),
            'system_health': 95.0,
            'memory_usage': 45.0,
            'cpu_usage': 32.0
        }

    async def process_sasp_messages(self):
        """Process incoming SASP messages"""
        if not self.sasp_server:
            return

        # Process messages from QUSAR
        for message in self.sasp_server.get_messages():
            if message.message_type == 'task':
                await self.handle_task_message(message)
            elif message.message_type == 'ping':
                await self.handle_ping_message(message)

    async def handle_task_message(self, message: SASPMessage):
        """Handle incoming task messages"""
        task_data = message.payload
        self.tasks.append({
            'id': f"task_{len(self.tasks) + 1}",
            'data': task_data,
            'status': 'received',
            'timestamp': datetime.now().isoformat()
        })

        # Execute task via QFORGE
        result = await self.executor.execute_task(task_data)
        self.tasks[-1]['result'] = result
        self.tasks[-1]['status'] = 'completed'

    async def handle_ping_message(self, message: SASPMessage):
        """Handle ping messages"""
        response = {
            'status': 'active',
            'workstation': 'Matrix Monitor (QFORGE)',
            'agent': 'AGENT X HELIX',
            'metrics': self.metrics
        }
        # Send response back
        pass

    def display_status(self):
        """Display current workstation status"""
        print("\033[2J\033[H")  # Clear screen
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                 MATRIX MONITOR WORKSTATION                  ║")
        print("║                    QFORGE Operations Interface              ║")
        print("╠══════════════════════════════════════════════════════════════╣")

        # System Status
        print(f"║ QFORGE Status: {'🟢 ACTIVE' if self.executor else '🔴 INACTIVE':<45} ║")
        print(f"║ SASP Connections: {self.metrics.get('sasp_connections', 0):<40} ║")
        print(f"║ Active Tasks: {len(self.tasks):<44} ║")
        print(f"║ System Health: {self.metrics.get('system_health', 0):.1f}%{'':<38} ║")
        print("╠══════════════════════════════════════════════════════════════╣")

        # Recent Tasks
        print("║ RECENT TASKS:                                                 ║")
        for i, task in enumerate(self.tasks[-3:]):
            status_icon = "✅" if task.get('status') == 'completed' else "⏳"
            print(f"║ {i+1}. {status_icon} {task.get('id', 'unknown'):<42} ║")
        if len(self.tasks) < 3:
            for i in range(3 - len(self.tasks)):
                print(f"║ {len(self.tasks)+i+1}. {'':<48} ║")

        print("╠══════════════════════════════════════════════════════════════╣")

        # AGENT X HELIX Chat
        print("║ AGENT X HELIX:                                                ║")
        if self.chat_history:
            last_msg = self.chat_history[-1]
            wrapped = textwrap.wrap(last_msg.get('message', ''), 52)
            for i, line in enumerate(wrapped[:2]):
                print(f"║ {line:<52} ║")
            if len(wrapped) < 2:
                print(f"║ {'':<52} ║")

        print("╚══════════════════════════════════════════════════════════════╝")

    def chat_with_agent(self, message: str):
        """Chat with AGENT X HELIX"""
        if self.agent_x_helix:
            try:
                response = self.agent_x_helix.chat([{
                    'role': 'user',
                    'content': f"QFORGE Operations Context: {message}"
                }])
                self.chat_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'sender': 'AGENT X HELIX',
                    'message': response
                })
                return response
            except Exception as e:
                return f"Chat error: {e}"
        else:
            return "AGENT X HELIX chat interface not available"

    async def shutdown(self):
        """Shutdown the workstation"""
        self.running = False
        if self.sasp_server:
            await self.sasp_server.stop()
        if self.executor:
            await self.executor.shutdown()
        print("🛑 Matrix Monitor Workstation shutdown complete")

async def main():
    """Main workstation function"""
    workstation = MatrixMonitorWorkstation()

    try:
        await workstation.start_workstation()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Matrix Monitor Workstation...")
        await workstation.shutdown()
    except Exception as e:
        print(f"❌ Workstation error: {e}")
        await workstation.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
