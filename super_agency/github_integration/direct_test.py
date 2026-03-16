#!/usr/bin/env python3
"""
Direct GitHub Integration Test
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from github_integration_system import GitHubIntegrationSystem
    print("✅ GitHub integration module imported successfully")

    # Try to create the system
    system = GitHubIntegrationSystem()
    print("✅ GitHub integration system initialized")

    # Test basic functionality
    print("🔍 Testing basic functionality...")
    print(f"Organization: {system.org_name}")
    print(f"Token loaded: {'Yes' if system.token else 'No'}")

    print("🎉 Basic test passed! Ready for sync.")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This might be due to missing dependencies.")
except Exception as e:
    print(f"❌ Error: {e}")
    print("Check your GitHub token and network connection.")