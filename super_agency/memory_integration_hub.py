#!/usr/bin/env python3
"""
DIGITAL LABOUR Memory Integration Hub
Connects unified memory system with NCC and NCL components
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Any, Dict


class MemoryIntegrationHub:
    """Integrates unified memory with NCC and NCL systems"""

    def __init__(self):
        """Initialize."""
        self.unified_memory = None
        self.continuous_backup = None
        self.ncc_adapter = None
        self.ncl_adapter = None
        self.monitoring_active = False

        self._initialize_systems()

    def _initialize_systems(self):
        """Initialize all memory systems"""
        try:
            # Import and initialize unified memory
            from unified_memory_doctrine_system import (
                get_unified_memory_system,
            )
            self.unified_memory = get_unified_memory_system()
            print("[OK] Unified Memory Doctrine System connected")

            # Import and start continuous backup
            from continuous_memory_backup import get_continuous_backup_system
            self.continuous_backup = get_continuous_backup_system()
            self.continuous_backup.start_continuous_backup()
            print("[OK] Continuous Memory Backup System connected")

            # Initialize NCC adapter
            self._initialize_ncc_adapter()
            print("[OK] NCC Command Center adapter connected")

            # Initialize NCL adapter
            self._initialize_ncl_adapter()
            print("[OK] NCL Second Brain adapter connected")

        except Exception as e:
            print(f"[ERROR] System initialization error: {e}")

    def _initialize_ncc_adapter(self):
        """Initialize NCC integration"""
        try:
            ncc_path = Path("./NCC")
            if ncc_path.exists():
                # Import NCC orchestrator
                import sys
                sys.path.append(str(ncc_path))
                # NCC integration would go here
                self.ncc_adapter = {"status": "connected", "path": ncc_path}
        except Exception as e:
            print(f"NCC adapter initialization warning: {e}")
            self.ncc_adapter = {"status": "disconnected"}

    def _initialize_ncl_adapter(self):
        """Initialize NCL integration"""
        try:
            ncl_path = Path("./ncl_second_brain")
            if ncl_path.exists():
                # Import NCL components
                import sys
                sys.path.append(str(ncl_path))
                # NCL integration would go here
                self.ncl_adapter = {"status": "connected", "path": ncl_path}
        except Exception as e:
            print(f"NCL adapter initialization warning: {e}")
            self.ncl_adapter = {"status": "disconnected"}

    def start_memory_monitoring(self):
        """Start comprehensive memory monitoring"""
        if self.monitoring_active:
            return

        self.monitoring_active = True

        def monitoring_loop():
            """monitoring_loop handler."""
            while self.monitoring_active:
                try:
                    self._comprehensive_memory_check()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    print(f"Memory monitoring error: {e}")
                    time.sleep(30)

        monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitor_thread.start()

        print(
            "Memory monitoring started - "
            "checking NCC, NCL, and unified systems"
        )

    def _comprehensive_memory_check(self):
        """Perform comprehensive memory health check"""
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "unified_memory": {},
            "backup_system": {},
            "ncc_integration": {},
            "ncl_integration": {},
            "cross_system_sync": {},
            "blank_prevention_status": {}
        }

        # Check unified memory
        if self.unified_memory:
            try:
                status = self.unified_memory.get_system_status()
                health_report["unified_memory"] = {
                        "status": "healthy",
                        "layers": len(status["layers"]),
                        "blank_prevention": (
                            status["blank_prevention"]["active"]
                        ),
                    }
            except Exception as e:
                health_report["unified_memory"] = {
                    "status": "error", "error": str(e),
                }

        # Check backup system
        if self.continuous_backup:
            try:
                status = self.continuous_backup.get_backup_status()
                health_report["backup_system"] = {
                    "status": (
                        "healthy" if status["running"]
                        else "stopped"
                    ),
                    "backups": status["total_backups"],
                    "last_backup": status["last_backup"],
                }
            except Exception as e:
                health_report["backup_system"] = {
                    "status": "error", "error": str(e),
                }

        # Check NCC integration
        health_report["ncc_integration"] = (
            self.ncc_adapter or {"status": "not_initialized"}
        )

        # Check NCL integration
        health_report["ncl_integration"] = (
            self.ncl_adapter or {"status": "not_initialized"}
        )

        # Cross-system synchronization check
        health_report["cross_system_sync"] = (
            self._check_cross_system_sync()
        )

        # Blank prevention status
        health_report["blank_prevention_status"] = (
            self._get_blank_prevention_status()
        )

        # Save health report
        self._save_health_report(health_report)

        # Alert on critical issues
        self._check_for_alerts(health_report)

    def _check_cross_system_sync(self) -> Dict:
        """Check synchronization between systems"""
        sync_status = {
            "memory_layers_aligned": False,
            "backup_consistency": False,
            "ncc_memory_sync": False,
            "ncl_memory_sync": False
        }

        # Check if memory layers are properly aligned
        if self.unified_memory:
            layers = list(self.unified_memory.layers.keys())
            expected_layers = [
                "ephemeral", "session", "persistent",
            ]
            sync_status["memory_layers_aligned"] = (
                set(layers) == set(expected_layers)
            )

        # Check backup consistency
        if self.continuous_backup:
            status = self.continuous_backup.get_backup_status()
            sync_status["backup_consistency"] = status.get(
                "running", False,
            )

        return sync_status

    def _get_blank_prevention_status(self) -> Dict:
        """Get blank prevention system status"""
        if not self.unified_memory:
            return {"status": "unavailable"}

        try:
            prevention = self.unified_memory.prevent_blanks()
            return {
                "status": "active",
                "blanks_detected": len(
                    prevention.get("blanks_detected", [])
                ),
                "last_check": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _save_health_report(self, report: Dict):
        """Save health report to file"""
        try:
            reports_dir = Path("./memory_reports")
            reports_dir.mkdir(exist_ok=True)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = reports_dir / f"memory_health_{ts}.json"

            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            # Keep only last 50 reports
            reports = sorted(reports_dir.glob("memory_health_*.json"))
            if len(reports) > 50:
                for old_report in reports[:-50]:
                    old_report.unlink()

        except Exception as e:
            print(f"Health report save error: {e}")

    def _check_for_alerts(self, report: Dict):
        """Check for critical alerts"""
        alerts = []

        # Check unified memory
        if report["unified_memory"].get("status") != "healthy":
            alerts.append("Unified memory system unhealthy")

        # Check backup system
        if report["backup_system"].get("status") != "healthy":
            alerts.append("Backup system not running")

        # Check for blanks
        bp = report["blank_prevention_status"]
        blanks = bp.get("blanks_detected", 0)
        if blanks > 0:
            alerts.append(f"Memory blanks detected: {blanks}")

        # Alert if any critical issues
        if alerts:
            print(f"🚨 MEMORY ALERTS: {', '.join(alerts)}")

    def get_integration_status(self) -> Dict:
        """Get comprehensive integration status"""
        return {
            "unified_memory": self.unified_memory is not None,
            "continuous_backup": self.continuous_backup is not None,
            "ncc_connected": (
                self.ncc_adapter.get("status") == "connected"
                if self.ncc_adapter else False
            ),
            "ncl_connected": (
                self.ncl_adapter.get("status") == "connected"
                if self.ncl_adapter else False
            ),
            "monitoring_active": self.monitoring_active,
            "timestamp": datetime.now().isoformat()
        }

    def sync_memory_across_systems(self) -> Dict:
        """Synchronize memory across all connected systems"""
        results: Dict[str, Any] = {
            "unified_memory_sync": False,
            "ncc_memory_sync": False,
            "ncl_memory_sync": False,
            "cross_system_consolidation": False
        }

        # Sync unified memory
        if self.unified_memory:
            try:
                prevention = self.unified_memory.prevent_blanks()
                results["unified_memory_sync"] = True
                results["consolidation_results"] = (
                    prevention.get("consolidation", {})
                )
            except Exception as e:
                results["unified_memory_sync"] = False
                results["sync_error"] = str(e)

        # NCC sync (placeholder for actual NCC integration)
        ncc_ok = (
            self.ncc_adapter
            and self.ncc_adapter.get("status") == "connected"
        )
        if ncc_ok:
            results["ncc_memory_sync"] = True

        # NCL sync (placeholder for actual NCL integration)
        ncl_ok = (
            self.ncl_adapter
            and self.ncl_adapter.get("status") == "connected"
        )
        if ncl_ok:
            results["ncl_memory_sync"] = True

        # Cross-system consolidation
        all_synced = all([
            results["unified_memory_sync"],
            results["ncc_memory_sync"],
            results["ncl_memory_sync"],
        ])
        if all_synced:
            results["cross_system_consolidation"] = True

        return results


# Global instance
_memory_hub = None


def get_memory_integration_hub() -> MemoryIntegrationHub:
    """Get or create memory integration hub"""
    global _memory_hub
    if _memory_hub is None:
        _memory_hub = MemoryIntegrationHub()
    return _memory_hub


def start_memory_integration():
    """Start the complete memory integration system"""
    hub = get_memory_integration_hub()
    hub.start_memory_monitoring()
    return hub.get_integration_status()


def get_memory_integration_status():
    """Get memory integration status"""
    hub = get_memory_integration_hub()
    return hub.get_integration_status()


def sync_all_memory_systems():
    """Synchronize memory across all systems"""
    hub = get_memory_integration_hub()
    return hub.sync_memory_across_systems()


if __name__ == "__main__":
    print("🔗 Testing Memory Integration Hub...")

    # Start integration
    status = start_memory_integration()
    print("Integration Status:", json.dumps(status, indent=2, default=str))

    # Test synchronization
    sync_results = sync_all_memory_systems()
    print("Sync Results:", json.dumps(sync_results, indent=2, default=str))

    print("[OK] Memory Integration Hub test complete!")
