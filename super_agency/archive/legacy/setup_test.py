#!/usr/bin/env python3
"""
Memory Doctrine System Setup Test
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_memory_system():
    """Test the memory doctrine system"""
    print("🧠 Testing Memory Doctrine System...")

    try:
        from memory_doctrine_system import remember, recall, memory_stats, optimize_memory

        # Test basic memory operations
        print("  Testing ephemeral memory...")
        remember("test_ephemeral", "ephemeral data", "ephemeral")
        retrieved = recall("test_ephemeral")
        assert retrieved == "ephemeral data", "Ephemeral memory failed"
        print("  ✅ Ephemeral memory working")

        print("  Testing session memory...")
        remember("test_session", "session data", "session")
        retrieved = recall("test_session")
        assert retrieved == "session data", "Session memory failed"
        print("  ✅ Session memory working")

        print("  Testing persistent memory...")
        remember("test_persistent", "persistent data", "persistent")
        retrieved = recall("test_persistent")
        assert retrieved == "persistent data", "Persistent memory failed"
        print("  ✅ Persistent memory working")

        print("  Testing memory stats...")
        stats = memory_stats()
        assert "layers" in stats, "Stats failed"
        assert len(stats["layers"]) == 3, "Not all layers active"
        print("  ✅ Memory stats working")

        print("  Testing memory optimization...")
        opt_result = optimize_memory()
        assert isinstance(opt_result, dict), "Optimization failed"
        print("  ✅ Memory optimization working")

        print("✅ Memory Doctrine System: ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"❌ Memory system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_doctrine_system():
    """Test the doctrine preservation system"""
    print("\n📋 Testing Doctrine Preservation System...")

    try:
        from doctrine_preservation_system import DoctrinePreservationSystem

        doctrine_system = DoctrinePreservationSystem()

        # Test doctrine validation
        test_doctrine = {
            "version": "1.0.0",
            "memory_principles": ["conservative_usage"],
            "operational_principles": ["human_oversight"]
        }

        is_valid, errors = doctrine_system.validate_doctrine(test_doctrine)
        assert is_valid, f"Valid doctrine rejected: {errors}"
        print("  ✅ Doctrine validation working")

        # Test doctrine storage
        doctrine_system.store_doctrine(test_doctrine, "Test doctrine")
        current = doctrine_system.get_current_doctrine()
        assert current["version"] == "1.0.0", "Doctrine storage failed"
        print("  ✅ Doctrine storage working")

        # Test compliance checking
        compliant_action = {"memory_usage": 100}
        is_compliant, violations = doctrine_system.check_compliance(compliant_action)
        assert is_compliant, f"Compliance check failed: {violations}"
        print("  ✅ Doctrine compliance working")

        print("✅ Doctrine Preservation System: ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"❌ Doctrine system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backlog_system():
    """Test the backlog management system"""
    print("\n📊 Testing Backlog Management System...")

    try:
        from backlog_management_system import BacklogManager

        backlog_manager = BacklogManager()

        # Test item creation
        item = backlog_manager.create_item(
            title="Test Memory System",
            category="memory",
            priority="high",
            effort="medium"
        )
        assert item.title == "Test Memory System", "Item creation failed"
        print("  ✅ Backlog item creation working")

        # Test item retrieval
        retrieved = backlog_manager.get_item(item.id)
        assert retrieved is not None, "Item retrieval failed"
        assert retrieved.title == "Test Memory System", "Item data mismatch"
        print("  ✅ Backlog item retrieval working")

        # Test AI insights
        insights = backlog_manager.generate_ai_insights(item)
        required_keys = ["estimated_effort_days", "priority_boost", "dependency_risk"]
        for key in required_keys:
            assert key in insights, f"Missing insight key: {key}"
        print("  ✅ AI insights generation working")

        # Test statistics
        stats = backlog_manager.get_stats()
        assert "total_items" in stats, "Stats missing total_items"
        assert stats["total_items"] >= 1, "Stats not counting items"
        print("  ✅ Backlog statistics working")

        print("✅ Backlog Management System: ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"❌ Backlog system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all setup tests"""
    print("🚀 DIGITAL LABOUR Memory Doctrine System Setup Test")
    print("=" * 60)

    results = []

    # Test each system
    results.append(("Memory System", test_memory_system()))
    results.append(("Doctrine System", test_doctrine_system()))
    results.append(("Backlog System", test_backlog_system()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 SETUP TEST RESULTS:")

    passed = 0
    total = len(results)

    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {name}: {status}")
        if success:
            passed += 1

    print(f"\n🎯 Overall: {passed}/{total} systems operational")

    if passed == total:
        print("\n🎉 ALL SYSTEMS READY FOR PRODUCTION!")
        print("🚀 You can now start the memory doctrine service:")
        print("   python memory_doctrine_service.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} system(s) need attention")
        return 1

if __name__ == "__main__":
    exit(main())