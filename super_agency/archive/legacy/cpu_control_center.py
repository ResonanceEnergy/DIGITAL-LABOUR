#!/usr/bin/env python3
"""
DIGITAL LABOUR CPU Control Center
Master coordinator for maximum CPU utilization across all systems
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

import psutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CPUControlCenter:
    """Master control center for CPU maximization"""

    def __init__(self):
        self.root = Path(__file__).resolve().parent
        self.cpu_count = psutil.cpu_count()
        self.memory_gb = psutil.virtual_memory().total / (1024**3)

        logger.info(f"CPU Control Center initialized - {self.cpu_count} cores, {self.memory_gb:.1f}GB RAM")

    def get_system_info(self) -> Dict[str, Any]:
        """Get current system resource information"""
        return {
            "cpu_cores": self.cpu_count,
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_total_gb": self.memory_gb,
            "memory_used_gb": psutil.virtual_memory().used / (1024**3),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_free_gb": psutil.disk_usage('/').free / (1024**3) if os.name != 'nt' else psutil.disk_usage('C:\\').free / (1024**3)
        }

    def launch_cpu_maximizer(self) -> subprocess.Popen:
        """Launch the main CPU maximizer"""
        try:
            cmd = [sys.executable, str(self.root / "cpu_maximizer.py")]
            process = subprocess.Popen(
                cmd,
                cwd=self.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"✅ Launched CPU Maximizer (PID: {process.pid})")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to launch CPU Maximizer: {str(e)}")
            return None

    def launch_parallel_orchestrator(self) -> subprocess.Popen:
        """Launch the parallel orchestrator"""
        try:
            cmd = [sys.executable, str(self.root / "parallel_orchestrator.py")]
            process = subprocess.Popen(
                cmd,
                cwd=self.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"✅ Launched Parallel Orchestrator (PID: {process.pid})")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to launch Parallel Orchestrator: {str(e)}")
            return None

    def launch_portfolio_intel(self) -> subprocess.Popen:
        """Launch parallel portfolio intelligence"""
        try:
            cmd = [sys.executable, str(self.root / "ResonanceEnergy_BitRageLabour" / "agents" / "parallel_portfolio_intel.py")]
            process = subprocess.Popen(
                cmd,
                cwd=self.root / "ResonanceEnergy_BitRageLabour",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"✅ Launched Portfolio Intel (PID: {process.pid})")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to launch Portfolio Intel: {str(e)}")
            return None

    def launch_aac_system(self) -> subprocess.Popen:
        """Launch AAC accounting system"""
        try:
            cmd = [sys.executable, str(self.root / "repos" / "AAC" / "run_aac.py")]
            process = subprocess.Popen(
                cmd,
                cwd=self.root / "repos" / "AAC",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"✅ Launched AAC System (PID: {process.pid})")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to launch AAC System: {str(e)}")
            return None

    def launch_batch_processor(self, cycles: int = 10) -> subprocess.Popen:
        """Launch batch processor"""
        try:
            cmd = [sys.executable, str(self.root / "batch_processor.py"), "--cycles", str(cycles)]
            process = subprocess.Popen(
                cmd,
                cwd=self.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"✅ Launched Batch Processor (PID: {process.pid})")
            return process
        except Exception as e:
            logger.error(f"❌ Failed to launch Batch Processor: {str(e)}")
            return None

    def monitor_processes(self, processes: List[subprocess.Popen], duration_seconds: int = 300) -> Dict[str, Any]:
        """Monitor running processes and collect performance data"""
        logger.info(f"📊 Monitoring {len(processes)} processes for {duration_seconds}s")

        start_time = time.time()
        end_time = start_time + duration_seconds

        monitoring_data = []

        while time.time() < end_time and processes:
            current_time = time.time()

            # Get system stats
            system_info = self.get_system_info()

            # Check process status
            active_processes = []
            for proc in processes:
                if proc.poll() is None:  # Still running
                    active_processes.append(proc)

            processes[:] = active_processes  # Update list

            monitoring_data.append({
                "timestamp": current_time,
                "active_processes": len(active_processes),
                "system_info": system_info
            })

            logger.info(f"📈 Active: {len(active_processes)} | CPU: {system_info['cpu_percent']:.1f}% | RAM: {system_info['memory_percent']:.1f}%")

            time.sleep(5)  # Monitor every 5 seconds

        # Cleanup remaining processes
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except:
                proc.kill()

        return {
            "monitoring_duration": time.time() - start_time,
            "data_points": len(monitoring_data),
            "peak_cpu_percent": max(d["system_info"]["cpu_percent"] for d in monitoring_data),
            "average_cpu_percent": sum(d["system_info"]["cpu_percent"] for d in monitoring_data) / len(monitoring_data),
            "peak_memory_percent": max(d["system_info"]["memory_percent"] for d in monitoring_data),
            "monitoring_data": monitoring_data
        }

    def run_maximum_cpu_mode(self, duration_minutes: int = 10) -> Dict[str, Any]:
        """Run maximum CPU utilization mode"""
        logger.info("🚀 Starting MAXIMUM CPU MODE")
        print("🔥 MAXIMUM CPU UTILIZATION MODE ACTIVATED")
        print("=" * 60)

        duration_seconds = duration_minutes * 60

        # Launch all available systems
        processes = []

        launchers = [
            ("CPU Maximizer", self.launch_cpu_maximizer),
            ("Parallel Orchestrator", self.launch_parallel_orchestrator),
            ("Portfolio Intel", self.launch_portfolio_intel),
            ("AAC System", self.launch_aac_system),
            ("Batch Processor", lambda: self.launch_batch_processor(cycles=50))
        ]

        for name, launcher in launchers:
            proc = launcher()
            if proc:
                processes.append(proc)
            time.sleep(1)  # Stagger launches

        if not processes:
            logger.error("❌ No processes launched successfully")
            return {"error": "No processes launched"}

        logger.info(f"✅ Launched {len(processes)} processes")

        # Monitor performance
        monitoring_results = self.monitor_processes(processes, duration_seconds)

        # Calculate final statistics
        final_stats = self.get_system_info()

        results = {
            "mode": "maximum_cpu",
            "duration_minutes": duration_minutes,
            "processes_launched": len(processes),
            "final_system_stats": final_stats,
            "monitoring_results": monitoring_results,
            "total_computation_cycles": monitoring_results["data_points"] * len(processes),
            "efficiency_score": monitoring_results["average_cpu_percent"] / 100.0
        }

        logger.info("🎯 Maximum CPU mode completed")
        return results

    def run_balanced_mode(self, duration_minutes: int = 15) -> Dict[str, Any]:
        """Run balanced CPU utilization mode"""
        logger.info("⚖️ Starting BALANCED MODE")
        print("⚖️ BALANCED CPU UTILIZATION MODE")
        print("=" * 50)

        duration_seconds = duration_minutes * 60

        # Launch systems with controlled parallelism
        processes = []

        # Phase 1: Core systems
        core_launchers = [
            self.launch_cpu_maximizer,
            self.launch_parallel_orchestrator
        ]

        for launcher in core_launchers:
            proc = launcher()
            if proc:
                processes.append(proc)
            time.sleep(2)

        # Phase 2: Analysis systems (after core systems are running)
        time.sleep(10)
        analysis_launchers = [
            self.launch_portfolio_intel,
            self.launch_aac_system
        ]

        for launcher in analysis_launchers:
            proc = launcher()
            if proc:
                processes.append(proc)
            time.sleep(3)

        if not processes:
            return {"error": "No processes launched"}

        # Monitor with balanced settings
        monitoring_results = self.monitor_processes(processes, duration_seconds)

        final_stats = self.get_system_info()

        return {
            "mode": "balanced",
            "duration_minutes": duration_minutes,
            "processes_launched": len(processes),
            "final_system_stats": final_stats,
            "monitoring_results": monitoring_results
        }

    def run_diagnostic_mode(self) -> Dict[str, Any]:
        """Run diagnostic mode to test all systems individually"""
        logger.info("🔍 Starting DIAGNOSTIC MODE")
        print("🔍 DIAGNOSTIC MODE - Testing All Systems")
        print("=" * 50)

        systems = [
            ("CPU Maximizer", self.launch_cpu_maximizer),
            ("Parallel Orchestrator", self.launch_parallel_orchestrator),
            ("Portfolio Intel", self.launch_portfolio_intel),
            ("AAC System", self.launch_aac_system)
        ]

        results = {}

        for name, launcher in systems:
            print(f"Testing {name}...")
            start_time = time.time()

            proc = launcher()
            if proc:
                # Wait for process to complete or timeout
                try:
                    proc.wait(timeout=30)
                    success = proc.returncode == 0
                    duration = time.time() - start_time

                    # Get output
                    stdout, stderr = proc.communicate()

                    results[name] = {
                        "success": success,
                        "duration": duration,
                        "return_code": proc.returncode,
                        "stdout_preview": stdout[:500] if stdout else "",
                        "stderr_preview": stderr[:500] if stderr else ""
                    }

                    status = "✅" if success else "❌"
                    print(f"  {status} {name}: {duration:.2f}s")

                except subprocess.TimeoutExpired:
                    proc.kill()
                    results[name] = {"success": False, "error": "Timeout", "duration": 30}
                    print(f"  ⏰ {name}: Timeout (30s)")
            else:
                results[name] = {"success": False, "error": "Failed to launch"}
                print(f"  ❌ {name}: Failed to launch")

            time.sleep(2)  # Brief pause between tests

        return {
            "mode": "diagnostic",
            "systems_tested": len(systems),
            "results": results
        }

def save_results(results: Dict[str, Any], filename: str) -> Path:
    """Save results to JSON file"""
    results_dir = Path("cpu_results")
    results_dir.mkdir(exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = results_dir / f"{filename}_{timestamp}.json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"Results saved to {filepath}")
    return filepath

def main():
    """Main CPU Control Center function"""
    parser = argparse.ArgumentParser(description="DIGITAL LABOUR CPU Control Center")
    parser.add_argument("mode", choices=["maximum", "balanced", "diagnostic"], help="Operation mode")
    parser.add_argument("--duration", type=int, default=10, help="Duration in minutes (for maximum/balanced modes)")
    parser.add_argument("--save-results", action="store_true", help="Save results to file")

    args = parser.parse_args()

    print("🎛️ DIGITAL LABOUR CPU Control Center")
    print("=" * 50)

    system_info = CPUControlCenter().get_system_info()
    print(f"System: {system_info['cpu_cores']} cores, {system_info['memory_total_gb']:.1f}GB RAM")
    print(f"Current CPU: {system_info['cpu_percent']:.1f}%, RAM: {system_info['memory_percent']:.1f}%")
    print()

    control_center = CPUControlCenter()

    try:
        if args.mode == "maximum":
            results = control_center.run_maximum_cpu_mode(args.duration)
        elif args.mode == "balanced":
            results = control_center.run_balanced_mode(args.duration)
        elif args.mode == "diagnostic":
            results = control_center.run_diagnostic_mode()

        # Display results
        print("📊 Results:")
        if "error" in results:
            print(f"❌ Error: {results['error']}")
        else:
            print(f"Mode: {results.get('mode', 'unknown')}")
            print(f"Duration: {results.get('duration_minutes', 'N/A')} minutes")
            print(f"Processes: {results.get('processes_launched', 'N/A')}")

            if "monitoring_results" in results:
                mon = results["monitoring_results"]
                print(f"Monitoring Points: {mon['data_points']}")
                print(f"Peak CPU: {mon['peak_cpu_percent']:.1f}%")
                print(f"Average CPU: {mon['average_cpu_percent']:.1f}%")

            if args.save_results:
                results_file = save_results(results, f"cpu_control_center_{args.mode}")
                print(f"Results saved: {results_file}")

    except KeyboardInterrupt:
        print("\n⚠️  CPU Control Center interrupted by user")
    except Exception as e:
        print(f"\n💥 CPU Control Center failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
