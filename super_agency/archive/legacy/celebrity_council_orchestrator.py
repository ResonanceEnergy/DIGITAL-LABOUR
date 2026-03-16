#!/usr/bin/env python3
"""
Celebrity Council Orchestrator
Runs all celebrity council agents in continuous work cycles
"""

import asyncio
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from elon_musk_agent import ElonMuskAgent
from jamie_dimon_agent import JamieDimonAgent
from warren_buffett_agent import WarrenBuffettAgent
from ryan_cohen_agent import RyanCohenAgent

class CelebrityCouncilOrchestrator:
    """Orchestrates all celebrity council agents"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

        # Initialize all executive council agents
        self.agents = {
            'elon_musk': ElonMuskAgent(),
            'jamie_dimon': JamieDimonAgent(),
            'warren_buffett': WarrenBuffettAgent(),
            'ryan_cohen': RyanCohenAgent()
        }

        self.cycle_count = 0
        self.is_running = False

    def setup_logging(self):
        """Setup orchestrator logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - EXECUTIVE COUNCIL ORCHESTRATOR - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('executive_council_orchestrator.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("ExecutiveCouncilOrchestrator")

    async def run_single_cycle(self) -> Dict[str, Any]:
        """Run one complete cycle of all executive council agents"""
        self.cycle_count += 1

        self.logger.info(f"🚀 Starting Executive Council Cycle #{self.cycle_count}")

        cycle_results = {
            'cycle_number': self.cycle_count,
            'timestamp': datetime.now().isoformat(),
            'agents_executed': [],
            'total_work_completed': 0,
            'cycle_duration': 0
        }

        start_time = time.time()

        try:
            # Execute each agent's work cycle
            for agent_name, agent in self.agents.items():
                self.logger.info(f"🎯 Executing {agent_name.replace('_', ' ').title()} Agent")

                try:
                    # Run the agent's work cycle
                    agent.execute_work_cycle()
                    cycle_results['agents_executed'].append({
                        'agent': agent_name,
                        'status': 'success',
                        'work_completed': True
                    })
                    cycle_results['total_work_completed'] += 1

                except Exception as e:
                    self.logger.error(f"❌ Error executing {agent_name}: {e}")
                    cycle_results['agents_executed'].append({
                        'agent': agent_name,
                        'status': 'error',
                        'error': str(e),
                        'work_completed': False
                    })

            cycle_results['cycle_duration'] = time.time() - start_time

            self.logger.info(f"✅ Executive Council Cycle #{self.cycle_count} completed in {cycle_results['cycle_duration']:.2f} seconds")

            # Save cycle results
            self.save_cycle_results(cycle_results)

            return cycle_results

        except Exception as e:
            self.logger.error(f"❌ Executive Council Cycle failed: {e}")
            return {
                'cycle_number': self.cycle_count,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def save_cycle_results(self, results: Dict[str, Any]):
        """Save cycle execution results"""
        results_dir = Path("executive_council_results")
        results_dir.mkdir(exist_ok=True)

        result_file = results_dir / f"cycle_{self.cycle_count:04d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(result_file, 'w') as f:
            import json
            json.dump(results, f, indent=2)

        self.logger.info(f"Saved cycle results to {result_file}")

    async def run_continuous_cycles(self, interval_minutes: int = 60):
        """Run continuous cycles at specified intervals"""
        self.is_running = True
        self.logger.info(f"🔄 Starting continuous Executive Council cycles every {interval_minutes} minutes")

        try:
            while self.is_running:
                await self.run_single_cycle()

                if self.is_running:  # Check if we should continue
                    self.logger.info(f"⏰ Waiting {interval_minutes} minutes until next cycle...")
                    await asyncio.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            self.logger.info("🛑 Executive Council Orchestrator stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Continuous cycles failed: {e}")
        finally:
            self.is_running = False

    def stop_cycles(self):
        """Stop continuous cycles"""
        self.logger.info("🛑 Stopping Executive Council continuous cycles")
        self.is_running = False

    async def run_once(self):
        """Run a single cycle and exit"""
        self.logger.info("🎯 Running single Executive Council cycle")
        result = await self.run_single_cycle()

        # Print summary
        print("\n" + "="*60)
        print("EXECUTIVE COUNCIL WORK CYCLE RESULTS")
        print("="*60)
        print(f"Cycle: #{result['cycle_number']}")
        print(f"Duration: {result.get('cycle_duration', 0):.2f} seconds")
        print(f"Agents Executed: {len(result.get('agents_executed', []))}")
        print(f"Work Completed: {result.get('total_work_completed', 0)}")
        print()

        for agent_result in result.get('agents_executed', []):
            status_icon = "✅" if agent_result['status'] == 'success' else "❌"
            print(f"{status_icon} {agent_result['agent'].replace('_', ' ').title()}: {agent_result['status']}")

        print("="*60)

        return result

async def main():
    """Main execution function"""
    import sys

    orchestrator = ExecutiveCouncilOrchestrator()

    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        # Run continuous cycles
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        await orchestrator.run_continuous_cycles(interval)
    else:
        # Run single cycle
        await orchestrator.run_once()

if __name__ == "__main__":
    asyncio.run(main())
