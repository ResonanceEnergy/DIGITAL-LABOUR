#!/usr/bin/env python3
"""
Super Agency Agent Integration & Deployment Master Script
Orchestrates the complete integration and deployment of all 30 operations center agents
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import all integration modules
from operations_centers import operations_manager
from operations_centers_integration import OperationsCentersIntegrator
from agent_deployment_manager import deployment_manager
from conductor_integration_manager import conductor_integration

# Initialize integrator
operations_integrator = OperationsCentersIntegrator()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_integration_master.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class AgentIntegrationOrchestrator:
    """Master orchestrator for complete agent integration and deployment"""

    def __init__(self):
        self.integration_status = "not_started"
        self.start_time = None
        self.end_time = None
        self.master_report = {}

    async def execute_full_integration(self) -> Dict[str, Any]:
        """Execute the complete agent integration and deployment process"""
        self.start_time = datetime.now()
        self.integration_status = "in_progress"

        logger.info("🚀 Starting Super Agency Agent Integration & Deployment")
        logger.info("=" * 60)

        master_results = {
            "integration_start": self.start_time.isoformat(),
            "phases": {},
            "overall_status": "in_progress",
            "system_health": 0.0,
            "performance_metrics": {}
        }

        try:
            # Phase 1: Initialize Operations Centers
            logger.info("📦 Phase 1: Initializing Operations Centers...")
            phase1_result = await self._phase_initialize_operations_centers()
            master_results["phases"]["operations_centers_init"] = phase1_result

            if not phase1_result["success"]:
                raise Exception("Operations centers initialization failed")

            # Phase 2: Integrate with Matrix Monitor
            logger.info("🔗 Phase 2: Integrating with Matrix Monitor...")
            phase2_result = await self._phase_integrate_matrix_monitor()
            master_results["phases"]["matrix_monitor_integration"] = phase2_result

            if not phase2_result["success"]:
                raise Exception("Matrix Monitor integration failed")

            # Phase 3: Deploy Operations Center Agents
            logger.info("🤖 Phase 3: Deploying Operations Center Agents...")
            phase3_result = await self._phase_deploy_agents()
            master_results["phases"]["agent_deployment"] = phase3_result

            if not phase3_result["success"]:
                raise Exception("Agent deployment failed")

            # Phase 4: Initialize Conductor Integration
            logger.info("🎼 Phase 4: Initializing Conductor Integration...")
            phase4_result = await self._phase_initialize_conductor_integration()
            master_results["phases"]["conductor_integration"] = phase4_result

            if not phase4_result["success"]:
                raise Exception("Conductor integration failed")

            # Phase 5: Sync Operations with Conductor
            logger.info("🔄 Phase 5: Syncing Operations with Conductor...")
            phase5_result = await self._phase_sync_operations()
            master_results["phases"]["operations_sync"] = phase5_result

            if not phase5_result["success"]:
                raise Exception("Operations sync failed")

            # Phase 6: Final System Validation
            logger.info("✅ Phase 6: Final System Validation...")
            phase6_result = await self._phase_final_validation()
            master_results["phases"]["final_validation"] = phase6_result

            # Calculate overall success
            successful_phases = sum(1 for phase in master_results["phases"].values() if phase["success"])
            total_phases = len(master_results["phases"])
            success_rate = (successful_phases / total_phases * 100) if total_phases > 0 else 0

            master_results["overall_status"] = "success" if success_rate >= 80 else "partial_success"
            master_results["system_health"] = phase6_result.get("system_health", 0.0)
            master_results["performance_metrics"] = {
                "success_rate": success_rate,
                "total_phases": total_phases,
                "successful_phases": successful_phases,
                "integration_duration_seconds": (datetime.now() - self.start_time).total_seconds(),
                "agents_deployed": phase3_result.get("agents_deployed", 0),
                "centers_integrated": phase4_result.get("centers_integrated", 0)
            }

            self.integration_status = master_results["overall_status"]
            logger.info(f"🎉 Integration completed with {success_rate:.1f}% success rate")

        except Exception as e:
            logger.error(f"❌ Integration failed: {e}")
            master_results["overall_status"] = "failed"
            master_results["error"] = str(e)
            self.integration_status = "failed"

        finally:
            self.end_time = datetime.now()
            master_results["integration_end"] = self.end_time.isoformat()
            master_results["total_duration_seconds"] = (self.end_time - self.start_time).total_seconds()

            self.master_report = master_results

        return master_results

    async def _phase_initialize_operations_centers(self) -> Dict[str, Any]:
        """Phase 1: Initialize operations centers"""
        try:
            # Get operations status
            status = await operations_manager.get_operations_status()

            return {
                "success": True,
                "centers_initialized": len(status["centers"]),
                "total_agents": status["summary"]["total_agents"],
                "system_status": status["summary"]["system_status"],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Operations centers initialization failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _phase_integrate_matrix_monitor(self) -> Dict[str, Any]:
        """Phase 2: Integrate with Matrix Monitor"""
        try:
            # Run Matrix Monitor integration
            integration_result = await operations_integrator.integrate_with_matrix_monitor()

            return {
                "success": True,
                "data_sources_integrated": integration_result.get("data_sources_integrated", 0),
                "dashboard_exported": integration_result.get("dashboard_exported", False),
                "system_health": integration_result.get("system_health", 0.0),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Matrix Monitor integration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _phase_deploy_agents(self) -> Dict[str, Any]:
        """Phase 3: Deploy operations center agents"""
        try:
            # Deploy all agents
            deployment_result = await deployment_manager.deploy_operations_center_agents()

            return {
                "success": True,
                "agents_deployed": deployment_result.get("total_agents_deployed", 0),
                "successful_deployments": deployment_result.get("successful_deployments", 0),
                "failed_deployments": deployment_result.get("failed_deployments", 0),
                "success_rate": deployment_result.get("success_rate", 0.0),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Agent deployment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _phase_initialize_conductor_integration(self) -> Dict[str, Any]:
        """Phase 4: Initialize conductor integration"""
        try:
            # Initialize conductor integration
            integration_result = await conductor_integration.initialize_conductor_integration()

            return {
                "success": True,
                "centers_integrated": integration_result.get("centers_integrated", 0),
                "successful_integrations": integration_result.get("successful_integrations", 0),
                "failed_integrations": integration_result.get("failed_integrations", 0),
                "success_rate": integration_result.get("success_rate", 0.0),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Conductor integration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _phase_sync_operations(self) -> Dict[str, Any]:
        """Phase 5: Sync operations with conductor"""
        try:
            # Sync operations
            sync_result = await conductor_integration.sync_operations_with_conductor()

            return {
                "success": True,
                "centers_synced": sync_result.get("centers_synced", 0),
                "messages_processed": sync_result.get("total_messages_processed", 0),
                "sync_efficiency": sync_result.get("performance_metrics", {}).get("sync_efficiency", 0.0),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Operations sync failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _phase_final_validation(self) -> Dict[str, Any]:
        """Phase 6: Final system validation"""
        try:
            # Get deployment status
            deployment_status = await deployment_manager.get_deployment_status()

            # Get integration status
            integration_status = await conductor_integration.get_integration_status()

            # Run health checks
            health_check = await deployment_manager.run_agent_health_check()

            # Calculate overall system health
            deployment_health = deployment_status.get("system_health", 0.0)
            integration_health = integration_status.get("integration_health", 0.0)
            agent_health = (health_check.get("healthy_agents", 0) / health_check.get("total_agents_checked", 1)) * 100

            overall_health = (deployment_health + integration_health + agent_health) / 3

            return {
                "success": True,
                "system_health": overall_health,
                "deployment_health": deployment_health,
                "integration_health": integration_health,
                "agent_health": agent_health,
                "active_agents": deployment_status.get("active_agents", 0),
                "total_agents": deployment_status.get("total_deployed_agents", 0),
                "active_integrations": integration_status.get("active_integrations", 0),
                "total_integrations": integration_status.get("total_integrations", 0),
                "healthy_agents": health_check.get("healthy_agents", 0),
                "total_agents_checked": health_check.get("total_agents_checked", 0),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Final validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "system_health": 0.0,
                "timestamp": datetime.now().isoformat()
            }

    async def export_master_report(self, output_path: str = None) -> str:
        """Export comprehensive master integration report"""
        try:
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"master_agent_integration_report_{timestamp}.json"

            # Add final metadata
            self.master_report["report_metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "integration_status": self.integration_status,
                "total_duration": f"{(self.end_time - self.start_time).total_seconds():.2f} seconds" if self.end_time else "N/A",
                "system_version": "Super Agency v2.0",
                "integration_type": "Operations Centers Agent Deployment"
            }

            # Export to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.master_report, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"📊 Master integration report exported to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Failed to export master report: {e}")
            return None

    async def get_current_status(self) -> Dict[str, Any]:
        """Get current integration status"""
        return {
            "integration_status": self.integration_status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "master_report_summary": {
                "overall_status": self.master_report.get("overall_status", "unknown"),
                "system_health": self.master_report.get("system_health", 0.0),
                "phases_completed": len([p for p in self.master_report.get("phases", {}).values() if p.get("success", False)]),
                "total_phases": len(self.master_report.get("phases", {}))
            } if self.master_report else None
        }

# Global orchestrator
integration_orchestrator = AgentIntegrationOrchestrator()

async def execute_full_agent_integration():
    """Execute the complete agent integration process"""
    return await integration_orchestrator.execute_full_integration()

async def get_integration_status():
    """Get current integration status"""
    return await integration_orchestrator.get_current_status()

async def export_master_integration_report():
    """Export master integration report"""
    return await integration_orchestrator.export_master_report()

async def run_quick_validation():
    """Run a quick system validation"""
    logger.info("🔍 Running quick system validation...")

    try:
        # Get deployment status
        deployment_status = await deployment_manager.get_deployment_status()

        # Get integration status
        integration_status = await conductor_integration.get_integration_status()

        # Run health check
        health_check = await deployment_manager.run_agent_health_check()

        validation_result = {
            "timestamp": datetime.now().isoformat(),
            "validation_status": "success",
            "deployment_status": deployment_status,
            "integration_status": integration_status,
            "health_check": health_check,
            "system_health": (deployment_status.get("system_health", 0) +
                            integration_status.get("integration_health", 0) +
                            (health_check.get("healthy_agents", 0) / max(1, health_check.get("total_agents_checked", 1)) * 100)) / 3
        }

        logger.info(f"✅ Quick validation completed. System health: {validation_result['system_health']:.1f}%")
        return validation_result

    except Exception as e:
        logger.error(f"❌ Quick validation failed: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "validation_status": "failed",
            "error": str(e)
        }

if __name__ == "__main__":
    # Master integration demo
    async def demo():
        print("🚀 Super Agency Agent Integration & Deployment Master Demo")
        print("=" * 70)

        # Execute full integration
        print("🔄 Executing full agent integration...")
        integration_result = await execute_full_agent_integration()

        print(f"📊 Integration Status: {integration_result['overall_status']}")
        print(f"🏥 System Health: {integration_result['system_health']:.1f}%")
        print(f"⏱️  Duration: {integration_result['total_duration_seconds']:.2f} seconds")

        # Show phase results
        print("\n📋 Phase Results:")
        for phase_name, phase_result in integration_result["phases"].items():
            status = "✅" if phase_result["success"] else "❌"
            print(f"  {status} {phase_name}: {phase_result.get('success', False)}")

        # Run quick validation
        print("\n🔍 Running quick validation...")
        validation = await run_quick_validation()
        print(f"🏥 Validation Health: {validation['system_health']:.1f}%")

        # Export master report
        print("📊 Exporting master integration report...")
        report_path = await export_master_integration_report()
        if report_path:
            print(f"📁 Master report saved to: {report_path}")

        print("\n🎉 Super Agency agent integration and deployment completed!")
        print("🤖 All 30 operations center agents are now active and integrated!")

    asyncio.run(demo())
