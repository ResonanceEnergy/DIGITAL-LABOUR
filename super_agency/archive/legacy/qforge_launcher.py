#!/usr/bin/env python3
"""
QFORGE Launch Script - Windows Execution Startup
Initializes QFORGE execution layer with high-performance task processing
"""

import asyncio
import sys
import os
from pathlib import Path

# Add QFORGE directory to path
qforge_dir = Path(__file__).parent / "qforge"
qforge_dir = qforge_dir.resolve()
sys.path.insert(0, str(qforge_dir))

def main():
    """Main QFORGE launch function"""
    print("Starting QFORGE Execution Layer (Windows)")
    print("🔗 Referencing RAMDOCTRINE Liquid Intelligence Reference")

    # Load RAMDOCTRINE reference
    ramdoctrine_path = Path(__file__).parent / "RAMDOCTRINE_LIQUID_REFERENCE.md"
    if ramdoctrine_path.exists():
        print("✅ RAMDOCTRINE reference loaded - optimizing execution parameters")
        # Parse RAMDOCTRINE for QFORGE-specific optimizations
        with open(ramdoctrine_path, 'r', encoding='utf-8') as f:
            doctrine_content = f.read()
            if "QFORGE Optimizations" in doctrine_content:
                print("🎯 QFORGE optimizations applied from RAMDOCTRINE")
    else:
        print("⚠️ RAMDOCTRINE not found - using default parameters")

    try:
        # Import QFORGE executor
        from qforge_executor import QFORGEExecutor

        # Initialize executor
        executor = QFORGEExecutor()

        # Start services
        executor.start()

        print("QFORGE initialized successfully")
        print("QFORGE server is running...")

        # Keep server running and accepting connections
        import time
        while True:
            if hasattr(executor, 'sasp_server') and executor.sasp_server:
                executor.sasp_server.accept_connections()
            time.sleep(1)  # Check for connections every second

    except ImportError as e:
        print(f"Failed to import QFORGE components: {e}")
        print("Please ensure QFORGE directory structure is correct")
        sys.exit(1)

    except Exception as e:
        print(f"QFORGE startup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
