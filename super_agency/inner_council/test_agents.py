#!/usr/bin/env python3
"""
Inner Council Agent Test Suite
Test all council member agents for proper initialization and functionality
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import json
import logging

# Add the agents directory to Python path
agents_dir = Path(__file__).parent / "agents"
sys.path.insert(0, str(agents_dir))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_agent_imports():
    """Test that all agent modules can be imported"""
    print("🧪 Testing agent imports...")

    council_members = load_council_config()
    successful_imports = []
    failed_imports = []

    for member in council_members:
        safe_name = member["name"].lower().replace(
            " ", "_").replace("'", "").replace("-", "_")
        module_name = f"{safe_name}_agent"

        try:
            # Import the module
            module = __import__(module_name)

            # Get the agent class
            class_name = f"{safe_name.title().replace('_', '')}Agent"
            agent_class = getattr(module, class_name)

            # Test instantiation
            agent = agent_class()
            agent_name = agent.name

            successful_imports.append({
                "name": member["name"],
                "module": module_name,
                "class": class_name,
                "agent_name": agent_name
            })

            print(f"✅ {member['name']} - Import and instantiation successful")

        except Exception as e:
            failed_imports.append({
                "name": member["name"],
                "module": module_name,
                "error": str(e)
            })
            print(f"❌ {member['name']} - Import failed: {e}")

    return successful_imports, failed_imports

def test_agent_functionality():
    """Test basic agent functionality"""
    print("\n🧪 Testing agent functionality...")

    council_members = load_council_config()
    functional_agents = []
    non_functional_agents = []

    for member in council_members:
        safe_name = member["name"].lower().replace(
            " ", "_").replace("'", "").replace("-", "_")
        module_name = f"{safe_name}_agent"

        try:
            # Import and create agent
            module = __import__(module_name)
            class_name = f"{safe_name.title().replace('_', '')}Agent"
            agent_class = getattr(module, class_name)
            agent = agent_class()

            # Test basic functionality
            status = agent.get_status()
            capabilities = agent.capabilities.__dict__

            # Test monitoring cycle (simulation)
            try:
                agent.run_monitoring_cycle()
                monitoring_success = True
            except Exception as e:
                monitoring_success = False
                monitoring_error = str(e)

            functional_agents.append({
                "name": member["name"],
                "status": status,
                "capabilities": capabilities,
                "monitoring_success": monitoring_success,
                "monitoring_error": getattr(locals(), 'monitoring_error', None)
            })

            success_msg = "✅" if monitoring_success else "⚠️"
            print(
                f"{success_msg} {member['name']} - Functional (monitoring: {'success' if monitoring_success else 'failed'})")

        except Exception as e:
            non_functional_agents.append({
                "name": member["name"],
                "error": str(e)
            })
            print(f"❌ {member['name']} - Functionality test failed: {e}")

    return functional_agents, non_functional_agents

def test_agent_registry():
    """Test the agent registry functionality"""
    print("\n🧪 Testing agent registry...")

    try:
        from agent_registry import AGENT_REGISTRY, create_all_agents, get_agent_class

        registry_count = len(AGENT_REGISTRY)
        print(f"📊 Agent registry contains {registry_count} agents")

        # Test creating all agents
        all_agents = create_all_agents()
        created_count = len(all_agents)
        print(f"📊 Successfully created {created_count} agent instances")

        # Test getting specific agent classes
        test_names = ["lex_fridman", "elon_musk", "andrew_huberman"]
        for name in test_names:
            agent_class = get_agent_class(name)
            if agent_class:
                print(
                    f"✅ Found agent class for '{name}': {agent_class.__name__}")
            else:
                print(f"❌ Agent class not found for '{name}'")

        return {
            "registry_count": registry_count,
            "created_count": created_count,
            "test_results": "passed"
        }

    except Exception as e:
        print(f"❌ Agent registry test failed: {e}")
        return {
            "error": str(e),
            "test_results": "failed"
        }

def load_council_config() -> List[Dict[str, Any]]:
    """Load council member configuration"""
    config_path = Path(__file__).parent / "config" / "settings.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config.get("council_members", [])

def generate_test_report(
        import_results, functionality_results, registry_results):
    """Generate a comprehensive test report"""
    successful_imports, failed_imports = import_results
    functional_agents, non_functional_agents = functionality_results

    report = {
        "test_timestamp": str(Path(__file__).stat().st_mtime),
        "summary": {
            "total_agents": len(successful_imports) + len(failed_imports),
            "successful_imports": len(successful_imports),
            "failed_imports": len(failed_imports),
            "functional_agents": len(functional_agents),
            "non_functional_agents": len(non_functional_agents),
            "registry_test": registry_results.get("test_results", "unknown")
        },
        "import_results": {
            "successful": successful_imports,
            "failed": failed_imports
        },
        "functionality_results": {
            "functional": functional_agents,
            "non_functional": non_functional_agents
        },
        "registry_results": registry_results
    }

    # Save report
    report_path = Path(__file__).parent / "tests" / "agent_test_report.json"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n📄 Test report saved to: {report_path}")
    return report

def main():
    """Run all agent tests"""
    print("🚀 Starting Inner Council Agent Test Suite")
    print("=" * 50)

    # Test imports
    import_results = test_agent_imports()

    # Test functionality
    functionality_results = test_agent_functionality()

    # Test registry
    registry_results = test_agent_registry()

    # Generate report
    report = generate_test_report(
        import_results, functionality_results, registry_results)

    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Total Agents: {report['summary']['total_agents']}")
    print(f"Successful Imports: {report['summary']['successful_imports']}")
    print(f"Failed Imports: {report['summary']['failed_imports']}")
    print(f"Functional Agents: {report['summary']['functional_agents']}")
    print(
        f"Non-Functional Agents: {report['summary']['non_functional_agents']}")
    print(f"Registry Test: {report['summary']['registry_test']}")

    if report['summary'] ['failed_imports'] ==0 and report['summary'] [
        'non_functional_agents'] ==0:
        print("\n🎉 ALL TESTS PASSED! Inner Council agents are ready for deployment.")
        return 0
    else:
        print(
            f"\n⚠️  {report['summary']['failed_imports'] + report['summary']['non_functional_agents']} issues found. Check the test report for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())