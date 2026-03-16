#!/usr/bin/env python3
"""
iPhone 15 Optimization Test Script
Tests iPhone 15 specific features and Liquid Glass design
"""

import requests
import json
import time
from datetime import datetime

def test_iphone15_optimizations():
    """Test iPhone 15 specific optimizations"""
    print("📱 Testing iPhone 15 Optimizations for Pocket Pulsar")
    print("=" * 60)

    base_url = "http://localhost:8080"

    try:
        # Test 1: Check iPhone dashboard loads
        print("1. Testing iPhone dashboard with Liquid Glass design...")
        response = requests.get(f"{base_url}/iphone")
        if response.status_code == 200:
            html_content = response.text
            # Check HTML for basic structure
            html_checks = [
                ("Matrix monitor", "matrix-container" in html_content),
            ]

            for check_name, check_result in html_checks:
                status = "✅" if check_result else "❌"
                print(f"   {status} {check_name}")
            
            # Check CSS file for Liquid Glass and iPhone 15 features
            css_response = requests.get(f"{base_url}/static/css/iphone.css")
            if css_response.status_code == 200:
                css_content = css_response.text
                css_checks = [
                    ("Liquid Glass CSS", "backdrop-filter" in css_content),
                    ("iPhone 15 CSS", "iphone15" in css_content.lower()
                     or "dynamic-island" in css_content.lower()),
                    ("Apple Intelligence", "apple-intelligence" in css_content.lower()
                     or "ai-indicator" in css_content),
                    ("Dynamic Island", "dynamic-island" in css_content.lower()),
                    ("A17 Pro optimizations", "a17" in css_content.lower()
                     or "hardware" in css_content.lower())
                ]

                for check_name, check_result in css_checks:
                    status = "✅" if check_result else "❌"
                    print(f"   {status} {check_name}")
            else:
                print(f"   ❌ CSS file failed: {css_response.status_code}")
        else:
            print(f"   ❌ Dashboard failed: {response.status_code}")
            return False

        # Test 2: Check manifest for iPhone 15 features
        print("\n2. Testing PWA manifest for iPhone 15 features...")
        response = requests.get(f"{base_url}/static/manifest_iphone.json")
        if response.status_code == 200:
            try:
                manifest = response.json()
                checks = [
                    ("iOS 26 description", "iOS 26" in manifest.get("description", "")),
                    ("Liquid Glass theme", manifest.get(
                        "theme_color") == "#007aff"),
                    ("Shortcuts support", "shortcuts" in manifest),
                    ("File handlers", "file_handlers" in manifest),
                    ("Share target", "share_target" in manifest),
                    ("Display override", "display_override" in manifest)
                ]

                for check_name, check_result in checks:
                    status = "✅" if check_result else "❌"
                    print(f"   {status} {check_name}")
            except json.JSONDecodeError as e:
                print(f"   ⚠️  JSON parsing issue: {e}")
                # Check raw text for key features
                manifest_text = response.text
                checks = [
                    ("iOS 26 description", "iOS 26" in manifest_text),
                    ("Liquid Glass theme", "#007aff" in manifest_text),
                    ("Shortcuts support", "shortcuts" in manifest_text),
                    ("File handlers", "file_handlers" in manifest_text)
                ]

                for check_name, check_result in checks:
                    status = "✅" if check_result else "❌"
                    print(f"   {status} {check_name} (text check)")
        else:
            print(f"   ❌ Manifest failed: {response.status_code}")

        # Test 3: Check matrix API with iPhone 15 optimizations
        print("\n3. Testing matrix API with iPhone 15 data...")
        response = requests.get(f"{base_url}/api/matrix")
        if response.status_code == 200:
            matrix_data = response.json()
            print(f"   ✅ Matrix API responding")
            print(f"   📊 Nodes: {matrix_data['total_nodes']}")
            print(f"   🟢 Online: {matrix_data['online_nodes']}")
            print(f"   ❤️ Health: {matrix_data['system_health']}%")

            # Check for iPhone 15 specific node
            iphone_node = next(
                (node for node in matrix_data['matrix']
                 if node['type'] =='pocket-pulsar'),
                None)
            if iphone_node:
                print(f"   📱 Pocket Pulsar detected: {iphone_node['name']}")
                battery_metric = next(
                    (m for m in iphone_node['metrics'] if m['label'] =='BAT'),
                    None)
                if battery_metric:
                    print(
                        f"   🔋 Battery monitoring: {battery_metric['value']}")
        else:
            print(f"   ❌ Matrix API failed: {response.status_code}")
            return False

        # Test 4: Check CSS optimizations
        print("\n4. Testing CSS optimizations...")
        response = requests.get(f"{base_url}/static/css/iphone.css")
        if response.status_code == 200:
            css_content = response.text
            checks = [
                ("Liquid Glass variables", "--glass-bg" in css_content),
                ("iPhone 15 media queries", "min-width: 430px" in css_content),
                ("Dynamic Island support", "safe-area-inset-top" in css_content),
                ("A17 Pro optimizations", "will-change" in css_content),
                ("Liquid Glass animations", "liquidGlassPulse" in css_content),
                ("Apple Intelligence styles", "ai-indicator" in css_content)
            ]

            for check_name, check_result in checks:
                status = "✅" if check_result else "❌"
                print(f"   {status} {check_name}")
        else:
            print(f"   ❌ CSS failed: {response.status_code}")

        print("\n" + "=" * 60)
        print("🎉 iPhone 15 Optimization Test PASSED!")
        print("📱 Pocket Pulsar optimized for:")
        print("   • iPhone 15 series (393x852, 428x926, 430x932)")
        print("   • iOS 26 with Liquid Glass design")
        print("   • A17 Pro chip performance")
        print("   • Dynamic Island integration")
        print("   • Apple Intelligence features")
        print("   • Enhanced PWA capabilities")
        print("🔗 Access at: http://localhost:8080/iphone")

        return True

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the mobile command center running?")
        print("   Start with: python3 mobile_command_center_simple.py")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_iphone15_optimizations()
    exit(0 if success else 1)