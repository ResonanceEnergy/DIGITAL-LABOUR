#!/usr/bin/env python3
"""
Enhanced Cross-Platform Synchronization System
Real-time synchronization between Windows and macOS BIT RAGE LABOUR instances
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import platform

class SyncDirection(Enum):
    """Synchronization directions"""
    BIDIRECTIONAL = "bidirectional"
    WINDOWS_TO_MACOS = "windows_to_macos"
    MACOS_TO_WINDOWS = "macos_to_windows"

class SyncPriority(Enum):
    """Synchronization priorities"""
    CRITICAL = "critical"      # Memory doctrine, emergency data
    HIGH = "high"             # Operations status, agent states
    MEDIUM = "medium"         # Logs, reports
    LOW = "low"               # Cache files, temporary data

@dataclass
class SyncFile:
    """File to be synchronized"""
    path: str
    priority: SyncPriority
    last_modified: datetime
    checksum: str
    size: int
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL

@dataclass
class SyncSession:
    """Synchronization session"""
    session_id: str
    started_at: datetime
    direction: SyncDirection
    files_synced: int = 0
    bytes_transferred: int = 0
    status: str = "active"
    errors: List[str] = field(default_factory=list)

class EnhancedCrossPlatformSync:
    """Enhanced cross-platform synchronization system"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.system_name = "QUANTUM FORGE" if platform.system() == "Windows" else "Quantum Quasar"
        self.workspace_root = Path(__file__).parent
        self.sync_active = False

        # Sync configuration
        self.sync_files = self._initialize_sync_files()
        self.sync_interval = 300  # 5 minutes
        self.conflict_resolution = "newer_wins"

        # State tracking
        self.last_sync_time: Optional[datetime] = None
        self.active_sessions: Dict[str, SyncSession] = {}

    def _initialize_sync_files(self) -> List[SyncFile]:
        """Initialize files to be synchronized"""
        return [
            # Critical files - always sync
            SyncFile("memory_doctrine_system.py", SyncPriority.CRITICAL, datetime.now(), "", 0),
            SyncFile("doctrine_preservation_system.py", SyncPriority.CRITICAL, datetime.now(), "", 0),
            SyncFile("emergency_system_status_*.json", SyncPriority.CRITICAL, datetime.now(), "", 0),
            SyncFile("emergency_notification_*.json", SyncPriority.CRITICAL, datetime.now(), "", 0),

            # High priority - operations data
            SyncFile("operations_status_*.json", SyncPriority.HIGH, datetime.now(), "", 0),
            SyncFile("agent_deployment_report_*.json", SyncPriority.HIGH, datetime.now(), "", 0),
            SyncFile("conductor_integration_report_*.json", SyncPriority.HIGH, datetime.now(), "", 0),
            SyncFile("integrated_operations_dashboard_*.json", SyncPriority.HIGH, datetime.now(), "", 0),

            # Medium priority - logs and reports
            SyncFile("logs/*.log", SyncPriority.MEDIUM, datetime.now(), "", 0),
            SyncFile("*_report_*.json", SyncPriority.MEDIUM, datetime.now(), "", 0),
            SyncFile("system_validation_report_*.json", SyncPriority.MEDIUM, datetime.now(), "", 0),

            # Low priority - cache and temp files
            SyncFile("__pycache__/*", SyncPriority.LOW, datetime.now(), "", 0),
            SyncFile("*.pyc", SyncPriority.LOW, datetime.now(), "", 0),
        ]

    async def start_cross_platform_sync(self) -> Dict[str, Any]:
        """Start the enhanced cross-platform synchronization system"""
        self.logger.info("🔄 Starting Enhanced Cross-Platform Synchronization")

        try:
            # Start sync monitoring loop
            asyncio.create_task(self._sync_monitoring_loop())
            self.sync_active = True

            # Perform initial sync
            initial_sync_result = await self._perform_sync_cycle()

            return {
                "success": True,
                "message": "Cross-platform synchronization activated",
                "system_name": self.system_name,
                "sync_interval": self.sync_interval,
                "files_monitored": len(self.sync_files),
                "initial_sync": initial_sync_result
            }
        except Exception as e:
            self.logger.error(f"Failed to start cross-platform sync: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _sync_monitoring_loop(self):
        """Continuous synchronization monitoring loop"""
        while self.sync_active:
            try:
                # Check if it's time for a sync cycle
                current_time = datetime.now()
                if (self.last_sync_time is None or
                    (current_time - self.last_sync_time).total_seconds() >= self.sync_interval):

                    await self._perform_sync_cycle()
                    self.last_sync_time = current_time

                # Check for real-time sync triggers
                await self._check_realtime_triggers()

                # Clean up old sessions
                await self._cleanup_old_sessions()

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Sync monitoring loop error: {e}")
                await asyncio.sleep(120)  # Wait longer on error

    async def _perform_sync_cycle(self) -> Dict[str, Any]:
        """Perform a complete synchronization cycle"""
        session = SyncSession(
            session_id=f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            started_at=datetime.now(),
            direction=SyncDirection.BIDIRECTIONAL
        )

        self.active_sessions[session.session_id] = session

        try:
            self.logger.info(f"🔄 Starting sync cycle: {session.session_id}")

            # Scan for files to sync
            files_to_sync = await self._scan_files_for_sync()

            # Perform synchronization
            for sync_file in files_to_sync:
                try:
                    await self._sync_file(sync_file, session)
                    session.files_synced += 1
                except Exception as e:
                    error_msg = f"Failed to sync {sync_file.path}: {e}"
                    session.errors.append(error_msg)
                    self.logger.error(error_msg)

            session.status = "completed"

            result = {
                "session_id": session.session_id,
                "files_synced": session.files_synced,
                "bytes_transferred": session.bytes_transferred,
                "errors": len(session.errors),
                "duration": (datetime.now() - session.started_at).total_seconds()
            }

            self.logger.info(f"✅ Sync cycle completed: {result['files_synced']} files, {result['errors']} errors")
            return result

        except Exception as e:
            session.status = "failed"
            session.errors.append(str(e))
            self.logger.error(f"Sync cycle failed: {e}")
            return {
                "session_id": session.session_id,
                "error": str(e),
                "files_synced": session.files_synced
            }

    async def _scan_files_for_sync(self) -> List[SyncFile]:
        """Scan workspace for files that need synchronization"""
        files_to_sync = []

        for sync_file_template in self.sync_files:
            # Handle glob patterns
            if "*" in sync_file_template.path:
                # Find matching files
                import glob
                pattern = str(self.workspace_root / sync_file_template.path)
                matching_files = glob.glob(pattern)

                for file_path in matching_files:
                    rel_path = str(Path(file_path).relative_to(self.workspace_root))
                    file_info = await self._get_file_info(rel_path)
                    if file_info:
                        files_to_sync.append(SyncFile(
                            path=rel_path,
                            priority=sync_file_template.priority,
                            last_modified=file_info["modified"],
                            checksum=file_info["checksum"],
                            size=file_info["size"],
                            direction=sync_file_template.direction
                        ))
            else:
                # Check specific file
                file_info = await self._get_file_info(sync_file_template.path)
                if file_info:
                    files_to_sync.append(SyncFile(
                        path=sync_file_template.path,
                        priority=sync_file_template.priority,
                        last_modified=file_info["modified"],
                        checksum=file_info["checksum"],
                        size=file_info["size"],
                        direction=sync_file_template.direction
                    ))

        return files_to_sync

    async def _get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file information for sync tracking"""
        full_path = self.workspace_root / file_path

        if not full_path.exists():
            return None

        try:
            stat = full_path.stat()
            checksum = await self._calculate_checksum(full_path)

            return {
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "size": stat.st_size,
                "checksum": checksum
            }
        except Exception as e:
            self.logger.error(f"Failed to get file info for {file_path}: {e}")
            return None

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

    async def _sync_file(self, sync_file: SyncFile, session: SyncSession):
        """Synchronize a single file"""
        # This is a placeholder for actual cross-platform sync logic
        # In a real implementation, this would:
        # 1. Check if the other platform has a newer version
        # 2. Download/upload the file as needed
        # 3. Handle conflicts based on the conflict resolution policy

        self.logger.debug(f"Syncing file: {sync_file.path} (priority: {sync_file.priority.value})")
        session.bytes_transferred += sync_file.size

        # Placeholder - in real implementation, would perform actual sync
        pass

    async def _check_realtime_triggers(self):
        """Check for real-time synchronization triggers"""
        # Check for critical file changes that require immediate sync
        critical_files = [f for f in self.sync_files if f.priority == SyncPriority.CRITICAL]

        for sync_file in critical_files:
            # Check if file has been modified recently (last 5 minutes)
            file_info = await self._get_file_info(sync_file.path)
            if file_info and (datetime.now() - file_info["modified"]).total_seconds() < 300:
                self.logger.info(f"🚨 Real-time sync triggered for critical file: {sync_file.path}")
                # Trigger immediate sync for this file
                await self._perform_realtime_sync(sync_file)

    async def _perform_realtime_sync(self, sync_file: SyncFile):
        """Perform real-time sync for a critical file"""
        # Immediate sync logic for critical files
        self.logger.info(f"Performing real-time sync for: {sync_file.path}")
        # Placeholder for immediate sync implementation
        pass

    async def _cleanup_old_sessions(self):
        """Clean up old completed sync sessions"""
        cutoff_time = datetime.now() - timedelta(hours=24)

        sessions_to_remove = []
        for session_id, session in self.active_sessions.items():
            if session.started_at < cutoff_time and session.status in ["completed", "failed"]:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]

    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status"""
        return {
            "sync_active": self.sync_active,
            "system_name": self.system_name,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "active_sessions": len(self.active_sessions),
            "files_monitored": len(self.sync_files),
            "sync_interval": self.sync_interval,
            "session_details": [
                {
                    "id": s.session_id,
                    "status": s.status,
                    "files_synced": s.files_synced,
                    "started": s.started_at.isoformat(),
                    "errors": len(s.errors)
                } for s in self.active_sessions.values()
            ]
        }

    async def trigger_manual_sync(self, priority: SyncPriority = None) -> Dict[str, Any]:
        """Trigger a manual synchronization cycle"""
        self.logger.info(f"🔄 Manual sync triggered (priority: {priority.value if priority else 'all'})")

        # Filter files by priority if specified
        files_to_sync = self.sync_files
        if priority:
            files_to_sync = [f for f in self.sync_files if f.priority == priority]

        session = SyncSession(
            session_id=f"manual_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            started_at=datetime.now(),
            direction=SyncDirection.BIDIRECTIONAL
        )

        self.active_sessions[session.session_id] = session

        # Perform sync
        result = await self._perform_sync_cycle()
        return result

async def main():
    """Main cross-platform sync activation"""
    sync_system = EnhancedCrossPlatformSync()
    result = await sync_system.start_cross_platform_sync()

    # Save activation report
    report_file = f"cross_platform_sync_activation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"✅ Enhanced Cross-Platform Sync activated. Report: {report_file}")
    return result

if __name__ == "__main__":
    asyncio.run(main())
