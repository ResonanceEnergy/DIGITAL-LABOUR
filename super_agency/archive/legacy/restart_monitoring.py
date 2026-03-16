#!/usr/bin/env python3
"""
Restart Comprehensive Monitoring Dashboard
"""

import os
import signal
import subprocess
import sys
import time

import psutil

print('🔄 Restarting Comprehensive Monitoring Dashboard')
print('=' * 50)

# Find and kill existing monitoring processes
killed_processes = 0
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] and 'python' in proc.info['name'].lower():
            cmdline = proc.info['cmdline']
            if cmdline and any('comprehensive_monitoring_dashboard.py' in arg for arg in cmdline):
                pid = proc.info['pid']
                print(f'Killing process PID {pid}...')
                proc.kill()
                killed_processes += 1
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        continue

print(f'✅ Killed {killed_processes} existing monitoring processes')
time.sleep(2)  # Wait for processes to fully terminate

print('🚀 Starting updated comprehensive monitoring dashboard...')

# Start the monitoring dashboard
try:
    subprocess.Popen([sys.executable, 'comprehensive_monitoring_dashboard.py'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    print('✅ Monitoring dashboard started successfully')
    print('⏳ Waiting for dashboard to initialize...')
    time.sleep(5)
    print('🎯 Dashboard should now be monitoring all 27 components!')
except Exception as e:
    print(f'❌ Failed to start dashboard: {e}')
