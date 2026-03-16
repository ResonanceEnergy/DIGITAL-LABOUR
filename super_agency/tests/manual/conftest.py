"""
Manual / integration test scripts.

These are NOT pytest-collected tests. They require a running server
or external API keys. Run them individually with:

    python tests/manual/test_api_setup.py

To prevent pytest from collecting them:
"""

collect_ignore_glob = ["test_*.py"]
