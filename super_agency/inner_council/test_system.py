#!/usr/bin/env python3
"""
Simple Inner Council Test Script
Test the basic functionality without pytest dependencies
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_import():
    """Test basic imports"""
    try:
        from council import InnerCouncil, CouncilMember
        print("✅ Council imports successful")
        return True
    except Exception as e:
        print(f"❌ Council import failed: {e}")
        return False

def test_ncl_integration():
    """Test NCL integration"""
    try:
        from integrations.ncl_integration import NCLIntegration
        ncl = NCLIntegration()
        print("✅ NCL integration import successful")
        return True
    except Exception as e:
        print(f"❌ NCL integration import failed: {e}")
        return False

def test_orchestrator_integration():
    """Test orchestrator integration"""
    try:
        from integrations.orchestrator_integration import OrchestratorIntegration
        orchestrator = OrchestratorIntegration()
        print("✅ Orchestrator integration import successful")
        return True
    except Exception as e:
        print(f"❌ Orchestrator integration import failed: {e}")
        return False

def test_council_creation():
    """Test council creation"""
    try:
        from council import InnerCouncil
        council = InnerCouncil()
        print(f"✅ Council created with {len(council.members)} members")
        return True
    except Exception as e:
        print(f"❌ Council creation failed: {e}")
        return False

def test_config_loading():
    """Test configuration loading"""
    try:
        config_path = Path(__file__).parent / "config" / "settings.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"✅ Config loaded with {len(config['council_members'])} members")
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

def test_ncl_storage():
    """Test NCL storage functionality"""
    try:
        from integrations.ncl_integration import NCLIntegration
        ncl = NCLIntegration()

        # Test storing an insight
        test_insight = {
            "type": "inner_council_analysis",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "council_member": "Test Member",
                "content_title": "Test Content",
                "key_insights": ["Test insight"]
            }
        }

        result = ncl.store_insight(test_insight)
        if result:
            print("✅ NCL storage test successful")
            return True
        else:
            print("❌ NCL storage test failed")
            return False
    except Exception as e:
        print(f"❌ NCL storage test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running Inner Council System Tests")
    print("=" * 50)

    tests = [
        test_basic_import,
        test_ncl_integration,
        test_orchestrator_integration,
        test_council_creation,
        test_config_loading,
        test_ncl_storage
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Inner Council system is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())