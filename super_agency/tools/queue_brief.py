#!/usr/bin/env python3
"""
Queue video for operations brief
"""

import sys
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: queue_brief.py <enrich_json_path>")
        sys.exit(1)

    enrich_json_path = sys.argv[1]

    try:
        from agents.daily_brief import queue_for_brief
        result = queue_for_brief(Path(enrich_json_path))
        print(
            '✓ Queued for ops brief'
            if result else '✗ Failed to queue for ops brief')
    except ImportError:
        print('✗ Failed to import daily_brief module')
        sys.exit(1)
    except Exception as e:
        print(f'✗ Failed to queue for ops brief: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
