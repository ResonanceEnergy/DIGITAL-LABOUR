# REPO DEPOT - Full Integration Test Suite

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from repo_depot.agents.agent_controller import AgentController, TaskPriority
from repo_depot.agents.collaboration_framework import CollaborationFramework
from repo_depot.agents.performance_monitor import PerformanceMonitor
from repo_depot.agents.specialization_engine import SpecializationEngine
from repo_depot.core.agent_specialization import AgentDispatcher
from repo_depot.flywheel.builder_agents import BuilderAgentPool
from repo_depot.flywheel.flywheel_controller import FlywheelController
from repo_depot.flywheel.optimization_engine import OptimizationEngine

# Import all system components
from repo_depot.flywheel.orchestration_engine import OrchestrationEngine
from repo_depot.flywheel.quality_gates import QualityGateSystem

logger = logging.getLogger(__name__)


class IntegrationTestSuite:
    """
    Comprehensive integration test suite for the SuperAgency system.
    Tests cross-component communication, agent orchestration, and flywheel workflows.
    """

    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run the complete integration test suite"""
        self.start_time = datetime.now()
        logger.info("🚀 Starting SuperAgency Integration Test Suite")

        try:
            # Test 1: Component Initialization
            await self.test_component_initialization()

            # Test 2: Flywheel Integration
            await self.test_flywheel_integration()

            # Test 3: Agent Specialization System
            await self.test_agent_specialization_system()

            # Test 4: Cross-Component Communication
            await self.test_cross_component_communication()

            # Test 5: Performance Under Load
            await self.test_performance_under_load()

            # Test 6: Error Recovery
            await self.test_error_recovery()

            # Test 7: End-to-End Workflow
            await self.test_end_to_end_workflow()

        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            self.record_test_result("test_suite_execution", False, str(e))
        finally:
            self.end_time = datetime.now()

        return self.generate_report()

    async def test_component_initialization(self):
        """Test that all components can be initialized properly"""
        logger.info("Testing component initialization...")

        try:
            # Test Flywheel components
            flywheel = FlywheelController()
            assert flywheel.orchestration is not None
            assert flywheel.builder_pool is not None
            assert flywheel.quality_gates is not None
            assert flywheel.optimization is not None

            # Test Agent components
            agent_controller = AgentController()
            assert agent_controller.registry is not None
            assert agent_controller.specialization_engine is not None
            assert agent_controller.collaboration_framework is not None
            assert agent_controller.performance_monitor is not None

            # Test Core components
            workspace = Path("/tmp/test_workspace")
            workspace.mkdir(exist_ok=True)
            dispatcher = AgentDispatcher(workspace)

            self.record_test_result(
                "component_initialization", True, "All components initialized successfully"
            )
            logger.info("✅ Component initialization test passed")

        except Exception as e:
            self.record_test_result("component_initialization", False, str(e))
            logger.error(f"❌ Component initialization test failed: {e}")

    async def test_flywheel_integration(self):
        """Test flywheel component integration"""
        logger.info("Testing flywheel integration...")

        try:
            flywheel = FlywheelController()

            # Test status reporting
            status = flywheel.get_status()
            assert "is_running" in status
            assert "active_phase" in status
            assert "cycle_count" in status

            # Test task addition
            from repo_depot.flywheel.flywheel_controller import FlywheelPhase, FlywheelTask

            task = FlywheelTask(
                task_id="test_task_001",
                phase=FlywheelPhase.CONSTRUCTION,
                description="Test task for integration testing",
                priority=1,
            )
            flywheel.add_task(task)

            # Verify task was added
            status_after = flywheel.get_status()
            assert status_after["total_tasks"] > status["total_tasks"]

            self.record_test_result(
                "flywheel_integration", True, "Flywheel components integrated successfully"
            )
            logger.info("✅ Flywheel integration test passed")

        except Exception as e:
            self.record_test_result("flywheel_integration", False, str(e))
            logger.error(f"❌ Flywheel integration test failed: {e}")

    async def test_agent_specialization_system(self):
        """Test agent specialization and orchestration"""
        logger.info("Testing agent specialization system...")

        try:
            controller = AgentController()

            # Test task submission
            task_id = await controller.submit_task(
                description="Create a simple API endpoint",
                priority=TaskPriority.HIGH,
                required_specializations=["implementation"],
            )

            assert task_id in controller.tasks
            assert controller.tasks[task_id].description == "Create a simple API endpoint"

            # Test status retrieval
            status = controller.get_task_status(task_id)
            assert status is not None
            assert status["status"] == "pending"

            # Test system status
            system_status = controller.get_system_status()
            assert "total_tasks" in system_status
            assert "active_agents" in system_status

            self.record_test_result(
                "agent_specialization_system", True, "Agent specialization system working"
            )
            logger.info("✅ Agent specialization system test passed")

        except Exception as e:
            self.record_test_result("agent_specialization_system", False, str(e))
            logger.error(f"❌ Agent specialization system test failed: {e}")

    async def test_cross_component_communication(self):
        """Test communication between different system components"""
        logger.info("Testing cross-component communication...")

        try:
            # Initialize components
            flywheel = FlywheelController()
            agent_controller = AgentController()

            # Test that components can share data
            flywheel_status = flywheel.get_status()
            agent_status = agent_controller.get_system_status()

            # Verify both systems are operational
            assert flywheel_status["is_running"] == False  # Not started
            assert agent_status["is_running"] == False  # Not started

            # Test performance monitoring integration
            await agent_controller.performance_monitor.record_global_metric(
                agent_controller.performance_monitor.MetricType.TASK_SUCCESS_RATE, 0.95
            )

            report = agent_controller.performance_monitor.get_system_performance_report()
            assert "global_metrics" in report

            self.record_test_result(
                "cross_component_communication", True, "Components communicate successfully"
            )
            logger.info("✅ Cross-component communication test passed")

        except Exception as e:
            self.record_test_result("cross_component_communication", False, str(e))
            logger.error(f"❌ Cross-component communication test failed: {e}")

    async def test_performance_under_load(self):
        """Test system performance under simulated load"""
        logger.info("Testing performance under load...")

        try:
            controller = AgentController()
            start_time = datetime.now()

            # Submit multiple tasks simultaneously
            tasks = []
            for i in range(10):
                task_id = await controller.submit_task(
                    description=f"Load test task {i}", priority=TaskPriority.MEDIUM
                )
                tasks.append(task_id)

            # Verify all tasks were submitted
            assert len(controller.tasks) >= 10

            # Complete some tasks to test performance tracking
            for i in range(5):
                await controller.complete_task(tasks[i], {"result": f"completed_task_{i}"})

            # Check performance metrics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Should complete within reasonable time
            assert duration < 30  # 30 seconds max for this test

            system_status = controller.get_system_status()
            assert system_status["completed_tasks"] >= 5

            self.record_test_result(
                "performance_under_load", True, f"Handled 10 tasks in {duration:.2f}s"
            )
            logger.info("✅ Performance under load test passed")

        except Exception as e:
            self.record_test_result("performance_under_load", False, str(e))
            logger.error(f"❌ Performance under load test failed: {e}")

    async def test_error_recovery(self):
        """Test system error recovery capabilities"""
        logger.info("Testing error recovery...")

        try:
            controller = AgentController()

            # Submit a task
            task_id = await controller.submit_task("Test error recovery")

            # Simulate task failure
            await controller.complete_task(task_id, error_message="Simulated failure")

            # Verify error was recorded
            task = controller.tasks[task_id]
            assert task.status.name == "FAILED"
            assert task.error_message == "Simulated failure"

            # Test system continues to function
            task_id2 = await controller.submit_task("Test after error")
            assert task_id2 in controller.tasks

            # Check system status still works
            status = controller.get_system_status()
            assert status["failed_tasks"] >= 1

            self.record_test_result(
                "error_recovery", True, "System recovered from errors gracefully"
            )
            logger.info("✅ Error recovery test passed")

        except Exception as e:
            self.record_test_result("error_recovery", False, str(e))
            logger.error(f"❌ Error recovery test failed: {e}")

    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        logger.info("Testing end-to-end workflow...")

        try:
            # This would test a complete workflow from task submission
            # through agent assignment, execution, and completion
            controller = AgentController()

            # Submit a comprehensive task
            task_id = await controller.submit_task(
                description="Implement a complete user authentication system with API endpoints, database models, and tests",
                priority=TaskPriority.HIGH,
                required_specializations=["strategic", "implementation", "analysis"],
            )

            # Verify task was created with all required properties
            task = controller.tasks[task_id]
            assert len(task.required_specializations) >= 2  # Should trigger collaboration

            # Simulate task completion
            await controller.complete_task(
                task_id,
                {
                    "artifacts": ["auth_service.py", "user_model.py", "auth_tests.py"],
                    "commit_sha": "abc123",
                    "duration_seconds": 1800,
                },
            )

            # Verify completion
            assert task.status.name == "COMPLETED"
            assert task.result is not None
            assert "artifacts" in task.result

            # Check that performance metrics were recorded
            system_status = controller.get_system_status()
            assert system_status["completed_tasks"] >= 1

            self.record_test_result(
                "end_to_end_workflow", True, "Complete workflow executed successfully"
            )
            logger.info("✅ End-to-end workflow test passed")

        except Exception as e:
            self.record_test_result("end_to_end_workflow", False, str(e))
            logger.error(f"❌ End-to-end workflow test failed: {e}")

    def record_test_result(self, test_name: str, success: bool, details: str = ""):
        """Record the result of a test"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests

        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        report = {
            "test_suite": "SuperAgency Integration Test Suite",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests) if total_tests > 0 else 0.0,
            "test_results": self.test_results,
            "summary": {
                "overall_status": "PASSED" if failed_tests == 0 else "FAILED",
                "recommendations": self.generate_recommendations(),
            },
        }

        return report

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        failed_tests = [r for r in self.test_results if not r["success"]]

        if failed_tests:
            recommendations.append(f"Address {len(failed_tests)} failed tests before deployment")

        # Check for specific patterns
        if any("performance" in r["test_name"] for r in failed_tests):
            recommendations.append("Review performance optimization settings")

        if any("communication" in r["test_name"] for r in failed_tests):
            recommendations.append("Check inter-component communication protocols")

        if not recommendations:
            recommendations.append("All systems operational - ready for deployment")

        return recommendations


async def main():
    """Run the integration test suite"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run tests
    test_suite = IntegrationTestSuite()
    report = await test_suite.run_all_tests()

    # Print results
    print("\n" + "=" * 60)
    print("SUPERAGENCY INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"Total Tests: {report['total_tests']}")
    print(f"Passed: {report['passed_tests']}")
    print(f"Failed: {report['failed_tests']}")
    print(".2f")
    print(f"Duration: {report['duration_seconds']:.2f} seconds")
    print(f"Status: {report['summary']['overall_status']}")
    print()

    if report["test_results"]:
        print("Test Details:")
        for result in report["test_results"]:
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {result['test_name']}: {result['details']}")

    if report["summary"]["recommendations"]:
        print("\nRecommendations:")
        for rec in report["summary"]["recommendations"]:
            print(f"  • {rec}")

    print("\n" + "=" * 60)

    # Save detailed report
    report_file = Path("integration_test_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Detailed report saved to: {report_file}")

    return report["summary"]["overall_status"] == "PASSED"


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
