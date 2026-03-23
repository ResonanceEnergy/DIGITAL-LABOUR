#!/usr/bin/env python3
"""
GitHub Authentication Setup Helper
Helps configure and test GitHub authentication for DIGITAL LABOUR
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests
import json

def load_environment():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        load_dotenv(env_file)
        print("✅ Loaded environment from .env file")
        return True
    else:
        print("❌ .env file not found")
        return False

def check_github_token():
    """Check if GitHub token is available"""
    token = os.getenv('GITHUB_TOKEN')

    if not token:
        print("❌ GITHUB_TOKEN not found in environment")
        return False

    if token == 'your_personal_access_token_here':
        print("❌ GITHUB_TOKEN is still set to placeholder value")
        print("   Please update .env file with your actual GitHub token")
        return False

    # Mask token for display
    masked_token = token[:8] + '*' * (len(token) - 16) + token[-8:] if len(
        token) > 16 else '*' * len(token)
    print(f"✅ GITHUB_TOKEN found: {masked_token}")
    return True

def test_github_connection():
    """Test connection to GitHub API"""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        return False

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    try:
        # Test API connection
        response = requests.get(
            'https://api.github.com/user', headers=headers, timeout=10)

        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ GitHub API connection successful")
            print(f"   Authenticated as: {user_data.get('login', 'Unknown')}")
            return True
        elif response.status_code == 401:
            print("❌ Authentication failed - invalid token")
            return False
        else:
            print(
                f"❌ GitHub API error: {response.status_code} - {response.text}")
            return False

    except requests.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False

def test_organization_access():
    """Test access to ResonanceEnergy organization"""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        return False

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    try:
        # Check organization access
        response = requests.get(
            'https://api.github.com/orgs/ResonanceEnergy', headers=headers,
            timeout=10)

        if response.status_code == 200:
            org_data = response.json()
            print(
                f"✅ Organization access confirmed: {org_data.get('name', 'ResonanceEnergy')}")
            return True
        elif response.status_code == 404:
            print("❌ Organization 'ResonanceEnergy' not found or no access")
            return False
        elif response.status_code == 401:
            print("❌ Not authorized to access organization")
            return False
        else:
            print(f"❌ Organization check failed: {response.status_code}")
            return False

    except requests.RequestException as e:
        print(f"❌ Organization check error: {e}")
        return False

def check_token_scopes():
    """Check if token has required scopes"""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        return False

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    try:
        # Get token scopes from user endpoint
        response = requests.get(
            'https://api.github.com/user', headers=headers, timeout=10)

        if response.status_code == 200:
            # Check OAuth scopes header
            scopes = response.headers.get('X-OAuth-Scopes', '')
            scope_list = [s.strip() for s in scopes.split(',')]

            required_scopes = ['repo', 'workflow', 'read:org', 'write:org']
            missing_scopes = []

            for required in required_scopes:
                if required not in scope_list:
                    missing_scopes.append(required)

            if missing_scopes:
                print(f"⚠️  Token missing scopes: {', '.join(missing_scopes)}")
                print(
                    "   Required scopes: repo, workflow, read:org, write:org, admin:org, admin:repo_hook")
                return False
            else:
                print("✅ Token has required scopes")
                return True
        else:
            print("❌ Could not verify token scopes")
            return False

    except requests.RequestException as e:
        print(f"❌ Scope check error: {e}")
        return False

def create_auth_summary():
    """Create authentication setup summary"""
    summary = f"""# GitHub Authentication Setup Summary
## Date: February 20, 2026

### Environment Configuration:
- ✅ .env file: {'Found' if Path('.env').exists() else 'Missing'}
- ✅ GITHUB_TOKEN: {'Configured' if os.getenv('GITHUB_TOKEN') else 'Missing'}
- ✅ API Connection: {'Working' if test_github_connection() else 'Failed'}
- ✅ Organization Access: {'Confirmed' if test_organization_access() else 'Failed'}
- ✅ Token Scopes: {'Verified' if check_token_scopes() else 'Incomplete'}

### Next Steps:
1. **Update .env file** with your actual GitHub token
2. **Verify token scopes** include: repo, workflow, read:org, write:org
3. **Test connection** by running this script again
4. **Run integration** with: `./run_github_integration.sh sync`

### Security Notes:
- Never commit .env file to version control
- Rotate tokens regularly
- Monitor token usage in GitHub settings
- Use minimal required permissions

---
*DIGITAL LABOUR GitHub Authentication Setup*
"""

    with open("AUTH_SETUP_SUMMARY.md", 'w') as f:
        f.write(summary)

    print("📋 Authentication setup summary created: AUTH_SETUP_SUMMARY.md")

def main():
    """Main setup function"""
    print("🔐 DIGITAL LABOUR GitHub Authentication Setup")
    print("=" * 50)

    # Load environment
    if not load_environment():
        print("\n❌ Setup failed - .env file not found")
        print("   Please ensure .env file exists with GITHUB_TOKEN")
        return False

    # Check token
    if not check_github_token():
        print("\n❌ Setup failed - GitHub token not configured")
        print("   Please update .env file with your actual GitHub token")
        return False

    # Test connection
    print("\n🔍 Testing GitHub connection...")
    connection_ok = test_github_connection()

    # Test organization access
    org_access_ok = test_organization_access()

    # Check scopes
    scopes_ok = check_token_scopes()

    # Create summary
    create_auth_summary()

    print("\n" + "=" * 50)

    if connection_ok and org_access_ok and scopes_ok:
        print("🎉 GitHub Authentication Setup Complete!")
        print("   Ready to run GitHub integration operations")
        print("   Try: ./run_github_integration.sh sync")
        return True
    else:
        print("❌ Authentication setup incomplete")
        print("   Check AUTH_SETUP_SUMMARY.md for details")
        print("   Fix issues and run this script again")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)