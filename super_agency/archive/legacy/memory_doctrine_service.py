#!/usr/bin/env python3
"""
Super Agency Memory Doctrine Service
Production-ready service launcher
"""

import time
import signal
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from memory_doctrine_system import get_memory_system
from doctrine_preservation_system import DoctrinePreservationSystem
from backlog_management_system import get_backlog_manager

class MemoryDoctrineService:
    """Production memory doctrine service"""

    def __init__(self):
        """Initialize."""
        self.running = True
        self.memory_system = get_memory_system()
        self.doctrine_system = DoctrinePreservationSystem()
        self.backlog_manager = get_backlog_manager()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def initialize_doctrine(self):
        """Initialize core Super Agency doctrine"""
        core_doctrine = {
            "version": "1.0.0",
            "memory_principles": [
                "conservative_resource_usage",
                "persistent_context_preservation",
                "layered_memory_architecture"
            ],
            "operational_principles": [
                "human_oversight_required",
                "audit_trail_maintenance",
                "doctrine_compliance_validation"
            ],
            "governance_principles": [
                "immutable_doctrine_storage",
                "version_controlled_updates",
                "cross_device_synchronization"
            ],
            "constraints": {
                "max_memory_mb": 256,
                "session_retention_hours": 24,
                "doctrine_update_approval_required": True
            }
        }

        self.doctrine_system.store_doctrine(core_doctrine, "Core Super Agency doctrine v1.0.0")
        print("✅ Core doctrine initialized")

    def create_initial_backlog(self):
        """Create initial backlog items"""
        initial_items = [
            {
                "title": "Implement SASP Protocol for Cross-Device Sync",
                "description": "Complete secure authenticated communication between MacBook, Windows, and mobile",
                "category": "integration",
                "priority": "high",
                "effort": "large"
            },
            {
                "title": "Deploy NCL Core Cognitive Layer",
                "description": "Launch the Neural Cognitive Layer as central AI processing system",
                "category": "integration",
                "priority": "critical",
                "effort": "epic"
            },
            {
                "title": "Complete Financial Reporting AAC System",
                "description": "Finish automated income statements, balance sheets, and reporting",
                "category": "integration",
                "priority": "high",
                "effort": "medium"
            }
        ]

        for item_data in initial_items:
            item = self.backlog_manager.create_item(**item_data)
            insights = self.backlog_manager.generate_ai_insights(item)
            self.backlog_manager.update_item(item.id, ai_insights=insights)
            print(f"✅ Created backlog item: {item.title}")

    def run_service_loop(self):
        """Main service loop"""
        print("🚀 Memory Doctrine Service started")
        print("📊 Monitoring memory, doctrine, and backlog systems...")

        while self.running:
            try:
                # Memory optimization (every 5 minutes)
                if int(time.time()) % 300 == 0:
                    self.memory_system.optimize()
                    print("🧹 Memory optimization completed")

                # Doctrine compliance check (every 10 minutes)
                if int(time.time()) % 600 == 0:
                    current_doctrine = self.doctrine_system.get_current_doctrine()
                    print(f"📋 Doctrine v{current_doctrine['version']} active")

                # Backlog status update (every 15 minutes)
                if int(time.time()) % 900 == 0:
                    stats = self.backlog_manager.get_stats()
                    print(f"📊 Backlog: {stats['total_items']} items, {stats.get('by_status', {}).get('completed', 0)} completed")

                time.sleep(60)  # Check every minute

            except Exception as e:
                print(f"⚠️  Service loop error: {e}")
                time.sleep(60)

    def shutdown(self, signum=None, frame=None):
        """Graceful shutdown"""
        print("\n🛑 Shutting down Memory Doctrine Service...")
        self.running = False
        self.memory_system.shutdown()
        print("✅ Service shutdown complete")

    def start(self):
        """Start the service"""
        try:
            print("🔧 Initializing Memory Doctrine Service...")

            # Initialize core systems
            self.initialize_doctrine()
            self.create_initial_backlog()

            # Start service loop
            self.run_service_loop()

        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            print(f"💥 Service error: {e}")
            self.shutdown()
            sys.exit(1)

if __name__ == "__main__":
    service = MemoryDoctrineService()
    service.start()