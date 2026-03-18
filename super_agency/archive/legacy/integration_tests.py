#!/usr/bin/env python3
"""
BIT RAGE LABOUR Memory Doctrine Integration Tests
Comprehensive validation of memory and doctrine systems
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backlog_intelligence_system import IntelligenceEngine
    from backlog_management_system import BacklogItem, BacklogManager
    from context_compression_system import ContextCompressionSystem
    from doctrine_evolution_framework import DoctrineChangeType, DoctrineEvolutionEngine
    from doctrine_preservation_system import (
        DoctrinePreservationSystem,
        DoctrineStorage,
        DoctrineValidator,
    )
    from memory_doctrine_system import (
        EphemeralMemory,
        MemoryDoctrineSystem,
        PersistentMemory,
        SessionMemory,
    )
    from production_deployment import ProductionDeployment
    from sasp_protocol import SASPMessageType, SASPProtocol
    from vector_database_integration import SemanticMemoryStore
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required files are in the same directory")
    sys.exit(1)

class IntegrationTestSuite:
    """Comprehensive integration test suite for memory and doctrine systems"""

    def __init__(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="memory_doctrine_test_"))
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "warnings": []
        }

        print(f"🧪 Test directory: {self.test_dir}")

    def cleanup(self):
        """Clean up test directory"""
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass

    def log_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        self.results["total_tests"] += 1

        if success:
            self.results["passed"] += 1
            print(f"✅ {test_name}")
            if message:
                print(f"   {message}")
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {message}")
            print(f"❌ {test_name}")
            if message:
                print(f"   {message}")

    def test_memory_system_initialization(self):
        """Test memory system initialization"""
        try:
            memory_system = MemoryDoctrineSystem(storage_path=self.test_dir / "memory.db")

            # Test layer initialization
            assert memory_system.ephemeral is not None
            assert memory_system.session is not None
            assert memory_system.persistent is not None

            # Test basic storage
            memory_system.store("test_key", "test_value", layer="ephemeral")
            retrieved = memory_system.retrieve("test_key", layer="ephemeral")
            assert retrieved == "test_value"

            self.log_result("Memory System Initialization", True, "All memory layers initialized successfully")

        except Exception as e:
            self.log_result("Memory System Initialization", False, str(e))

    def test_memory_layer_operations(self):
        """Test individual memory layer operations"""
        try:
            memory_system = MemoryDoctrineSystem(storage_path=self.test_dir / "memory_layers.db")

            # Test ephemeral memory
            memory_system.store("ephemeral_key", {"data": "ephemeral_value"}, layer="ephemeral")
            data = memory_system.retrieve("ephemeral_key", layer="ephemeral")
            assert data["data"] == "ephemeral_value"

            # Test session memory
            memory_system.store("session_key", {"data": "session_value"}, layer="session")
            data = memory_system.retrieve("session_key", layer="session")
            assert data["data"] == "session_value"

            # Test persistent memory
            memory_system.store("persistent_key", {"data": "persistent_value"}, layer="persistent")
            data = memory_system.retrieve("persistent_key", layer="persistent")
            assert data["data"] == "persistent_value"

            self.log_result("Memory Layer Operations", True, "All memory layers store/retrieve correctly")

        except Exception as e:
            self.log_result("Memory Layer Operations", False, str(e))

    def test_memory_optimization(self):
        """Test memory optimization features"""
        try:
            memory_system = MemoryDoctrineSystem(storage_path=self.test_dir / "memory_opt.db")

            # Fill memory with test data
            for i in range(100):
                memory_system.store(f"key_{i}", f"value_{i}", layer="ephemeral")

            # Test optimization
            stats_before = memory_system.get_memory_stats()
            memory_system.optimize_memory()
            stats_after = memory_system.get_memory_stats()

            # Optimization should reduce memory usage
            assert stats_after["total_items"] <= stats_before["total_items"]

            self.log_result("Memory Optimization", True, f"Optimized from {stats_before['total_items']} to {stats_after['total_items']} items")

        except Exception as e:
            self.log_result("Memory Optimization", False, str(e))

    def test_doctrine_validation(self):
        """Test doctrine validation system"""
        try:
            doctrine_system = DoctrinePreservationSystem(storage_path=self.test_dir / "doctrine.db")

            # Test valid doctrine
            valid_doctrine = {
                "version": "1.0.0",
                "principles": {
                    "memory_optimization": {
                        "description": "Optimize memory usage",
                        "priority": "high"
                    }
                },
                "constraints": {
                    "max_memory_mb": 100
                }
            }

            is_valid, errors = doctrine_system.validate_doctrine(valid_doctrine)
            assert is_valid, f"Valid doctrine rejected: {errors}"

            # Test invalid doctrine
            invalid_doctrine = {
                "version": "1.0.0"
                # Missing required fields
            }

            is_valid, errors = doctrine_system.validate_doctrine(invalid_doctrine)
            assert not is_valid, "Invalid doctrine accepted"

            self.log_result("Doctrine Validation", True, "Doctrine validation works correctly")

        except Exception as e:
            self.log_result("Doctrine Validation", False, str(e))

    def test_doctrine_storage(self):
        """Test doctrine storage and versioning"""
        try:
            doctrine_system = DoctrinePreservationSystem(storage_path=self.test_dir / "doctrine_store.db")

            # Store initial doctrine
            doctrine_v1 = {
                "version": "1.0.0",
                "principles": {
                    "memory": {"priority": "high"}
                }
            }

            doctrine_system.store_doctrine(doctrine_v1, "Initial doctrine")

            # Update doctrine
            doctrine_v2 = {
                "version": "1.1.0",
                "principles": {
                    "memory": {"priority": "high"},
                    "security": {"priority": "critical"}
                }
            }

            doctrine_system.store_doctrine(doctrine_v2, "Added security principle")

            # Retrieve latest
            latest = doctrine_system.get_current_doctrine()
            assert latest["version"] == "1.1.0"
            assert "security" in latest["principles"]

            # Check history
            history = doctrine_system.get_doctrine_history()
            assert len(history) == 2

            self.log_result("Doctrine Storage", True, f"Stored {len(history)} doctrine versions")

        except Exception as e:
            self.log_result("Doctrine Storage", False, str(e))

    def test_doctrine_compliance(self):
        """Test doctrine compliance checking"""
        try:
            doctrine_system = DoctrinePreservationSystem(storage_path=self.test_dir / "doctrine_comp.db")

            # Store doctrine with constraints
            doctrine = {
                "version": "1.0.0",
                "constraints": {
                    "max_memory_mb": 100,
                    "required_principles": ["memory", "security"]
                }
            }

            doctrine_system.store_doctrine(doctrine, "Compliance test doctrine")

            # Test compliant action
            compliant_action = {
                "type": "memory_optimization",
                "memory_usage_mb": 50,
                "principles_applied": ["memory"]
            }

            is_compliant, violations = doctrine_system.check_compliance(compliant_action)
            assert is_compliant, f"Compliant action rejected: {violations}"

            # Test non-compliant action
            non_compliant_action = {
                "type": "memory_optimization",
                "memory_usage_mb": 150,  # Exceeds limit
                "principles_applied": ["memory"]
            }

            is_compliant, violations = doctrine_system.check_compliance(non_compliant_action)
            assert not is_compliant, "Non-compliant action accepted"

            self.log_result("Doctrine Compliance", True, "Compliance checking works correctly")

        except Exception as e:
            self.log_result("Doctrine Compliance", False, str(e))

    def test_backlog_management(self):
        """Test backlog management system"""
        try:
            backlog_manager = BacklogManager(storage_path=self.test_dir / "backlog.db")

            # Create test items
            item1 = backlog_manager.create_item(
                title="Test Memory Optimization",
                category="memory",
                priority="high",
                effort="medium"
            )

            item2 = backlog_manager.create_item(
                title="Test Doctrine Update",
                category="doctrine",
                priority="medium",
                effort="small"
            )

            # Test retrieval
            retrieved = backlog_manager.get_item(item1.id)
            assert retrieved.title == "Test Memory Optimization"

            # Test querying
            memory_items = backlog_manager.query_items(filters={"category": "memory"})
            assert len(memory_items) == 1

            # Test stats
            stats = backlog_manager.get_stats()
            assert stats["total_items"] == 2
            assert stats["by_category"]["memory"] == 1

            self.log_result("Backlog Management", True, f"Managing {stats['total_items']} backlog items")

        except Exception as e:
            self.log_result("Backlog Management", False, str(e))

    def test_ai_insights_generation(self):
        """Test AI insights generation for backlog items"""
        try:
            backlog_manager = BacklogManager(storage_path=self.test_dir / "backlog_ai.db")

            # Create item with dependencies
            item = backlog_manager.create_item(
                title="Complex Memory Integration",
                description="Integrate memory system with doctrine compliance",
                category="memory",
                priority="high",
                effort="large"
            )

            # Add dependencies
            dep1 = backlog_manager.create_item(title="Dependency 1", category="memory")
            dep2 = backlog_manager.create_item(title="Dependency 2", category="memory")

            backlog_manager.update_item(item.id, dependencies=[dep1.id, dep2.id])

            # Generate AI insights
            insights = backlog_manager.generate_ai_insights(item)

            # Verify insights structure
            assert "estimated_effort_days" in insights
            assert "priority_boost" in insights
            assert "dependency_risk" in insights
            assert "suggested_tags" in insights

            # Dependency risk should be high due to multiple dependencies
            assert insights["dependency_risk"] == "high"

            self.log_result("AI Insights Generation", True, f"Generated insights: effort={insights['estimated_effort_days']}d, risk={insights['dependency_risk']}")

        except Exception as e:
            self.log_result("AI Insights Generation", False, str(e))

    def test_cross_system_integration(self):
        """Test integration between memory, doctrine, and backlog systems"""
        try:
            # Initialize all systems
            memory_system = MemoryDoctrineSystem(storage_path=self.test_dir / "integrated_memory.db")
            doctrine_system = DoctrinePreservationSystem(storage_path=self.test_dir / "integrated_doctrine.db")
            backlog_manager = BacklogManager(storage_path=self.test_dir / "integrated_backlog.db")

            # Create doctrine
            doctrine = {
                "version": "1.0.0",
                "principles": {
                    "memory_optimization": {"priority": "high"},
                    "doctrine_compliance": {"priority": "critical"}
                },
                "constraints": {
                    "max_memory_mb": 100
                }
            }

            doctrine_system.store_doctrine(doctrine, "Integration test doctrine")

            # Create backlog item aligned with doctrine
            backlog_item = backlog_manager.create_item(
                title="Implement Memory Doctrine Integration",
                category="memory",
                priority="high",
                doctrine_alignment={
                    "memory_optimization": 0.9,
                    "doctrine_compliance": 0.8
                }
            )

            # Store integration context in memory
            integration_context = {
                "backlog_item_id": backlog_item.id,
                "doctrine_version": doctrine["version"],
                "timestamp": datetime.now().isoformat()
            }

            memory_system.store("integration_context", integration_context, layer="persistent")

            # Verify integration
            stored_context = memory_system.retrieve("integration_context", layer="persistent")
            assert stored_context["backlog_item_id"] == backlog_item.id

            retrieved_item = backlog_manager.get_item(backlog_item.id)
            assert retrieved_item.doctrine_alignment["memory_optimization"] == 0.9

            current_doctrine = doctrine_system.get_current_doctrine()
            assert current_doctrine["principles"]["memory_optimization"]["priority"] == "high"

            self.log_result("Cross-System Integration", True, "All systems integrated successfully")

        except Exception as e:
            self.log_result("Cross-System Integration", False, str(e))

    def test_performance_validation(self):
        """Test performance of the integrated systems"""
        try:
            memory_system = MemoryDoctrineSystem(storage_path=self.test_dir / "perf_memory.db")
            doctrine_system = DoctrinePreservationSystem(storage_path=self.test_dir / "perf_doctrine.db")
            backlog_manager = BacklogManager(storage_path=self.test_dir / "perf_backlog.db")

            import time

            # Performance test: Memory operations
            start_time = time.time()
            for i in range(1000):
                memory_system.store(f"perf_key_{i}", f"perf_value_{i}", layer="ephemeral")
            memory_time = time.time() - start_time

            # Performance test: Backlog operations
            start_time = time.time()
            for i in range(100):
                backlog_manager.create_item(
                    title=f"Performance Test Item {i}",
                    category="performance",
                    priority="medium"
                )
            backlog_time = time.time() - start_time

            # Performance test: Doctrine operations
            start_time = time.time()
            for i in range(10):
                doctrine = {
                    "version": f"1.{i}.0",
                    "principles": {"test": {"priority": "medium"}}
                }
                doctrine_system.store_doctrine(doctrine, f"Performance test {i}")
            doctrine_time = time.time() - start_time

            # Validate reasonable performance (should complete in reasonable time)
            assert memory_time < 5.0, f"Memory operations too slow: {memory_time}s"
            assert backlog_time < 2.0, f"Backlog operations too slow: {backlog_time}s"
            assert doctrine_time < 1.0, f"Doctrine operations too slow: {doctrine_time}s"

            self.log_result("Performance Validation", True,
                          f"Memory: {memory_time:.2f}s, Backlog: {backlog_time:.2f}s, Doctrine: {doctrine_time:.2f}s")

        except Exception as e:
            self.log_result("Performance Validation", False, str(e))

    def test_doctrine_evolution(self):
        """Test doctrine evolution framework"""
        try:
            evolution_engine = DoctrineEvolutionEngine(storage_path=self.test_dir / "evolution.db")

            # Test proposing a change
            change_data = {
                "name": "enhanced_memory_compression",
                "description": "Implement advanced semantic compression for better memory efficiency"
            }

            change_id = evolution_engine.propose_doctrine_change(
                DoctrineChangeType.ADD_PRINCIPLE,
                "memory_principles",
                change_data,
                "Improve memory efficiency through semantic compression",
                "system"
            )

            assert change_id, "Change ID should be generated"

            # Test reviewing the change
            approved = evolution_engine.review_change(change_id, "admin", True, "Good enhancement")
            assert approved, "Change should be approved"

            # Test implementing the change
            implemented = evolution_engine.implement_change(change_id, "system")
            assert implemented, "Change should be implemented successfully"

            # Test getting pending changes (should be empty now)
            pending = evolution_engine.get_pending_changes()
            assert len(pending) == 0, "Should have no pending changes"

            # Test evolution stats
            stats = evolution_engine.get_evolution_stats()
            assert stats["total_changes"] == 1
            assert stats["implemented_changes"] == 1
            assert stats["implementation_rate"] == 100.0

            # Test change history
            history = evolution_engine.get_change_history()
            assert len(history) == 1
            assert history[0]["status"] == "implemented"
            assert history[0]["change_type"] == "add_principle"

            self.log_result("Doctrine Evolution", True, f"Evolution framework working: {stats['total_changes']} changes processed")

        except Exception as e:
            self.log_result("Doctrine Evolution", False, str(e))

    def test_context_compression(self):
        """Test context compression system"""
        try:
            compression_system = ContextCompressionSystem(storage_path=self.test_dir / "compression.db")

            # Test conversation compression
            conversation = [
                {"role": "user", "content": "Hello, I need help with memory optimization"},
                {"role": "assistant", "content": "I'd be happy to help you with memory optimization. What specific aspects are you interested in?"},
                {"role": "user", "content": "I want to understand how context compression works"},
                {"role": "assistant", "content": "Context compression is a technique that reduces memory usage by semantically compressing conversation history while preserving important information."}
            ]

            compressed = compression_system.compress_conversation(conversation)
            assert compressed, "Compression should return data"
            assert len(compressed) < len(str(conversation)), "Compressed data should be smaller"

            # Test memory optimization
            memory_data = {
                "conversations": [conversation],
                "metadata": {"importance": 0.8}
            }

            optimized = compression_system.optimize_memory_usage(memory_data)
            assert optimized, "Optimization should return data"

            # Test compression stats
            stats = compression_system.get_compression_stats()
            assert stats, "Should return compression statistics"

            self.log_result("Context Compression", True, f"Compressed conversation: {len(compressed)} chars")

        except Exception as e:
            self.log_result("Context Compression", False, str(e))

    def test_backlog_intelligence(self):
        """Test backlog intelligence system"""
        try:
            intelligence_engine = IntelligenceEngine(storage_path=self.test_dir / "intelligence.db")

            # Create some test backlog items
            backlog_manager = BacklogManager(storage_path=self.test_dir / "intelligence_backlog.db")

            items = []
            for i in range(5):
                item = backlog_manager.create_item(
                    title=f"Test Item {i}",
                    category="memory" if i % 2 == 0 else "doctrine",
                    priority="high" if i < 2 else "medium",
                    effort="large" if i == 0 else "medium"
                )
                items.append(item)

            # Test pattern analysis
            patterns = intelligence_engine.analyze_backlog_patterns()
            assert patterns, "Should return pattern analysis"
            assert "completion_rates" in patterns.get("patterns", {})

            # Test priority suggestions
            suggestions = intelligence_engine.generate_priority_suggestions()
            assert suggestions, "Should return priority suggestions"
            assert len(suggestions.get("suggestions", {})) > 0

            # Test dependency optimization
            optimizations = intelligence_engine.optimize_dependencies()
            assert optimizations, "Should return optimization suggestions"

            # Test intelligence report
            report = intelligence_engine.get_intelligence_report()
            assert report, "Should return intelligence report"

            self.log_result("Backlog Intelligence", True, f"Analyzed {len(items)} items with {len(suggestions.get('suggestions', {}))} suggestions")

        except Exception as e:
            self.log_result("Backlog Intelligence", False, str(e))

    def test_sasp_protocol(self):
        """Test SASP protocol"""
        try:
            protocol = SASPProtocol(storage_path=self.test_dir / "sasp.db")

            # Test key generation and management
            pub_key = protocol.get_public_key_pem()
            assert pub_key, "Should generate public key"
            assert "BEGIN PUBLIC KEY" in pub_key

            # Test node registration
            success = protocol.register_node(
                "test_node_1",
                "127.0.0.1",
                9999,
                public_key_pem=pub_key
            )
            assert success, "Should register node"

            # Test network status
            status = protocol.get_network_status()
            assert status, "Should return network status"
            assert status["node_id"] == protocol.node_id

            # Test handshake initiation
            session_id = protocol.initiate_handshake("test_node_1")
            assert session_id, "Should initiate handshake"

            self.log_result("SASP Protocol", True, f"Protocol initialized with node ID: {protocol.node_id[:8]}...")

        except Exception as e:
            self.log_result("SASP Protocol", False, str(e))

    def test_vector_database(self):
        """Test vector database integration"""
        try:
            semantic_memory = SemanticMemoryStore(storage_path=self.test_dir / "semantic")

            # Test memory storage
            memory_id = semantic_memory.store_memory(
                "The BIT RAGE LABOUR uses advanced memory systems for optimal performance.",
                content_type="documentation",
                importance=0.9,
                tags=["memory", "performance", "agency"]
            )
            assert memory_id, "Should store memory and return ID"

            # Test semantic search
            results = semantic_memory.retrieve_memory("memory systems performance", top_k=5)
            assert len(results) > 0, "Should return search results"
            assert results[0]["semantic_score"] > 0, "Should have semantic score"

            # Test memory relationships
            memory_id2 = semantic_memory.store_memory(
                "Context compression algorithms enhance memory efficiency.",
                content_type="technical"
            )

            success = semantic_memory.add_relationship(memory_id, memory_id2, "related_concept", 0.8)
            assert success, "Should add relationship"

            related = semantic_memory.get_related_memories(memory_id)
            assert len(related) > 0, "Should find related memories"

            # Test statistics
            stats = semantic_memory.get_memory_stats()
            assert stats, "Should return memory statistics"
            assert stats["records"]["total_records"] > 0

            self.log_result("Vector Database", True, f"Stored {stats['records']['total_records']} memories with semantic search")

        except Exception as e:
            self.log_result("Vector Database", False, str(e))

    def test_production_deployment(self):
        """Test production deployment system"""
        try:
            # Create test config
            test_config = {
                "services": {
                    "memory_doctrine": {"enabled": True},
                    "backlog_intelligence": {"enabled": True},
                    "context_compression": {"enabled": True},
                    "vector_database": {"enabled": True}
                },
                "monitoring": {"enabled": False},  # Disable for testing
                "performance": {"cleanup_interval_hours": 1}
            }

            config_path = self.test_dir / "test_deployment_config.json"
            with open(config_path, 'w') as f:
                json.dump(test_config, f)

            deployment = ProductionDeployment(config_path)

            # Test initialization
            assert deployment.status.value == "initializing", "Should be in initializing state"
            assert len(deployment.services) > 0, "Should have services initialized"

            # Test status reporting
            status = deployment.get_deployment_status()
            assert status, "Should return deployment status"
            assert "overall_status" in status

            # Test service health checks
            for service_name in ["memory_doctrine", "vector_database"]:
                health = deployment._check_service_health(service_name)
                assert health in ["healthy", "unhealthy", "unknown", "error"], f"Invalid health status: {health}"

            self.log_result("Production Deployment", True, f"Initialized deployment with {len(deployment.services)} services")

        except Exception as e:
            self.log_result("Production Deployment", False, str(e))

    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Memory Doctrine Integration Tests...\n")

        test_methods = [
            self.test_memory_system_initialization,
            self.test_memory_layer_operations,
            self.test_memory_optimization,
            self.test_doctrine_validation,
            self.test_doctrine_storage,
            self.test_doctrine_compliance,
            self.test_backlog_management,
            self.test_ai_insights_generation,
            self.test_cross_system_integration,
            self.test_performance_validation,
            self.test_doctrine_evolution,
            self.test_context_compression,
            self.test_backlog_intelligence,
            self.test_sasp_protocol,
            self.test_vector_database,
            self.test_production_deployment
        ]

        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_result(test_method.__name__, False, f"Unexpected error: {str(e)}")

        print(f"\n📊 Test Results: {self.results['passed']}/{self.results['total_tests']} passed")

        if self.results['failed'] > 0:
            print("❌ Failed Tests:")
            for error in self.results['errors']:
                print(f"   - {error}")

        success_rate = (self.results['passed'] / self.results['total_tests']) * 100 if self.results['total_tests'] > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        return self.results['failed'] == 0

def main():
    """Main test runner"""
    test_suite = IntegrationTestSuite()

    try:
        success = test_suite.run_all_tests()

        if success:
            print("\n🎉 All integration tests passed!")
            return 0
        else:
            print("\n💥 Some tests failed. Check the output above.")
            return 1

    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        return 1

    finally:
        test_suite.cleanup()

if __name__ == "__main__":
    exit(main())
