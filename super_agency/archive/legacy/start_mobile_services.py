#!/usr/bin/env python3
"""
Super Agency Mobile Services Launcher
Starts Matrix Maximizer and Mobile Command Center for iPhone/iPad testing
"""

import subprocess
import sys
import time
import threading
import signal
import os
from pathlib import Path

class MobileServicesLauncher:
    """Launcher for Super Agency mobile services"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.processes = []
        self.threads = []

    def start_matrix_maximizer(self):
        """Start Matrix Maximizer on port 3000"""
        print("🚀 Starting Matrix Maximizer on port 3000...")
        try:
            cmd = [sys.executable, str(self.base_dir / "matrix_maximizer.py")]
            process = subprocess.Popen(
                cmd,
                cwd=self.base_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(process)
            print("✅ Matrix Maximizer started")
            return True
        except Exception as e:
            print(f"❌ Failed to start Matrix Maximizer: {e}")
            return False

    def start_mobile_command_center(self):
        """Start Mobile Command Center on port 8081"""
        print("📱 Starting Mobile Command Center on port 8081...")
        try:
            cmd = [sys.executable, str(self.base_dir / "mobile_command_center_simple.py")]
            process = subprocess.Popen(
                cmd,
                cwd=self.base_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(process)
            print("✅ Mobile Command Center started")
            return True
        except Exception as e:
            print(f"❌ Failed to start Mobile Command Center: {e}")
            return False

    def test_services(self):
        """Test that services are responding"""
        import requests

        print("\n🧪 Testing Services...")

        # Test Matrix Maximizer
        try:
            response = requests.get("http://localhost:3000/", timeout=5)
            if response.status_code == 200:
                print("✅ Matrix Maximizer: Responding on port 3000")
            else:
                print(f"❌ Matrix Maximizer: HTTP {response.status_code}")
        except:
            print("❌ Matrix Maximizer: Not responding")

        # Test Mobile Command Center
        try:
            response = requests.get("http://localhost:8081/", timeout=5)
            if response.status_code == 200:
                print("✅ Mobile Command Center: Responding on port 8081")
            else:
                print(f"❌ Mobile Command Center: HTTP {response.status_code}")
        except:
            print("❌ Mobile Command Center: Not responding")

        # Test iPhone interface
        try:
            response = requests.get("http://localhost:8081/iphone", timeout=5)
            if response.status_code == 200:
                html = response.text
                if "Pocket Pulsar" in html and "iphone.css" in html:
                    print("✅ iPhone Interface: Working with optimizations")
                else:
                    print("⚠️ iPhone Interface: Basic response (missing optimizations)")
            else:
                print(f"❌ iPhone Interface: HTTP {response.status_code}")
        except:
            print("❌ iPhone Interface: Not responding")

    def run_departmental_orchestrator(self):
        """Run the departmental orchestrator"""
        print("🏢 Running Departmental Operations Orchestrator...")
        try:
            cmd = [sys.executable, str(self.base_dir / "agents" / "orchestrator.py")]
            result = subprocess.run(cmd, cwd=self.base_dir, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("✅ Departmental Orchestrator: Completed successfully")
                return True
            else:
                print(f"❌ Departmental Orchestrator: Failed with code {result.returncode}")
                print(f"Error: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Departmental Orchestrator: Exception - {e}")
            return False

    def start_all_services(self):
        """Start all Super Agency mobile services"""
        print("🎯 Starting Super Agency Mobile Services")
        print("=" * 50)

        success_count = 0

        # Start Matrix Maximizer in background
        if self.start_matrix_maximizer():
            success_count += 1
            time.sleep(2)  # Wait for startup

        # Start Mobile Command Center in background
        if self.start_mobile_command_center():
            success_count += 1
            time.sleep(2)  # Wait for startup

        # Run departmental orchestrator
        if self.run_departmental_orchestrator():
            success_count += 1

        # Test services
        time.sleep(3)  # Wait for services to be ready
        self.test_services()

        print(f"\n📊 Services Started: {success_count}/3")
        print("🔗 Access Points:")
        print("   🧠 Matrix Maximizer: http://localhost:3000")
        print("   📱 Mobile Command Center: http://localhost:8081")
        print("   📱 iPhone UI: http://localhost:8081/iphone")
        print("   📱 iPad UI: http://localhost:8081/ipad")
        print("   🖥️ Desktop UI: http://localhost:8081/desktop")

        if success_count >= 2:
            print("\n✅ Super Agency Mobile Services: OPERATIONAL")
        else:
            print("\n❌ Super Agency Mobile Services: ISSUES DETECTED")

        return success_count >= 2

    def stop_services(self):
        """Stop all running services"""
        print("\n🛑 Stopping services...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        print("✅ Services stopped")

def main():
    """Main launcher function"""
    launcher = MobileServicesLauncher()

    def signal_handler(signum, frame):
        print("\n🛑 Shutdown requested...")
        launcher.stop_services()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        success = launcher.start_all_services()

        if success:
            print("\n⏳ Services running... Press Ctrl+C to stop")
            # Keep running until interrupted
            while True:
                time.sleep(1)
        else:
            print("\n❌ Service startup failed")
            sys.exit(1)

    except KeyboardInterrupt:
        launcher.stop_services()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        launcher.stop_services()
        sys.exit(1)

if __name__ == "__main__":
    main()