#!/usr/bin/env python3
"""
Super Agency Complete System Integration Demo
Demonstrates all components working together
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Complete system integration demo"""

    print("🚀 Super Agency Complete System Integration Demo")
    print("=" * 60)

    try:
        # Import all system components
        print("📦 Loading system components...")

        from backlog_intelligence_system import get_intelligence_engine
        from backlog_management_system import get_backlog_manager
        from context_compression_system import get_context_compression
        from doctrine_evolution_framework import get_doctrine_evolution
        from doctrine_preservation_system import get_doctrine_preservation_system
        from memory_doctrine_system import get_memory_doctrine_system
        from production_deployment import get_production_deployment
        from sasp_protocol import get_sasp_network, get_sasp_protocol
        from vector_database_integration import get_semantic_memory

        print("✅ All components loaded successfully")

        # Initialize core systems
        print("\n🔧 Initializing core systems...")

        memory_system = get_memory_doctrine_system()
        doctrine_system = get_doctrine_preservation_system()
        backlog_manager = get_backlog_manager()
        compression_system = get_context_compression()
        evolution_engine = get_doctrine_evolution()
        intelligence_engine = get_intelligence_engine()
        sasp_protocol = get_sasp_protocol()
        sasp_network = get_sasp_network()
        semantic_memory = get_semantic_memory()

        print("✅ Core systems initialized")

        # Demonstrate doctrine management
        print("\n📜 Doctrine Management Demo")

        # Store initial doctrine
        doctrine = {
            "version": "2.0.0",
            "memory_principles": [
                {
                    "name": "context_preservation",
                    "description": "Preserve important context across sessions"
                },
                {
                    "name": "semantic_compression",
                    "description": "Use semantic analysis for memory optimization"
                }
            ],
            "operational_principles": [
                {
                    "name": "intelligence_driven",
                    "description": "Use AI for decision making and optimization"
                }
            ],
            "constraints": {
                "max_memory_mb": 512,
                "session_timeout_hours": 24
            }
        }

        doctrine_system.store_doctrine(doctrine, "Complete system integration demo")
        print("✅ Doctrine stored")

        # Propose doctrine change
        change_id = evolution_engine.propose_doctrine_change(
            "add_principle",
            "memory_principles",
            {
                "name": "cross_device_sync",
                "description": "Synchronize memory across devices securely"
            },
            "Add cross-device synchronization capability",
            "system_demo"
        )
        print(f"✅ Doctrine change proposed: {change_id}")

        # Approve and implement change
        evolution_engine.review_change(change_id, "admin", True, "Approved for demo")
        evolution_engine.implement_change(change_id, "system")
        print("✅ Doctrine change implemented")

        # Demonstrate memory operations
        print("\n🧠 Memory System Demo")

        # Store memory across layers
        memory_system.store("demo_context", {
            "session": "integration_demo",
            "timestamp": datetime.now().isoformat(),
            "components": ["memory", "doctrine", "backlog", "compression", "sasp", "vector_db"]
        }, layer="persistent")

        memory_system.store("temp_calculation", {"result": 42}, layer="ephemeral")
        print("✅ Memory stored across layers")

        # Demonstrate context compression
        print("\n🗜️  Context Compression Demo")

        conversation = [
            {"role": "user", "content": "How does the Super Agency memory system work?"},
            {"role": "assistant", "content": "The Super Agency uses a multi-layer memory architecture with ephemeral, session, and persistent layers. It includes semantic compression and vector-based retrieval."},
            {"role": "user", "content": "What about cross-device synchronization?"},
            {"role": "assistant", "content": "Cross-device sync is handled by the SASP protocol, which provides secure authenticated communication between devices."}
        ]

        compressed = compression_system.compress_conversation(conversation)
        print(f"✅ Conversation compressed: {len(str(conversation))} -> {len(compressed)} chars")

        # Demonstrate backlog intelligence
        print("\n📋 Backlog Intelligence Demo")

        # Create backlog items
        items = []
        for i, title in enumerate([
            "Implement advanced memory compression",
            "Add SASP protocol security features",
            "Optimize vector database performance",
            "Enhance doctrine evolution governance"
        ]):
            item = backlog_manager.create_item(
                title=title,
                category="memory" if i % 2 == 0 else "infrastructure",
                priority="high" if i < 2 else "medium",
                effort="large" if i == 0 else "medium"
            )
            items.append(item)

        print(f"✅ Created {len(items)} backlog items")

        # Generate intelligence insights
        patterns = intelligence_engine.analyze_backlog_patterns()
        suggestions = intelligence_engine.generate_priority_suggestions()
        optimizations = intelligence_engine.optimize_dependencies()

        print(f"✅ Generated {len(suggestions.get('suggestions', {}))} priority suggestions")
        print(f"✅ Found {optimizations.get('total_opportunities', 0)} optimization opportunities")

        # Demonstrate semantic memory
        print("\n🧬 Semantic Memory Demo")

        # Store semantic memories
        memories = [
            "The Super Agency doctrine emphasizes memory optimization and context preservation.",
            "SASP protocol enables secure cross-device communication with RSA encryption.",
            "Vector databases provide semantic search capabilities for efficient information retrieval.",
            "Backlog intelligence uses AI to optimize task prioritization and dependency management."
        ]

        memory_ids = []
        for memory in memories:
            mem_id = semantic_memory.store_memory(
                memory,
                content_type="documentation",
                importance=0.8,
                tags=["super_agency", "integration_demo"]
            )
            memory_ids.append(mem_id)

        print(f"✅ Stored {len(memory_ids)} semantic memories")

        # Perform semantic search
        results = semantic_memory.retrieve_memory("secure communication memory optimization", top_k=3)
        print(f"✅ Semantic search returned {len(results)} results")

        # Demonstrate SASP protocol
        print("\n🔐 SASP Protocol Demo")

        # Get protocol status
        status = sasp_protocol.get_network_status()
        print(f"✅ SASP protocol initialized: {status['node_id'][:8]}...")

        # Register a demo node
        pub_key = sasp_protocol.get_public_key_pem()
        sasp_protocol.register_node(
            "demo_node_1",
            "127.0.0.1",
            9999,
            public_key_pem=pub_key
        )
        print("✅ Demo node registered in SASP network")

        # Demonstrate cross-system integration
        print("\n🔗 Cross-System Integration Demo")

        # Create integrated workflow
        integration_context = {
            "workflow": "complete_system_demo",
            "components_active": [
                "memory_doctrine_system",
                "doctrine_preservation",
                "backlog_intelligence",
                "context_compression",
                "doctrine_evolution",
                "sasp_protocol",
                "vector_database",
                "production_deployment"
            ],
            "timestamp": datetime.now().isoformat(),
            "doctrine_version": doctrine["version"]
        }

        # Store in multiple systems
        memory_system.store("integration_context", integration_context, layer="persistent")
        semantic_memory.store_memory(
            json.dumps(integration_context),
            content_type="integration_log",
            importance=0.9,
            tags=["integration", "demo", "complete_system"]
        )

        # Create backlog item for integration
        integration_item = backlog_manager.create_item(
            title="Complete system integration verification",
            category="integration",
            priority="high",
            doctrine_alignment={
                "memory_optimization": 0.9,
                "cross_device_sync": 0.8,
                "intelligence_driven": 0.9
            }
        )

        print("✅ Cross-system integration context stored")

        # Generate final intelligence report
        print("\n📊 Final Intelligence Report")

        report = intelligence_engine.get_intelligence_report()
        print(f"Backlog Items: {report['patterns_analysis'].get('analyzed_items', 0)}")
        print(f"Priority Suggestions: {report['priority_suggestions'].get('suggested_changes', 0)}")
        print(f"Optimization Opportunities: {report['dependency_optimizations'].get('total_opportunities', 0)}")

        # Get system-wide statistics
        memory_stats = memory_system.get_memory_stats()
        doctrine_stats = doctrine_system.get_doctrine_history()
        semantic_stats = semantic_memory.get_memory_stats()

        print("\n📈 System Statistics:")
        print(f"  Memory Items: {memory_stats.get('total_items', 0)}")
        print(f"  Doctrine Versions: {len(doctrine_stats)}")
        print(f"  Semantic Memories: {semantic_stats['records']['total_records']}")
        print(f"  Backlog Items: {len(items) + 1}")  # +1 for integration item

        # Demonstrate production deployment status
        print("\n🏭 Production Deployment Status")

        deployment = get_production_deployment()
        dep_status = deployment.get_deployment_status()

        print(f"Deployment Status: {dep_status['overall_status']}")
        print(f"Services Initialized: {len(dep_status['services'])}")
        print(f"Uptime: {dep_status.get('uptime_seconds', 0):.1f}s")
        print(f"Active Threads: {dep_status['active_threads']}")

        # Final success message
        print("\n🎉 COMPLETE SYSTEM INTEGRATION SUCCESSFUL!")
        print("=" * 60)
        print("All Super Agency components are working together:")
        print("✅ Multi-layer Memory System")
        print("✅ Doctrine Preservation & Evolution")
        print("✅ AI-Powered Backlog Intelligence")
        print("✅ Context Compression & Optimization")
        print("✅ Secure SASP Protocol")
        print("✅ Semantic Vector Database")
        print("✅ Production Deployment & Monitoring")
        print("\n🚀 Super Agency is ready for production use!")

        return True

    except Exception as e:
        print(f"\n❌ Integration demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
