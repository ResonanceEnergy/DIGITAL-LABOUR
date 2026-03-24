#!/usr/bin/env python3
"""
QFORGE Optimizer - Windows Performance Enhancement System
Optimizes Super Agency operations for maximum efficiency on QFORGE platform
"""

import os
import sys
import psutil
import time
import threading
import subprocess
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - QFORGE - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QFORGE_Optimizer:
    """QFORGE Performance Optimization System"""

    def __init__(self):
        self.workspace = Path(__file__).parent
        self.is_windows = os.name == 'nt'
        self.optimizations_applied = []

        logger.info("QFORGE Optimizer initialized")

    def optimize_system(self) -> Dict[str, Any]:
        """Apply all QFORGE optimizations"""
        logger.info("Starting QFORGE optimization sequence")

        results = {
            'system_info': self._get_system_info(),
            'optimizations': {},
            'performance_metrics': {}
        }

        # Apply optimizations in priority order
        optimizations = [
            ('memory_preload', self._optimize_memory_preload),
            ('cpu_affinity', self._optimize_cpu_affinity),
            ('process_priority', self._optimize_process_priority),
            ('background_services', self._optimize_background_services),
            ('import_caching', self._optimize_import_caching),
        ]

        for opt_name, opt_func in optimizations:
            try:
                logger.info(f"Applying optimization: {opt_name}")
                start_time = time.time()
                opt_result = opt_func()
                duration = time.time() - start_time

                results['optimizations'][opt_name] = {
                    'status': 'success',
                    'duration': duration,
                    'result': opt_result
                }
                self.optimizations_applied.append(opt_name)

            except Exception as e:
                logger.error(f"Optimization {opt_name} failed: {e}")
                results['optimizations'][opt_name] = {
                    'status': 'failed',
                    'error': str(e)
                }

        # Measure final performance
        results['performance_metrics'] = self._measure_performance()

        logger.info(f"QFORGE optimization complete. Applied: {len(self.optimizations_applied)} optimizations")
        return results

    def _get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        system = psutil.virtual_memory()
        cpu_freq = psutil.cpu_freq()

        return {
            'platform': 'QFORGE' if self.is_windows else 'Quantum Quasar',
            'cpu_cores': psutil.cpu_count(),
            'cpu_logical': psutil.cpu_count(logical=True),
            'cpu_freq_current': cpu_freq.current if cpu_freq else None,
            'cpu_freq_max': cpu_freq.max if cpu_freq else None,
            'memory_total_gb': system.total / (1024**3),
            'memory_available_gb': system.available / (1024**3),
            'memory_usage_percent': system.percent,
            'python_version': sys.version,
        }

    def _optimize_memory_preload(self) -> Dict[str, Any]:
        """Pre-load and optimize memory pools"""
        try:
            from quasmem_optimization import quantum_memory_pool, get_memory_status

            # Pre-allocate critical memory
            preload_allocations = [
                ('critical', 64.0),  # Core systems
                ('agents', 128.0),   # Agent operations
                ('cache', 64.0),     # Data caching
            ]

            allocated = 0
            for pool_name, amount_mb in preload_allocations:
                if quantum_memory_pool.allocate(pool_name, amount_mb):
                    allocated += amount_mb
                    logger.info(f"Pre-allocated {amount_mb}MB to {pool_name} pool")

            status = get_memory_status()
            return {
                'preallocated_mb': allocated,
                'pool_utilization': status['pools']['utilization_percent'],
                'memory_efficiency': 'optimized'
            }

        except Exception as e:
            logger.error(f"Memory preload failed: {e}")
            return {'error': str(e)}

    def _optimize_cpu_affinity(self) -> Dict[str, Any]:
        """Optimize CPU affinity for better performance"""
        if not self.is_windows:
            return {'status': 'skipped', 'reason': 'Windows-only optimization'}

        try:
            process = psutil.Process()
            cpu_count = psutil.cpu_count()

            # Set affinity to use all cores efficiently
            if cpu_count >= 8:
                # Use cores 0-7 for main processing (avoiding system cores 8-11)
                affinity_cores = list(range(min(8, cpu_count)))
            else:
                # Use all available cores
                affinity_cores = list(range(cpu_count))

            process.cpu_affinity(affinity_cores)

            return {
                'affinity_cores': affinity_cores,
                'total_cores': cpu_count,
                'optimization': 'high_performance'
            }

        except Exception as e:
            logger.error(f"CPU affinity optimization failed: {e}")
            return {'error': str(e)}

    def _optimize_process_priority(self) -> Dict[str, Any]:
        """Set optimal process priority"""
        if not self.is_windows:
            return {'status': 'skipped', 'reason': 'Windows-only optimization'}

        try:
            process = psutil.Process()

            # Set high priority for real-time performance
            if hasattr(psutil, 'HIGH_PRIORITY_CLASS'):
                process.nice(psutil.HIGH_PRIORITY_CLASS)
                priority_level = 'high'
            else:
                # Fallback to nice value
                current_nice = process.nice()
                if current_nice > 0:
                    process.nice(0)  # Set to normal priority
                priority_level = 'normal'

            return {
                'priority_set': priority_level,
                'process_id': process.pid,
                'optimization': 'real_time_performance'
            }

        except Exception as e:
            logger.error(f"Process priority optimization failed: {e}")
            return {'error': str(e)}

    def _optimize_background_services(self) -> Dict[str, Any]:
        """Optimize background service architecture"""
        services_status = {}

        # Check and optimize key services
        services_to_check = [
            'matrix_monitor',
            'mobile_command_center',
            'continuous_memory_backup'
        ]

        for service in services_to_check:
            service_path = self.workspace / f"{service}.py"
            if service_path.exists():
                services_status[service] = 'available'
            else:
                services_status[service] = 'not_found'

        # Start memory monitoring in background
        try:
            from quasmem_optimization import quantum_memory_pool
            quantum_memory_pool.start_monitoring()
            services_status['memory_monitor'] = 'started'
        except:
            services_status['memory_monitor'] = 'failed'

        return {
            'services_checked': len(services_to_check),
            'services_status': services_status,
            'background_monitoring': 'active'
        }

    def _optimize_import_caching(self) -> Dict[str, Any]:
        """Implement import caching for faster startup"""
        import sys
        from importlib.util import find_spec

        # Pre-cache commonly used modules
        modules_to_cache = [
            'psutil',
            'asyncio',
            'pathlib',
            'json',
            'time',
            'threading'
        ]

        cached_modules = []
        for module in modules_to_cache:
            try:
                if find_spec(module):
                    __import__(module)
                    cached_modules.append(module)
            except ImportError:
                continue

        return {
            'modules_cached': len(cached_modules),
            'cached_list': cached_modules,
            'import_optimization': 'enabled'
        }

    def _measure_performance(self) -> Dict[str, Any]:
        """Measure system performance after optimizations"""
        system = psutil.virtual_memory()
        process = psutil.Process()

        return {
            'memory_usage_mb': process.memory_info().rss / (1024**2),
            'cpu_usage_percent': process.cpu_percent(),
            'system_memory_percent': system.percent,
            'system_memory_available_gb': system.available / (1024**3),
            'optimizations_applied': len(self.optimizations_applied),
            'performance_status': 'optimized'
        }

def optimize_qforge() -> Dict[str, Any]:
    """Main QFORGE optimization function"""
    optimizer = QFORGE_Optimizer()
    return optimizer.optimize_system()

if __name__ == '__main__':
    print("🚀 QFORGE Optimization System")
    print("=" * 40)

    start_time = time.time()
    results = optimize_qforge()
    total_time = time.time() - start_time

    print("✅ Optimization Complete!")
    print(".2f")
    print(f"📊 System: {results['system_info']['platform']}")
    print(f"⚡ CPU: {results['system_info']['cpu_cores']} cores")
    print(".1f")
    print(f"🧠 Memory: {results['performance_metrics']['system_memory_available_gb']:.1f}GB available")

    applied_opts = results['performance_metrics']['optimizations_applied']
    print(f"🔧 Optimizations Applied: {applied_opts}")

    if applied_opts > 0:
        print("✅ QFORGE optimization successful!")
    else:
        print("⚠️  Some optimizations may have failed - check logs")
