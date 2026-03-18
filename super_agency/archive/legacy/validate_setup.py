#!/usr/bin/env python3
"""
Simple Memory Doctrine Setup Validator
"""

import sys
import os
import traceback

def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing imports...")

    try:
        # Test memory system import
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from memory_doctrine_system import MemoryDoctrineSystem, remember, recall
        print("  ✅ Memory system import successful")

        # Test doctrine system import
        from doctrine_preservation_system import DoctrinePreservationSystem
        print("  ✅ Doctrine system import successful")

        # Test backlog system import
        from backlog_management_system import BacklogManager
        print("  ✅ Backlog system import successful")

        return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_memory_basic():
    """Test basic memory operations"""
    print("🧠 Testing basic memory operations...")

    try:
        from memory_doctrine_system import remember, recall

        # Test ephemeral
        remember("test_ephemeral", "ephemeral data", "ephemeral")
        result = recall("test_ephemeral")
        assert result == "ephemeral data", "Ephemeral memory failed"
        print("  ✅ Ephemeral memory working")

        # Test session
        remember("test_session", "session data", "session")
        result = recall("test_session")
        assert result == "session data", "Session memory failed"
        print("  ✅ Session memory working")

        # Test persistent
        remember("test_persistent", "persistent data", "persistent")
        result = recall("test_persistent")
        assert result == "persistent data", "Persistent memory failed"
        print("  ✅ Persistent memory working")

        return True
    except Exception as e:
        print(f"  ❌ Memory test failed: {e}")
        traceback.print_exc()
        return False

def test_doctrine_basic():
    """Test basic doctrine operations"""
    print("📋 Testing basic doctrine operations...")

    try:
        from doctrine_preservation_system import DoctrinePreservationSystem

        doctrine_system = DoctrinePreservationSystem()

        # Test validation
        test_doctrine = {
            "version": "1.0.0",
            "memory_principles": ["test"],
            "operational_principles": ["test"]
        }

        is_valid, errors = doctrine_system.validate_doctrine(test_doctrine)
        assert is_valid, f"Doctrine validation failed: {errors}"
        print("  ✅ Doctrine validation working")

        # Test storage
        doctrine_system.store_doctrine(test_doctrine, "Test doctrine")
        current = doctrine_system.get_current_doctrine()
        assert current["version"] == "1.0.0", "Doctrine storage failed"
        print("  ✅ Doctrine storage working")

        return True
    except Exception as e:
        print(f"  ❌ Doctrine test failed: {e}")
        traceback.print_exc()
        return False

def test_backlog_basic():
    """Test basic backlog operations"""
    print("📊 Testing basic backlog operations...")

    try:
        from backlog_management_system import BacklogManager

        backlog_manager = BacklogManager()

        # Test item creation
        item = backlog_manager.create_item("Test item", category="test", priority="medium")
        assert item.title == "Test item", "Item creation failed"
        print("  ✅ Backlog item creation working")

        # Test retrieval
        retrieved = backlog_manager.get_item(item.id)
        assert retrieved is not None, "Item retrieval failed"
        print("  ✅ Backlog item retrieval working")

        return True
    except Exception as e:
        print(f"  ❌ Backlog test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run setup validation"""
    print("🚀 BIT RAGE LABOUR Memory Doctrine Setup Validation")
    print("=" * 60)

    tests = [
        ("Module Imports", test_imports),
        ("Memory Operations", test_memory_basic),
        ("Doctrine Operations", test_doctrine_basic),
        ("Backlog Operations", test_backlog_basic)
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"💥 Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION RESULTS:")

    passed = 0
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {name}: {status}")
        if success:
            passed += 1

    total = len(results)
    print(f"\n🎯 Overall: {passed}/{total} components operational")

    if passed == total:
        print("\n🎉 ALL SYSTEMS VALIDATED AND READY!")
        print("🚀 Your BIT RAGE LABOUR Memory Doctrine system is operational!")
        print("\nNext steps:")
        print("1. Run: python memory_doctrine_service.py (for continuous operation)")
        print("2. Your AI will now have persistent memory across sessions")
        print("3. All actions will be validated against doctrine")
        print("4. Tasks will be intelligently prioritized")
        return 0
    else:
        print(f"\n⚠️  {total - passed} component(s) need attention")
        print("Check the error messages above for details")
        return 1

if __name__ == "__main__":
    exit(main())