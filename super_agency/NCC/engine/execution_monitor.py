#!/usr/bin/env python3
"""
NCC Execution Monitor
Tracks and oversees command implementation and operational workflows
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import threading

class NCCExecutionMonitor:
    """Neural Command Center - Execution tracking and oversight"""

    def __init__(self, config_path: str = "ncc_execution_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.setup_logging()
        self.execution_tracking = {}
        self.performance_metrics = []
        self.alerts = []
        self.monitoring_active = False

    def load_config(self) -> Dict:
        """Load execution monitoring configuration"""
        default_config = {
            "monitoring": {
                "check_interval_seconds": 30,
                "max_execution_time_minutes": 30,
                "alert_thresholds": {
                    "execution_timeout": 30,  # minutes
                    "error_rate_threshold": 0.1,  # 10%
                    "performance_degradation": 0.2  # 20% slower
                },
                "auto_recovery": True,
                "detailed_logging": True
            },
            "oversight": {
                "real_time_tracking": True,
                "performance_baselining": True,
                "anomaly_detection": True,
                "predictive_alerts": True
            }
        }

        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                user_config = json.load(f)
                self.deep_update(default_config, user_config)

        return default_config

    def deep_update(self, base_dict: Dict, update_dict: Dict):
        """Deep update dictionary"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                self.deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def setup_logging(self):
        """Setup execution monitoring logging"""
        os.makedirs("ncc_logs", exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - NCC-Execution - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ncc_logs/execution_monitoring.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("NCC-Execution")

    def start_monitoring(self):
        """Start the execution monitoring system"""
        if self.monitoring_active:
            self.logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()

        self.logger.info("Execution monitoring started")

    def stop_monitoring(self):
        """Stop the execution monitoring system"""
        self.monitoring_active = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
        self.logger.info("Execution monitoring stopped")

    def monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                self.perform_monitoring_checks()
                time.sleep(self.config["monitoring"]["check_interval_seconds"])
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {str(e)}")
                time.sleep(60)  # Wait longer on error

    def perform_monitoring_checks(self):
        """Perform all monitoring checks"""

        # Check for timed-out executions
        self.check_execution_timeouts()

        # Check system performance
        self.check_performance_metrics()

        # Check for anomalies
        self.check_anomalies()

        # Update performance baselines
        self.update_performance_baselines()

    def track_execution_start(self, execution_id: str, command_type: str,
                            requester: str, metadata: Dict = None):
        """Start tracking an execution"""

        tracking = {
            "execution_id": execution_id,
            "command_type": command_type,
            "requester": requester,
            "start_time": datetime.now(),
            "status": "running",
            "metadata": metadata or {},
            "checkpoints": [],
            "performance_data": []
        }

        self.execution_tracking[execution_id] = tracking
        self.logger.info(f"Started tracking execution: {execution_id}")

    def track_execution_checkpoint(self, execution_id: str, checkpoint: str,
                                 data: Dict = None):
        """Record an execution checkpoint"""

        if execution_id not in self.execution_tracking:
            self.logger.warning(f"Unknown execution ID: {execution_id}")
            return

        checkpoint_record = {
            "timestamp": datetime.now(),
            "checkpoint": checkpoint,
            "data": data or {}
        }

        self.execution_tracking[execution_id]["checkpoints"].append(
            checkpoint_record)

        # Log significant checkpoints
        if checkpoint in ["started", "completed", "failed"]:
            self.logger.info(
                f"Execution {execution_id} checkpoint: {checkpoint}")

    def track_execution_complete(self, execution_id: str, success: bool,
                               result: Any = None, error: str = None):
        """Mark execution as completed"""

        if execution_id not in self.execution_tracking:
            self.logger.warning(f"Unknown execution ID: {execution_id}")
            return

        tracking = self.execution_tracking[execution_id]
        tracking["end_time"] = datetime.now()
        tracking["duration"] = (tracking["end_time"] - \
                                tracking["start_time"]).total_seconds()
        tracking["success"] = success
        tracking["result"] = result
        tracking["error"] = error
        tracking["status"] = "completed"

        # Calculate performance metrics
        self.calculate_execution_metrics(tracking)

        # Check for issues
        self.check_execution_issues(tracking)

        self.logger.info(
            f"Execution completed: {execution_id} - Success: {success}")

    def calculate_execution_metrics(self, tracking: Dict):
        """Calculate performance metrics for an execution"""

        metrics = {
            "execution_id": tracking["execution_id"],
            "command_type": tracking["command_type"],
            "duration_seconds": tracking["duration"],
            "success": tracking["success"],
            "checkpoint_count": len(tracking["checkpoints"]),
            "timestamp": datetime.now().isoformat()
        }

        # Calculate efficiency score
        expected_duration = self.get_expected_duration(
            tracking["command_type"])
        if expected_duration:
            metrics["efficiency_score"] = min(
                1.0, expected_duration / tracking["duration"])
        else:
            metrics["efficiency_score"] = 0.8  # Default

        self.performance_metrics.append(metrics)

        # Keep metrics history manageable
        if len(self.performance_metrics) > 1000:
            self.performance_metrics = self.performance_metrics[-500:]

    def get_expected_duration(self, command_type: str) -> Optional[float]:
        """Get expected duration for command type"""

        expectations = {
            "intelligence_gathering": 300,  # 5 minutes
            "api_management": 60,          # 1 minute
            "resource_allocation": 30,     # 30 seconds
            "council_coordination": 120    # 2 minutes
        }

        return expectations.get(command_type)

    def check_execution_issues(self, tracking: Dict):
        """Check for issues in completed execution"""

        issues = []

        # Check timeout
        max_time = self.config["monitoring"]["max_execution_time_minutes"] * 60
        if tracking["duration"] > max_time:
            issues.append(
                f"Execution timeout: {tracking['duration']:.1f}s > {max_time}s")

        # Check failure
        if not tracking["success"]:
            issues.append(
                f"Execution failed: {tracking.get('error', 'Unknown error')}")

        # Check performance degradation
        if len(self.performance_metrics) > 5:
            recent_metrics = [m for m in self.performance_metrics[-10:]
                            if m["command_type"] == tracking["command_type"]]

            if recent_metrics:
                avg_duration = sum(m["duration_seconds"]
                                   for m in recent_metrics) / len(recent_metrics)
                degradation_threshold = self.config["monitoring"] [
                    "alert_thresholds"] ["performance_degradation"]

                if tracking["duration"] >avg_duration * (
                    1 +degradation_threshold):
                    issues.append(
                        f"Performance degradation: {tracking['duration']:.1f}s vs avg {avg_duration:.1f}s")

        if issues:
            alert = {
                "type": "execution_issue",
                "execution_id": tracking["execution_id"],
                "issues": issues,
                "timestamp": datetime.now().isoformat()
            }
            self.alerts.append(alert)
            self.logger.warning(
                f"Execution issues detected: {tracking['execution_id']} - {issues}")

    def check_execution_timeouts(self):
        """Check for executions that have timed out"""

        now = datetime.now()
        timeout_threshold = timedelta(
            minutes=self.config["monitoring"]["max_execution_time_minutes"])

        for execution_id, tracking in self.execution_tracking.items():
            if tracking["status"] == "running":
                runtime = now - tracking["start_time"]
                if runtime > timeout_threshold:
                    # Mark as timed out
                    tracking["status"] = "timed_out"
                    tracking["end_time"] = now
                    tracking["duration"] = runtime.total_seconds()
                    tracking["error"] = "Execution timed out"

                    alert = {
                        "type": "timeout",
                        "execution_id": execution_id,
                        "runtime_minutes": runtime.total_seconds() / 60,
                        "timestamp": datetime.now().isoformat()
                    }
                    self.alerts.append(alert)
                    self.logger.error(f"Execution timeout: {execution_id}")

    def check_performance_metrics(self):
        """Check overall system performance"""

        if len(self.performance_metrics) < 10:
            return  # Need more data

        recent_metrics = self.performance_metrics[-50:]

        # Calculate error rate
        error_count = sum(1 for m in recent_metrics if not m["success"])
        error_rate = error_count / len(recent_metrics)

        if error_rate >self.config["monitoring"] ["alert_thresholds"] [
            "error_rate_threshold"]:
            alert = {
                "type": "high_error_rate",
                "error_rate": error_rate,
                "sample_size": len(recent_metrics),
                "timestamp": datetime.now().isoformat()
            }
            self.alerts.append(alert)
            self.logger.warning(f"High error rate detected: {error_rate:.2%}")

    def check_anomalies(self):
        """Check for anomalous execution patterns"""

        if len(self.performance_metrics) < 20:
            return

        # Simple anomaly detection based on duration outliers
        recent_durations = [m["duration_seconds"]
            for m in self.performance_metrics[-50:]]
        if recent_durations:
            mean_duration = sum(recent_durations) / len(recent_durations)
            std_dev = (
                sum((x -mean_duration) **2 for x in recent_durations) /
                len(recent_durations)) **0.5

            # Check last few executions for anomalies
            for i in range(
                max(0, len(recent_durations) -5),
                len(recent_durations)):
                duration = recent_durations[i]
                if abs(duration - mean_duration) > 3 * std_dev:  # 3 standard deviations
                    alert = {
                        "type": "performance_anomaly", "duration": duration,
                        "mean_duration": mean_duration,
                        "deviation_sigma": (duration -mean_duration) /std_dev,
                        "timestamp": datetime.now().isoformat()}
                    self.alerts.append(alert)
                    self.logger.warning(
                        f"Performance anomaly detected: {duration:.1f}s (mean: {mean_duration:.1f}s)")

    def update_performance_baselines(self):
        """Update performance baselines for future comparisons"""

        if len(self.performance_metrics) < 50:
            return  # Need more data

        # Calculate baselines by command type
        command_types = set(m["command_type"]
                            for m in self.performance_metrics)

        baselines = {}
        for cmd_type in command_types:
            type_metrics = [
                m for m in self.performance_metrics
                if m["command_type"] ==cmd_type]
            if len(type_metrics) >= 10:
                durations = [m["duration_seconds"] for m in type_metrics]
                baselines[cmd_type] = {
                    "mean_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "sample_size": len(durations)
                }

        # Save baselines
        with open("ncc_performance_baselines.json", 'w') as f:
            json.dump({
                "baselines": baselines,
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)

    def get_monitoring_status(self) -> Dict:
        """Get comprehensive monitoring status"""

        active_executions = {k: v for k, v in self.execution_tracking.items()
                           if v["status"] == "running"}

        recent_alerts = [a for a in self.alerts if datetime.fromisoformat(
            a["timestamp"]) > datetime.now() - timedelta(hours=1)]

        status = {
            "monitoring_active": self.monitoring_active,
            "active_executions": len(active_executions),
            "total_tracked_executions": len(self.execution_tracking),
            "recent_alerts": len(recent_alerts),
            "performance_metrics_count": len(self.performance_metrics),
            "system_health": self.assess_system_health(),
            # Top 5
            "active_execution_details": list(active_executions.keys())[:5]
        }

        return status

    def assess_system_health(self) -> Dict:
        """Assess overall system health based on monitoring data"""

        health_score = 100

        # Check recent error rate
        if len(self.performance_metrics) > 10:
            recent_metrics = self.performance_metrics[-20:]
            error_rate = sum(
                1 for m in recent_metrics if not m["success"]) / len(recent_metrics)
            if error_rate > 0.1:
                health_score -= 20
            elif error_rate > 0.05:
                health_score -= 10

        # Check active timeouts
        timeout_count = sum(1 for t in self.execution_tracking.values()
                          if t["status"] == "timed_out")
        if timeout_count > 0:
            health_score -= timeout_count * 5

        # Check recent alerts
        recent_alerts = [a for a in self.alerts if datetime.fromisoformat(
            a["timestamp"]) > datetime.now() - timedelta(hours=1)]
        health_score -= len(recent_alerts) * 2

        health_status = "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical"

        return {
            "score": max(0, health_score),
            "status": health_status,
            "issues": len(recent_alerts)
        }

    def get_execution_report(self, execution_id: str) -> Optional[Dict]:
        """Get detailed report for a specific execution"""

        if execution_id not in self.execution_tracking:
            return None

        tracking = self.execution_tracking[execution_id]

        report = {
            "execution_id": execution_id,
            "command_type": tracking["command_type"],
            "requester": tracking["requester"],
            "status": tracking["status"],
            "start_time": tracking["start_time"].isoformat(),
            "duration_seconds": tracking.get("duration"),
            "success": tracking.get("success"),
            "error": tracking.get("error"),
            "checkpoint_count": len(tracking["checkpoints"]),
            "checkpoints": tracking["checkpoints"],
            "metadata": tracking["metadata"]
        }

        if "end_time" in tracking:
            report["end_time"] = tracking["end_time"].isoformat()

        return report

    def cleanup_old_data(self):
        """Clean up old monitoring data"""

        cutoff_date = datetime.now() - timedelta(days=7)

        # Clean old execution tracking
        to_remove = []
        for exec_id, tracking in self.execution_tracking.items():
            if tracking["start_time"] < cutoff_date:
                to_remove.append(exec_id)

        for exec_id in to_remove:
            del self.execution_tracking[exec_id]

        # Clean old alerts
        self.alerts = [a for a in self.alerts
                      if datetime.fromisoformat(a["timestamp"]) > cutoff_date]

        # Clean old performance metrics (keep last 500)
        if len(self.performance_metrics) > 500:
            self.performance_metrics = self.performance_metrics[-500:]

        self.logger.info(
            f"Cleaned up old monitoring data: {len(to_remove)} executions removed")

# Global execution monitor instance
execution_monitor = NCCExecutionMonitor()

def start_execution_tracking(execution_id: str, command_type: str,
                           requester: str, metadata: Dict = None):
    """Convenience function to start execution tracking"""
    execution_monitor.track_execution_start(
        execution_id, command_type, requester, metadata)

def checkpoint_execution(
        execution_id: str, checkpoint: str, data: Dict=None):
    """Convenience function for execution checkpoints"""
    execution_monitor.track_execution_checkpoint(
        execution_id, checkpoint, data)

def complete_execution(
        execution_id: str, success: bool, result: Any=None, error: str=None):
    """Convenience function to complete execution tracking"""
    execution_monitor.track_execution_complete(
        execution_id, success, result, error)

def get_monitoring_status():
    """Get current monitoring status"""
    return execution_monitor.get_monitoring_status()

if __name__ == "__main__":
    # Test Execution Monitor
    print("📊 NCC Execution Monitor Test")
    print("=" * 35)

    # Start monitoring
    execution_monitor.start_monitoring()
    print("✅ Monitoring started")

    # Simulate execution tracking
    exec_id = "test_exec_001"

    start_execution_tracking(exec_id, "intelligence_gathering", "test_user")
    print("✅ Started tracking execution")

    time.sleep(2)  # Simulate work

    checkpoint_execution(exec_id, "data_collection_started")
    print("✅ Recorded checkpoint")

    time.sleep(1)  # More work

    complete_execution(exec_id, True, {"result": "success"})
    print("✅ Completed execution tracking")

    # Get status
    status = get_monitoring_status()
    print(f"Active executions: {status['active_executions']}")
    print(
        f"System health: {status['system_health']['status']} ({status['system_health']['score']})")

    # Stop monitoring
    execution_monitor.stop_monitoring()
    print("✅ Monitoring stopped")

    print("\n✅ NCC Execution Monitor Ready!")
    print("   • Real-time execution tracking: Active")
    print("   • Performance monitoring: Operational")
    print("   • Anomaly detection: Enabled")
    print("   • Alert system: Configured")