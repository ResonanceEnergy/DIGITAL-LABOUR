#!/usr/bin/env python3
"""
Generate Missing Integration Reports
Creates the three missing operational reports for DIGITAL LABOUR
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

async def generate_integration_reports():
    """Generate all missing integration reports"""
    print('🔍 Generating Missing Integration Reports...')

    # 1. Agent Deployment Report
    try:
        from agent_deployment_manager import deployment_manager
        deployment_status = await deployment_manager.deploy_operations_center_agents()

        report_file = f'agent_deployment_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(deployment_status, f, indent=2, default=str)
        print(f'✅ Generated: {report_file}')
    except Exception as e:
        print(f'❌ Agent deployment report failed: {e}')

    # 2. Conductor Integration Report
    try:
        from conductor_integration_manager import ConductorIntegrationManager
        conductor_manager = ConductorIntegrationManager()
        conductor_status = await conductor_manager.initialize_conductor_integration()

        report_file = f'conductor_integration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(conductor_status, f, indent=2, default=str)
        print(f'✅ Generated: {report_file}')
    except Exception as e:
        print(f'❌ Conductor integration report failed: {e}')

    # 3. Master Agent Integration Report
    try:
        from agent_integration_master import AgentIntegrationOrchestrator
        master_orchestrator = AgentIntegrationOrchestrator()
        master_status = await master_orchestrator.execute_full_integration()

        report_file = f'master_agent_integration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(master_status, f, indent=2, default=str)
        print(f'✅ Generated: {report_file}')
    except Exception as e:
        print(f'❌ Master integration report failed: {e}')

if __name__ == "__main__":
    asyncio.run(generate_integration_reports())
