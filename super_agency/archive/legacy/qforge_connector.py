#!/usr/bin/env python3
"""
QFORGE Connection Manager
Establishes and maintains QFORGE/SASP network connection
"""

from sasp_protocol import init_sasp_network, get_sasp_status
import time
import signal
import sys

def signal_handler(sig, frame):
    print('\n🛑 QFORGE connection terminated by user')
    sys.exit(0)

def main():
    print('🚀 Establishing QFORGE Connection...')
    print('🔐 Initializing SASP Network Services...')

    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    success = init_sasp_network(8888)
    if success:
        print('✅ QFORGE connection established successfully!')
        print('🌐 SASP Network Services running on port 8888')
        print('🔄 QFORGE is now active and ready for cross-platform synchronization')
        print('💡 Press Ctrl+C to stop the connection')

        # Keep the service running and show status
        while True:
            try:
                status = get_sasp_status()
                if status.get('network_running'):
                    print(f'🔄 QFORGE Active - Network Status: {status}')
                time.sleep(30)  # Status check every 30 seconds
            except Exception as e:
                print(f'⚠️  Status check error: {e}')
                time.sleep(5)
    else:
        print('❌ Failed to establish QFORGE connection')
        sys.exit(1)

if __name__ == "__main__":
    main()
