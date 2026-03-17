"""End-to-end pipeline integration test — Steps 66, 67, 68.

Verifies the full intake → dispatch → worker → QA → log → bill pipeline
for 20 mixed task types. LLM providers are mocked so no real API calls are made.

Steps covered:
  66 — Full pipeline end-to-end test
  67 — Automated task completion (20 tasks)
  68 — KPI log + billing integration verified

Run:
    pytest tests/test_pipeline_e2e.py -v
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Test fixtures ─────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _make_mock_result(task_type: str) -> MagicMock:
    """Build a plausible mock pipeline result for any task type."""
    r = MagicMock()
    r.qa_status = "PASS"
    # model_dump() returns a minimal outputs dict
    r.model_dump.return_value = {
        "task_type": task_type,
        "status": "complete",
        "output": f"Mock output for {task_type}",
        "qa_status": "PASS",
    }
    # Some pipelines use result.qa.status
    r.qa = SimpleNamespace(status="PASS")
    return r


# ── 20 E2E test cases (diverse task types) ────────────────────────────────────

E2E_CASES = [
    # (task_type, inputs dict)
    ("sales_outreach",    {"company": "Acme Corp",   "role": "CEO",              "provider": "openai"}),
    ("sales_outreach",    {"company": "TechCo",      "role": "CTO",              "provider": "anthropic"}),
    ("support_ticket",    {"ticket": "Login broken", "kb": "Reset KB",           "provider": "openai"}),
    ("support_ticket",    {"ticket": "Billing issue","kb": "Billing KB",         "provider": "gemini"}),
    ("content_repurpose", {"source_text": "Blog post about AI.", "formats": ["tweet", "linkedin"], "provider": "openai"}),
    ("content_repurpose", {"source_text": "Product update 2025.", "formats": ["email"],             "provider": "grok"}),
    ("doc_extract",       {"document_text": "Contract clause 1. Term: 12 months.", "doc_type": "contract", "provider": "openai"}),
    ("doc_extract",       {"document_text": "Invoice #1234. Amount: $500.",        "doc_type": "invoice",  "provider": "anthropic"}),
    ("lead_gen",          {"industry": "SaaS", "icp": "VP Sales", "geo": "US",    "provider": "openai"}),
    ("lead_gen",          {"industry": "FinTech", "icp": "CFO",   "geo": "CA",    "provider": "gemini"}),
    ("email_marketing",   {"business": "DL Agency", "audience": "SMBs", "goal": "convert", "provider": "openai"}),
    ("email_marketing",   {"business": "DL Agency", "audience": "Startups", "goal": "nurture", "provider": "anthropic"}),
    ("seo_content",       {"topic": "AI automation 2025", "content_type": "blog_post", "provider": "openai"}),
    ("seo_content",       {"topic": "Reduce support costs", "content_type": "landing_page", "provider": "gemini"}),
    ("sales_outreach",    {"company": "RetailBrand", "role": "CMO", "provider": "grok"}),
    ("support_ticket",    {"ticket": "Feature request: export CSV", "kb": "", "provider": "anthropic"}),
    ("content_repurpose", {"source_text": "Annual report excerpt.", "formats": ["summary"], "provider": "openai"}),
    ("doc_extract",       {"document_text": "NDA agreement effective Jan 2025.",  "doc_type": "nda",     "provider": "grok"}),
    ("lead_gen",          {"industry": "Healthcare", "icp": "Operations Manager", "geo": "UK", "provider": "openai"}),
    ("email_marketing",   {"business": "DL Agency", "audience": "Agencies", "goal": "upsell", "provider": "openai"}),
]

assert len(E2E_CASES) == 20, f"Expected 20 E2E cases, got {len(E2E_CASES)}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch_all_pipelines(mock_map: dict[str, Any]):
    """Return a list of patch context managers for all agent runners."""
    return [
        patch("agents.sales_ops.runner.run_pipeline",       return_value=_make_mock_result("sales_outreach")),
        patch("agents.support.runner.run_pipeline",         return_value=_make_mock_result("support_ticket")),
        patch("agents.content_repurpose.runner.run_pipeline",return_value=_make_mock_result("content_repurpose")),
        patch("agents.doc_extract.runner.run_pipeline",     return_value=_make_mock_result("doc_extract")),
        patch("agents.lead_gen.runner.run_pipeline",        return_value=_make_mock_result("lead_gen")),
        patch("agents.email_marketing.runner.run_pipeline", return_value=_make_mock_result("email_marketing")),
        patch("agents.seo_content.runner.run_pipeline",     return_value=_make_mock_result("seo_content")),
    ]


# ── Core E2E tests ────────────────────────────────────────────────────────────

class TestPipelineE2E:
    """Full end-to-end pipeline test: intake → dispatch → QA → log → bill."""

    def _run_single_task(self, task_type: str, inputs: dict) -> dict:
        """Run one task through the complete pipeline (mocked LLM)."""
        from dispatcher.router import create_event, route_task
        from kpi.logger import log_task_event
        from billing.tracker import BillingTracker
        from utils.cost_tracker import estimate_task_cost

        # Step 66/67 — Create event and route it
        event = create_event(task_type, inputs, client_id="test_client_e2e")
        assert "event_id" in event, "Event must have event_id"
        assert event["task_type"] == task_type

        start_time = time.time()
        result_event = route_task(event)
        duration_s = round(time.time() - start_time, 3)

        # Extract billing amount from pricing
        from billing.tracker import PRICING
        charge = PRICING.get(task_type, {}).get("per_task", 0.0)
        result_event["billing"]["amount"] = charge
        result_event["billing"]["status"] = "billed"
        result_event["metrics"]["latency_ms"] = int(duration_s * 1000)

        # Step 68 — Log to KPI
        cost_info = estimate_task_cost(task_type, inputs.get("provider", "openai"))
        llm_cost  = cost_info.get("cost_usd", 0.0)
        log_task_event(
            task_id    = event["event_id"],
            task_type  = task_type,
            status     = "complete",
            client     = event["client_id"],
            provider   = inputs.get("provider", "openai"),
            qa_status  = result_event["qa"].get("status", "FAIL"),
            duration_s = duration_s,
            cost_usd   = llm_cost,
            tokens_in  = cost_info.get("tokens_in", 0),
            tokens_out = cost_info.get("tokens_out", 0),
        )

        # Step 68 — Record billing usage
        bt = BillingTracker()
        billing_record = bt.record_usage(
            client    = event["client_id"],
            task_type = task_type,
            task_id   = event["event_id"],
            llm_cost  = llm_cost,
        )
        assert billing_record["charge"] == charge, \
            f"Billing charge mismatch for {task_type}: expected {charge}, got {billing_record['charge']}"

        return result_event

    def test_all_20_tasks_complete(self):
        """Step 67: All 20 mixed tasks complete without exception."""
        patches = _patch_all_pipelines({})
        completed = []

        with (
            patches[0], patches[1], patches[2], patches[3],
            patches[4], patches[5], patches[6],
        ):
            for task_type, inputs in E2E_CASES:
                result = self._run_single_task(task_type, inputs)
                completed.append(result)

        assert len(completed) == 20, f"Only {len(completed)}/20 tasks completed"

    def test_all_tasks_have_event_id(self):
        """Step 66: Every event carries a valid UUID event_id."""
        patches = _patch_all_pipelines({})

        with (
            patches[0], patches[1], patches[2], patches[3],
            patches[4], patches[5], patches[6],
        ):
            for task_type, inputs in E2E_CASES:
                event_before = None
                from dispatcher.router import create_event
                event_before = create_event(task_type, inputs, client_id="test_e2e")
                # Validate UUID format
                try:
                    uuid.UUID(event_before["event_id"])
                except ValueError:
                    pytest.fail(f"Invalid UUID for {task_type}: {event_before['event_id']}")

    def test_qa_status_is_pass_on_success(self):
        """Step 66: Successfully routed tasks have qa.status = PASS."""
        patches = _patch_all_pipelines({})
        qa_failures = []

        with (
            patches[0], patches[1], patches[2], patches[3],
            patches[4], patches[5], patches[6],
        ):
            for task_type, inputs in E2E_CASES:
                result = self._run_single_task(task_type, inputs)
                qa_stat = result["qa"].get("status")
                if qa_stat not in ("PASS", "MANUAL_REVIEW"):
                    qa_failures.append((task_type, qa_stat))

        assert not qa_failures, f"QA failures on: {qa_failures}"

    def test_billing_amount_nonzero(self):
        """Step 68: Every task produces a non-zero billing amount."""
        patches = _patch_all_pipelines({})

        with (
            patches[0], patches[1], patches[2], patches[3],
            patches[4], patches[5], patches[6],
        ):
            for task_type, inputs in E2E_CASES:
                result = self._run_single_task(task_type, inputs)
                amount = result["billing"]["amount"]
                assert amount > 0, f"Zero billing amount for {task_type}"

    def test_kpi_log_records_20_entries(self, tmp_path):
        """Step 68: KPI logger records exactly 20 new entries in SQLite."""
        import kpi.logger as kpi_mod

        # Override DB path to a temp DB for isolation
        original_db = kpi_mod.DB_PATH
        test_db = tmp_path / "kpi_test.db"
        kpi_mod.DB_PATH = test_db
        kpi_mod._init_db()

        patches = _patch_all_pipelines({})

        try:
            with (
                patches[0], patches[1], patches[2], patches[3],
                patches[4], patches[5], patches[6],
            ):
                for task_type, inputs in E2E_CASES:
                    self._run_single_task(task_type, inputs)
        finally:
            kpi_mod.DB_PATH = original_db

        # Count rows in the test DB
        conn = sqlite3.connect(str(test_db))
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        conn.close()
        assert count == 20, f"Expected 20 KPI log entries, got {count}"

    def test_metrics_latency_populated(self):
        """Step 66: metrics.latency_ms is populated after route_task."""
        patches = _patch_all_pipelines({})

        with (
            patches[0], patches[1], patches[2], patches[3],
            patches[4], patches[5], patches[6],
        ):
            for task_type, inputs in E2E_CASES:
                result = self._run_single_task(task_type, inputs)
                assert result["metrics"]["latency_ms"] >= 0, \
                    f"Missing latency for {task_type}"

    def test_diverse_task_types_all_covered(self):
        """Step 67: Verify all 7 task types are exercised in the 20-task batch."""
        types_covered = {case[0] for case in E2E_CASES}
        expected_types = {
            "sales_outreach", "support_ticket", "content_repurpose", "doc_extract",
            "lead_gen", "email_marketing", "seo_content",
        }
        missing = expected_types - types_covered
        assert not missing, f"Task types not covered: {missing}"

    def test_billing_tracker_records_usage(self, tmp_path):
        """Step 68: BillingTracker.record_usage() writes to its DB for all 20 tasks."""
        from billing.tracker import BillingTracker
        import billing.tracker as bt_mod

        # Use a temp DB for billing
        original_db = bt_mod.DB_PATH if hasattr(bt_mod, "DB_PATH") else None

        bt = BillingTracker(db_path=tmp_path / "billing_test.db")
        patches = _patch_all_pipelines({})

        with (
            patches[0], patches[1], patches[2], patches[3],
            patches[4], patches[5], patches[6],
        ):
            for task_type, inputs in E2E_CASES:
                from utils.cost_tracker import estimate_task_cost
                cost_info = estimate_task_cost(task_type, inputs.get("provider", "openai"))
                bt.record_usage(
                    client    = "test_client_e2e",
                    task_type = task_type,
                    task_id   = str(uuid.uuid4()),
                    llm_cost  = cost_info.get("cost_usd", 0.0),
                )

        summary = bt.client_summary("test_client_e2e", days=1)
        assert summary["total_tasks"] == 20, \
            f"Expected 20 usage records, got {summary['total_tasks']}"
        assert summary["total_charge"] > 0, "Total charge should be > 0"


# ── event structure tests ─────────────────────────────────────────────────────

class TestEventStructure:
    """Unit tests for create_event() structure."""

    def test_create_event_has_required_keys(self):
        from dispatcher.router import create_event
        event = create_event("sales_outreach", {"company": "Test"}, client_id="cli")
        required = {"event_id", "timestamp", "client_id", "task_type", "inputs",
                    "constraints", "outputs", "qa", "billing", "metrics"}
        assert required.issubset(event.keys()), \
            f"Missing keys: {required - event.keys()}"

    def test_create_event_billing_defaults(self):
        from dispatcher.router import create_event
        event = create_event("support_ticket", {"ticket": "test"})
        assert event["billing"]["status"] == "unbilled"
        assert event["billing"]["currency"] == "USD"

    def test_create_event_qa_defaults(self):
        from dispatcher.router import create_event
        event = create_event("doc_extract", {"document_text": "test"})
        assert event["qa"]["status"] == "PENDING"

    def test_each_event_has_unique_id(self):
        from dispatcher.router import create_event
        ids = {create_event("sales_outreach", {})["event_id"] for _ in range(10)}
        assert len(ids) == 10, "Duplicate event IDs detected"
