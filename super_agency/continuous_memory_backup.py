#!/usr/bin/env python3
"""
DIGITAL LABOUR Continuous Memory Backup System.

Prevents memory blanks through real-time backup
and synchronization.
"""
from __future__ import annotations

import os
import json
import time
import threading
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict
import psutil


class ContinuousMemoryBackup:
    """Real-time memory backup to prevent blanks"""

    def __init__(self, backup_interval: int = 300, max_backups: int = 10):
        """Initialize."""
        self.backup_interval = backup_interval  # 5 minutes default
        self.max_backups = max_backups
        self.backup_dir = Path(__file__).resolve().parent / "memory_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.running = False
        self.backup_thread: threading.Thread | None = None
        self.last_backup: datetime | None = None

        # Import memory systems
        try:
            from unified_memory_doctrine_system import (
                get_unified_memory_system,
            )
            self.memory_system = get_unified_memory_system()
        except ImportError:
            # Fallback to original system
            from memory_doctrine_system import (
                get_memory_system,
            )
            ms = get_memory_system()
            self.memory_system = ms  # type: ignore[assignment]

    def start_continuous_backup(self):
        """Start continuous backup process"""
        if self.running:
            print("Continuous backup already running")
            return

        self.running = True
        self.backup_thread = threading.Thread(
            target=self._backup_loop, daemon=True,
        )
        self.backup_thread.start()

        print(
            "[BACKUP] Continuous Memory Backup started"
            f" - Interval: {self.backup_interval}s",
        )

    def stop_continuous_backup(self):
        """Stop continuous backup"""
        self.running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=10)
        print("[BACKUP] Continuous Memory Backup stopped")

    def _backup_loop(self):
        """Main backup loop"""
        while self.running:
            try:
                snapshot_path = self.create_backup_snapshot()
                self._sync_offsite(snapshot_path)
                self._cleanup_old_backups()
                time.sleep(self.backup_interval)
            except Exception as e:
                print(f"Backup error: {e}")
                time.sleep(60)  # Wait before retry

    def create_backup_snapshot(self) -> str:
        """Create a complete memory snapshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"memory_snapshot_{timestamp}"

        try:
            backup_path.mkdir(parents=True, exist_ok=True)

            # Backup all memory layers
            self._backup_memory_layers(backup_path)

            # Backup system state
            self._backup_system_state(backup_path)

            # Backup configuration
            self._backup_configuration(backup_path)

            # Create manifest
            self._create_backup_manifest(backup_path, timestamp)

            self.last_backup = datetime.now()

            print(f"[OK] Memory snapshot created: {backup_path.name}")
            return str(backup_path)

        except Exception as e:
            print(f"[ERROR] Backup snapshot failed: {e}")
            # Clean up failed backup
            if backup_path.exists():
                shutil.rmtree(backup_path)
            raise

    def _backup_memory_layers(self, backup_path: Path):
        """Backup all memory layers"""
        layers_dir = backup_path / "layers"
        layers_dir.mkdir(parents=True, exist_ok=True)

        for layer_name, layer in self.memory_system.layers.items():
            layer_backup = layers_dir / f"{layer_name}_layer.json"

            try:
                if layer_name == "ephemeral":
                    # Backup ephemeral cache
                    ephemeral_data = {}
                    for key, data in layer.cache.items():
                        ephemeral_data[key] = {
                            'data': data.get('data'),
                            'metadata': data.get('metadata', {}),
                            'stored_at': (
                                data.get('stored_at').isoformat()
                                if data.get('stored_at')
                                else None
                            ),
                            'access_count': data.get('access_count', 0)
                        }

                    with open(layer_backup, 'w') as f:
                        json.dump(ephemeral_data, f, indent=2, default=str)

                elif layer_name == "session":
                    # Backup session database (now SQLite)
                    db_backup = layers_dir / "session_memory.db"
                    if (
                        hasattr(layer, 'db_path')
                        and Path(layer.db_path).exists()
                    ):
                        shutil.copy2(layer.db_path, db_backup)
                    else:
                        # Legacy fallback: export data attribute if still JSON
                        data = getattr(layer, 'data', {})
                        with open(layer_backup, 'w') as f:
                            json.dump(data, f, indent=2, default=str)

                elif layer_name == "persistent":
                    # Backup persistent database
                    db_backup = layers_dir / "persistent_memory.db"
                    db_path = Path(layer.db_path)
                    if db_path.exists():
                        shutil.copy2(db_path, db_backup)

                print(f"  [OK] {layer_name} layer backed up")

            except Exception as e:
                print(f"  [ERROR] {layer_name} layer backup failed: {e}")

    def _backup_system_state(self, backup_path: Path):
        """Backup system state and health"""
        state_dir = backup_path / "system_state"
        state_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Memory system status
            status = self.memory_system.get_system_status()
            with open(state_dir / "memory_status.json", 'w') as f:
                json.dump(status, f, indent=2, default=str)

            # System resource usage
            system_info = {
                'timestamp': datetime.now().isoformat(),
                'memory': dict(
                    psutil.virtual_memory()._asdict(),
                ),
                'cpu': psutil.cpu_percent(interval=1),
                'disk': dict(
                    psutil.disk_usage(
                        os.environ.get('SystemDrive', 'C:\\\\')
                        if os.name == 'nt' else '/'
                    )._asdict(),
                ),
                'process_count': len(
                    list(psutil.process_iter()),
                )
            }

            with open(state_dir / "system_resources.json", 'w') as f:
                json.dump(system_info, f, indent=2, default=str)

            # Running processes (filtered)
            processes = []
            for proc in psutil.process_iter(
                ['pid', 'name', 'cpu_percent', 'memory_percent'],
            ):
                try:
                    name = proc.info.get('name') or ''
                    if 'python' in name.lower() or 'agency' in name.lower():
                        processes.append({
                            'pid': proc.info.get('pid'),
                            'name': name,
                            'cpu_percent': proc.info.get('cpu_percent', 0),
                            'memory_percent': proc.info.get(
                                'memory_percent', 0,
                            ),
                        })
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    AttributeError,
                ):
                    continue

            try:
                with open(state_dir / "agency_processes.json", 'w') as f:
                    json.dump(processes, f, indent=2)
            except OSError as write_err:
                print(f"Failed to write agency_processes.json: {write_err}")

        except Exception as e:
            print(f"System state backup error: {e}")

    def _backup_configuration(self, backup_path: Path):
        """Backup configuration files"""
        config_dir = backup_path / "configuration"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_files = [
            "config/settings.json",
            "portfolio.json",
            "portfolio.yaml",
            "DOCTRINE_NCL_SECOND_BRAIN.md",
            "NORTH_STAR.md"
        ]

        for config_file in config_files:
            src_path = Path(config_file)
            if src_path.exists():
                dst_path = config_dir / src_path.name
                try:
                    if src_path.is_file():
                        shutil.copy2(src_path, dst_path)
                    else:
                        shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                except Exception as e:
                    print(f"Config backup error for {config_file}: {e}")

    def _create_backup_manifest(self, backup_path: Path, timestamp: str):
        """Create backup manifest"""
        manifest = {
            'backup_id': f"memory_snapshot_{timestamp}",
            'timestamp': datetime.now().isoformat(),
            'type': 'continuous_memory_backup',
            'version': '1.0',
            'contents': {
                'layers': list(self.memory_system.layers.keys()),
                'system_state': True,
                'configuration': True
            },
            'metadata': {
                'backup_interval': self.backup_interval,
                'memory_system_type': type(self.memory_system).__name__,
                'total_memory_layers': len(self.memory_system.layers)
            }
        }

        with open(backup_path / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2, default=str)

    def _cleanup_old_backups(self):
        """Clean up old backups to prevent disk bloat"""
        try:
            backups = sorted(self.backup_dir.glob("memory_snapshot_*"))
            if len(backups) > self.max_backups:
                to_remove = backups[:-self.max_backups]  # Keep newest
                for old_backup in to_remove:
                    shutil.rmtree(old_backup)
                    print(f"[CLEANUP] Removed old backup: {old_backup.name}")
        except Exception as e:
            print(f"Backup cleanup error: {e}")

    def _sync_offsite(self, snapshot_path: str | None):
        """Copy the latest snapshot to an off-site directory (if configured).

        Set BACKUP_OFFSITE_DIR to a path (e.g. a mounted network share,
        Dropbox / OneDrive folder, or second disk) and the newest snapshot
        will be replicated there after each backup run.
        """
        offsite = os.environ.get("BACKUP_OFFSITE_DIR")
        if not offsite or not snapshot_path:
            return
        dst_root = Path(offsite)
        try:
            dst_root.mkdir(parents=True, exist_ok=True)
            src = Path(snapshot_path)
            dst = dst_root / src.name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            # Also copy the raw SQLite databases for fast restore
            for db_name in ("session_memory.db", "persistent_memory.db"):
                db_src = Path("./memory") / db_name
                if db_src.exists():
                    shutil.copy2(db_src, dst_root / db_name)
            print(f"[OFFSITE] Synced to {dst}")
        except Exception as e:
            print(f"[OFFSITE] Sync failed: {e}")

    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore memory from backup"""
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            print(f"Backup not found: {backup_path}")
            return False

        try:
            print(f"[RESTORE] Restoring from backup: {backup_dir.name}")

            # Restore memory layers
            layers_dir = backup_dir / "layers"
            if layers_dir.exists():
                self._restore_memory_layers(layers_dir)

            print("[OK] Memory restoration complete")
            return True

        except Exception as e:
            print(f"[ERROR] Memory restoration failed: {e}")
            return False

    def _restore_memory_layers(self, layers_dir: Path):
        """Restore memory layers from backup"""
        for layer_name in self.memory_system.layers.keys():
            layer_backup = layers_dir / f"{layer_name}_layer.json"

            if layer_backup.exists():
                try:
                    with open(layer_backup, 'r') as f:
                        data = json.load(f)

                    if layer_name == "ephemeral":
                        for key, item in data.items():
                            self.memory_system.layers[layer_name].store(
                                key,
                                item['data'],
                                item.get('metadata', {})
                            )

                    elif layer_name == "session":
                        # Session is now SQLite — restore via store()
                        for key, item in data.items():
                            self.memory_system.layers[layer_name].store(
                                key,
                                item.get('data'),
                                item.get('metadata', {})
                            )

                    print(f"  [OK] {layer_name} layer restored")

                except Exception as e:
                    print(f"  [ERROR] {layer_name} layer restore failed: {e}")

            # Restore persistent database
            if layer_name == "persistent":
                db_backup = layers_dir / "persistent_memory.db"
                if db_backup.exists():
                    try:
                        shutil.copy2(
                            db_backup,
                            Path(
                                self.memory_system
                                .layers[layer_name].db_path
                            ),
                        )
                        print(
                            "  [OK] Persistent"
                            " database restored",
                        )
                    except Exception as e:
                        print(
                            "  [ERROR] Persistent"
                            f" database restore failed: {e}",
                        )

    def get_backup_status(self) -> Dict:
        """Get backup system status"""
        backups = list(self.backup_dir.glob("memory_snapshot_*"))
        backups.sort(reverse=True)  # Newest first

        return {
            'running': self.running,
            'backup_interval': self.backup_interval,
            'max_backups': self.max_backups,
            'total_backups': len(backups),
            'last_backup': (
                self.last_backup.isoformat()
                if self.last_backup else None
            ),
            'latest_backup': backups[0].name if backups else None,
            'oldest_backup': backups[-1].name if backups else None,
            'backup_disk_usage': self._calculate_backup_size()
        }

    def _calculate_backup_size(self) -> str:
        """Calculate total backup disk usage"""
        try:
            total_size: float = sum(
                sum(f.stat().st_size for f in backup.rglob('*') if f.is_file())
                for backup in self.backup_dir.glob("memory_snapshot_*")
            )

            # Convert to human readable
            for unit in ['B', 'KB', 'MB', 'GB']:
                if total_size < 1024:
                    return f"{total_size:.1f} {unit}"
                total_size = total_size / 1024

            return f"{total_size:.1f} TB"

        except OSError:
            return "Unknown"

    def force_backup_now(self) -> str | None:
        """Force an immediate backup."""
        if not self.running:
            print("Backup system not running")
            return None

        try:
            return self.create_backup_snapshot()
        except Exception as e:
            print(f"Force backup failed: {e}")
            return None


