"""4-agent concurrent stress test — Step 90.

Fires 40 mixed tasks (10 per core agent) across all 4 LLM providers
using ThreadPoolExecutor for concurrency. Verifies:
  - Zero crashes / unhandled exceptions
  - All 40 tasks return a valid result event
  - QA pass rate ≥ 80 %
  - p50 / p95 latency within acceptable bounds
  - Dispatcher metrics recorded correctly

Run:
    pytest tests/test_stress.py -v
    pytest tests/test_stress.py -v -s           # with timing output
"""

from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median, quantiles
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ── Task matrix: 4 agents × 10 providers combos each = 40 tasks ─────────────

# 4 core agents, 4 providers → 10 tasks each (mix providers per agent)
STRESS_TASKS = []
PROVIDERS = ["openai", "anthropic", "gemini", "grok"]
CORE_AGENTS = ["sales_outreach", "support_ticket", "content_repurpose", "doc_extract"]

AGENT_INPUTS = {
    "sales_outreach":    {"company": "StressTestCo", "role": "CEO"},
    "support_ticket":    {"ticket": "Stress test ticket #%d", "kb": "Test KB"},
    "content_repurpose": {"source_text": "Stress test content article #%d.", "formats": ["tweet"]},
    "doc_extract":       {"document_text": "Stress test document clause #%d.", "doc_type": "contract"},
}

for i in range(10):
    agent   = CORE_AGENTS[i % 4]
    provider = PROVIDERS[i % 4]
    base_inputs = dict(AGENT_INPUTS[agent])
    # Interpolate any %d format strings
    base_inputs = {k: (v % i if isinstance(v, str) and "%d" in v else v)
                   for k, v in base_inputs.items()}
    base_inputs["provider"] = provider
    STRESS_TASKS.append((agent, base_inputs))

# Add 5 tasks per remaining agent to reach exactly 40
for i, agent in enumerate(CORE_AGENTS):
    for j in range(5):
        provider = PROVIDERS[j % 4]
        base_inputs = dict(AGENT_INPUTS[agent])
        base_inputs = {k: (v % (i * 10 + j) if isinstance(v, str) and "%d" in v else v)
                       for k, v in base_inputs.items()}
        base_inputs["provider"] = provider
        STRESS_TASKS.append((agent, base_inputs))

# Trim or extend to exactly 40
while len(STRESS_TASKS) < 40:
    agent    = CORE_AGENTS[len(STRESS_TASKS) % 4]
    provider = PROVIDERS[len(STRESS_TASKS) % 4]
    base_inputs = dict(AGENT_INPUTS[agent])
    base_inputs["provider"] = provider
    STRESS_TASKS.append((agent, base_inputs))

STRESS_TASKS = STRESS_TASKS[:40]
assert len(STRESS_TASKS) == 40, f"Expected 40 stress tasks, got {len(STRESS_TASKS)}"


# ── Mock helpers ─────────────────────────────────────────────────────────────

def _make_mock_result(task_type: str) -> MagicMock:
    r = MagicMock()
    r.qa_status = "PASS"
    r.model_dump.return_value = {
        "task_type": task_type,
        "status": "complete",
        "output": f"Stress result for {task_type}",
        "qa_status": "PASS",
    }
    r.qa = SimpleNamespace(status="PASS")
    return r


def _all_pipeline_patches():
    return [
        patch("agents.sales_ops.runner.run_pipeline",        return_value=_make_mock_result("sales_outreach")),
        patch("agents.support.runner.run_pipeline",          return_value=_make_mock_result("support_ticket")),
        patch("agents.content_repurpose.runner.run_pipeline", return_value=_make_mock_result("content_repurpose")),
        patch("agents.doc_extract.runner.run_pipeline",      return_value=_make_mock_result("doc_extract")),
        patch("agents.lead_gen.runner.run_pipeline",         return_value=_make_mock_result("lead_gen")),
        patch("agents.email_marketing.runner.run_pipeline",  return_value=_make_mock_result("email_marketing")),
        patch("agents.seo_content.runner.run_pipeline",      return_value=_make_mock_result("seo_content")),
    ]


