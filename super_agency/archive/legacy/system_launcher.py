#!/usr/bin/env python3
"""
SYSTEM LAUNCHER - Controlled startup of BIT RAGE LABOUR components
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n🔧 {description}")
    print(f"Command: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✅ SUCCESS: {description}")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ FAILED: {description}")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT: {description}")
        return False
    except Exception as e:
        print(f"💥 ERROR: {description} - {e}")
        return False

def main():
    """Main launcher function"""
    workspace = Path(__file__).parent

    print("🚀 BIT RAGE LABOUR SYSTEM LAUNCHER")
    print("="*50)

    # Change to workspace directory
    os.chdir(workspace)

    # Test 1: Basic Python import test
    success = run_command(
        'python -c "print(\\"Python OK\\")"',
        "Testing Python environment"
    )

    if not success:
        print("❌ Python environment test failed")
        return 1

    # Test 2: Import matrix_maximizer
    success = run_command(
        'python -c "import matrix_maximizer; print(\\"Matrix Maximizer import OK\\")"',
        "Testing Matrix Maximizer import"
    )

    # Test 3: Import qforge components
    success = run_command(
        'python -c "from qforge.qforge_executor import QFORGEExecutor; print(\\"QFORGE import OK\\")"',
        "Testing QFORGE import"
    )

    # Test 4: Import QUSAR components
    success = run_command(
        'python -c "import sys; sys.path.append(\\"repos/QUSAR\\"); from qusar_orchestrator import QUSAROrchestrator; print(\\"QUSAR import OK\\")"',
        "Testing QUSAR import"
    )

    # Test 5: Import executive council
    success = run_command(
        'python -c "from celebrity_council_orchestrator import CelebrityCouncilOrchestrator; print(\\"Celebrity Council import OK\\")"',
        "Testing Executive Council import"
    )

    print("\n" + "="*50)
    print("🎯 SYSTEM LAUNCHER COMPLETE")
    print("All components tested. Check output above for any failures.")
    print("="*50)

    return 0

if __name__ == "__main__":
    sys.exit(main())
