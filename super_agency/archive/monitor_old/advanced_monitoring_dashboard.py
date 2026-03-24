#!/usr/bin/env python3
"""
Super Agency Advanced Monitoring Dashboard
Modern monitoring solution with Prometheus-style metrics and Grafana visualization
"""

import json
import time
import psutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedMonitoringDashboard:
    """Advanced monitoring dashboard with modern metrics collection"""

    def __init__(self):
        self.metrics_store = {}
        self.alerts = []
        self.projects = self.load_projects()
        self.monitoring_thread = None
        self.is_monitoring = False

    def load_projects(self) -> List[Dict]:
        """Load all active projects from portfolio"""
        try:
            with open('portfolio.json', 'r') as f:
                data = json.load(f)
                return data.get('repositories', [])
        except Exception as e:
            logger.error(f"Failed to load projects: {e}")
            return []

    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system metrics"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=1),
                "cores": psutil.cpu_count(),
                "frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                "per_core": psutil.cpu_percent(percpu=True)
            },
            "memory": {
                "total_gb": psutil.virtual_memory().total / (1024**3),
                "used_gb": psutil.virtual_memory().used / (1024**3),
                "available_gb": psutil.virtual_memory().available / (1024**3),
                "usage_percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total_gb": psutil.disk_usage('/').total / (1024**3),
                "used_gb": psutil.disk_usage('/').used / (1024**3),
                "free_gb": psutil.disk_usage('/').free / (1024**3),
                "usage_percent": psutil.disk_usage('/').percent
            },
            "network": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
                "packets_sent": psutil.net_io_counters().packets_sent,
                "packets_recv": psutil.net_io_counters().packets_recv
            }
        }

    def collect_project_metrics(self) -> Dict[str, Any]:
        """Collect metrics for each project"""
        project_metrics = {}

        for project in self.projects:
            name = project['name']
            project_metrics[name] = {
                "name": name,
                "visibility": project.get('visibility', 'unknown'),
                "tier": project.get('tier', 'unknown'),
                "autonomy_level": project.get('autonomy_level', 'unknown'),
                "risk_tier": project.get('risk_tier', 'unknown'),
                "category": project.get('category', 'unknown'),
                "last_updated": project.get('last_updated', 'unknown'),
                "language_hint": project.get('language_hint', 'unknown'),
                "status": self.check_project_status(name)
            }

        return project_metrics

    def check_project_status(self, project_name: str) -> Dict[str, Any]:
        """Check the status of a specific project"""
        # Check if project directory exists
        project_path = Path('repos') / project_name
        if project_path.exists():
            # Check for recent activity
            try:
                # Get last commit date
                result = subprocess.run(
                    ['git', 'log', '-1', '--format=%ct'],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    timestamp = int(result.stdout.strip())
                    last_commit = datetime.fromtimestamp(timestamp)
                    days_since_commit = (datetime.now() - last_commit).days
                else:
                    days_since_commit = -1
            except:
                days_since_commit = -1

            return {
                "exists": True,
                "has_git": True,
                "days_since_commit": days_since_commit,
                "size_mb": sum(f.stat().st_size for f in project_path.rglob('*') if f.is_file()) / (1024**2)
            }
        else:
            return {
                "exists": False,
                "has_git": False,
                "days_since_commit": -1,
                "size_mb": 0
            }

    def collect_agent_metrics(self) -> Dict[str, Any]:
        """Collect metrics from running agents"""
        agent_metrics = {}

        # Check for running agents
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'python.*agent'],
                capture_output=True,
                text=True
            )
            running_agents = result.stdout.strip().split('\n') if result.stdout.strip() else []
        except:
            running_agents = []

        agent_metrics["running_count"] = len([p for p in running_agents if p])
        agent_metrics["agent_processes"] = running_agents

        # Check agent logs for activity
        log_files = [
            'inner_council_intelligence.log',
            'ncc_logs/execution_monitoring.log',
            'youtube_intelligence.log'
        ]

        for log_file in log_files:
            if Path(log_file).exists():
                try:
                    # Get file modification time
                    mtime = Path(log_file).stat().st_mtime
                    last_activity = datetime.fromtimestamp(mtime)
                    minutes_since_activity = (datetime.now() - last_activity).total_seconds() / 60
                    agent_metrics[f"{log_file}_last_activity_minutes"] = minutes_since_activity
                except:
                    agent_metrics[f"{log_file}_last_activity_minutes"] = -1

        return agent_metrics

    def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_metrics": self.collect_system_metrics(),
            "project_metrics": self.collect_project_metrics(),
            "agent_metrics": self.collect_agent_metrics(),
            "alerts": self.alerts,
            "summary": {
                "total_projects": len(self.projects),
                "active_projects": len([p for p in self.projects if p.get('tier') in ['L', 'M', 'EXECUTIVE']]),
                "high_risk_projects": len([p for p in self.projects if p.get('risk_tier') == 'HIGH']),
                "running_agents": self.collect_agent_metrics().get('running_count', 0)
            }
        }

    def display_dashboard(self):
        """Display the monitoring dashboard"""
        report = self.generate_monitoring_report()

        print("🚀 Super Agency Advanced Monitoring Dashboard")
        print("=" * 60)

        # System Metrics
        sys_metrics = report['system_metrics']
        print("\n📊 SYSTEM METRICS:")
        print(f"   CPU Usage: {sys_metrics['cpu']['usage_percent']:.1f}%")
        print(f"   Memory Usage: {sys_metrics['memory']['usage_percent']:.1f}%")
        print(f"   Disk Usage: {sys_metrics['disk']['usage_percent']:.1f}%")
        print(f"   CPU Cores: {sys_metrics['cpu']['cores']}")
        print(f"   Memory Total: {sys_metrics['memory']['total_gb']:.1f}GB")
        # Project Summary
        summary = report['summary']
        print("\n📁 PROJECT SUMMARY:")
        print(f"   Total Projects: {summary['total_projects']}")
        print(f"   Active Projects: {summary['active_projects']}")
        print(f"   High Risk Projects: {summary['high_risk_projects']}")

        # Top Projects by Tier
        print("\n🏆 TOP PROJECTS BY TIER:")
        executive_projects = [p for p in self.projects if p.get('tier') == 'EXECUTIVE']
        large_projects = [p for p in self.projects if p.get('tier') == 'L'][:3]
        medium_projects = [p for p in self.projects if p.get('tier') == 'M'][:3]

        if executive_projects:
            print(f"   EXECUTIVE: {executive_projects[0]['name']}")
        if large_projects:
            print(f"   LARGE: {', '.join([p['name'] for p in large_projects])}")
        if medium_projects:
            print(f"   MEDIUM: {', '.join([p['name'] for p in medium_projects])}")

        # Agent Status
        agent_metrics = report['agent_metrics']
        print("\n🤖 AGENT STATUS:")
        print(f"   Running Agents: {agent_metrics.get('running_count', 0)}")

        # CPU & Task Manager Status (if available)
        try:
            from cpu_task_manager import CPUAndTaskManager
            temp_manager = CPUAndTaskManager()
            ctm_status = temp_manager.get_status()
            print("\n🎛️ CPU & TASK MANAGER:")
            print(f"   Status: {'🟢 Active' if ctm_status['overall_status'] == 'running' else '🔴 Inactive'}")
            tm = ctm_status['task_manager']
            print(f"   Tasks - Running: {tm['running_tasks']}, Queued: {tm['queued_tasks']}, Completed: {tm['completed_tasks']}")
            cpu_reg = ctm_status['cpu_regulator']
            print(f"   CPU Regulation - Current: {cpu_reg['current_cpu']:.1f}%, Throttled: {cpu_reg['throttled_processes']}")
        except ImportError:
            print("\n🎛️ CPU & TASK MANAGER:")
            print("   Status: 📦 Not installed (run cpu_task_manager.py start)")

        # Recent Activity
        print("\n📈 RECENT ACTIVITY:")
        project_metrics = report['project_metrics']
        active_projects = []
        for name, metrics in project_metrics.items():
            if metrics.get('status', {}).get('exists', False):
                days = metrics['status'].get('days_since_commit', -1)
                if days >= 0 and days <= 7:  # Active in last week
                    active_projects.append((name, days))

        active_projects.sort(key=lambda x: x[1])
        for name, days in active_projects[:5]:
            print(f"   {name}: {days} days ago")

        print("\n💡 RECOMMENDATIONS:")
        if sys_metrics['cpu']['usage_percent'] > 80:
            print("   ⚠️  High CPU usage - consider load balancing")
        if sys_metrics['memory']['usage_percent'] > 90:
            print("   ⚠️  High memory usage - consider cleanup")
        if summary['high_risk_projects'] > 0:
            print(f"   ⚠️  {summary['high_risk_projects']} high-risk projects need attention")
        if agent_metrics.get('running_count', 0) == 0:
            print("   ℹ️  No agents currently running")

def main():
    """Main monitoring function"""
    dashboard = AdvancedMonitoringDashboard()
    dashboard.display_dashboard()

if __name__ == "__main__":
    main()