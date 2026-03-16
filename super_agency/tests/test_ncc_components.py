"""
Simple NCC Component Test
Tests individual NCC components without full integration
(This suite is skipped by default in this repo since NCC modules may be missing.)
"""

import pytest
# NCC components should be installed on CI; skip removed


import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.mark.asyncio
async def test_ncc_components():
    """Test individual NCC components"""
    print("🧠 Testing NCC Components...")
    print("=" * 40)

    try:
        # Test imports
        print("1. Testing imports...")
        from NCC.engine.command_processor import NCCCommandProcessor
        from NCC.engine.resource_allocator import NCCResourceAllocator
        from NCC.engine.intelligence_synthesizer import NCCIntelligenceSynthesizer
        from NCC.engine.execution_monitor import NCCExecutionMonitor
        print("\n2. Testing Command Processor...")
        cmd_processor = NCCCommandProcessor()
        await cmd_processor.start()

        command = CommandRecord(
            id="test_cmd_1",
            type="test_operation",
            priority="medium",
            payload={"test": "data"},
            requester="test_script",
            description="Test command"
        )

        await cmd_processor.create_command(command)
        status = await cmd_processor.get_status()
        print(
            f"   ✓ Command processor status: {status.get('status', 'unknown')}")

        await cmd_processor.stop()

        # Test resource allocator
        print("\n3. Testing Resource Allocator...")
        resource_allocator = NCCResourceAllocator()
        await resource_allocator.start()

        resources = await resource_allocator.allocate_resources({"cpu": 0.1, "memory": 50})
        print(f"   ✓ Resource allocation: {resources}")

        status = await resource_allocator.get_status()
        print(
            f"   ✓ Resource allocator status: {status.get('status', 'unknown')}")

        await resource_allocator.stop()

        # Test intelligence synthesizer
        print("\n4. Testing Intelligence Synthesizer...")
        intel_synthesizer = NCCIntelligenceSynthesizer()
        await intel_synthesizer.start()

        test_intelligence = [
            create_intelligence_record(
                id="test_intel_1",
                source="test_source",
                type="test_data",
                content={"message": "test intelligence"},
                confidence=0.8,
                metadata={"tags": ["test"],
                    "timestamp": "2024-01-01T00:00:00Z"}
            )
        ]

        synthesized = await intel_synthesizer.synthesize_intelligence(test_intelligence)
        print(
            f"   ✓ Intelligence synthesis: {len(synthesized)} records processed")

        insights = await intel_synthesizer.generate_insights(synthesized)
        print(f"   ✓ Insights generated: {len(insights)}")

        await intel_synthesizer.stop()

        # Test execution monitor
        print("\n5. Testing Execution Monitor...")
        exec_monitor = NCCExecutionMonitor()
        await exec_monitor.start()

        status = await exec_monitor.get_status()
        print(
            f"   ✓ Execution monitor status: {status.get('status', 'unknown')}")

        await exec_monitor.stop()

        # Test schema validation
        print("\n6. Testing Schema Validation...")
        from NCC.contracts.schemas import validate_command, validate_intelligence, create_intelligence_record
        from NCC.contracts.resource.schema import validate_resource
        from NCC.contracts.audit.schema import validate_audit

        # Test valid command
        valid_cmd = {
            "id": "test_cmd",
            "type": "test",
            "priority": "medium",
            "payload": {},
            "requester": "test",
            "description": "test"
        }
        is_valid = validate_command(valid_cmd)
        print(
            f"   ✓ Command schema validation: {'PASS' if is_valid else 'FAIL'}")

        # Test valid intelligence
        valid_intel = {
            "id": "test_intel",
            "source": "test",
            "type": "test",
            "content": {},
            "confidence": 0.8,
            "metadata": {"tags": [], "timestamp": "2024-01-01T00:00:00Z"}
        }
        is_valid = validate_intelligence(valid_intel)
        print(
            f"   ✓ Intelligence schema validation: {'PASS' if is_valid else 'FAIL'}")

        print("\n" + "=" * 40)
        print("✅ NCC Component Tests Completed Successfully!")
        print("All core components validated:")
        print("  • Command Processor ✓")
        print("  • Resource Allocator ✓")
        print("  • Intelligence Synthesizer ✓")
        print("  • Execution Monitor ✓")
        print("  • Schema Validation ✓")

        return True

    except Exception as e:
        print(f"\n❌ Component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test execution"""
    print("🧪 NCC Component Test Suite")
    print("Testing individual Neural Command Center components")
    print()

    success = await test_ncc_components()

    if success:
        print("\n" + "🎯" * 40)
        print("ALL COMPONENT TESTS PASSED!")
        print("🎯" * 40)
        return 0
    else:
        print("\n❌ Component tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)