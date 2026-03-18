"""Shared pytest fixtures for the Bit Rage Labour test suite."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_ncc_bridge():
    """Auto-mock the NCC relay HTTP call so tests never hit the network.

    NCCBridge._post() returns False → bridge queues locally, no HTTP call made.
    This prevents tests from taking 5+ seconds per task (request timeout) when
    the NCC relay server is unreachable or slow.
    """
    with patch("resonance.ncc_bridge.NCCBridge._post", return_value=False):
        yield
