#!/usr/bin/env python3
"""
Super Agency API & Account Setup Orchestrator
Coordinates YouTube API setup and Microsoft account creation
"""

import os
import json
import subprocess
import sys
from datetime import datetime

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n🔧 {description}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Success")
            return True
        else:
            print(f"❌ Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def setup_youtube_api():
    """Guide through YouTube API setup"""
    print("\n🎥 YOUTUBE DATA API V3 SETUP")
    print("=" * 40)

    print("1. Go to: https://console.cloud.google.com/")
    print("2. Select/Create project: 'agent-bravo-487119'")
    print("3. Enable YouTube Data API v3")
    print("4. Create API credentials (API Key)")
    print("5. Restrict the API key to YouTube Data API v3")

    api_key = input("\nEnter your YouTube API key: ").strip()
    if api_key:
        # Set environment variable
        os.environ['YOUTUBE_API_KEY'] = api_key
        print("✅ API key set in environment")

        # Test the API
        print("\n🧪 Testing API connection...")
        return run_command("python test_api_setup.py", "Running API connectivity test")
    else:
        print("❌ No API key provided")
        return False

def setup_microsoft_accounts():
    """Guide through Microsoft account creation"""
    print("\n📧 MICROSOFT ACCOUNT CREATION")
    print("=" * 40)

    print("1. Go to: https://admin.microsoft.com/")
    print("2. Sign in with admin account")
    print("3. Go to: Users → Active users → Add a user")

    domain = input("Enter your custom domain (e.g., yourdomain.onmicrosoft.com): ").strip()
    if not domain:
        print("❌ No domain provided")
        return False

    print("\n📋 Accounts to create:")
    print("   • council52@{}".format(domain))
    print("   • operations@{}".format(domain))
    print("   • intelligence@{}".format(domain))
    print("   • admin@{}".format(domain))

    # Run PowerShell script
    script_path = "create_super_agency_accounts.ps1"
    if os.path.exists(script_path):
        command = f'powershell -ExecutionPolicy Bypass -File "{script_path}" -Domain "{domain}" -AdminUsername "admin@{domain}"'
        return run_command(command, "Creating Microsoft accounts")
    else:
        print(f"❌ PowerShell script not found: {script_path}")
        return False

def test_full_system():
    """Test the complete Council 52 system"""
    print("\n🧪 FULL SYSTEM TEST")
    print("=" * 40)

    tests = [
        ("python test_api_setup.py", "API and configuration test"),
        ("python youtube_intelligence_monitor.py", "Council 52 intelligence gathering")
    ]

    all_passed = True
    for command, description in tests:
        if not run_command(command, description):
            all_passed = False

    return all_passed

def main():
    """Main setup orchestrator"""
    print("🏛️ SUPER AGENCY COUNCIL 52 SETUP ORCHESTRATOR")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    steps = [
        ("YouTube API Setup", setup_youtube_api),
        ("Microsoft Account Creation", setup_microsoft_accounts),
        ("Full System Test", test_full_system)
    ]

    completed_steps = []

    for step_name, step_function in steps:
        print(f"\n🚀 PHASE: {step_name}")
        if step_function():
            completed_steps.append(step_name)
            print(f"✅ {step_name} completed successfully")
        else:
            print(f"❌ {step_name} failed")
            break

    print(f"\n🏁 SETUP COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Completed steps: {len(completed_steps)}/{len(steps)}")

    if len(completed_steps) == len(steps):
        print("\n🎉 COUNCIL 52 IS NOW OPERATIONAL!")
        print("   • Live YouTube intelligence gathering")
        print("   • Automated policy directives")
        print("   • New Microsoft accounts configured")
        print("   • Cross-platform integration active")
    else:
        print(f"\n⚠️  Setup incomplete. Completed: {', '.join(completed_steps)}")
        print("   Please resolve errors and re-run this script")

if __name__ == "__main__":
    main()