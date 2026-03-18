#!/usr/bin/env python3
"""
Mobile Interface Tests for BIT RAGE LABOUR
Tests Matrix Maximizer mobile routes and iPhone dashboard integration
"""

import requests
import time
import json
import subprocess
import sys
import os

def test_matrix_mobile_routes():
    """Test Matrix Maximizer mobile API routes"""
    print("Testing Matrix Maximizer mobile routes...")

    base_url = "http://localhost:3000"

    # Test mobile dashboard route
    try:
        response = requests.get(f"{base_url}/mobile", timeout=5)
        if response.status_code == 200:
            print("✓ Mobile dashboard route accessible")
        else:
            print(f"✗ Mobile dashboard route failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Mobile dashboard route error: {e}")

    # Test mobile status API
    try:
        response = requests.get(f"{base_url}/api/mobile/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Mobile status API: {data.get('status', 'unknown')}")
        else:
            print(f"✗ Mobile status API failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Mobile status API error: {e}")

    # Test mobile metrics API
    try:
        response = requests.get(f"{base_url}/api/mobile/metrics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(
                f"✓ Mobile metrics API: CPU {data.get('cpu_usage', 'N/A')}%, Memory {data.get('memory_usage', 'N/A')}%")
        else:
            print(f"✗ Mobile metrics API failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Mobile metrics API error: {e}")

def test_mobile_command_center():
    """Test Mobile Command Center functionality"""
    print("\nTesting Mobile Command Center...")

    base_url = "http://localhost:8081"

    # Test main dashboard
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✓ Mobile Command Center dashboard accessible")
        else:
            print(
                f"✗ Mobile Command Center dashboard failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Mobile Command Center dashboard error: {e}")

    # Test iPhone dashboard
    try:
        response = requests.get(f"{base_url}/iphone", timeout=5)
        if response.status_code == 200:
            print("✓ iPhone dashboard accessible")
        else:
            print(f"✗ iPhone dashboard failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ iPhone dashboard error: {e}")

def test_services_running():
    """Check if required services are running"""
    print("\nChecking service status...")

    # Check if Matrix Maximizer is running (port 3000)
    try:
        response = requests.get("http://localhost:3000/api/status", timeout=2)
        if response.status_code == 200:
            print("✓ Matrix Maximizer service running")
        else:
            print("✗ Matrix Maximizer service not responding properly")
    except:
        print("✗ Matrix Maximizer service not running")

    # Check if Mobile Command Center is running (port 8081)
    try:
        response = requests.get("http://localhost:8081/", timeout=2)
        if response.status_code == 200:
            print("✓ Mobile Command Center service running")
        else:
            print("✗ Mobile Command Center service not responding properly")
    except:
        print("✗ Mobile Command Center service not running")

def main():
    """Run all mobile interface tests"""
    print("=== BIT RAGE LABOUR Mobile Interface Tests ===\n")

    # Check if services are running first
    test_services_running()

    # Test Matrix mobile routes
    test_matrix_mobile_routes()

    # Test Mobile Command Center
    test_mobile_command_center()

    print("\n=== Test Complete ===")
    print("Note: If services are not running, start them with:")
    print("python run_bit_rage_labour.py")

if __name__ == "__main__":
    main()