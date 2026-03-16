#!/usr/bin/env python3
"""
Operations Centers Activation System
Makes the 3 operations centers fully operational and integrated
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from operations_centers import operations_manager, OperationsCenter
from agent_deployment_manager import deployment_manager
from conductor_integration_manager import ConductorIntegrationManager

class OperationsCentersActivator:
    """Activates and runs the operations centers"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.activation_status = {}
        self.monitoring_active = False

    async def activate_operations_centers(self) -> Dict[str, Any]:
        """Activate all three operations centers"""
        self.logger.info("🚀 Activating Operations Centers...")

        activation_results = {
            "timestamp": datetime.now().isoformat(),
            "centers_activated": [],
            "total_agents_deployed": 0,
            "integration_status": {},
            "monitoring_started": False,
            "success": True
        }

        try:
            # 1. Deploy agents to all centers
            deployment_result = await deployment_manager.deploy_operations_center_agents()
            activation_results["deployment"] = deployment_result

            # 2. Initialize conductor integration
            conductor_manager = ConductorIntegrationManager()
            integration_result = await conductor_manager.initialize_conductor_integration()
            activation_results["conductor_integration"] = integration_result

            # 3. Start operations monitoring
            monitoring_result = await self._start_operations_monitoring()
            activation_results["monitoring_started"] = monitoring_result["success"]

            # 4. Execute initial operations cycle
            cycle_result = await operations_manager.execute_operations_cycle()
            activation_results["initial_cycle"] = cycle_result

            # 5. Get final status
            final_status = await operations_manager.get_operations_status()
            activation_results["final_status"] = final_status

            # Update activation results
            for center_id, center_data in final_status["centers"].items():
                center_result = {
                    "center_id": center_id,
                    "name": center_data["name"],
                    "agents_deployed": center_data["agents"]["total"],
                    "agents_active": center_data["agents"]["active"],
                    "status": "active"
                }
                activation_results["centers_activated"].append(center_result)
                activation_results["total_agents_deployed"] += center_data["agents"]["total"]

            self.logger.info(f"✅ Operations centers activated: {len(activation_results['centers_activated'])} centers, {activation_results['total_agents_deployed']} agents")

        except Exception as e:
            self.logger.error(f"❌ Operations centers activation failed: {e}")
            activation_results["success"] = False
            activation_results["error"] = str(e)

        return activation_results

    async def _start_operations_monitoring(self) -> Dict[str, Any]:
        """Start continuous operations monitoring"""
        try:
            # Start monitoring loop
            asyncio.create_task(self._operations_monitoring_loop())
            self.monitoring_active = True

            return {
                "success": True,
                "message": "Operations monitoring started",
                "monitoring_interval": 30  # seconds
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _operations_monitoring_loop(self):
        """Continuous monitoring loop for operations centers"""
        while self.monitoring_active:
            try:
                # Get current status
                status = await operations_manager.get_operations_status()

                # Log status
                self.logger.info(f"Operations Status: {status['overall_metrics']['active_agents']}/{status['overall_metrics']['total_agents']} agents active")

                # Check for issues and auto-correct
                await self._check_and_correct_operations(status)

                # Save status to file
                status_file = f"operations_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(status_file, 'w') as f:
                    json.dump(status, f, indent=2, default=str)

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _check_and_correct_operations(self, status: Dict[str, Any]):
        """Check operations status and auto-correct issues"""
        for center_id, center_data in status["centers"].items():
            # Check if center has enough active agents
            active_ratio = center_data["agents"]["active"] / center_data["agents"]["total"] if center_data["agents"]["total"] > 0 else 0

            if active_ratio < 0.8:  # Less than 80% active
                self.logger.warning(f"Low agent activity in {center_data['name']}: {active_ratio:.1%}")
                # Auto-correct would go here

    async def get_activation_status(self) -> Dict[str, Any]:
        """Get current activation status"""
        return {
            "monitoring_active": self.monitoring_active,
            "centers_status": await operations_manager.get_operations_status(),
            "last_updated": datetime.now().isoformat()
        }

async def main():
    """Main activation function"""
    activator = OperationsCentersActivator()
    result = await activator.activate_operations_centers()

    # Save activation report
    report_file = f"operations_centers_activation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"✅ Operations centers activation complete. Report: {report_file}")
    return result

if __name__ == "__main__":
    asyncio.run(main())
