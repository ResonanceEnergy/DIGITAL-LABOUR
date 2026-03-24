#!/usr/bin/env python3
"""
DIGITAL LABOUR Batch Processor
Run multiple CPU maximization cycles in parallel for maximum throughput
"""

import json
import logging
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BatchProcessor:
    """Batch processor for running multiple DIGITAL LABOUR operations in parallel"""

    def __init__(self, batch_size: int = 4):
        self.root = Path(__file__).resolve().parent
        self.batch_size = batch_size
        self.results_dir = self.root / "batch_results"
        self.results_dir.mkdir(exist_ok=True)

    def run_single_cycle(self, cycle_id: int) -> Dict[str, Any]:
        """Run a single CPU maximization cycle"""
        logger.info(f"Starting cycle {cycle_id}")

        start_time = time.time()

        try:
            # Run CPU maximizer
            result = subprocess.run(
                [sys.executable, str(self.root / "cpu_maximizer.py")],
                capture_output=True,
                text=True,
                cwd=self.root,
                timeout=600  # 10 minute timeout per cycle
            )

            end_time = time.time()

            return {
                "cycle_id": cycle_id,
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": end_time - start_time,
                "timestamp": time.time()
            }

        except subprocess.TimeoutExpired:
            end_time = time.time()
            return {
                "cycle_id": cycle_id,
                "success": False,
                "error": "Timeout after 600 seconds",
                "duration": end_time - start_time,
                "timestamp": time.time()
            }
        except Exception as e:
            end_time = time.time()
            return {
                "cycle_id": cycle_id,
                "success": False,
                "error": str(e),
                "duration": end_time - start_time,
                "timestamp": time.time()
            }

    def run_batch_cycles(self, num_cycles: int) -> List[Dict[str, Any]]:
        """Run multiple cycles in parallel batches"""
        logger.info(f"🚀 Starting batch processing of {num_cycles} cycles in batches of {self.batch_size}")

        all_results = []

        # Process in batches to avoid overwhelming the system
        for batch_start in range(0, num_cycles, self.batch_size):
            batch_end = min(batch_start + self.batch_size, num_cycles)
            batch_size_actual = batch_end - batch_start

            logger.info(f"Processing batch {batch_start//self.batch_size + 1}: cycles {batch_start + 1}-{batch_end}")

            with ProcessPoolExecutor(max_workers=batch_size_actual) as executor:
                # Submit batch of cycles
                futures = {
                    executor.submit(self.run_single_cycle, cycle_id): cycle_id
                    for cycle_id in range(batch_start + 1, batch_end + 1)
                }

                # Collect results as they complete
                for future in as_completed(futures):
                    cycle_id = futures[future]
                    try:
                        result = future.result()
                        all_results.append(result)

                        status = "✅" if result["success"] else "❌"
                        duration = result.get("duration", 0)
                        logger.info(f"{status} Cycle {cycle_id}: {duration:.2f}s")

                    except Exception as e:
                        logger.error(f"Failed to get result for cycle {cycle_id}: {str(e)}")
                        all_results.append({
                            "cycle_id": cycle_id,
                            "success": False,
                            "error": str(e),
                            "timestamp": time.time()
                        })

        return sorted(all_results, key=lambda x: x["cycle_id"])

    def run_continuous_processing(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Run continuous processing for specified duration"""
        logger.info(f"🔄 Starting continuous processing for {duration_minutes} minutes")

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        cycles_completed = 0
        results = []

        while time.time() < end_time:
            remaining_time = end_time - time.time()
            logger.info(f"Time remaining: {remaining_time/60:.1f} minutes, cycles completed: {cycles_completed}")

            # Run one cycle at a time to avoid resource exhaustion
            result = self.run_single_cycle(cycles_completed + 1)
            results.append(result)
            cycles_completed += 1

            # Brief pause between cycles
            time.sleep(1)

        total_duration = time.time() - start_time

        return {
            "mode": "continuous",
            "target_duration_minutes": duration_minutes,
            "actual_duration_seconds": total_duration,
            "cycles_completed": cycles_completed,
            "cycles_per_minute": cycles_completed / (total_duration / 60),
            "results": results
        }

    def save_batch_results(self, results: List[Dict[str, Any]], mode: str = "batch") -> Path:
        """Save batch processing results"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{mode}_results_{timestamp}.json"
        results_file = self.results_dir / filename

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Batch results saved to {results_file}")
        return results_file

    def analyze_performance(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze batch processing performance"""
        if not results:
            return {"error": "No results to analyze"}

        successful_cycles = sum(1 for r in results if r.get("success", False))
        total_cycles = len(results)
        total_duration = sum(r.get("duration", 0) for r in results)

        durations = [r.get("duration", 0) for r in results if r.get("duration", 0) > 0]

        analysis = {
            "total_cycles": total_cycles,
            "successful_cycles": successful_cycles,
            "failed_cycles": total_cycles - successful_cycles,
            "success_rate": successful_cycles / total_cycles if total_cycles > 0 else 0,
            "total_duration_seconds": total_duration,
            "average_duration_per_cycle": total_duration / total_cycles if total_cycles > 0 else 0,
            "cycles_per_second": total_cycles / total_duration if total_duration > 0 else 0
        }

        if durations:
            analysis.update({
                "min_duration": min(durations),
                "max_duration": max(durations),
                "median_duration": sorted(durations)[len(durations)//2]
            })

        return analysis

def main():
    """Main batch processing function"""
    import argparse

    parser = argparse.ArgumentParser(description="DIGITAL LABOUR Batch Processor")
    parser.add_argument("--cycles", type=int, default=10, help="Number of cycles to run")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size for parallel processing")
    parser.add_argument("--continuous", type=int, help="Run continuous processing for N minutes")
    parser.add_argument("--mode", choices=["batch", "continuous"], default="batch", help="Processing mode")

    args = parser.parse_args()

    print("🔥 DIGITAL LABOUR Batch Processor")
    print("=" * 50)
    print(f"Mode: {args.mode}")
    print(f"Batch Size: {args.batch_size}")

    processor = BatchProcessor(batch_size=args.batch_size)

    try:
        if args.mode == "continuous" or args.continuous:
            duration = args.continuous or 60
            print(f"Continuous Mode: {duration} minutes")
            results = processor.run_continuous_processing(duration_minutes=duration)
            results_file = processor.save_batch_results(results, "continuous")

            print("📊 Continuous Processing Results:")
            print(f"   Duration: {results['actual_duration_seconds']/60:.1f} minutes")
            print(f"   Cycles Completed: {results['cycles_completed']}")
            print(f"   Cycles/Minute: {results['cycles_per_minute']:.2f}")
            print(f"   Results Saved: {results_file}")

        else:
            print(f"Batch Mode: {args.cycles} cycles")
            results = processor.run_batch_cycles(args.cycles)
            results_file = processor.save_batch_results(results, "batch")

            analysis = processor.analyze_performance(results)

            print("📊 Batch Processing Results:")
            print(f"   Total Cycles: {analysis['total_cycles']}")
            print(f"   Successful: {analysis['successful_cycles']}")
            print(f"   Failed: {analysis['failed_cycles']}")
            print(f"   Success Rate: {analysis['success_rate']*100:.1f}%")
            print(f"   Total Duration: {analysis['total_duration_seconds']:.2f}s")
            print(f"   Avg Duration/Cycle: {analysis['average_duration_per_cycle']:.2f}s")
            print(f"   Cycles/Second: {analysis['cycles_per_second']:.3f}")
            print(f"   Results Saved: {results_file}")

    except KeyboardInterrupt:
        print("\n⚠️  Batch processing interrupted by user")
    except Exception as e:
        print(f"\n💥 Batch processing failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
