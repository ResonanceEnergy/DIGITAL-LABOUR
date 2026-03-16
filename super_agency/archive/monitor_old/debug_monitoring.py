#!/usr/bin/env python3
"""
Debug Component Monitoring Status
"""

import requests
import json

print('🔍 Investigating Component Monitoring Status')
print('=' * 45)

try:
    # Get current status
    response = requests.get('http://localhost:8080/api/status', timeout=5)
    if response.status_code == 200:
        data = response.json()
        components = data.get('components', {})

        print(f'📊 Total Components Found: {len(components)}')
        print(f'🏥 Overall Health: {data.get("overall_health", "unknown")}')
        print('')

        print('📋 Current Components:')
        for name, comp_data in components.items():
            status = comp_data.get('status', 'unknown')
            message = comp_data.get('message', 'No message')
            print(f'  {status.upper():8} | {name:25} | {message}')

        print('')
        print('🔧 Checking if monitoring is running...')

        # Check if the monitoring process is active
        import psutil
        import os

        current_pid = os.getpid()
        python_processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline']
                    if cmdline and any('comprehensive_monitoring_dashboard.py' in arg for arg in cmdline):
                        python_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if python_processes:
            print(f'✅ Found {len(python_processes)} monitoring process(es):')
            for proc in python_processes:
                cmdline_str = ' '.join(proc['cmdline'][:3]) + '...'
                print(f'   PID: {proc["pid"]}, Command: {cmdline_str}')
        else:
            print('❌ No monitoring processes found - dashboard may not be running the monitoring loop')

    else:
        print(f'❌ API request failed: {response.status_code}')

except Exception as e:
    print(f'❌ Error: {e}')
