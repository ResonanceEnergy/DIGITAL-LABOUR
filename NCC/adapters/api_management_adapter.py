"""API Management Adapter — bridges external API orchestration to BRS."""
from __future__ import annotations

import logging

_log = logging.getLogger("brs.adapter.api_management")


def register_endpoint(endpoint: dict) -> dict:
    """Register an API endpoint for BRS management."""
    _log.info("API endpoint registered: %s", endpoint.get("path", "unknown"))
    return {"status": "registered", "source": "api_management"}


def health() -> dict:
    return {"adapter": "api_management", "status": "online"}