def _run_one(task_type: str, inputs: dict) -> dict:
    """Worker function — routes one task and returns timing + result."""
    from dispatcher.router import create_event, route_task
    from billing.tracker import PRICING

    event    = create_event(task_type, inputs, client_id="stress_test")
    t0       = time.perf_counter()
    result   = route_task(event)
    latency  = round((time.perf_counter() - t0) * 1000, 1)  # ms

    charge = PRICING.get(task_type, {}).get("per_task", 0.0)
    result["billing"]["amount"] = charge
    result["metrics"]["latency_ms"] = latency

    return {
        "event_id":      event["event_id"],
        "task_type":     task_type,
        "qa_status":     result["qa"].get("status", "UNKNOWN"),
        "billing_amt":   charge,
        "latency_ms":    latency,
        "error":         None,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestStress40Tasks:
    """Step 90 — 4-agent stress test: 40 tasks, concurrent, all providers."""

    @pytest.fixture(scope="class")
    def stress_results(self):
        """Run all 40 tasks concurrently and return results list."""
        patches = _all_pipeline_patches()
        results = []
        errors  = []

        with (
            patches[0], patches[1], patches[2], patches[3],
            patches[4], patches[5], patches[6],
        ):
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {
                    executor.submit(_run_one, task_type, inputs): (task_type, inputs)
                    for task_type, inputs in STRESS_TASKS
                }
                for future in as_completed(futures):
                    task_type, inputs = futures[future]
                    try:
                        results.append(future.result(timeout=30))
                    except Exception as exc:
                        errors.append({"task_type": task_type, "error": str(exc)})

        return {"results": results, "errors": errors}

    def test_all_40_complete(self, stress_results):
        """All 40 stress tasks return without exception."""
        errors  = stress_results["errors"]
        results = stress_results["results"]
        assert not errors, f"Exceptions in {len(errors)}/40 tasks: {errors[:3]}"
        assert len(results) == 40, f"Only {len(results)}/40 tasks returned"

    def test_qa_pass_rate_above_80pct(self, stress_results):
        """QA pass rate ≥ 80 % across all 40 tasks."""
        results = stress_results["results"]
        passed  = sum(1 for r in results if r["qa_status"] in ("PASS", "MANUAL_REVIEW"))
        rate    = (passed / len(results)) * 100 if results else 0
        assert rate >= 80, f"QA pass rate too low: {rate:.1f}% ({passed}/40)"

    def test_all_billing_amounts_nonzero(self, stress_results):
        """Every completed task has a non-zero billing amount."""
        results = stress_results["results"]
        zero_billing = [r for r in results if r["billing_amt"] <= 0]
        assert not zero_billing, \
            f"{len(zero_billing)} tasks with zero billing: {[z['task_type'] for z in zero_billing[:5]]}"

    def test_p95_latency_under_5s(self, stress_results):
        """p95 latency < 5 000 ms (mocked, so should be near-zero)."""
        results   = stress_results["results"]
        latencies = sorted(r["latency_ms"] for r in results)
        if len(latencies) < 2:
            pytest.skip("Not enough results for percentile calculation")
        p95 = quantiles(latencies, n=20)[18]  # 95th percentile
        assert p95 < 5000, f"p95 latency {p95:.0f}ms exceeds 5 000ms threshold"

    def test_all_4_agents_exercised(self, stress_results):
        """All 4 core agents are called at least once."""
        results       = stress_results["results"]
        types_covered = {r["task_type"] for r in results}
        required      = set(CORE_AGENTS)
        missing       = required - types_covered
        assert not missing, f"Agents not exercised: {missing}"

    def test_all_4_providers_in_inputs(self):
        """Task matrix includes all 4 LLM providers."""
        providers_covered = {inputs["provider"] for _, inputs in STRESS_TASKS}
        assert providers_covered == set(PROVIDERS), \
            f"Missing providers: {set(PROVIDERS) - providers_covered}"

    def test_event_ids_unique_across_all_40(self, stress_results):
        """All 40 event IDs are unique (no collisions under concurrency)."""
        results = stress_results["results"]
        ids     = [r["event_id"] for r in results]
        assert len(ids) == len(set(ids)), \
            f"{len(ids) - len(set(ids))} duplicate event IDs found under concurrent load"

    def test_dispatcher_metrics_populated(self, stress_results):
        """Dispatcher metrics are non-zero after 40 routed tasks."""
        from dispatcher.router import get_metrics
        metrics = get_metrics()
        total_calls = sum(m["calls"] for m in metrics.values())
        assert total_calls > 0, "Dispatcher metrics show 0 calls after stress run"


class TestStressLatencyDistribution:
    """Latency distribution analysis — purely statistical."""

    def test_latency_stats(self):
        """Run 40 tasks sequentially and compute latency distribution."""
        patches = _all_pipeline_patches()
        latencies = []

        with (
            patches[0], patches[1], patches[2], patches[3],
            patches[4], patches[5], patches[6],
        ):
            for task_type, inputs in STRESS_TASKS:
                result = _run_one(task_type, inputs)
                latencies.append(result["latency_ms"])

        assert len(latencies) == 40
        p50 = median(latencies)
        p95 = quantiles(latencies, n=20)[18]
        avg = mean(latencies)

        # These should all be very small with mocked LLM, but assert reasonable bounds
        assert p50 < 10_000, f"Median latency {p50:.0f}ms is unexpectedly high"
        assert avg  < 10_000, f"Mean latency {avg:.0f}ms is unexpectedly high"
        # Print stats (visible with pytest -s)
        print(f"\n  Latency stats over 40 tasks:")
        print(f"    p50 = {p50:.1f}ms")
        print(f"    p95 = {p95:.1f}ms")
        print(f"    avg = {avg:.1f}ms")
        print(f"    min = {min(latencies):.1f}ms")
        print(f"    max = {max(latencies):.1f}ms")
