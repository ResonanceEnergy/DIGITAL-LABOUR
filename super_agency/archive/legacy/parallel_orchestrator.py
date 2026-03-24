#!/usr/bin/env python3
"""
Parallel Orchestrator
High-performance version of the DIGITAL LABOUR orchestrator with maximum CPU utilization
"""

import concurrent.futures
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParallelOrchestrator:
    """Orchestrates multiple DIGITAL LABOUR agents in parallel for maximum throughput"""

    def __init__(self):
        self.root = Path(__file__).resolve().parent
        self.agents = {
            "repo_sentry": self.root / "agents" / "repo_sentry.py",
            "daily_brief": self.root / "agents" / "daily_brief.py",
            "council": self.root / "agents" / "council.py",
            "integrate_cell": self.root / "agents" / "integrate_cell.py",
            "github_orchestrator": self.root / "github_orchestrator.py"
        }

    def run_agent_parallel(self, agent_name: str, agent_path: Path) -> Dict[str, Any]:
        """Run a single agent and return results"""
        logger.info(f"Starting {agent_name}...")
        start_time = time.time()

        try:
            result = subprocess.run(
                [sys.executable, str(agent_path)],
                capture_output=True,
                text=True,
                cwd=self.root,
                timeout=300  # 5 minute timeout
            )

            end_time = time.time()
            duration = end_time - start_time

            return {
                "agent": agent_name,
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration
            }

        except subprocess.TimeoutExpired:
            end_time = time.time()
            return {
                "agent": agent_name,
                "success": False,
                "error": "Timeout after 300 seconds",
                "duration": end_time - start_time
            }
        except Exception as e:
            end_time = time.time()
            return {
                "agent": agent_name,
                "success": False,
                "error": str(e),
                "duration": end_time - start_time
            }

    def orchestrate_parallel(self) -> Dict[str, Any]:
        """Run all agents in parallel"""
        logger.info("🚀 Starting parallel orchestration...")

        # Use ThreadPoolExecutor since agents may do I/O operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            # Submit all agents
            futures = {
                executor.submit(self.run_agent_parallel, name, path): name
                for name, path in self.agents.items()
                if path.exists()
            }

            results = {}
            for future in concurrent.futures.as_completed(futures):
                agent_name = futures[future]
                try:
                    result = future.result()
                    results[agent_name] = result

                    status = "✅" if result["success"] else "❌"
                    logger.info(f"{status} {agent_name}: {result['duration']:.2f}s")

                    if not result["success"]:
                        logger.warning(f"{agent_name} stderr: {result.get('stderr', '')[:200]}...")

                except Exception as e:
                    logger.error(f"Failed to get result for {agent_name}: {str(e)}")
                    results[agent_name] = {"agent": agent_name, "success": False, "error": str(e)}

        return results

    def run_critical_path_optimization(self) -> Dict[str, Any]:
        """Run critical path optimization with dependency management"""
        logger.info("🎯 Running critical path optimization...")

        # Define execution phases with dependencies
        phases = {
            "phase_1_critical": ["repo_sentry"],  # Must run first
            "phase_2_parallel": ["daily_brief", "council"],  # Can run in parallel
            "phase_3_final": ["integrate_cell"]  # Must run last
        }

        all_results = {}

        for phase_name, agents in phases.items():
            logger.info(f"Starting {phase_name} with {len(agents)} agents...")

            if len(agents) == 1:
                # Single agent - run directly
                agent_name = agents[0]
                agent_path = self.agents.get(agent_name)
                if agent_path and agent_path.exists():
                    result = self.run_agent_parallel(agent_name, agent_path)
                    all_results[agent_name] = result
                    status = "✅" if result["success"] else "❌"
                    logger.info(f"{status} {phase_name} -> {agent_name}: {result['duration']:.2f}s")
            else:
                # Multiple agents - run in parallel
                phase_results = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as executor:
                    futures = {
                        executor.submit(self.run_agent_parallel, name, self.agents[name]): name
                        for name in agents
                        if name in self.agents and self.agents[name].exists()
                    }

                    for future in concurrent.futures.as_completed(futures):
                        agent_name = futures[future]
                        result = future.result()
                        phase_results[agent_name] = result
                        all_results[agent_name] = result

                        status = "✅" if result["success"] else "❌"
                        logger.info(f"{status} {phase_name} -> {agent_name}: {result['duration']:.2f}s")

        return all_results

def main():
    """Main parallel orchestration function"""
    print("⚡ DIGITAL LABOUR Parallel Orchestrator")
    print("=" * 50)

    orchestrator = ParallelOrchestrator()

    try:
        # Run critical path optimization for maximum efficiency
        results = orchestrator.run_critical_path_optimization()

        # Calculate performance metrics
        total_duration = sum(result.get("duration", 0) for result in results.values())
        successful_agents = sum(1 for result in results.values() if result.get("success", False))
        total_agents = len(results)

        print("\n📊 Orchestration Results:")
        print(f"   Total Agents: {total_agents}")
        print(f"   Successful: {successful_agents}")
        print(f"   Failed: {total_agents - successful_agents}")
        print(f"   Total Duration: {total_duration:.2f}s")

        # Show individual results
        print("\n🤖 Agent Results:")
        for agent_name, result in results.items():
            status = "✅" if result.get("success") else "❌"
            duration = result.get("duration", 0)
            print(f"   {status} {agent_name}: {duration:.2f}s")

            if not result.get("success"):
                error = result.get("error", "Unknown error")
                print(f"      Error: {error[:100]}...")

    except KeyboardInterrupt:
        print("\n⚠️  Orchestration interrupted by user")
    except Exception as e:
        print(f"\n💥 Orchestration failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
