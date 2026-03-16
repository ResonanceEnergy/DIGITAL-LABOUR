#!/usr/bin/env python3
"""
Quick GitHub Token Test
"""

import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

token = os.getenv('GITHUB_TOKEN')
if not token or token == 'your_personal_access_token_here':
    print("❌ No valid token found")
    exit(1)

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json'
}

# Test user authentication
response = requests.get('https://api.github.com/user',
                        headers=headers, timeout=10)
if response.status_code == 200:
    user = response.json()
    print(f"✅ Authenticated as: {user.get('login')}")
else:
    print(f"❌ Auth failed: {response.status_code}")
    exit(1)

# Test organization access
response = requests.get(
    'https://api.github.com/orgs/ResonanceEnergy', headers=headers, timeout=10)
if response.status_code == 200:
    org = response.json()
    print(f"✅ Organization access: {org.get('name')}")
else:
    print(f"❌ Org access failed: {response.status_code}")

print("🎉 GitHub authentication test complete!")