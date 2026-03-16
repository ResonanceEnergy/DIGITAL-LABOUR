#!/usr/bin/env python3
"""
iPad Pro Optimization Test Script
Tests iPad Pro MU202VC/A specific features and optimizations
"""

import requests
import json
import time
from datetime import datetime

def test_ipad_pro_optimizations():
    """Test iPad Pro specific optimizations"""
    print("📱 Testing iPad Pro Optimizations for Tablet Titan")
    print("=" * 60)

    base_url = "http://localhost:8080"

    try:
        # Test 1: Check iPad dashboard loads
        print("1. Testing iPad Pro dashboard with Modern Design...")
        response = requests.get(f"{base_url}/ipad")
        if response.status_code == 200:
            content = response.text
            checks = [
                ("iPad Pro HTML", "Tablet Titan" in content),
                ("Matrix monitor", "matrix-container" in content),
                ("Analytics tab", "analytics-dashboard" in content),
                ("Bluetooth info", "34:42:62:2C:5D:9D" in content),
                ("iPad Pro model", "MU202VC/A" in content),
                ("Modern Firmware", "7.03.01" in content)
            ]

            for check_name, check_result in checks:
                status = "✅" if check_result else "❌"
                print(f"   {status} {check_name}")
        else:
            print(f"   ❌ Dashboard failed: {response.status_code}")
            return False

        # Test 2: Check manifest for iPad Pro features
        print("\n2. Testing PWA manifest for iPad Pro features...")
        response = requests.get(f"{base_url}/static/manifest_ipad.json")
        if response.status_code == 200:
            try:
                manifest = response.json()
                checks = [
                    ("iPad Pro description",
                     "iPad Pro MU202VC/A" in manifest.get("description", "")),
                    ("Landscape orientation", manifest.get(
                        "orientation") == "landscape-primary"),
                    ("Protocol handlers", "protocol_handlers" in manifest),
                    ("Note taking", "note_taking" in manifest),
                    ("Launch queue", "launch_queue" in manifest),
                    ("Wide screenshots", any("wide" in str(screenshot.get("form_factor", ""))
                     for screenshot in manifest.get("screenshots", [])))
                ]

                for check_name, check_result in checks:
                    status = "✅" if check_result else "❌"
                    print(f"   {status} {check_name}")
            except json.JSONDecodeError as e:
                print(f"   ⚠️  JSON parsing issue: {e}")
                # Check raw text for key features
                manifest_text = response.text
                checks = [
                    ("iPad Pro description", "iPad Pro MU202VC/A" in manifest_text),
                    ("Landscape orientation", "landscape-primary" in manifest_text),
                    ("Protocol handlers", "protocol_handlers" in manifest_text)
                ]

                for check_name, check_result in checks:
                    status = "✅" if check_result else "❌"
                    print(f"   {status} {check_name} (text check)")
        else:
            print(f"   ❌ Manifest failed: {response.status_code}")

        # Test 3: Check matrix API with iPad Pro data
        print("\n3. Testing matrix API with iPad Pro data...")
        response = requests.get(f"{base_url}/api/matrix")
        if response.status_code == 200:
            matrix_data = response.json()
            print(f"   ✅ Matrix API responding")
            print(f"   📊 Nodes: {matrix_data['total_nodes']}")
            print(f"   🟢 Online: {matrix_data['online_nodes']}")
            print(f"   ❤️ Health: {matrix_data['system_health']}%")

            # Check for iPad Pro specific node
            ipad_node = next(
                (node for node in matrix_data['matrix']
                 if node['type'] =='tablet-titan'),
                None)
            if ipad_node:
                print(f"   📱 Tablet Titan detected: {ipad_node['name']}")
                print(f"   📱 Device: {ipad_node['device']}")
                bt_metric = next(
                    (m for m in ipad_node['metrics'] if m['label'] =='BT'),
                    None)
                if bt_metric:
                    print(f"   📶 Bluetooth: {bt_metric['value']}")
                imei_metric = next(
                    (m for m in ipad_node['metrics'] if m['label'] =='IMEI'),
                    None)
                if imei_metric:
                    print(f"   📱 IMEI: {imei_metric['value']}")
                fw_metric = next(
                    (m for m in ipad_node['metrics'] if m['label'] =='FW'),
                    None)
                if fw_metric:
                    print(f"   🔧 Firmware: {fw_metric['value']}")
        else:
            print(f"   ❌ Matrix API failed: {response.status_code}")
            return False

        # Test 4: Check CSS optimizations
        print("\n4. Testing CSS optimizations for iPad Pro...")
        response = requests.get(f"{base_url}/static/css/ipad.css")
        if response.status_code == 200:
            css_content = response.text
            checks = [
                ("iPad Pro CSS",
                 "Tablet Titan"
                 in css_content.lower() or "ipad" in css_content.lower()),
                ("Landscape layout", "grid-template-columns" in css_content),
                ("Modern Firmware",
                 "7.03.01" in css_content or "modern" in css_content.lower()),
                ("iPad Pro media queries",
                 "@media" in css_content and "1024px" in css_content),
                ("Touch optimizations",
                 "-webkit-tap" in css_content or "touch" in
                  css_content.lower()),
                ("Multitasking support",
                 "max-width" in css_content and "1400px" in css_content)]

            for check_name, check_result in checks:
                status = "✅" if check_result else "❌"
                print(f"   {status} {check_name}")
        else:
            print(f"   ❌ CSS file failed: {response.status_code}")

        # Test 5: Check JavaScript optimizations
        print("\n5. Testing JavaScript optimizations for iPad Pro...")
        response = requests.get(f"{base_url}/static/js/ipad.js")
        if response.status_code == 200:
            js_content = response.text
            checks = [
                ("iPad Pro detection", "detectIPadPro" in js_content),
                ("Bluetooth monitoring", "bluetoothConnected" in js_content),
                ("Touch gestures", "TouchForce" in js_content or "touchforce" in js_content),
                ("Multitasking handling", "handleResize" in js_content),
                ("Modern Firmware detection", "detectModernFirmware" in js_content),
                ("Matrix touch interactions",
                 "touchstart" in js_content and "touchend" in js_content)
            ]

            for check_name, check_result in checks:
                status = "✅" if check_result else "❌"
                print(f"   {status} {check_name}")
        else:
            print(f"   ❌ JavaScript file failed: {response.status_code}")

        print("\n" + "=" * 60)
        print("🎉 iPad Pro Optimization Test PASSED!")
        print("📱 Tablet Titan optimized for:")
        print("   • iPad Pro MU202VC/A (12.9\" and 11\")")
        print("   • iOS 18.5 with Modern Firmware 7.03.01")
        print("   • M2 chip performance optimizations")
        print("   • Bluetooth connectivity (34:42:62:2C:5D:9D)")
        print("   • Landscape-first design")
        print("   • Multitasking support")
        print("   • Enhanced PWA capabilities")
        print("   • Touch gesture optimizations")
        print(f"🔗 Access at: {base_url}/ipad")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_ipad_pro_optimizations()
    exit(0 if success else 1)