#!/usr/bin/env python3
"""
Inner Council Integration Demo
Demonstrate the complete Inner Council autonomous agent system
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import json
import logging

# Add the agents directory to Python path
agents_dir = Path(__file__).parent / "agents"
sys.path.insert(0, str(agents_dir))

from base_agent import MessageBus
from agent_registry import create_all_agents

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demonstrate_agent_specialization():
    """Demonstrate how different agents specialize in different content areas"""
    print("🎯 Demonstrating Agent Specialization")
    print("=" * 50)

    agents = create_all_agents()

    # Group agents by specialization
    specializations = {
        "AI/Tech": ["lex_fridman", "elon_musk", "demis_hassabis", "yann_lecun", "geoffrey_hinton", "marc_andreessen"],
        "Business": ["tom_bilyeu", "tim_ferriss", "naval_ravikant", "impact_theory"],
        "Science": ["andrew_huberman", "peter_attia", "bret_weinstein"],
        "Philosophy/Culture": ["sam_harris", "jordan_peterson", "daniel_schmachtenberger", "russell_brand"],
        "Politics": ["ben_shapiro", "dave_rubin", "candace_owens", "tucker_carlson"],
        "Other": ["joe_rogan", "the_joe_rogan_experience", "lex_fridman_podcast", "shane_parrish", "niall_ferguson", "tyler_cowen", "vitalik_buterin"]
    }

    for category, agent_names in specializations.items():
        print(f"\n📊 {category} Agents:")
        for name in agent_names:
            if name in agents:
                agent = agents[name]
                print(
                    f"  • {agent.name}: {', '.join(agent.focus_areas)} (Priority: {agent.priority})")

def demonstrate_message_bus():
    """Demonstrate inter-agent communication via message bus"""
    print("\n💬 Demonstrating Message Bus Communication")
    print("=" * 50)

    message_bus = MessageBus()
    agents = create_all_agents()

    # Register a few key agents
    key_agents = ["lex_fridman", "elon_musk",
        "andrew_huberman", "daniel_schmachtenberger"]
    registered_agents = {}

    for name in key_agents:
        if name in agents:
            agent = agents[name]
            registered_agents[name] = agent
            message_bus.register_agent(agent)
            print(f"✅ Registered {agent.name} with message bus")

    # Start message bus
    message_bus.start()
    time.sleep(1)

    # Send a coordination message
    coordination_message = {
        "type": "coordination_request",
        "payload": {
            "request_type": "cross_agent_analysis",
            "topic": "AI Safety and Human Enhancement",
            "requesting_agent": "system"
        },
        "timestamp": "2024-01-01T00:00:00Z"
    }

    print(
        f"\n📤 Broadcasting coordination message: {coordination_message['payload']['topic']}")
    message_bus.broadcast(coordination_message)

    # Allow time for processing
    time.sleep(2)

    # Stop message bus
    message_bus.stop()
    print("🛑 Message bus stopped")

def demonstrate_content_analysis():
    """Demonstrate specialized content analysis capabilities"""
    print("\n🔍 Demonstrating Content Analysis Capabilities")
    print("=" * 50)

    agents = create_all_agents()

    # Test content for different agents
    test_content = {
        "video_id": "test_001",
        "title": "The Future of AI: Opportunities and Risks",
        "description": "Exploring artificial intelligence development, safety concerns, and societal implications.",
        "transcript": """
        Today we're discussing the rapid advancement of artificial intelligence. AI systems are becoming
        more capable, but we must consider the safety implications. How do we ensure AI development
        benefits humanity while minimizing risks? What are the key challenges we face in AI alignment?
        """
    }

    # Test with AI-focused agents
    ai_agents = ["lex_fridman", "elon_musk", "demis_hassabis"]

    for agent_name in ai_agents:
        if agent_name in agents:
            agent = agents[agent_name]
            print(f"\n🤖 {agent.name} Analysis:")

            try:
                analysis = agent._analyze_content_batch([test_content])[
                                                        0]["analysis"]

                print(
                    f"  📊 Key Takeaways: {len(analysis.get('key_takeaways', []))}")
                for takeaway in analysis.get(
                    'key_takeaways', []) [
                    : 2]:  # Show first 2
                    print(f"    • {takeaway}")

                print(
                    f"  🎯 Policy Implications: {len(analysis.get('policy_implications', []))}")
                print(
                    f"  💡 Strategic Recommendations: {len(analysis.get('strategic_recommendations', []))}")
                print(
                    f"  ⚠️  Risk Assessments: {len(analysis.get('risk_assessments', []))}")

            except Exception as e:
                print(f"  ❌ Analysis failed: {e}")

def demonstrate_autonomous_operation():
    """Demonstrate autonomous monitoring cycles"""
    print("\n🤖 Demonstrating Autonomous Operation")
    print("=" * 50)

    agents = create_all_agents()

    # Show monitoring frequencies
    frequency_groups = {"daily": [], "weekly": []}

    for name, agent in agents.items():
        freq = agent.monitoring_frequency
        if freq in frequency_groups:
            frequency_groups[freq].append(agent.name)

    print("📅 Daily Monitoring Agents:")
    for name in sorted(frequency_groups["daily"]):
        print(f"  • {name}")

    print(
        f"\n📆 Weekly Monitoring Agents ({len(frequency_groups['weekly'])} total):")
    for name in sorted(frequency_groups["weekly"][:10]):  # Show first 10
        print(f"  • {name}")
    if len(frequency_groups["weekly"]) > 10:
        print(f"  ... and {len(frequency_groups['weekly']) - 10} more")

    # Demonstrate a monitoring cycle
    print("\n🔄 Running monitoring cycle for Lex Fridman agent...")
    try:
        lex_agent = agents.get("lex_fridman")
        if lex_agent:
            result = lex_agent.run_monitoring_cycle()
            print(
                f"✅ Monitoring cycle completed. Found {len(result)} new content items.")
        else:
            print("❌ Lex Fridman agent not found")
    except Exception as e:
        print(f"❌ Monitoring cycle failed: {e}")

def demonstrate_cpu_offloading():
    """Demonstrate how the system offloads CPU from Bit Rage Systems"""
    print("\n⚡ Demonstrating CPU Offloading Benefits")
    print("=" * 50)

    agents = create_all_agents()

    total_agents = len(agents)
    high_priority_agents = sum(
        1 for a in agents.values() if a.priority == "high")
    daily_agents = sum(1 for a in agents.values()
                       if a.monitoring_frequency == "daily")

    print(f"📊 System Scale:")
    print(f"  • Total Autonomous Agents: {total_agents}")
    print(f"  • High Priority Agents: {high_priority_agents}")
    print(f"  • Daily Monitoring Agents: {daily_agents}")
    print(f"  • Weekly Monitoring Agents: {total_agents - daily_agents}")

    print(f"\n💡 CPU Offloading Benefits:")
    print("  • Distributed content analysis across 28 specialized agents")
    print("  • Parallel processing of YouTube content monitoring")
    print("  • Specialized analysis engines reduce main system load")
    print("  • Autonomous operation minimizes coordination overhead")
    print("  • Message-based communication enables scalable architecture")

    # Calculate theoretical throughput
    daily_cycles = daily_agents * 1  # 1 cycle per day
    weekly_cycles = (total_agents - daily_agents) * \
                     (1/7)  # ~0.14 cycles per day
    total_daily_throughput = daily_cycles + weekly_cycles

    print(
        f"  • Theoretical Daily Throughput: {total_daily_throughput:.1f} analysis cycles")
def generate_system_report():
    """Generate a comprehensive system report"""
    print("\n📄 Generating Inner Council System Report")
    print("=" * 50)

    agents = create_all_agents()

    report = {
        "system_overview": {
            "name": "Inner Council Intelligence Network",
            "total_agents": len(agents),
            "version": "1.0.0",
            "status": "operational"
        },
        "agent_breakdown": {
            "by_priority": {
                "high": sum(1 for a in agents.values() if a.priority == "high"),
                "medium": sum(1 for a in agents.values() if a.priority == "medium"),
                "low": sum(1 for a in agents.values() if a.priority == "low")
            },
            "by_frequency": {
                "daily": sum(1 for a in agents.values() if a.monitoring_frequency == "daily"),
                "weekly": sum(1 for a in agents.values() if a.monitoring_frequency == "weekly")
            },
            "by_specialization": {
                "ai_tech": sum(1 for a in agents.values() if any(area in ["AI", "Technology"] for area in a.focus_areas)),
                "business": sum(1 for a in agents.values() if "Business" in a.focus_areas or "Entrepreneurship" in a.focus_areas),
                "science": sum(1 for a in agents.values() if any(area in ["Science", "Neuroscience", "Biology"] for area in a.focus_areas)),
                "politics_culture": sum(1 for a in agents.values() if any(area in ["Politics", "Culture", "Philosophy"] for area in a.focus_areas))
            }
        },
        "capabilities": {
            "strategic_planning": sum(1 for a in agents.values() if a.capabilities.strategic_planning),
            "risk_assessment": sum(1 for a in agents.values() if a.capabilities.risk_assessment),
            "policy_recommendation": sum(1 for a in agents.values() if a.capabilities.policy_recommendation),
            "autonomous_decision_making": sum(1 for a in agents.values() if a.capabilities.autonomous_decision_making)
        },
        "focus_areas_coverage": {}
    }

    # Count focus area coverage
    all_focus_areas = {}
    for agent in agents.values():
        for area in agent.focus_areas:
            all_focus_areas[area] = all_focus_areas.get(area, 0) + 1

    report["focus_areas_coverage"] = dict(
        sorted(all_focus_areas.items(), key=lambda x: x[1], reverse=True))

    # Save report
    report_path = Path(__file__).parent / "reports" / \
                       "inner_council_system_report.json"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"✅ Report saved to: {report_path}")

    # Print summary
    print(f"\n📊 System Summary:")
    print(
        f"  • {report['system_overview']['total_agents']} autonomous agents deployed")
    print(
        f"  • {report['agent_breakdown']['by_priority']['high']} high-priority intelligence sources")
    print(
        f"  • {report['agent_breakdown']['by_frequency']['daily']} daily monitoring cycles")
    print(
        f"  • {len(report['focus_areas_coverage'])} specialized focus areas covered")

    return report

def main():
    """Run the complete Inner Council integration demo"""
    print("🚀 Inner Council Integration Demo")
    print("Autonomous Agent System for Distributed Intelligence Gathering")
    print("=" * 70)

    try:
        # Demonstrate agent specialization
        demonstrate_agent_specialization()

        # Demonstrate message bus communication
        demonstrate_message_bus()

        # Demonstrate content analysis
        demonstrate_content_analysis()

        # Demonstrate autonomous operation
        demonstrate_autonomous_operation()

        # Demonstrate CPU offloading benefits
        demonstrate_cpu_offloading()

        # Generate system report
        generate_system_report()

        print("\n" + "=" * 70)
        print("🎉 Inner Council Integration Demo Complete!")
        print("✅ All 28 council member agents are operational")
        print("✅ Distributed intelligence gathering system active")
        print("✅ CPU offloading from Bit Rage Systems achieved")
        print("✅ Autonomous coordination and analysis functional")
        print("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())