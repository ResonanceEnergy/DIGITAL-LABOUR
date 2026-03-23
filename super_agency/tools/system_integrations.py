#!/usr/bin/env python3
"""
System Integrations — NCC, NCL, AAC, DIGITAL LABOUR.

Bridges the four core subsystems into the DIGITAL LABOUR
orchestrator pipeline and message bus.

Usage::

    python tools/system_integrations.py status
    python tools/system_integrations.py sync
    python tools/system_integrations.py report
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    get_portfolio, Log, ensure_dir, now_iso,
)

REPORTS_DIR = ROOT / "reports" / "integrations"
LABOUR_DB = ROOT / "reports" / "bit_rage_labour"
ensure_dir(REPORTS_DIR)
ensure_dir(LABOUR_DB)

# Message bus (best-effort)
try:
    from agents.message_bus import bus as _bus
except Exception:
    _bus = None


def _emit(topic: str, payload: dict | None = None):
    if _bus:
        _bus.publish(
            topic, payload or {},
            source="system_integrations",
        )


# ── NCC Integration ─────────────────────────────────────────

def ncc_health_check() -> dict[str, Any]:
    """Check NCC subsystem health without async."""
    result: dict[str, Any] = {
        "system": "NCC",
        "status": "unknown",
        "checked_at": now_iso(),
        "components": {},
    }

    ncc_dir = ROOT / "NCC"
    if not ncc_dir.is_dir():
        result["status"] = "not_found"
        return result

    # Check core engine modules exist
    engine_dir = ncc_dir / "engine"
    components = {
        "command_processor": engine_dir / "command_processor.py",
        "resource_allocator": engine_dir / "resource_allocator.py",
        "intelligence_synthesizer": (
            engine_dir / "intelligence_synthesizer.py"
        ),
        "execution_monitor": engine_dir / "execution_monitor.py",
    }
    for name, path in components.items():
        result["components"][name] = path.exists()

    # Check adapters
    adapters_dir = ncc_dir / "adapters"
    adapters = {
        "ncl_adapter": adapters_dir / "ncl_adapter.py",
        "council_52_adapter": (
            adapters_dir / "council_52_adapter.py"
        ),
        "api_management_adapter": (
            adapters_dir / "api_management_adapter.py"
        ),
    }
    for name, path in adapters.items():
        result["components"][name] = path.exists()

    # Check contracts
    contracts_dir = ncc_dir / "contracts"
    if contracts_dir.is_dir():
        schemas = list(contracts_dir.glob("*.json"))
        result["components"]["schemas"] = len(schemas)

    all_present = all(
        v for k, v in result["components"].items()
        if isinstance(v, bool)
    )
    result["status"] = "healthy" if all_present else "degraded"
    return result


def ncc_sync() -> dict[str, Any]:
    """Run NCC intelligence sync cycle."""
    result: dict[str, Any] = {
        "system": "NCC",
        "action": "sync",
        "synced_at": now_iso(),
        "events_processed": 0,
    }

    ncl_events = ROOT / "NCL" / "events.ndjson"
    if not ncl_events.exists():
        result["status"] = "no_events"
        return result

    try:
        events = []
        with open(ncl_events, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        result["events_processed"] = len(events)
        result["status"] = "synced"

        # Write sync receipt
        receipt = REPORTS_DIR / "ncc_sync_latest.json"
        receipt.write_text(
            json.dumps(result, indent=2),
            encoding="utf-8",
        )

        _emit("ncc.sync.done", {
            "events": len(events),
        })
    except OSError as exc:
        result["status"] = "error"
        result["error"] = str(exc)

    return result


# ── NCL Integration ─────────────────────────────────────────

def ncl_health_check() -> dict[str, Any]:
    """Check NCL Second Brain subsystem health."""
    result: dict[str, Any] = {
        "system": "NCL",
        "status": "unknown",
        "checked_at": now_iso(),
        "components": {},
    }

    ncl_dir = ROOT / "NCL"
    if not ncl_dir.is_dir():
        result["status"] = "not_found"
        return result

    catalog_dir = ncl_dir / "catalog"
    result["components"]["catalog_dir"] = catalog_dir.is_dir()

    # Check catalog index
    index_file = catalog_dir / "index.json"
    if index_file.exists():
        try:
            idx = json.loads(
                index_file.read_text(encoding="utf-8"),
            )
            result["components"]["catalog_entries"] = len(
                idx.get("entries", {}),
            )
        except (json.JSONDecodeError, OSError):
            result["components"]["catalog_entries"] = 0
    else:
        result["components"]["catalog_entries"] = 0

    # Check knowledge graph
    graph_file = catalog_dir / "graph.json"
    if graph_file.exists():
        try:
            graph = json.loads(
                graph_file.read_text(encoding="utf-8"),
            )
            result["components"]["graph_nodes"] = len(
                graph.get("nodes", []),
            )
            result["components"]["graph_edges"] = len(
                graph.get("edges", []),
            )
        except (json.JSONDecodeError, OSError):
            result["components"]["graph_nodes"] = 0
            result["components"]["graph_edges"] = 0

    # Check events file
    events_file = ncl_dir / "events.ndjson"
    if events_file.exists():
        try:
            count = sum(
                1 for _ in open(
                    events_file, "r", encoding="utf-8",
                )
            )
            result["components"]["total_events"] = count
        except OSError:
            result["components"]["total_events"] = 0

    result["status"] = (
        "healthy" if result["components"].get("catalog_dir")
        else "degraded"
    )
    return result


def ncl_sync() -> dict[str, Any]:
    """Rebuild NCL catalog index and verify graph."""
    result: dict[str, Any] = {
        "system": "NCL",
        "action": "sync",
        "synced_at": now_iso(),
    }

    try:
        sys.path.insert(
            0,
            str(
                ROOT / "departments"
                / "technology_infrastructure"
                / "development_operations"
            ),
        )
        from ncl_catalog import NCLCatalog
        catalog = NCLCatalog()
        result["entries"] = len(
            catalog.catalog.get("entries", {}),
        )
        result["graph_nodes"] = len(
            catalog.graph.get("nodes", []),
        )
        result["status"] = "synced"

        _emit("ncl.sync.done", {
            "entries": result["entries"],
            "nodes": result["graph_nodes"],
        })
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)

    return result


# ── AAC Integration ──────────────────────────────────────────

def aac_health_check() -> dict[str, Any]:
    """Check AAC financial subsystem health."""
    result: dict[str, Any] = {
        "system": "AAC",
        "status": "unknown",
        "checked_at": now_iso(),
        "components": {},
    }

    # Check cost database
    cost_db = ROOT / "memory" / "api_costs.db"
    result["components"]["cost_db"] = cost_db.exists()

    # Check budget config
    budget_cfg = ROOT / "config" / "budget.json"
    result["components"]["budget_config"] = budget_cfg.exists()

    # Check financial reports directory
    fin_dir = ROOT / "reports" / "financial"
    result["components"]["reports_dir"] = fin_dir.is_dir()

    # Check AAC repo
    aac_repo = ROOT / "repos" / "AAC"
    result["components"]["aac_repo"] = aac_repo.is_dir()

    # Check AAC company profile
    aac_company = ROOT / "companies" / "AAC"
    result["components"]["aac_company"] = aac_company.is_dir()

    result["status"] = (
        "healthy"
        if result["components"]["cost_db"]
        else "degraded"
    )
    return result


def aac_sync() -> dict[str, Any]:
    """Run AAC financial sync: ROI + budget check + sync."""
    result: dict[str, Any] = {
        "system": "AAC",
        "action": "sync",
        "synced_at": now_iso(),
    }

    try:
        sys.path.insert(0, str(ROOT / "tools"))
        from financial_ops import (
            calculate_roi, check_budget, sync_to_aac,
        )

        roi = calculate_roi()
        budget = check_budget()
        aac = sync_to_aac()

        result["roi_repos"] = len(roi.get("repos", []))
        result["budget_status"] = budget.get("status", "unknown")
        result["budget_alerts"] = len(
            budget.get("alerts", []),
        )
        result["aac_synced"] = aac.get("synced", False)
        result["status"] = "synced"

        # Emit budget alerts to bus
        for alert in budget.get("alerts", []):
            _emit("aac.budget.alert", alert)

        _emit("aac.sync.done", {
            "roi_repos": result["roi_repos"],
            "budget_status": result["budget_status"],
            "aac_synced": result["aac_synced"],
        })
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)

    return result


# ── DIGITAL LABOUR ───────────────────────────────────────────

def _load_mandates() -> dict[str, Any]:
    """Load agent mandates."""
    path = ROOT / "agent_mandates.json"
    if path.exists():
        try:
            return json.loads(
                path.read_text(encoding="utf-8"),
            )
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _load_protocols() -> dict[str, Any]:
    """Load agent protocols."""
    path = ROOT / "agent_protocols.json"
    if path.exists():
        try:
            return json.loads(
                path.read_text(encoding="utf-8"),
            )
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def bit_rage_labour_status() -> dict[str, Any]:
    """Track DIGITAL LABOUR force status."""
    result: dict[str, Any] = {
        "system": "BitRageLabour",
        "status": "unknown",
        "checked_at": now_iso(),
        "workforce": {},
        "mandates": {},
        "protocols": {},
    }

    mandates = _load_mandates()
    protocols = _load_protocols()

    # Mandate tracking
    for name, mandate in mandates.get("mandates", {}).items():
        result["mandates"][name] = {
            "owner": mandate.get("owner", "unassigned"),
            "target": mandate.get("target", ""),
            "description": mandate.get("description", ""),
        }

    # Protocol tracking
    for name, protocol in protocols.get("protocols", {}).items():
        result["protocols"][name] = {
            "rule": protocol.get("rule", ""),
            "owner": protocol.get("owner", "unassigned"),
        }

    # Agent pool from portfolio
    portfolio = get_portfolio()
    repos = portfolio.get("repositories", [])
    result["workforce"]["managed_repos"] = len(repos)

    # Classify repos by tier
    tiers: dict[str, int] = {}
    for repo in repos:
        tier = repo.get("tier", "unknown")
        tiers[tier] = tiers.get(tier, 0) + 1
    result["workforce"]["repos_by_tier"] = tiers

    # Check orchestrator stage history
    events_log = ROOT / "logs" / "events.ndjson"
    stage_counts: dict[str, int] = {"done": 0, "fail": 0, "skip": 0}
    if events_log.exists():
        try:
            with open(
                events_log, "r", encoding="utf-8",
            ) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        topic = ev.get("topic", "")
                        if "stage.done" in topic:
                            stage_counts["done"] += 1
                        elif "stage.fail" in topic:
                            stage_counts["fail"] += 1
                        elif "stage.skip" in topic:
                            stage_counts["skip"] += 1
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
    result["workforce"]["stage_history"] = stage_counts

    # Calculate completion rate
    total = stage_counts["done"] + stage_counts["fail"]
    if total > 0:
        rate = round(
            stage_counts["done"] / total * 100, 1,
        )
        result["workforce"]["completion_rate_pct"] = rate
    else:
        result["workforce"]["completion_rate_pct"] = 0

    result["status"] = "operational"
    return result


def bit_rage_labour_sync() -> dict[str, Any]:
    """Sync DIGITAL LABOUR metrics and write report."""
    status = bit_rage_labour_status()

    report_file = LABOUR_DB / "labour_report_latest.json"
    report_file.write_text(
        json.dumps(status, indent=2),
        encoding="utf-8",
    )

    # Daily snapshot
    ts = datetime.now().strftime("%Y%m%d")
    daily = LABOUR_DB / f"labour_{ts}.json"
    if not daily.exists():
        daily.write_text(
            json.dumps(status, indent=2),
            encoding="utf-8",
        )

    _emit("bit_rage_labour.sync.done", {
        "repos": status["workforce"].get(
            "managed_repos", 0,
        ),
        "completion_rate": status["workforce"].get(
            "completion_rate_pct", 0,
        ),
    })

    return {
        "system": "BitRageLabour",
        "action": "sync",
        "synced_at": now_iso(),
        "status": "synced",
        "report": str(report_file.name),
    }


# ── Unified Integration ─────────────────────────────────────

def full_status() -> dict[str, Any]:
    """Get health status of all four subsystems."""
    return {
        "ncc": ncc_health_check(),
        "ncl": ncl_health_check(),
        "aac": aac_health_check(),
        "bit_rage_labour": bit_rage_labour_status(),
        "checked_at": now_iso(),
    }


def full_sync() -> dict[str, Any]:
    """Run sync across all four subsystems."""
    _emit("integrations.sync.start", {})
    t0 = time.monotonic()

    results = {
        "ncc": ncc_sync(),
        "ncl": ncl_sync(),
        "aac": aac_sync(),
        "bit_rage_labour": bit_rage_labour_sync(),
        "synced_at": now_iso(),
        "elapsed_seconds": 0.0,
    }
    results["elapsed_seconds"] = round(
        time.monotonic() - t0, 2,
    )

    # Write combined report
    report = REPORTS_DIR / "integration_report_latest.json"
    report.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    _emit("integrations.sync.done", {
        "elapsed": results["elapsed_seconds"],
    })

    Log.info(
        f"Integration sync complete: "
        f"{results['elapsed_seconds']}s"
    )
    return results


# ── CLI ──────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        out = full_status()
    elif cmd == "sync":
        out = full_sync()
    elif cmd == "report":
        out = full_sync()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: system_integrations.py "
              "[status|sync|report]")
        sys.exit(1)

    print(json.dumps(out, indent=2))
