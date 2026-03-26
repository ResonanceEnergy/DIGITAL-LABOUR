"""Council 52 Adapter — bridges NCC Council decisions to BRS execution."""
from __future__ import annotations

import logging

_log = logging.getLogger("brs.adapter.council_52")


def receive_directive(directive: dict) -> dict:
    """Process a Council 52 governance directive by routing through orchestrator."""
    _log.info("Council 52 directive: %s", directive.get("type", "unknown"))
    try:
        from NCC.ncc_orchestrator import dispatch
        return dispatch(directive)
    except Exception as e:
        _log.error("Council 52 dispatch failed: %s", e)
        return {"status": "error", "source": "council_52", "error": str(e)}


def health() -> dict:
    return {"adapter": "council_52", "status": "online"}
