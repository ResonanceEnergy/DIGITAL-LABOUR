#!/usr/bin/env python3
"""
Inner Council Validation Script
Simple validation of Inner Council system components
"""

import sys
import os
from pathlib import Path

def main():
    print("🔍 Inner Council System Validation")
    print("=" * 40)

    # Change to inner_council directory
    inner_council_dir = Path(__file__).parent / "inner_council"
    os.chdir(inner_council_dir)

    # Add to path
    sys.path.insert(0, str(inner_council_dir))

    success_count = 0
    total_tests = 0

    # Test 1: Import Council
    total_tests += 1
    try:
        from council import InnerCouncil, CouncilMember
        print("✅ Council module imported successfully")
        success_count += 1
    except Exception as e:
        print(f"❌ Council import failed: {e}")

    # Test 2: Create Council
    total_tests += 1
    try:
        council = InnerCouncil()
        print(f"✅ Inner Council created with {len(council.members)} members")
        success_count += 1
    except Exception as e:
        print(f"❌ Council creation failed: {e}")

    # Test 3: NCL Integration
    total_tests += 1
    try:
        from integrations.ncl_integration import NCLIntegration
        ncl = NCLIntegration()
        print("✅ NCL integration initialized")
        success_count += 1
    except Exception as e:
        print(f"❌ NCL integration failed: {e}")

    # Test 4: Orchestrator Integration
    total_tests += 1
    try:
        from integrations.orchestrator_integration import OrchestratorIntegration
        orchestrator = OrchestratorIntegration()
        print("✅ Orchestrator integration initialized")
        success_count += 1
    except Exception as e:
        print(f"❌ Orchestrator integration failed: {e}")

    # Test 5: Config Loading
    total_tests += 1
    try:
        import json
        config_path = Path("config/settings.json")
        with open(config_path, 'r') as f:
            config = json.load(f)
        members = config.get('council_members', [])
        print(f"✅ Configuration loaded with {len(members)} council members")
        success_count += 1
    except Exception as e:
        print(f"❌ Config loading failed: {e}")

    # Test 6: NCL Storage
    total_tests += 1
    try:
        from integrations.ncl_integration import NCLIntegration
        ncl = NCLIntegration()

        test_insight = {
            "type": "test_insight",
            "data": {"test": "data"}
        }

        result = ncl.store_insight(test_insight)
        if result:
            print("✅ NCL storage test successful")
            success_count += 1
        else:
            print("❌ NCL storage test failed")
    except Exception as e:
        print(f"❌ NCL storage test failed: {e}")

    print("=" * 40)
    print(f"Validation Results: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print("🎉 Inner Council system validation successful!")
        print("The strategic intelligence network is ready for operation.")
        return 0
    else:
        print("⚠️  Some validation tests failed.")
        print("Please check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())