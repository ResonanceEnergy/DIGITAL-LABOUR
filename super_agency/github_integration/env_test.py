#!/usr/bin/env python3
"""
Simple environment variable test
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing environment variable loading...")
print(f"GITHUB_TOKEN loaded: {'Yes' if os.getenv('GITHUB_TOKEN') else 'No'}")
print(
    f"GITHUB_TOKEN value (first 10 chars): {os.getenv('GITHUB_TOKEN')[:10] if os.getenv('GITHUB_TOKEN') else 'None'}...")