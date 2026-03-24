#!/usr/bin/env python3
"""
Portfolio Intelligence Runner - Execute Resonance Energy portfolio agents
"""
import sys
import os
import subprocess
from pathlib import Path

# Add the ResonanceEnergy_BitRageLabour path
repo_path = Path(__file__).parent / "ResonanceEnergy_BitRageLabour"
sys.path.insert(0, str(repo_path))

def run_agent(agent_name, description):
    """Run a portfolio agent and report results"""
    print(f"\n🔄 Running {description}...")
    agent_path = repo_path / "agents" / f"portfolio_{agent_name}.py"

    try:
        result = subprocess.run([sys.executable, str(agent_path)],
                              capture_output=True, text=True, cwd=repo_path)

        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
        else:
            print(f"❌ {description} failed with code {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr.strip()}")

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False

def main():
    print("🚀 Starting Resonance Energy Portfolio Intelligence System")
    print("=" * 60)

    # Change to the ResonanceEnergy_BitRageLabour directory
    os.chdir(repo_path)

    # Run the agents in sequence
    agents = [
        ("autodiscover", "Repository Discovery"),
        ("autotier", "Automatic Tiering"),
        ("intel", "Intelligence Gathering"),
        ("maintainer", "Portfolio Maintenance"),
        ("selfheal", "Self-Healing")
    ]

    results = []
    for agent_name, description in agents:
        success = run_agent(agent_name, description)
        results.append((agent_name, success))

    print("\n" + "=" * 60)
    print("📊 PORTFOLIO INTELLIGENCE EXECUTION SUMMARY")
    print("=" * 60)

    successful = 0
    for agent_name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{agent_name:12} | {status}")
        if success:
            successful += 1

    print(f"\n🎯 Overall: {successful}/{len(results)} agents completed successfully")

    if successful == len(results):
        print("🎉 RESONANCE ENERGY PORTFOLIO INTELLIGENCE SYSTEM FULLY OPERATIONAL!")
    else:
        print("⚠️  Some agents failed - manual intervention may be required")

    return successful == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)