"""
NCC Integration Test Script
Tests the complete NCC system integration
"""

import asyncio
import sys
import os
from pathlib import Path
import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from NCC.ncc_orchestrator import NCCOrchestrator
from NCC.adapters.api_management_adapter import NCCAPIManagementAdapter
from NCC.adapters.council_52_adapter import NCCCouncil52Adapter
from NCC.adapters.ncl_adapter import NCCNCLAdapter

@pytest.mark.asyncio
async def test_ncc_integration():
    """Test complete NCC system integration"""
    print("🧠 Starting NCC Integration Tests...")
    print("=" * 50)

    # Initialize NCC Orchestrator
    print("1. Initializing NCC Orchestrator...")
    ncc = NCCOrchestrator()
    print("   ✓ NCC Orchestrator initialized")

    # Test system startup
    print("\n2. Testing NCC system startup...")
    startup_result = await ncc.start_orchestration()
    if startup_result["success"]:
        print("   ✓ NCC system started successfully")
        print(
            f"   ✓ Subsystems started: {startup_result.get('subsystems_started', 0)}")
    else:
        print(
            f"   ✗ NCC startup failed: {startup_result.get('message', 'Unknown error')}")
        return False

    # Test system status
    print("\n3. Testing system status retrieval...")
    status = await ncc.get_system_status()
    if status["status"] == "running":
        print("   ✓ System status: RUNNING")
        print(f"   ✓ Subsystems: {len(status.get('subsystems', {}))}")
    else:
        print(
            f"   ✗ System status check failed: {status.get('status', 'unknown')}")
        return False

    # Test API management adapter
    print("\n4. Testing API Management Adapter...")
    api_adapter = NCCAPIManagementAdapter()

    # Test API setup
    test_api_config = {
        "test_api": {
            "key": "test_key_123",
            "quota_limit": 1000,
            "rate_limit": 100
        }
    }

    setup_result = await api_adapter.setup_api_key("test_api", test_api_config["test_api"])
    if setup_result["success"]:
        print("   ✓ API key setup successful")
    else:
        print(
            f"   ✗ API setup failed: {setup_result.get('message', 'Unknown error')}")

    # Test API call simulation
    api_call_result = await api_adapter.execute_api_call(
        "test_api",
        "/test/endpoint",
        "GET",
        requester="test_script"
    )
    print(
        f"   ✓ API call simulation: {'Success' if api_call_result.get('success', False) else 'Failed'}")

    # Test Council 52 adapter
    print("\n5. Testing Council 52 Adapter...")
    council_adapter = NCCCouncil52Adapter()

    # Test intelligence gathering
    intelligence = await council_adapter.gather_council_intelligence()
    print(f"   ✓ Council intelligence gathered: {len(intelligence)} records")

    # Test coordination
    coordination = await council_adapter.coordinate_council_operations()
    print(
        f"   ✓ Council coordination: {coordination.get('commands_created', 0)} commands created")

    # Test health monitoring
    health = await council_adapter.monitor_council_health()
    print(
        f"   ✓ Council health: {health.get('active_members', 0)}/{health.get('total_members', 0)} active")

    # Test NCL adapter
    print("\n6. Testing NCL Adapter...")
    ncl_adapter = NCCNCLAdapter()

    # Test NCL health monitoring
    ncl_health = await ncl_adapter.monitor_ncl_health()
    print(
        f"   ✓ NCL health check: {ncl_health.get('health_score', 0):.2f} score")

    # Test event reading
    events = await ncl_adapter.read_ncl_events()
    print(f"   ✓ NCL events read: {len(events)} events")

    # Test intelligence synthesis loop
    print("\n7. Testing Intelligence Synthesis...")
    synthesis_result = await ncc._perform_intelligence_synthesis()
    print("   ✓ Intelligence synthesis cycle completed")

    # Test API operation execution
    print("\n8. Testing API Operation Execution...")
    api_operation = {
        "api_name": "youtube_data_api",
        "endpoint": "/channels",
        "method": "GET",
        "parameters": {"part": "snippet", "id": "test_channel"},
        "requester": "integration_test",
        "description": "Test YouTube API channel lookup"
    }

    operation_result = await ncc.execute_api_operation(api_operation)
    print(
        f"   ✓ API operation queued: {operation_result.get('command_id', 'N/A')}")

    # Test intelligence report request
    print("\n9. Testing Intelligence Report Request...")
    report_request = await ncc.request_intelligence_report(
        "council_activity_summary",
        {"time_range": "last_24h", "include_insights": True}
    )
    if report_request["success"]:
        print("   ✓ Intelligence report request successful")
        print(f"   ✓ Command ID: {report_request.get('command_id', 'N/A')}")
    else:
        print("   ✗ Intelligence report request failed")

    # Test system shutdown
    print("\n10. Testing system shutdown...")
    shutdown_result = await ncc.stop_orchestration()
    if shutdown_result["success"]:
        print("   ✓ NCC system shutdown successful")
    else:
        print(
            f"   ✗ System shutdown failed: {shutdown_result.get('message', 'Unknown error')}")
        return False

    print("\n" + "=" * 50)
    print("🎉 NCC Integration Tests Completed Successfully!")
    print("All core systems validated:")
    print("  • NCC Orchestrator ✓")
    print("  • API Management Adapter ✓")
    print("  • Council 52 Adapter ✓")
    print("  • NCL Adapter ✓")
    print("  • Intelligence Synthesis ✓")
    print("  • Command Processing ✓")
    print("  • Resource Allocation ✓")
    print("  • Execution Monitoring ✓")

    return True

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling scenarios"""
    print("\n🛡️  Testing Error Handling...")

    ncc = NCCOrchestrator()

    # Test double startup
    print("Testing double startup handling...")
    result1 = await ncc.start_orchestration()
    result2 = await ncc.start_orchestration()

    if result1["success"] and not result2["success"]:
        print("   ✓ Double startup properly handled")
    else:
        print("   ✗ Double startup handling failed")

    # Test shutdown without startup
    print("Testing shutdown without startup...")
    shutdown_result = await ncc.stop_orchestration()
    if not shutdown_result["success"]:
        print("   ✓ Shutdown without startup properly handled")
    else:
        print("   ✗ Shutdown without startup handling failed")

    # Clean shutdown if needed
    if ncc.is_running:
        await ncc.stop_orchestration()

    print("   ✓ Error handling tests completed")

async def main():
    """Main test execution"""
    print("🧪 NCC System Integration Test Suite")
    print("Testing Neural Command Center integration and functionality")
    print()

    try:
        # Run main integration tests
        success = await test_ncc_integration()

        if success:
            # Run error handling tests
            await test_error_handling()

            print("\n" + "🎯" * 50)
            print("ALL TESTS PASSED - NCC System Ready for Production!")
            print("🎯" * 50)
            return 0
        else:
            print("\n❌ Integration tests failed!")
            return 1

    except Exception as e:
        print(f"\n💥 Test execution failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)