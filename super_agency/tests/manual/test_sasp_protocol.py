#!/usr/bin/env python3
"""
SASP Protocol Test Script
Tests the DIGITAL LABOUR Share Protocol implementation
"""

import requests
import json
import time
import hmac
import hashlib
from datetime import datetime

# Test configuration
TEST_CONFIG = {
    'mac_ip': '127.0.0.1',  # Local testing
    'mac_port': 8080,
    'shared_secret': 'Digital-Labour-shared-key-2026',
    'protocol': 'SASP',
    'version': '1.0'
}

def create_test_message(message_type, payload):
    """Create a test SASP message"""
    timestamp = datetime.utcnow().isoformat() + 'Z'
    message_id = f"test-{int(time.time())}-{hash(str(time.time())) % 1000}"

    message = {
        'protocol': TEST_CONFIG['protocol'],
        'version': TEST_CONFIG['version'],
        'timestamp': timestamp,
        'message_id': message_id,
        'sender': {
            'type': 'test',
            'id': 'test-client',
            'ip': '127.0.0.1'
        },
        'recipient': {
            'type': 'mac',
            'id': 'mac-hub'
        },
        'message_type': message_type,
        'payload': payload
    }

    # Add signature
    message_copy = {k: v for k, v in message.items() if k != 'signature'}
    json_string = json.dumps(
        message_copy, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        TEST_CONFIG['shared_secret'].encode('utf-8'),
        json_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    message['signature'] = signature
    return message

def test_sasp_health():
    """Test SASP health endpoint"""
    print("🩺 Testing SASP health endpoint...")
    try:
        url = f"http://{
            TEST_CONFIG['mac_ip']}: {
            TEST_CONFIG['mac_port']} /sasp/health"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_sasp_status():
    """Test SASP status message"""
    print("📊 Testing SASP status message...")
    try:
        payload = {
            'system_status': 'testing',
            'services': {
                'test_service': 'running'
            },
            'resources': {
                'cpu_percent': 50.0,
                'memory_used_gb': 2.0
            }
        }

        message = create_test_message('status', payload)
        url = f"http://{
            TEST_CONFIG['mac_ip']}: {
            TEST_CONFIG['mac_port']} /sasp/status"
        response = requests.post(url, json=message, timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status message accepted: {data['status']}")
            return True
        else:
            print(
                f"❌ Status message rejected: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Status message error: {e}")
        return False

def test_sasp_command():
    """Test SASP command endpoint"""
    print("⚡ Testing SASP command endpoint...")
    try:
        payload = {
            'command_id': 'test_command',
            'parameters': {'test_param': 'test_value'}
        }

        message = create_test_message('command', payload)
        url = f"http://{
            TEST_CONFIG['mac_ip']}: {
            TEST_CONFIG['mac_port']} /sasp/command"
        response = requests.post(url, json=message, timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Command sent: {data['command_id']}")
            return True
        else:
            print(
                f"❌ Command failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Command error: {e}")
        return False

def test_invalid_signature():
    """Test invalid signature rejection"""
    print("🔐 Testing invalid signature rejection...")
    try:
        message = create_test_message('status', {'test': 'data'})
        message['signature'] = 'invalid-signature'

        url = f"http://{
            TEST_CONFIG['mac_ip']}: {
            TEST_CONFIG['mac_port']} /sasp/status"
        response = requests.post(url, json=message, timeout=5)

        if response.status_code == 401:
            print("✅ Invalid signature correctly rejected")
            return True
        else:
            print(f"❌ Invalid signature not rejected: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid signature test error: {e}")
        return False

def test_sasp_status_api():
    """Test SASP status API endpoint"""
    print("📈 Testing SASP status API...")
    try:
        url = f"http://{
            TEST_CONFIG['mac_ip']}: {
            TEST_CONFIG['mac_port']} /api/sasp/status"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(
                f"✅ SASP status API working: {len(data.get('windows_nodes', {}))} nodes")
            return True
        else:
            print(f"❌ SASP status API failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ SASP status API error: {e}")
        return False

def main():
    """Run all SASP tests"""
    print("🧪 Starting SASP Protocol Tests")
    print("=" * 40)

    # Check if mobile center is running
    if not test_sasp_health():
        print("❌ Mobile Command Center not running. Start it first:")
        print("   python mobile_command_center.py")
        return

    tests = [
        test_sasp_status,
        test_sasp_command,
        test_invalid_signature,
        test_sasp_status_api
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 40)
    print(f"📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All SASP tests passed!")
    else:
        print("⚠️ Some tests failed. Check implementation.")

if __name__ == '__main__':
    main()