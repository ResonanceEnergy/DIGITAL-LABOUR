"""AAC Financial Bridge — Reads BANK pillar data for LEDGR and ops.

Connects to AAC's CrossDepartmentIntegrationEngine to pull:
  - CentralAccounting: reconciled PnL, risk budget, drawdown
  - TradingExecution: fill rate, slippage, positions
  - CryptoIntelligence: venue health, counterparty exposure

Data is surfaced to LEDGR (CFO) and the ops dashboard.

Usage:
    from resonance.aac_bridge import aac

    snapshot = aac.snapshot()   # Full cross-department snapshot
    financials = aac.financials()  # CentralAccounting subset
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AAC_ROOT = Path(os.getenv("AAC_ROOT", r"C:\dev\AAC_fresh"))
sys.path.insert(0, str(AAC_ROOT))

logger = logging.getLogger(__name__)

# Try to import AAC engine — graceful fallback if AAC not available
_engine = None


def _get_engine():
    """Lazy-load the AAC CrossDepartmentIntegrationEngine."""
    global _engine
    if _engine is not None:
        return _engine
    try:
        from aac.integration.cross_department_engine import CrossDepartmentIntegrationEngine
        _engine = CrossDepartmentIntegrationEngine()
        return _engine
    except ImportError:
        logger.warning("AAC integration not available — cross_department_engine not found")
        return None


def _run(coro):
    """Run an async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return loop.run_in_executor(pool, lambda: asyncio.run(coro))
    except RuntimeError:
        return asyncio.run(coro)


class AACBridge:
    """Read-only connector to AAC BANK pillar data."""

    def _metrics_to_dict(self, metrics) -> dict:
        """Convert list of DepartmentMetric to dict keyed by name."""
        return {m.name: {"value": m.value, "unit": m.unit, "healthy": m.is_healthy} for m in metrics}

    async def _connect_engine(self):
        """Connect adapters if not connected."""
        engine = _get_engine()
        if engine is None:
            return None
        for dept, adapter in engine.adapters.items():
            if not adapter.is_connected:
                await adapter.connect()
        return engine

    async def _snapshot_async(self) -> dict:
        """Async snapshot of all AAC departments."""
        engine = await self._connect_engine()
        if engine is None:
            return {"status": "offline", "departments": {}}

        result = {"status": "online", "departments": {}}
        for dept, adapter in engine.adapters.items():
            try:
                metrics = await adapter.get_metrics()
                result["departments"][dept.value] = self._metrics_to_dict(metrics)
            except Exception as e:
                result["departments"][dept.value] = {"error": str(e)}
        return result

    def snapshot(self) -> dict:
        """Full cross-department metric snapshot."""
        return _run(self._snapshot_async())

    async def _financials_async(self) -> dict:
        """Async financial data from CentralAccounting."""
        engine = await self._connect_engine()
        if engine is None:
            return {"status": "offline"}

        from aac.integration.cross_department_engine import Department
        acct = engine.adapters[Department.CENTRAL_ACCOUNTING]
        if not acct.is_connected:
            await acct.connect()

        metrics = await acct.get_metrics()
        risk_remaining = await acct.get_risk_budget_remaining()

        return {
            "status": "online",
            "metrics": self._metrics_to_dict(metrics),
            "risk_budget_remaining": risk_remaining,
        }

    def financials(self) -> dict:
        """CentralAccounting financial summary for LEDGR."""
        return _run(self._financials_async())

    async def _trading_async(self) -> dict:
        """Async trading execution data."""
        engine = await self._connect_engine()
        if engine is None:
            return {"status": "offline"}

        from aac.integration.cross_department_engine import Department
        trading = engine.adapters[Department.TRADING_EXECUTION]
        if not trading.is_connected:
            await trading.connect()

        metrics = await trading.get_metrics()
        return {
            "status": "online",
            "metrics": self._metrics_to_dict(metrics),
        }

    def trading(self) -> dict:
        """TradingExecution metrics for ops monitoring."""
        return _run(self._trading_async())

    async def _venue_health_async(self) -> dict:
        """Async venue health from CryptoIntelligence."""
        engine = await self._connect_engine()
        if engine is None:
            return {"status": "offline"}

        from aac.integration.cross_department_engine import Department
        crypto = engine.adapters[Department.CRYPTO_INTELLIGENCE]
        if not crypto.is_connected:
            await crypto.connect()

        metrics = await crypto.get_metrics()
        return {
            "status": "online",
            "metrics": self._metrics_to_dict(metrics),
        }

    def venue_health(self) -> dict:
        """CryptoIntelligence venue health for ops monitoring."""
        return _run(self._venue_health_async())


# Module-level singleton
aac = AACBridge()
