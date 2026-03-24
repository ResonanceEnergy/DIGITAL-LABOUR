#!/usr/bin/env python3
"""
YouTube API Setup Test - Bit Rage Systems
Tests YouTube Data API v3 connectivity and Council 52 configuration
"""

import os
import json
import requests
from datetime import datetime

def test_youtube_api():
    """Test YouTube API connectivity"""
    api_key = os.getenv('YOUTUBE_API_KEY')

    if not api_key:
        print("❌ No YOUTUBE_API_KEY environment variable found")
        print("   Please set it with: $env:YOUTUBE_API_KEY = 'your_api_key_here'")
        return False

    print(f"✅ YouTube API key found: {api_key[:10]}...")

    # Test API with a simple request
    test_channel_id = "UCnYMOAMTyJw4M5m0v6qp0DQ"  # Tom Bilyeu
    url = f"https://www.googleapis.com/youtube/v3/channels"
    params = {
        'part': 'snippet,statistics',
        'id': test_channel_id,
        'key': api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                channel = data['items'][0]
                print(f"✅ API connection successful!")
                print(f"   Channel: {channel['snippet']['title']}")
                print(
                    f"   Subscribers: {channel['statistics'].get('subscriberCount', 'N/A')}")
                return True
            else:
                print("❌ API returned no data for test channel")
                return False
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
        return False

def test_council_config():
    """Test Council 52 configuration"""
    try:
        with open('inner_council_config.json', 'r') as f:
            config = json.load(f)

        council_members = config.get(
            'youtube_channels', {}).get('inner_council', {})
        member_count = len(council_members)

        print(f"✅ Council configuration loaded")
        print(f"   Total members: {member_count}")

        if member_count == 52:
            print("✅ Council 52 fully configured!")
        else:
            print(f"⚠️  Expected 52 members, found {member_count}")

        # Check for required fields
        required_fields = ['channel_id', 'channel_name',
            'description', 'priority', 'role']
        missing_fields = []

        for member_key, member_data in council_members.items():
            for field in required_fields:
                if field not in member_data:
                    missing_fields.append(f"{member_key}.{field}")

        if missing_fields:
            print(f"❌ Missing fields: {missing_fields}")
            return False
        else:
            print("✅ All members have required fields")
            return True

    except FileNotFoundError:
        print("❌ inner_council_config.json not found")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 YouTube API & Council 52 Setup Test")
    print("=" * 50)

    api_test = test_youtube_api()
    print()

    config_test = test_council_config()
    print()

    if api_test and config_test:
        print("🎉 All tests passed! Council 52 is ready for live intelligence gathering.")
        print("\n🚀 Next steps:")
        print("   1. Run: python youtube_intelligence_monitor.py")
        print("   2. Check: inner_council_intelligence/ directory")
        print("   3. Review: daily_policy_directives/ directory")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\n🔧 To fix:")
        if not api_test:
            print("   - Set YOUTUBE_API_KEY environment variable")
            print("   - Verify API key is valid and has YouTube Data API v3 enabled")
        if not config_test:
            print("   - Check inner_council_config.json for completeness")

if __name__ == "__main__":
    main()