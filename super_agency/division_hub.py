"""Division Hub — Unified entry point for all 4 autonomous divisions.

Routes incoming tasks to the correct division orchestrator based on
service_type. Provides aggregate health checks for NERVE integration
and C-Suite reporting.

Divisions:
    GRANT-OPS  — Grant proposals, SBIR, RFP responses
    INS-OPS    — Insurance appeals, prior auth, denial letters
    CTR-SVC    — Contractor docs, permits, safety plans
    MUN-SVC    — Municipal minutes, notices, ordinances

Usage:
    from super_agency.division_hub import DivisionHub
    hub = DivisionHub()
    result = await hub.route(service_type="grant_proposal", request=data)
    health = hub.health_report()
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("division.hub")

# Lazy-load divisions to avoid import-time side effects
_grant_division = None
_insurance_division = None
_contractor_division = None
_municipal_division = None


def _get_grant():
    global _grant_division
    if _grant_division is None:
        from super_agency.departments.grant_operations.orchestrator import GrantDivision
        _grant_division = GrantDivision()
    return _grant_division


def _get_insurance():
    global _insurance_division
    if _insurance_division is None:
        from super_agency.departments.insurance_operations.orchestrator import InsuranceDivision
        _insurance_division = InsuranceDivision()
    return _insurance_division


def _get_contractor():
    global _contractor_division
    if _contractor_division is None:
        from super_agency.departments.contractor_services.orchestrator import ContractorDivision
        _contractor_division = ContractorDivision()
    return _contractor_division


def _get_municipal():
    global _municipal_division
    if _municipal_division is None:
        from super_agency.departments.municipal_services.orchestrator import MunicipalDivision
        _municipal_division = MunicipalDivision()
    return _municipal_division


# ── Service → Division routing table ───────────────────────────────────────

ROUTE_TABLE = {
    # Grant Operations
    "grant_proposal": "grant_ops",
    "sbir_proposal": "grant_ops",
    "rfa_response": "grant_ops",
    "rfp_response_grant": "grant_ops",

    # Insurance Operations
    "insurance_appeal": "ins_ops",
    "prior_auth": "ins_ops",
    "denial_overturn": "ins_ops",
    "external_review": "ins_ops",

    # Contractor Services
    "permit_application": "ctr_svc",
    "inspection_report": "ctr_svc",
    "contractor_proposal": "ctr_svc",
    "lien_waiver": "ctr_svc",
    "safety_plan": "ctr_svc",
    "change_order": "ctr_svc",
    "progress_report": "ctr_svc",
    "bid_document": "ctr_svc",

    # Municipal Services
    "meeting_minutes": "mun_svc",
    "public_notice": "mun_svc",
    "ordinance": "mun_svc",
    "resolution": "mun_svc",
    "municipal_grant": "mun_svc",
    "budget_summary": "mun_svc",
    "annual_report": "mun_svc",
    "municipal_rfp": "mun_svc",
    "agenda": "mun_svc",
    "staff_report": "mun_svc",
}

DIVISION_GETTERS = {
    "grant_ops": _get_grant,
    "ins_ops": _get_insurance,
    "ctr_svc": _get_contractor,
    "mun_svc": _get_municipal,
}


class DivisionHub:
    """Unified router and health aggregator for all autonomous divisions."""

    async def route(self, service_type: str, request: dict) -> dict:
        """Route a task to the appropriate division."""
        division_key = ROUTE_TABLE.get(service_type)
        if not division_key:
            return {
                "status": "rejected",
                "reason": f"Unknown service_type: {service_type}",
                "supported": list(ROUTE_TABLE.keys()),
            }

        getter = DIVISION_GETTERS.get(division_key)
        if not getter:
            return {"status": "error", "reason": f"Division {division_key} not configured"}

        division = getter()

        # Map certain service_types to doc_type for contractor/municipal routing
        if division_key in ("ctr_svc", "mun_svc"):
            if "doc_type" not in request:
                request["doc_type"] = service_type

        logger.info("[HUB] Routing %s → %s", service_type, division_key)
        return await division.process(request)

    def health_report(self) -> dict:
        """Aggregate health report for all divisions — consumed by NERVE."""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "GREEN",
            "divisions": {},
        }

        for key, getter in DIVISION_GETTERS.items():
            try:
                division = getter()
                health = division.health_check()
                report["divisions"][key] = health
                if health.get("status") == "DEGRADED":
                    report["overall_status"] = "DEGRADED"
            except Exception as exc:
                report["divisions"][key] = {"status": "ERROR", "reason": str(exc)}
                report["overall_status"] = "DEGRADED"

        return report

    def reset_all_breakers(self):
        """Reset circuit breakers on all divisions (NERVE self-heal action)."""
        for key, getter in DIVISION_GETTERS.items():
            try:
                division = getter()
                division.reset_breaker()
            except Exception as exc:
                logger.warning("[HUB] Failed to reset breaker for %s: %s", key, exc)

    def get_division(self, key: str):
        """Get a specific division instance by key."""
        getter = DIVISION_GETTERS.get(key)
        return getter() if getter else None

    @staticmethod
    def list_services() -> dict:
        """Return all supported service types grouped by division."""
        grouped = {}
        for svc, div in ROUTE_TABLE.items():
            grouped.setdefault(div, []).append(svc)
        return grouped
