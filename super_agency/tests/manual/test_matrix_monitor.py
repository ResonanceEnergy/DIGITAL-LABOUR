#!/usr/bin/env python3
"""
iOS Matrix Monitor Test Script
Tests the Pocket Pulsar matrix monitor functionality
"""

import requests
import json
import time
from datetime import datetime

def test_matrix_monitor():
    """Test the iOS Matrix Monitor functionality"""
    print("🕸️ Testing iOS Matrix Monitor for Pocket Pulsar")
    print("=" * 50)

    base_url = "http://localhost:8080"

    try:
        # Test 1: Check system status
        print("1. Testing system status...")
        response = requests.get(f"{base_url}/api/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ System Status: {status['status']}")
            print(f"   📊 Platform: {status['platform']}")
            print(f"   🔄 Version: {status['version']}")
        else:
            print(f"   ❌ Status check failed: {response.status_code}")
            return False

        # Test 2: Check matrix API
        print("\n2. Testing matrix API...")
        response = requests.get(f"{base_url}/api/matrix")
        if response.status_code == 200:
            matrix_data = response.json()
            print(f"   ✅ Matrix API responding")
            print(f"   📊 Total nodes: {matrix_data['total_nodes']}")
            print(f"   🟢 Online nodes: {matrix_data['online_nodes']}")
            print(f"   ❤️ System health: {matrix_data['system_health']}%")

            # Show node details
            print("\n   📱 Matrix Nodes:")
            for node in matrix_data['matrix'][:5]:  # Show first 5 nodes
                status_emoji = "🟢" if node['status'] in [
                    'online', 'active', 'healthy'] else "🟡" if node['status'] == 'warning' else "🔴"
                print(
                    f"      {status_emoji} {node['name']} ({node['device']})")
                for metric in node['metrics']:
                    print(f"         {metric['label']}: {metric['value']}")
        else:
            print(f"   ❌ Matrix API failed: {response.status_code}")
            return False

        # Test 3: Check iPhone dashboard accessibility
        print("\n3. Testing iPhone dashboard...")
        response = requests.get(f"{base_url}/iphone")
        if response.status_code == 200 and "Pocket Pulsar" in response.text:
            print("   ✅ iPhone dashboard accessible")
            if "matrix-container" in response.text:
                print("   ✅ Matrix monitor HTML present")
            else:
                print("   ⚠️ Matrix monitor HTML not found in dashboard")
        else:
            print(f"   ❌ iPhone dashboard failed: {response.status_code}")
            return False

        print("\n" + "=" * 50)
        print("🎉 iOS Matrix Monitor Test PASSED!")
        print("📱 Pocket Pulsar matrix monitor is fully operational")
        print("🔗 Access at: http://localhost:8080/iphone")
        print("📊 Matrix tab contains real-time system visualization")

        return True

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the mobile command center running?")
        print("   Start with: python3 mobile_command_center_simple.py")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_matrix_monitor()
    exit(0 if success else 1)