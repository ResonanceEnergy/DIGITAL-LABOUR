#!/usr/bin/env python3
"""
Quick test of GitHub integration system
"""

import sys
import os
from pathlib import Path

def test_import():
    """Test if the system can be imported"""
    try:
        # Add current directory to path
        current_dir = Path(__file__).parent
        sys.path.insert(0, str(current_dir))

        from github_integration_system import GitHubIntegrationSystem
        print("✅ GitHub integration system import successful")

        # Test initialization
        system = GitHubIntegrationSystem()
        print("✅ GitHub integration system initialization successful")

        # Check config
        if hasattr(system, 'config') and system.config:
            print("✅ Configuration loaded successfully")
        else:
            print("❌ Configuration loading failed")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_config():
    """Test configuration files"""
    config_file = Path("config/github_config.json")
    if config_file.exists():
        print("✅ Configuration file exists")
        return True
    else:
        print("❌ Configuration file missing")
        return False

def test_templates():
    """Test template files"""
    template_dir = Path("templates")
    if template_dir.exists():
        templates = list(template_dir.glob("*.yml"))
        if templates:
            print(f"✅ {len(templates)} workflow templates found")
            return True
        else:
            print("❌ No workflow templates found")
            return False
    else:
        print("❌ Templates directory missing")
        return False

def main():
    """Run all tests"""
    print("🧪 Bit Rage Systems GitHub Integration - System Test")
    print("=" * 50)

    tests = [
        ("Import Test", test_import),
        ("Config Test", test_config),
        ("Template Test", test_templates)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1

    print(f"\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! GitHub integration system is ready.")
        return True
    else:
        print("❌ Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)