#!/usr/bin/env python3
"""
DIGITAL LABOUR Conductor Agent
Orchestrates Inner Council agents using AutoGen and CrewAI patterns
Maximizes distributed intelligence and resource efficiency
"""

import asyncio
import sys
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

# AutoGen imports
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.tools import AgentTool
from autogen_ext.models.openai import OpenAIChatCompletionClient

# CrewAI imports (optional - will work without it)
try:
    from crewai import Agent, Task, Crew, Process
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("CrewAI not available - running with AutoGen only")

# Local imports
sys.path.append(str(Path(__file__).parent))
from agents.common import CommonAgent
from agents.repo_sentry import RepoSentryAgent
from agents.daily_brief import DailyBriefAgent
from agents.council import CouncilAgent
from agents.integrate_cell import IntegrateCellAgent
from agents.openclaw_integration import OpenClawIntegrationAgent

class ConductorAgent:
    """Master orchestrator for DIGITAL LABOUR agents"""

    def __init__(self):
        """Initialize Conductor Agent."""
        self.workspace = Path(__file__).parent
        self.system_name = "QUANTUM FORGE" if os.name == 'nt' else "Quantum Quasar"

        # Initialize AutoGen model client (requires OPENAI_API_KEY)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and len(api_key) > 10:  # Basic validation
            try:
                self.model_client = OpenAIChatCompletionClient(
                    model="gpt-4o",
                    api_key=api_key
                )
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
                self.model_client = None
        else:
            print("OPENAI_API_KEY not set or invalid - model client disabled")
            self.model_client = None

        # Initialize Inner Council agents
        self.agents = self._initialize_agents()

        # Initialize CrewAI crew (if available)
        self.crew = self._initialize_crew()

    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize all Inner Council agents"""
        return {
            'repo_sentry': RepoSentryAgent(model_client=self.model_client),
            'daily_brief': DailyBriefAgent(model_client=self.model_client),
            'council': CouncilAgent(model_client=self.model_client),
            'integrate_cell': IntegrateCellAgent(model_client=self.model_client),
            'openclaw': OpenClawIntegrationAgent(model_client=self.model_client),
            'common': CommonAgent(model_client=self.model_client)
        }

    def _initialize_crew(self) -> Optional[Any]:
        """Initialize CrewAI crew for orchestration (if available)"""
        if not CREWAI_AVAILABLE:
            return None

        # Create CrewAI agents
        crew_agents = [
            Agent(
                role="Repository Monitor",
                goal="Monitor and analyze repository changes",
                backstory="Expert in code analysis and change detection",
                allow_delegation=False,
                verbose=True
            ),
            Agent(
                role="Intelligence Synthesizer",
                goal="Compile and synthesize operational intelligence",
                backstory="Master of data aggregation and insight generation",
                allow_delegation=False,
                verbose=True
            ),
            Agent(
                role="Executive Decision Maker",
                goal="Make autonomous decisions within authority limits",
                backstory="Strategic thinker with risk assessment expertise",
                allow_delegation=False,
                verbose=True
            ),
            Agent(
                role="System Integrator",
                goal="Integrate new systems and maintain coherence",
                backstory="Specialist in system architecture and integration",
                allow_delegation=False,
                verbose=True
            )
        ]

        return Crew(
            agents=crew_agents,
            verbose=True,
            process=Process.sequential
        )

    async def orchestrate_cycle(self) -> Dict[str, Any]:
        """Execute complete orchestration cycle"""
        print(f"[{self.system_name}] Starting Conductor Orchestration Cycle")

        results = {}

        try:
            # Phase 1: Repository Intelligence Gathering
            print("Phase 1: Repository Intelligence")
            repo_results = await self._run_repo_intelligence()
            results['repo_intelligence'] = repo_results

            # Phase 2: Decision Making
            print("Phase 2: Executive Decisions")
            decision_results = await self._run_decision_making(repo_results)
            results['decisions'] = decision_results

            # Phase 3: System Integration
            print("Phase 3: System Integration")
            integration_results = await self._run_integration(decision_results)
            results['integration'] = integration_results

            # Phase 4: External Communications via OpenClaw
            print("Phase 4: External Communications")
            openclaw_results = await self._run_openclaw_communications(integration_results)
            results['openclaw_communications'] = openclaw_results

            # Phase 5: Resource Optimization
            print("Phase 5: Resource Optimization")
            resource_results = await self._optimize_resources()
            results['resource_optimization'] = resource_results

            print(f"[{self.system_name}] Orchestration Cycle Complete")
            return {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'results': results
            }

        except Exception as e:
            print(f"[{self.system_name}] Orchestration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def _run_repo_intelligence(self) -> Dict[str, Any]:
        """Gather repository intelligence using available agents"""
        if self.model_client:
            # Create AutoGen agents for repo tasks
            repo_agent = AssistantAgent(
                "repo_analyzer",
                model_client=self.model_client,
                system_message="You are an expert repository analyst. Analyze changes and generate insights."
            )
            autogen_result = "AutoGen analysis completed"
        else:
            # Use stub agent
            autogen_result = self.agents['repo_sentry'].execute("analyze repositories")

        if CREWAI_AVAILABLE and self.crew:
            # Use CrewAI for structured tasks
            tasks = [
                Task(
                    description="Analyze recent repository changes and categorize them",
                    agent=self.crew.agents[0],  # Repository Monitor
                    expected_output="Detailed analysis of repository changes with categories and priorities"
                ),
                Task(
                    description="Generate daily operational intelligence brief",
                    agent=self.crew.agents[1],  # Intelligence Synthesizer
                    expected_output="Comprehensive intelligence brief with insights and recommendations"
                )
            ]

            # Execute tasks
            crew_results = self.crew.kickoff(tasks)
            crewai_data = crew_results
        else:
            # Fallback to stub agent
            crewai_data = self.agents['daily_brief'].execute("generate intelligence brief")

        return {
            'autogen_analysis': autogen_result,
            'crewai_results': crewai_data,
            'timestamp': datetime.now().isoformat()
        }

    async def _run_decision_making(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make executive decisions based on intelligence"""
        if self.model_client:
            decision_agent = AssistantAgent(
                "decision_maker",
                model_client=self.model_client,
                system_message="You are an executive decision maker. Evaluate options and make strategic decisions."
            )
            autogen_decision = "AutoGen decision analysis completed"
        else:
            autogen_decision = self.agents['council'].execute("evaluate decisions")

        if CREWAI_AVAILABLE and self.crew:
            # Decision task
            decision_task = Task(
                description=f"Evaluate repository intelligence and make strategic decisions: {json.dumps(repo_data)}",
                agent=self.crew.agents[2],  # Executive Decision Maker
                expected_output="Strategic decisions with reasoning and action items"
            )

            result = self.crew.kickoff([decision_task])
            decision_data = result
        else:
            # Fallback to stub agent
            decision_data = self.agents['council'].execute("make strategic decisions")

        return {
            'decisions': decision_data,
            'authority_level': 'council',
            'timestamp': datetime.now().isoformat()
        }

    async def _run_integration(self, decisions: Dict[str, Any]) -> Dict[str, Any]:
        """Execute system integration based on decisions"""
        if CREWAI_AVAILABLE and self.crew:
            integration_task = Task(
                description=f"Execute integration tasks based on decisions: {json.dumps(decisions)}",
                agent=self.crew.agents[3],  # System Integrator
                expected_output="Integration results and system status updates"
            )

            result = self.crew.kickoff([integration_task])
            integration_data = result
        else:
            # Fallback to stub agent
            integration_data = self.agents['integrate_cell'].execute("execute integration tasks")

        return {
            'integration_status': 'completed',
            'results': integration_data,
            'timestamp': datetime.now().isoformat()
        }

    async def _run_openclaw_communications(self, integration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send updates and notifications via OpenClaw"""
        openclaw_agent = self.agents.get('openclaw')
        if not openclaw_agent or not openclaw_agent.is_openclaw_installed():
            print("OpenClaw agent not available or not installed. Skipping communications.")
            return {
                'status': 'skipped',
                'reason': 'OpenClaw not available'
            }

        # Example: Send a summary of the integration results to a default platform
        summary_message = f"DIGITAL LABOUR Orchestration Cycle Update:\n"
        summary_message += f"Integration Status: {integration_data.get('integration_status', 'N/A')}\n"
        summary_message += f"Results: {json.dumps(integration_data.get('results', {}), indent=2)}"

        # This is a placeholder for a more sophisticated notification strategy
        # In a real scenario, you would determine the platform and recipient dynamically
        platform = "discord" # or "slack", "telegram", etc.

        print(f"Sending update to {platform} via OpenClaw...")
        communication_result = openclaw_agent.send_message_to_openclaw(
            platform=platform,
            message=summary_message
        )

        return {
            'communication_status': communication_result.get('status', 'error'),
            'results': communication_result,
            'timestamp': datetime.now().isoformat()
        }

    async def _optimize_resources(self) -> Dict[str, Any]:
        """Optimize resource allocation across agents"""
        # Analyze current resource usage
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent

        # Determine optimization actions
        optimizations = []

        if cpu_percent > 80:
            optimizations.append("Scale back parallel processing")
        elif cpu_percent < 50:
            optimizations.append("Increase CPU utilization to maximum mode")

        if memory_percent > 85:
            optimizations.append("Enable memory compression")
        elif memory_percent < 60:
            optimizations.append("Expand memory buffers")

        return {
            'current_cpu': cpu_percent,
            'current_memory': memory_percent,
            'optimizations': optimizations,
            'timestamp': datetime.now().isoformat()
        }

async def main():
    """Main conductor execution"""
    conductor = ConductorAgent()

    # Warn but don't exit if no API key — run in degraded mode with stub agents
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set — running in degraded mode (stub agents only)")

    # Run orchestration cycle
    result = await conductor.orchestrate_cycle()

    # Save results
    output_file = conductor.workspace / "conductor_results.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"Results saved to {output_file}")

    # Exit with error code if orchestration failed
    if result.get('status') == 'error':
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
