#!/usr/bin/env python3
"""
DIGITAL LABOUR CPU Maximizer
Parallel processing orchestrator for maximum computational output
"""

import multiprocessing as mp
import concurrent.futures
import subprocess
import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CPUMaximizer:
    """Maximizes CPU utilization across all DIGITAL LABOUR systems"""

    def __init__(self, max_workers=None):
        self.max_workers = max_workers or mp.cpu_count()
        self.root = Path(__file__).resolve().parents[1]
        logger.info(f"CPU Maximizer initialized with {self.max_workers} workers")

    def get_all_repos(self) -> List[str]:
        """Get all repository names from portfolio"""
        portfolio_file = self.root / "portfolio.json"
        if portfolio_file.exists():
            portfolio = json.loads(portfolio_file.read_text())
            return [repo["name"] for repo in portfolio.get("repositories", [])]
        return ["AAC", "demo", "TESLACALLS2026"]  # fallback

    def parallel_repo_analysis(self) -> Dict[str, Any]:
        """Run repo sentry analysis in parallel across all repos"""
        logger.info("Starting parallel repository analysis...")

        repos = self.get_all_repos()
        results = {}

        def analyze_repo(repo_name: str) -> tuple:
            try:
                cmd = [sys.executable, str(self.root / "agents" / "repo_sentry.py")]
                env = os.environ.copy()
                env["TARGET_REPO"] = repo_name

                start_time = time.time()
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.root)
                end_time = time.time()

                return repo_name, {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration": end_time - start_time
                }
            except Exception as e:
                return repo_name, {"success": False, "error": str(e)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(analyze_repo, repo): repo for repo in repos}
            for future in concurrent.futures.as_completed(futures):
                repo_name, result = future.result()
                results[repo_name] = result
                status = "✅" if result["success"] else "❌"
                logger.info(f"{status} {repo_name}: {result.get('duration', 0):.2f}s")

        return results

    def parallel_portfolio_intelligence(self) -> Dict[str, Any]:
        """Run portfolio intelligence analysis in parallel"""
        logger.info("Starting parallel portfolio intelligence...")

        # Multiple analysis types to run in parallel
        analysis_tasks = [
            "portfolio_intel.py",
            "portfolio_autodiscover.py",
            "portfolio_autotier.py",
            "portfolio_selfheal.py"
        ]

        results = {}

        def run_analysis(task: str) -> tuple:
            try:
                script_path = self.root / "ResonanceEnergy_DigitalLabour" / "agents" / task
                if not script_path.exists():
                    return task, {"success": False, "error": "Script not found"}

                start_time = time.time()
                result = subprocess.run([sys.executable, str(script_path)],
                                      capture_output=True, text=True,
                                      cwd=self.root / "ResonanceEnergy_DigitalLabour")
                end_time = time.time()

                return task, {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration": end_time - start_time
                }
            except Exception as e:
                return task, {"success": False, "error": str(e)}

        with concurrent.futures.ProcessPoolExecutor(max_workers=min(len(analysis_tasks), self.max_workers)) as executor:
            futures = {executor.submit(run_analysis, task): task for task in analysis_tasks}
            for future in concurrent.futures.as_completed(futures):
                task_name, result = future.result()
                results[task_name] = result
                status = "✅" if result["success"] else "❌"
                logger.info(f"{status} {task_name}: {result.get('duration', 0):.2f}s")

        return results

    def parallel_ncl_processing(self) -> Dict[str, Any]:
        """Run NCL Second Brain processing in parallel"""
        logger.info("Starting parallel NCL processing...")

        # Multiple NCL tasks
        ncl_tasks = [
            ("classifier.py", "classify_events"),
            ("summarizer.py", "summarize_events"),
            ("para_router.py", "route_events")
        ]

        results = {}

        def run_ncl_task(task_file: str, task_name: str) -> tuple:
            try:
                script_path = self.root / "ncl_second_brain" / "engine" / task_file
                if not script_path.exists():
                    return task_name, {"success": False, "error": "Script not found"}

                start_time = time.time()
                result = subprocess.run([sys.executable, str(script_path)],
                                      capture_output=True, text=True,
                                      cwd=self.root / "ncl_second_brain")
                end_time = time.time()

                return task_name, {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration": end_time - start_time
                }
            except Exception as e:
                return task_name, {"success": False, "error": str(e)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(ncl_tasks), self.max_workers)) as executor:
            futures = {executor.submit(run_ncl_task, task, name): name for task, name in ncl_tasks}
            for future in concurrent.futures.as_completed(futures):
                task_name, result = future.result()
                results[task_name] = result
                status = "✅" if result["success"] else "❌"
                logger.info(f"{status} {task_name}: {result.get('duration', 0):.2f}s")

        return results

    def parallel_aac_processing(self) -> Dict[str, Any]:
        """Run AAC (Automated Accounting Center) processing in parallel"""
        logger.info("Starting parallel AAC processing...")

        aac_tasks = [
            ("aac_engine.py", "init_engine"),
            ("aac_compliance.py", "run_compliance"),
            ("aac_intelligence.py", "run_intelligence"),
            ("test_integration.py", "run_tests")
        ]

        results = {}

        def run_aac_task(task_file: str, task_name: str) -> tuple:
            try:
                script_path = self.root / "repos" / "AAC" / task_file
                if not script_path.exists():
                    return task_name, {"success": False, "error": "Script not found"}

                start_time = time.time()
                result = subprocess.run([sys.executable, str(script_path)],
                                      capture_output=True, text=True,
                                      cwd=self.root / "repos" / "AAC")
                end_time = time.time()

                return task_name, {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration": end_time - start_time
                }
            except Exception as e:
                return task_name, {"success": False, "error": str(e)}

        with concurrent.futures.ProcessPoolExecutor(max_workers=min(len(aac_tasks), self.max_workers)) as executor:
            futures = {executor.submit(run_aac_task, task, name): name for task, name in aac_tasks}
            for future in concurrent.futures.as_completed(futures):
                task_name, result = future.result()
                results[task_name] = result
                status = "✅" if result["success"] else "❌"
                logger.info(f"{status} {task_name}: {result.get('duration', 0):.2f}s")

        return results

    def run_max_cpu_cycle(self) -> Dict[str, Any]:
        """Run one complete cycle of maximum CPU utilization"""
        logger.info("🚀 Starting maximum CPU utilization cycle")
        start_time = time.time()

        # Run all systems in parallel using ThreadPoolExecutor for I/O bound tasks
        # and ProcessPoolExecutor for CPU bound tasks
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all major tasks
            futures = {
                executor.submit(self.parallel_repo_analysis): "repo_analysis",
                executor.submit(self.parallel_portfolio_intelligence): "portfolio_intel",
                executor.submit(self.parallel_ncl_processing): "ncl_processing",
                executor.submit(self.parallel_aac_processing): "aac_processing"
            }

            results = {}
            for future in concurrent.futures.as_completed(futures):
                task_name = futures[future]
                try:
                    result = future.result()
                    results[task_name] = result
                    logger.info(f"✅ {task_name} completed")
                except Exception as e:
                    logger.error(f"❌ {task_name} failed: {str(e)}")
                    results[task_name] = {"error": str(e)}

        end_time = time.time()
        total_duration = end_time - start_time

        summary = {
            "total_duration": total_duration,
            "cpu_cores_utilized": self.max_workers,
            "tasks_completed": len([r for r in results.values() if not isinstance(r, dict) or "error" not in r]),
            "results": results
        }

        logger.info(f"🎯 CPU maximization cycle completed in {total_duration:.2f}s")
        return summary

def main():
    """Main CPU maximization function"""
    print("🔥 DIGITAL LABOUR CPU Maximizer")
    print("=" * 50)
    print(f"CPU Cores Available: {mp.cpu_count()}")
    print()

    maximizer = CPUMaximizer()

    try:
        result = maximizer.run_max_cpu_cycle()

        print("\n📊 Cycle Summary:")
        print(f"   Duration: {result['total_duration']:.2f}s")
        print(f"   CPU Cores Used: {result['cpu_cores_utilized']}")
        print(f"   Tasks Completed: {result['tasks_completed']}")

        print("\n📈 Performance Metrics:")
        for task_name, task_result in result['results'].items():
            if isinstance(task_result, dict) and "error" not in task_result:
                print(f"   {task_name}: {len(task_result)} subtasks")
            else:
                print(f"   {task_name}: Failed")

    except KeyboardInterrupt:
        print("\n⚠️  CPU maximization interrupted by user")
    except Exception as e:
        print(f"\n💥 CPU maximization failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()