#!/usr/bin/env python3
"""
BIT RAGE LABOUR Cross-Platform Refresh System
5-minute automated sync between Quantum Quasar (macOS) and QUANTUM FORGE (Windows)

Features:
- Git status checks and auto-pull
- Cross-platform status synchronization
- Health monitoring updates
- Shared state refresh
- Error handling and logging
"""

import subprocess
import sys
import os
import platform
import json
from datetime import datetime
from pathlib import Path
import time

class CrossPlatformRefresher:
    """Handles 5-minute refresh cycles between Quantum Quasar and QUANTUM FORGE"""

    def __init__(self):
        """Initialize."""
        self.system_name = "Quantum Quasar" if platform.system() == "Darwin" else "QUANTUM FORGE"
        self.workspace_root = Path(__file__).parent  # Use script's directory
        self.status_file = self.workspace_root / "cross_platform_status.json"
        self.log_file = self.workspace_root / "logs" / "cross_platform_refresh.log"

        # Ensure log directory exists
        self.log_file.parent.mkdir(exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{self.system_name}] [{level}] {message}"

        print(log_entry)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

    def run_command(self, cmd: list, cwd: Path = None) -> tuple:
        """Run a command and return (success, output, error)"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.workspace_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def check_git_status(self) -> dict:
        """Check git repository status"""
        self.log("Checking git status...")

        status = {
            'local_changes': False,
            'remote_updates': False,
            'current_branch': 'unknown',
            'last_commit': 'unknown'
        }

        # Check if we're in a git repo
        success, _, _ = self.run_command(['git', 'rev-parse', '--git-dir'])
        if not success:
            self.log("Not in a git repository", "WARNING")
            return status

        # Get current branch
        success, branch, _ = self.run_command(['git', 'branch', '--show-current'])
        if success:
            status['current_branch'] = branch

        # Check for local changes
        success, changes, _ = self.run_command(['git', 'status', '--porcelain'])
        status['local_changes'] = bool(changes.strip())

        # Check for remote updates
        success, remote_status, _ = self.run_command(['git', 'fetch', '--dry-run'])
        if success and remote_status.strip():
            status['remote_updates'] = True

        # Get last commit info
        success, commit_info, _ = self.run_command(['git', 'log', '-1', '--oneline'])
        if success:
            status['last_commit'] = commit_info

        return status

    def sync_git_changes(self) -> bool:
        """Sync git changes if safe to do so"""
        self.log("Attempting git sync...")

        git_status = self.check_git_status()

        if git_status['local_changes']:
            self.log("Local changes detected - skipping auto-pull to avoid conflicts", "WARNING")
            return False

        if not git_status['remote_updates']:
            self.log("No remote updates detected")
            return True

        # Safe to pull
        self.log("Pulling remote changes...")
        success, output, error = self.run_command(['git', 'pull', 'origin', git_status['current_branch']])

        if success:
            self.log(f"Successfully pulled changes: {output}")
            return True
        else:
            self.log(f"Failed to pull changes: {error}", "ERROR")
            return False

    def update_shared_status(self) -> dict:
        """Update shared status file with current system state"""
        self.log("Updating shared status...")

        status = {
            'system': self.system_name,
            'timestamp': datetime.now().isoformat(),
            'platform': platform.system(),
            'python_version': sys.version.split()[0],
            'git_status': self.check_git_status(),
            'workspace_path': str(self.workspace_root),
            'last_refresh': datetime.now().isoformat()
        }

        # Try to get some basic system info
        try:
            import psutil
            status['cpu_percent'] = psutil.cpu_percent(interval=1)
            status['memory_percent'] = psutil.virtual_memory().percent
        except ImportError:
            status['system_info'] = 'psutil not available'

        # Write to shared status file
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
            self.log(f"Updated shared status file: {self.status_file}")
        except Exception as e:
            self.log(f"Failed to update status file: {e}", "ERROR")

        return status

    def check_peer_status(self) -> dict:
        """Check the status from the other system"""
        peer_status = {}

        if self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Find the other system's status
                peer_system = "QUANTUM FORGE" if self.system_name == "Quantum Quasar" else "Quantum Quasar"

                if data.get('system') == peer_system:
                    peer_status = data
                    age_seconds = (datetime.now() - datetime.fromisoformat(data['timestamp'])).total_seconds()
                    peer_status['age_seconds'] = age_seconds
                    peer_status['is_recent'] = age_seconds < 600  # 10 minutes

                    self.log(f"Peer status: {peer_system} - {age_seconds:.0f}s ago")

                    if not peer_status['is_recent']:
                        self.log(f"Peer status is stale (>10 minutes)", "WARNING")
                else:
                    self.log(f"No peer status found for {peer_system}")

            except Exception as e:
                self.log(f"Error reading peer status: {e}", "ERROR")

        return peer_status

    def perform_health_checks(self) -> dict:
        """Perform basic health checks"""
        self.log("Running health checks...")

        health = {
            'git_accessible': False,
            'workspace_readable': False,
            'logs_writable': False,
            'network_connectivity': False
        }

        # Check git access
        success, _, _ = self.run_command(['git', '--version'])
        health['git_accessible'] = success

        # Check workspace readability
        health['workspace_readable'] = self.workspace_root.exists() and self.workspace_root.is_dir()

        # Check log file writability
        try:
            with open(self.log_file, 'a') as f:
                f.write('')
            health['logs_writable'] = True
        except:
            health['logs_writable'] = False

        # Check network connectivity (simple ping test)
        if platform.system() == 'Windows':
            success, _, _ = self.run_command(['ping', '-n', '1', '-w', '2000', '8.8.8.8'])
        else:
            success, _, _ = self.run_command(['ping', '-c', '1', '-W', '2', '8.8.8.8'])
        health['network_connectivity'] = success

        # Log health status
        issues = [k for k, v in health.items() if not v]
        if issues:
            self.log(f"Health check issues: {', '.join(issues)}", "WARNING")
        else:
            self.log("All health checks passed")

        return health

    def run_refresh_cycle(self):
        """Execute the complete 5-minute refresh cycle"""
        self.log("=== Starting Cross-Platform Refresh Cycle ===")

        try:
            # 1. Health checks
            health = self.perform_health_checks()

            # 2. Git sync
            git_success = self.sync_git_changes()

            # 3. Update shared status
            status = self.update_shared_status()

            # 4. Check peer status
            peer_status = self.check_peer_status()

            # 5. Summary
            summary = {
                'timestamp': datetime.now().isoformat(),
                'system': self.system_name,
                'git_sync_success': git_success,
                'health_checks': health,
                'peer_status': peer_status
            }

            self.log("=== Refresh Cycle Complete ===")
            git_status = '✓' if git_success else '✗'
            health_status = '✓' if all(health.values()) else '✗'
            self.log(f"Summary: Git sync {git_status}, Health {health_status}")

            return True, summary

        except Exception as e:
            self.log(f"Refresh cycle failed: {e}", "ERROR")
            return False, {'error': str(e)}

def main():
    """Main entry point for cross-platform refresh"""
    refresher = CrossPlatformRefresher()

    try:
        success, summary = refresher.run_refresh_cycle()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        refresher.log("Refresh interrupted by user")
        sys.exit(1)
    except Exception as e:
        refresher.log(f"Unexpected error: {e}", "ERROR")
        sys.exit(1)

if __name__ == '__main__':
    main()
