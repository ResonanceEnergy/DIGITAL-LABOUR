#!/usr/bin/env python3
"""
Super Agency Performance Monitoring Script
24-48 Hour Validation of System Optimizations
Monitors QUASMEM, agent health, and system performance
"""

import time
import json
import requests
import psutil
from datetime import datetime, timedelta
import threading
import sys
import os
from pathlib import Path

class PerformanceMonitor:
    """Monitor system performance over extended period"""

    def __init__(self, duration_hours=24):
        self.duration = timedelta(hours=duration_hours)
        self.start_time = datetime.now()
        self.end_time = self.start_time + self.duration
        self.monitoring_active = False
        self.metrics_data = []
        self.alerts = []

        # Create monitoring directory
        self.monitor_dir = Path("performance_monitoring")
        self.monitor_dir.mkdir(exist_ok=True)

        print(f"[START] Performance Monitor initialized for {duration_hours} hours")
        print(f"[STATS] Monitoring from {self.start_time} to {self.end_time}")

    def collect_system_metrics(self):
        """Collect comprehensive system metrics"""
        try:
            # System metrics
            system = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')

            # Network metrics
            net = psutil.net_io_counters()
            network_bytes = net.bytes_sent + net.bytes_recv

            # Process metrics
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024**2)

            return {
                'timestamp': datetime.now().isoformat(),
                'system_memory_percent': system.percent,
                'system_memory_used_gb': system.used / (1024**3),
                'system_memory_available_gb': system.available / (1024**3),
                'cpu_percent': cpu,
                'disk_used_percent': disk.percent,
                'disk_used_gb': disk.used / (1024**3),
                'network_total_bytes': network_bytes,
                'process_memory_mb': memory_mb,
                'process_cpu_percent': process.cpu_percent()
            }
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

    def collect_quasmem_metrics(self):
        """Collect QUASMEM optimization metrics"""
        try:
            response = requests.get('http://localhost:8080/api/comprehensive-monitoring', timeout=5)
            if response.status_code == 200:
                data = response.json()
                quasmem = data.get('components', {}).get('quasmem_optimization', {})

                return {
                    'timestamp': datetime.now().isoformat(),
                    'quasmem_status': quasmem.get('status', 'unknown'),
                    'quasmem_message': quasmem.get('message', ''),
                    'pools_used_mb': quasmem.get('details', {}).get('pools', {}).get('current_usage', 0),
                    'pools_available_mb': quasmem.get('details', {}).get('pools', {}).get('available', 0),
                    'compression_ratio': quasmem.get('details', {}).get('compression_ratio', 1.0)
                }
            else:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'error': f'HTTP {response.status_code}'
                }
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

    def collect_agent_metrics(self):
        """Collect agent health and performance metrics"""
        try:
            response = requests.get('http://localhost:8080/api/agents', timeout=5)
            if response.status_code == 200:
                data = response.json()
                agents = data.get('agents', {})

                # Collect metrics for key agents
                agent_summary = {}
                total_health = 0
                agent_count = 0

                key_agents = ['common', 'repo_sentry', 'council', 'orchestrator', 'andrew_huberman', 'elon_musk']

                for agent_name in key_agents:
                    if agent_name in agents:
                        agent = agents[agent_name]
                        health = agent.get('health_score', 0)
                        total_health += health
                        agent_count += 1

                        agent_summary[agent_name] = {
                            'health_score': health,
                            'performance_trend': agent.get('performance_trend', 'unknown'),
                            'status': agent.get('status', 'unknown')
                        }

                return {
                    'timestamp': datetime.now().isoformat(),
                    'agent_summary': agent_summary,
                    'average_health_score': total_health / max(agent_count, 1),
                    'total_agents_monitored': agent_count,
                    'healthy_agents': sum(1 for a in agent_summary.values() if a['health_score'] >= 80),
                    'warning_agents': sum(1 for a in agent_summary.values() if 60 <= a['health_score'] < 80),
                    'critical_agents': sum(1 for a in agent_summary.values() if a['health_score'] < 60)
                }
            else:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'error': f'HTTP {response.status_code}'
                }
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

    def check_alerts(self, system_data, quasmem_data, agent_data):
        """Check for performance alerts"""
        alerts = []

        # System alerts
        if system_data.get('system_memory_percent', 0) > 95:
            alerts.append(f"CRITICAL: System memory usage at {system_data['system_memory_percent']:.1f}%")

        if system_data.get('cpu_percent', 0) > 90:
            alerts.append(f"WARNING: High CPU usage at {system_data['cpu_percent']:.1f}%")

        # QUASMEM alerts
        if quasmem_data.get('pools_used_mb', 0) == 0:
            alerts.append("WARNING: QUASMEM pools not actively used")

        # Agent alerts
        avg_health = agent_data.get('average_health_score', 100)
        if avg_health < 70:
            alerts.append(f"CRITICAL: Average agent health score below 70: {avg_health:.1f}")

        critical_agents = agent_data.get('critical_agents', 0)
        if critical_agents > 0:
            alerts.append(f"CRITICAL: {critical_agents} agents in critical health state")

        return alerts

    def save_metrics(self):
        """Save collected metrics to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_metrics_{timestamp}.json"

        data = {
            'monitoring_period': {
                'start': self.start_time.isoformat(),
                'end': datetime.now().isoformat(),
                'duration_hours': (datetime.now() - self.start_time).total_seconds() / 3600
            },
            'metrics': self.metrics_data,
            'alerts': self.alerts,
            'summary': self.generate_summary()
        }

        filepath = self.monitor_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"[SAVE] Metrics saved to {filepath}")

    def generate_summary(self):
        """Generate performance summary"""
        if not self.metrics_data:
            return {"error": "No metrics collected"}

        # Calculate averages and trends
        system_memory_avg = sum(m['system']['system_memory_percent'] for m in self.metrics_data if 'system' in m) / len(self.metrics_data)
        quasmem_usage_avg = sum(m['quasmem']['pools_used_mb'] for m in self.metrics_data if 'quasmem' in m and 'pools_used_mb' in m['quasmem']) / len([m for m in self.metrics_data if 'quasmem' in m])
        agent_health_avg = sum(m['agents']['average_health_score'] for m in self.metrics_data if 'agents' in m) / len([m for m in self.metrics_data if 'agents' in m])

        return {
            'total_measurements': len(self.metrics_data),
            'average_system_memory_percent': system_memory_avg,
            'average_quasmem_usage_mb': quasmem_usage_avg,
            'average_agent_health_score': agent_health_avg,
            'total_alerts': len(self.alerts),
            'monitoring_effectiveness': 'good' if len(self.metrics_data) > 10 else 'insufficient'
        }

    def run_monitoring_cycle(self):
        """Run one monitoring cycle"""
        timestamp = datetime.now()

        # Collect all metrics
        system_data = self.collect_system_metrics()
        quasmem_data = self.collect_quasmem_metrics()
        agent_data = self.collect_agent_metrics()

        # Check for alerts
        cycle_alerts = self.check_alerts(system_data, quasmem_data, agent_data)
        if cycle_alerts:
            self.alerts.extend(cycle_alerts)
            for alert in cycle_alerts:
                print(f"[ALERT] {timestamp}: {alert}")

        # Store metrics
        metrics_entry = {
            'timestamp': timestamp.isoformat(),
            'system': system_data,
            'quasmem': quasmem_data,
            'agents': agent_data,
            'alerts': cycle_alerts
        }

        self.metrics_data.append(metrics_entry)

        print(f"[STATS] {timestamp}: System={system_data.get('system_memory_percent', 0):.1f}%, QUASMEM={quasmem_data.get('pools_used_mb', 0):.1f}MB, Agents={agent_data.get('average_health_score', 0):.1f}")

    def start_monitoring(self, interval_minutes=15):
        """Start the monitoring process"""
        self.monitoring_active = True
        interval_seconds = interval_minutes * 60

        print(f"[TARGET] Starting performance monitoring (interval: {interval_minutes} minutes)")

        cycle_count = 0
        while self.monitoring_active and datetime.now() < self.end_time:
            try:
                self.run_monitoring_cycle()
                cycle_count += 1

                # Save intermediate results every 10 cycles
                if cycle_count % 10 == 0:
                    self.save_metrics()

                # Wait for next cycle
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\n[STOP] Monitoring interrupted by user")
                break
            except Exception as e:
                print(f"[ERROR] Monitoring error: {e}")
                time.sleep(60)  # Wait a minute before retrying

        # Final save
        self.save_metrics()
        print("[FINISH] Performance monitoring completed")
        self.print_final_report()

    def stop_monitoring(self):
        """Stop the monitoring process"""
        self.monitoring_active = False
        print("[STOP] Monitoring stop requested")

    def print_final_report(self):
        """Print final performance report"""
        print("\n" + "="*60)
        print("[REPORT] PERFORMANCE MONITORING REPORT")
        print("="*60)

        if not self.metrics_data:
            print("[ERROR] No metrics collected")
            return

        summary = self.generate_summary()

        print(f"[TIME] Monitoring Duration: {summary['total_measurements']} measurements")
        print(f"[MEMORY] System Memory: {summary['average_system_memory_percent']:.1f}% average")
        print(f"[BRAIN] QUASMEM Usage: {summary['average_quasmem_usage_mb']:.1f}MB average")
        print(f"[AGENT] Agent Health: {summary['average_agent_health_score']:.1f} average")
        print(f"[ALERTS] Total Alerts: {summary['total_alerts']}")

        # Performance assessment
        print("\n[TARGET] PERFORMANCE ASSESSMENT:")
        if summary['average_system_memory_percent'] < 85:
            print("[OK] System memory usage is optimal")
        else:
            print("[WARNING] System memory usage is high - consider optimization")

        if summary['average_quasmem_usage_mb'] > 50:
            print("[OK] QUASMEM optimization is active and effective")
        else:
            print("[WARNING] QUASMEM usage is low - verify pool allocation")

        if summary['average_agent_health_score'] > 80:
            print("[OK] Agent health is excellent")
        elif summary['average_agent_health_score'] > 60:
            print("[WARNING] Agent health needs attention")
        else:
            print("[CRITICAL] Agent health is critical")

        print("\n[RECOMMENDATIONS] RECOMMENDATIONS:")
        if summary['total_alerts'] == 0:
            print("[OK] System performing optimally - proceed with agent workflow development")
        else:
            print(f"[WARNING] {summary['total_alerts']} alerts detected - review and address before proceeding")

        print("="*60)

def main():
    """Main monitoring function"""
    import argparse

    parser = argparse.ArgumentParser(description='Super Agency Performance Monitor')
    parser.add_argument('--hours', type=int, default=24, help='Monitoring duration in hours')
    parser.add_argument('--interval', type=int, default=15, help='Monitoring interval in minutes')

    args = parser.parse_args()

    monitor = PerformanceMonitor(duration_hours=args.hours)
    monitor.start_monitoring(interval_minutes=args.interval)

if __name__ == '__main__':
    main()
