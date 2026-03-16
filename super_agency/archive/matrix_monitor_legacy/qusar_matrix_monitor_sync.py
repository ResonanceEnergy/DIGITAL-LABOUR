#!/usr/bin/env python3
"""
QUSAR Matrix Monitor Sync
Ping Quantum Quasar (QUSAR) for latest Matrix Monitor files
"""

import socket
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import requests

class QUSARMatrixMonitorSync:
    """Sync Matrix Monitor data with Quantum Quasar (QUSAR)"""

    def __init__(self):
        self.qusar_host = "192.168.1.100"  # Quantum Quasar IP address
        self.qusar_port = 8888  # SASP port
        self.matrix_monitor_endpoint = "/api/matrix-monitor"
        self.timeout = 30

    def ping_qusar(self) -> Dict[str, Any]:
        """Ping QUSAR to check availability and get system status"""
        try:
            print("🔗 Pinging QUSAR (Quantum Quasar)...")

            # Create ping message
            ping_data = {
                "message_type": "ping",
                "source": "QUANTUM FORGE",
                "timestamp": datetime.now().isoformat(),
                "request": "matrix_monitor_sync"
            }

            # Try to connect to QUSAR SASP service
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)

            try:
                sock.connect((self.qusar_host, self.qusar_port))
                print(f"✅ Connected to QUSAR on port {self.qusar_port}")

                # Send ping
                ping_json = json.dumps(ping_data).encode('utf-8')
                sock.send(ping_json)

                # Receive response
                response = sock.recv(4096).decode('utf-8')
                response_data = json.loads(response)

                print(f"📡 QUSAR Response: {response_data.get('status', 'unknown')}")
                return response_data

            except socket.error as e:
                print(f"❌ Socket connection failed: {e}")
                return {"status": "connection_failed", "error": str(e)}

            finally:
                sock.close()

        except Exception as e:
            print(f"❌ Ping failed: {e}")
            return {"status": "error", "error": str(e)}

    def request_matrix_monitor_files(self) -> Dict[str, Any]:
        """Request latest Matrix Monitor files from QUSAR"""
        try:
            print("📊 Requesting Matrix Monitor files from QUSAR...")

            # Try HTTP request first (if Matrix Monitor has web interface)
            try:
                url = f"http://{self.qusar_host}:3000{self.matrix_monitor_endpoint}"
                print(f"🌐 Trying HTTP request to: {url}")

                response = requests.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Matrix Monitor data retrieved via HTTP")
                    return {
                        "status": "success",
                        "method": "http",
                        "data": data,
                        "timestamp": datetime.now().isoformat()
                    }
            except requests.RequestException as e:
                print(f"⚠️ HTTP request failed: {e}")

            # Fallback to SASP protocol
            print("🔄 Falling back to SASP protocol...")

            request_data = {
                "message_type": "data_request",
                "source": "QUANTUM FORGE",
                "timestamp": datetime.now().isoformat(),
                "request_type": "matrix_monitor_files",
                "data_types": ["dashboard_data", "metrics", "visual_components"]
            }

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)

            try:
                sock.connect((self.qusar_host, self.qusar_port))

                # Send request
                request_json = json.dumps(request_data).encode('utf-8')
                sock.send(request_json)

                # Receive response
                response = sock.recv(65536).decode('utf-8')
                response_data = json.loads(response)

                print("✅ Matrix Monitor files received via SASP")
                return {
                    "status": "success",
                    "method": "sasp",
                    "data": response_data,
                    "timestamp": datetime.now().isoformat()
                }

            except socket.error as e:
                print(f"❌ SASP request failed: {e}")
                return {"status": "connection_failed", "error": str(e)}

            finally:
                sock.close()

        except Exception as e:
            print(f"❌ Request failed: {e}")
            return {"status": "error", "error": str(e)}

    def save_matrix_monitor_data(self, data: Dict[str, Any]) -> bool:
        """Save received Matrix Monitor data to local files"""
        try:
            if data.get("status") != "success":
                print("❌ No valid data to save")
                return False

            # Create dashboard_data directory if it doesn't exist
            dashboard_dir = Path("dashboard_data")
            dashboard_dir.mkdir(exist_ok=True)

            # Save the data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"qusar_matrix_monitor_{timestamp}.json"
            filepath = dashboard_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"💾 Matrix Monitor data saved to: {filepath}")

            # Also save as latest
            latest_file = dashboard_dir / "qusar_matrix_monitor_latest.json"
            with open(latest_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"🔄 Latest data also saved to: {latest_file}")
            return True

        except Exception as e:
            print(f"❌ Failed to save data: {e}")
            return False

    def sync_matrix_monitor(self) -> Dict[str, Any]:
        """Complete sync process: ping QUSAR and get Matrix Monitor files"""
        print("🚀 Starting QUSAR Matrix Monitor Sync...")
        print("=" * 50)

        # Step 1: Ping QUSAR
        ping_result = self.ping_qusar()
        if ping_result.get("status") not in ["active", "ready", "success"]:
            return {
                "sync_status": "failed",
                "step": "ping",
                "error": "QUSAR not available",
                "ping_result": ping_result
            }

        # Step 2: Request Matrix Monitor files
        sync_result = self.request_matrix_monitor_files()
        if sync_result.get("status") != "success":
            return {
                "sync_status": "failed",
                "step": "request",
                "error": "Failed to get Matrix Monitor files",
                "ping_result": ping_result,
                "sync_result": sync_result
            }

        # Step 3: Save data
        save_success = self.save_matrix_monitor_data(sync_result)

        # Return complete result
        result = {
            "sync_status": "success" if save_success else "partial_success",
            "timestamp": datetime.now().isoformat(),
            "qusar_status": ping_result,
            "matrix_monitor_data": sync_result,
            "data_saved": save_success
        }

        print("=" * 50)
        if save_success:
            print("✅ QUSAR Matrix Monitor Sync completed successfully!")
        else:
            print("⚠️ Sync completed but data save failed")

        return result

def main():
    """Main sync function"""
    sync = QUSARMatrixMonitorSync()
    result = sync.sync_matrix_monitor()

    # Print summary
    print("\n📋 Sync Summary:")
    print(f"Status: {result.get('sync_status', 'unknown')}")
    print(f"Timestamp: {result.get('timestamp', datetime.now().isoformat())}")

    if result.get('sync_status') == 'success':
        print("✅ Matrix Monitor data successfully synced from QUSAR")
    else:
        print(f"❌ Sync failed at step: {result.get('step', 'unknown')}")
        if 'error' in result:
            print(f"Error: {result['error']}")

if __name__ == "__main__":
    main()