# Global instance
_continuous_backup: ContinuousMemoryBackup | None = None


def get_continuous_backup_system() -> ContinuousMemoryBackup:
    """Get or create continuous backup system."""
    global _continuous_backup
    if _continuous_backup is None:
        _continuous_backup = ContinuousMemoryBackup()
    return _continuous_backup


def start_memory_backup():
    """Start continuous memory backup."""
    return get_continuous_backup_system().start_continuous_backup()


def stop_memory_backup():
    """Stop continuous memory backup."""
    return get_continuous_backup_system().stop_continuous_backup()


def force_memory_backup():
    """Force immediate memory backup."""
    return get_continuous_backup_system().force_backup_now()


def get_backup_status():
    """Get backup system status."""
    return get_continuous_backup_system().get_backup_status()


def restore_memory_from_backup(backup_path: str):
    """Restore memory from backup."""
    return get_continuous_backup_system().restore_from_backup(
        backup_path,
    )


if __name__ == "__main__":
    print("[BACKUP] Testing Continuous Memory Backup System...")

    # Start backup system
    backup_system = get_continuous_backup_system()
    backup_system.start_continuous_backup()

    # Force a backup
    backup_path = backup_system.force_backup_now()
    if backup_path:
        print(f"Backup created: {backup_path}")

    # Get status
    status = backup_system.get_backup_status()
    print("Backup Status:", json.dumps(status, indent=2, default=str))

    # Test restore (commented out to avoid accidental data loss)
    # if backup_path:
    #     success = backup_system.restore_from_backup(backup_path)
    #     print(f"Restore successful: {success}")

    # Stop backup
    time.sleep(2)  # Let it run briefly
    backup_system.stop_continuous_backup()

    print("[OK] Continuous Memory Backup System test complete!")
