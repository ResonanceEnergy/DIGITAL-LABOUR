"""OpenClaw Engine — Central automation orchestrator for Bit Rage Labour.

Connects all platform automation (job hunt, bidding, delivery, revenue tracking)
into a single dispatch layer that NERVE runs autonomously.

Three operational modes:
  1. Pipeline executor   — run multi-agent pipelines from pipelines.json locally
  2. Freelance lifecycle — hunt → bid → win → deliver → collect across 5 platforms
  3. Revenue reconciler  — track earnings from all platforms into billing.db

Usage:
    from openclaw.engine import OpenClawEngine
    engine = OpenClawEngine()

    # Run a pipeline
    result = engine.run_pipeline("lead_to_close", INDUSTRY="fintech", ROLE="CTO")

    # Full freelance cycle
    report = engine.freelance_cycle()

    # Revenue reconciliation
    engine.reconcile_revenue()
"""

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

PIPELINES_FILE = PROJECT_ROOT / "openclaw" / "bit-rage-labour" / "workflows" / "pipelines.json"
STATE_FILE = PROJECT_ROOT / "data" / "openclaw_state.json"
LOG_DIR = PROJECT_ROOT / "data" / "openclaw_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Platform config ─────────────────────────────────────────────────────────

PLATFORMS = ["freelancer", "upwork", "fiverr", "pph", "guru"]

# Maps platform names to their job hunt modules + functions
JOBHUNT_DISPATCH = {
    "freelancer": "automation.freelancer_jobhunt",
    "upwork": "automation.upwork_jobhunt",
    "pph": "automation.pph_jobhunt",
    "guru": "automation.guru_jobhunt",
}

# Maps platform names to their delivery modules
DELIVERY_DISPATCH = {
    "freelancer": "automation.freelancer_client",
    "upwork": "automation.upwork_delivery",
    "fiverr": "automation.fiverr_orders",
}

# Maps platform names to their work agents
AGENT_DISPATCH = {
    "freelancer": "agents.freelancer_work.runner",
    "upwork": "agents.upwork_work.runner",
    "fiverr": "agents.fiverr_work.runner",
    "pph": "agents.pph_work.runner",
    "guru": "agents.guru_work.runner",
}


class OpenClawEngine:
    """Central orchestration engine for all Bit Rage Labour automation."""

    def __init__(self):
        self.state = self._load_state()
        self.pipelines = self._load_pipelines()

    # ── State Management ────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return {
            "cycles_run": 0,
            "total_bids": 0,
            "total_deliveries": 0,
            "total_revenue_tracked": 0.0,
            "last_cycle": None,
            "platform_stats": {p: {"bids": 0, "wins": 0, "delivered": 0, "revenue": 0.0} for p in PLATFORMS},
        }

    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def _log(self, event_type: str, data: dict):
        """Append event to daily log."""
        log_file = LOG_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            **data,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    # ── Pipeline Executor ───────────────────────────────────────────────────

    def _load_pipelines(self) -> list[dict]:
        if PIPELINES_FILE.exists():
            return json.loads(PIPELINES_FILE.read_text(encoding="utf-8"))
        return []

    def list_pipelines(self) -> list[str]:
        return [p["name"] for p in self.pipelines]

    def run_pipeline(self, name: str, provider: str = "openai", **variables) -> dict:
        """Execute a multi-agent pipeline locally (not via HTTP).

        Args:
            name: Pipeline name from pipelines.json
            provider: LLM provider to use
            **variables: Variable substitutions (INDUSTRY, TOPIC, etc.)

        Returns:
            dict with pipeline results per step
        """
        pipeline = None
        for p in self.pipelines:
            if p["name"] == name:
                pipeline = p
                break

        if not pipeline:
            return {"error": f"Unknown pipeline: {name}", "available": self.list_pipelines()}

        print(f"\n[OPENCLAW] Pipeline: {name} ({len(pipeline['steps'])} steps)")
        results = []
        step_outputs: dict[int, Any] = {}

        for i, step in enumerate(pipeline["steps"]):
            agent_name = step["agent"]
            raw_inputs = step.get("inputs", {})

            # Substitute variables
            resolved = self._substitute(raw_inputs, variables, step_outputs)

            # Resolve dynamic agent name (e.g. $FROM_STEP_2.assigned_agent)
            if agent_name.startswith("$"):
                agent_name = self._resolve_var(agent_name, variables, step_outputs)
                if not agent_name or agent_name.startswith("$"):
                    results.append({"step": i + 1, "agent": agent_name, "status": "skipped", "reason": "unresolved agent"})
                    continue

            print(f"  [{i + 1}/{len(pipeline['steps'])}] {agent_name}...")
            start = time.time()

            try:
                from dispatcher.router import create_event, route_task
                event = create_event(
                    task_type=agent_name,
                    inputs={**resolved, "provider": provider},
                    client_id="openclaw-pipeline",
                )
                result = route_task(event)
                elapsed = time.time() - start
                qa = result.get("qa", {}).get("status", "N/A")
                outputs = result.get("outputs", {})
                step_outputs[i + 1] = outputs

                step_result = {
                    "step": i + 1,
                    "agent": agent_name,
                    "status": "completed",
                    "qa": qa,
                    "elapsed_s": round(elapsed, 1),
                    "outputs": outputs,
                }
                results.append(step_result)
                print(f"      Done ({elapsed:.1f}s) QA: {qa}")
            except Exception as e:
                elapsed = time.time() - start
                results.append({
                    "step": i + 1,
                    "agent": agent_name,
                    "status": "error",
                    "error": str(e),
                    "elapsed_s": round(elapsed, 1),
                })
                print(f"      ERROR: {e}")
                step_outputs[i + 1] = {}

        report = {
            "pipeline": name,
            "steps_total": len(pipeline["steps"]),
            "steps_completed": sum(1 for r in results if r["status"] == "completed"),
            "steps_passed_qa": sum(1 for r in results if r.get("qa") == "PASS"),
            "total_elapsed_s": round(sum(r.get("elapsed_s", 0) for r in results), 1),
            "results": results,
        }

        self._log("pipeline_run", {"pipeline": name, "steps": len(results), "passed": report["steps_passed_qa"]})
        print(f"[OPENCLAW] Pipeline {name}: {report['steps_completed']}/{report['steps_total']} completed, {report['steps_passed_qa']} passed QA")
        return report

    def _substitute(self, obj: Any, variables: dict, step_outputs: dict) -> Any:
        """Recursively substitute $VAR and $FROM_STEP_N references."""
        if isinstance(obj, str):
            for key, val in variables.items():
                obj = obj.replace(f"${key}", str(val))
            # Handle $FROM_STEP_N references
            for step_num, output in step_outputs.items():
                token = f"$FROM_STEP_{step_num}"
                if token in obj:
                    obj = obj.replace(token, json.dumps(output) if isinstance(output, (dict, list)) else str(output))
            return obj
        if isinstance(obj, dict):
            return {k: self._substitute(v, variables, step_outputs) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._substitute(v, variables, step_outputs) for v in obj]
        return obj

    def _resolve_var(self, token: str, variables: dict, step_outputs: dict) -> str:
        """Resolve a single variable reference like $FROM_STEP_2.assigned_agent."""
        if not token.startswith("$"):
            return token
        token = token[1:]  # strip $
        if token in variables:
            return str(variables[token])
        # Parse FROM_STEP_N.field
        if token.startswith("FROM_STEP_"):
            parts = token.split(".", 1)
            try:
                step_num = int(parts[0].replace("FROM_STEP_", ""))
                output = step_outputs.get(step_num, {})
                if len(parts) > 1 and isinstance(output, dict):
                    return str(output.get(parts[1], f"${token}"))
                return str(output)
            except (ValueError, IndexError):
                pass
        return f"${token}"

    # ── Freelance Lifecycle ─────────────────────────────────────────────────

    def freelance_cycle(self, platforms: list[str] | None = None, scan_only: bool = False) -> dict:
        """Run one full freelance automation cycle across platforms.

        Steps:
          1. Aggregate jobs from all platforms via job_aggregator
          2. Run autobidder scan (scores, filters, generates bids)
          3. Check for active orders/contracts needing delivery
          4. Track and reconcile revenue

        Args:
            platforms: Subset of platforms to scan (default: all)
            scan_only: If True, aggregate + score but don't bid

        Returns:
            Cycle report with stats per platform
        """
        cycle_id = uuid4().hex[:8]
        cycle_start = time.time()
        target_platforms = platforms or PLATFORMS
        print(f"\n[OPENCLAW] Freelance Cycle {cycle_id} — {', '.join(target_platforms)}")

        report: dict[str, Any] = {
            "cycle_id": cycle_id,
            "started": datetime.now(timezone.utc).isoformat(),
            "platforms": target_platforms,
            "phases": {},
        }

        # ── Phase 1: Job Aggregation ────────────────────────────────────────
        print(f"\n  [1/4] Job Aggregation...")
        try:
            from automation.job_aggregator import aggregate, show_feed
            feed = aggregate(max_age_hours=24)
            unbid = [j for j in feed if not j.get("already_bid") and j.get("rank_score", 0) >= 0.25]
            report["phases"]["aggregation"] = {
                "total_jobs": len(feed),
                "unbid_opportunities": len(unbid),
                "top_platforms": list(set(j.get("platform", "unknown") for j in feed[:20])),
            }
            print(f"      {len(feed)} jobs aggregated, {len(unbid)} unbid opportunities")
        except Exception as e:
            report["phases"]["aggregation"] = {"error": str(e)}
            print(f"      ERROR: {e}")
            feed = []
            unbid = []

        # ── Phase 2: Autobidder ─────────────────────────────────────────────
        print(f"\n  [2/4] Autobidder...")
        if scan_only:
            report["phases"]["bidding"] = {"status": "scan_only", "bids": 0}
            print(f"      Scan-only mode — skipping bids")
        else:
            try:
                from automation.autobidder import run_scan
                scan_result = run_scan(dry_run=False)
                bids_queued = scan_result.get("bids_queued", 0) if isinstance(scan_result, dict) else 0
                report["phases"]["bidding"] = {
                    "bids_queued": bids_queued,
                    "daily_spend": scan_result.get("daily_spend", 0) if isinstance(scan_result, dict) else 0,
                }
                self.state["total_bids"] += bids_queued
                print(f"      {bids_queued} bids queued")
            except Exception as e:
                report["phases"]["bidding"] = {"error": str(e)}
                print(f"      ERROR: {e}")

        # ── Phase 3: Delivery Check ─────────────────────────────────────────
        print(f"\n  [3/4] Delivery Status...")
        delivery_report: dict[str, Any] = {}
        for platform in target_platforms:
            if platform in DELIVERY_DISPATCH:
                try:
                    mod = __import__(DELIVERY_DISPATCH[platform], fromlist=["show_status"])
                    if hasattr(mod, "show_status"):
                        mod.show_status()
                        delivery_report[platform] = "checked"
                    else:
                        delivery_report[platform] = "no show_status fn"
                except Exception as e:
                    delivery_report[platform] = f"error: {e}"
            else:
                delivery_report[platform] = "no delivery module"
        report["phases"]["delivery"] = delivery_report
        print(f"      Checked: {list(delivery_report.keys())}")

        # ── Phase 4: Revenue Reconciliation ─────────────────────────────────
        print(f"\n  [4/4] Revenue Reconciliation...")
        rev = self.reconcile_revenue()
        report["phases"]["revenue"] = rev

        # ── Finalize ────────────────────────────────────────────────────────
        elapsed = time.time() - cycle_start
        report["elapsed_s"] = round(elapsed, 1)
        report["finished"] = datetime.now(timezone.utc).isoformat()

        self.state["cycles_run"] += 1
        self.state["last_cycle"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

        self._log("freelance_cycle", {
            "cycle_id": cycle_id,
            "jobs": report["phases"].get("aggregation", {}).get("total_jobs", 0),
            "bids": report["phases"].get("bidding", {}).get("bids_queued", 0),
            "elapsed_s": elapsed,
        })

        print(f"\n[OPENCLAW] Freelance Cycle {cycle_id} complete ({elapsed:.1f}s)")
        return report

    # ── Revenue Reconciliation ──────────────────────────────────────────────

    def reconcile_revenue(self) -> dict:
        """Check all revenue sources and record to billing tracker.

        Scans:
          1. Stripe (via revenue_daemon)
          2. Platform earnings data files
          3. BillingTracker usage records

        Returns:
            Revenue summary across all sources
        """
        revenue: dict[str, Any] = {"sources": {}, "total": 0.0}

        # Stripe
        try:
            from automation.revenue_daemon import check_stripe_revenue
            stripe_rev = check_stripe_revenue()
            revenue["sources"]["stripe"] = {
                "total": stripe_rev.get("total", 0),
                "new_charges": stripe_rev.get("new_charges", 0),
            }
            revenue["total"] += stripe_rev.get("total", 0)
        except Exception as e:
            revenue["sources"]["stripe"] = {"error": str(e)}

        # Platform earnings from data files
        data_dir = PROJECT_ROOT / "data"
        for platform in PLATFORMS:
            platform_dir = data_dir / f"{platform}_jobs"
            earnings_file = platform_dir / "earnings.json"
            if earnings_file.exists():
                try:
                    earnings = json.loads(earnings_file.read_text(encoding="utf-8"))
                    total = sum(e.get("amount", 0) for e in earnings) if isinstance(earnings, list) else earnings.get("total", 0)
                    revenue["sources"][platform] = {"total": round(total, 2), "entries": len(earnings) if isinstance(earnings, list) else 0}
                    revenue["total"] += total
                except Exception as e:
                    revenue["sources"][platform] = {"error": str(e)}

        # BillingTracker internal usage
        try:
            from billing.tracker import BillingTracker
            bt = BillingTracker()
            report = bt.revenue_report(days=30)
            revenue["sources"]["internal_billing"] = {
                "total_revenue": report["total_revenue"],
                "total_cost": report["total_cost"],
                "gross_margin": report["gross_margin"],
                "total_tasks": report["total_tasks"],
            }
        except Exception as e:
            revenue["sources"]["internal_billing"] = {"error": str(e)}

        revenue["total"] = round(revenue["total"], 2)
        revenue["checked_at"] = datetime.now(timezone.utc).isoformat()
        self._log("revenue_check", revenue)

        print(f"      Revenue total: ${revenue['total']:.2f} across {len(revenue['sources'])} sources")
        return revenue

    # ── Direct Agent Dispatch ───────────────────────────────────────────────

    def dispatch_to_agent(self, task_type: str, inputs: dict, client: str = "openclaw",
                          provider: str = "openai") -> dict:
        """Dispatch a single task through the router (with billing)."""
        from dispatcher.router import create_event, route_task
        event = create_event(task_type=task_type, inputs={**inputs, "provider": provider}, client_id=client)
        return route_task(event)

    def dispatch_platform_work(self, platform: str, action: str, job_data: dict = None,
                                provider: str = "openai") -> dict:
        """Dispatch work to a specific platform agent.

        Args:
            platform: freelancer, upwork, fiverr, pph, guru
            action: bid/propose/deliver/quote depending on platform
            job_data: Platform-specific job data
            provider: LLM provider
        """
        agent_module = AGENT_DISPATCH.get(platform)
        if not agent_module:
            return {"error": f"Unknown platform: {platform}"}

        try:
            mod = __import__(agent_module, fromlist=["run_pipeline"])
            result = mod.run_pipeline(
                action=action,
                job_data=job_data or {},
                provider=provider,
            )
            output = result.model_dump() if hasattr(result, "model_dump") else result
            self._log("platform_dispatch", {"platform": platform, "action": action, "qa": output.get("qa", {}).get("status", "N/A")})
            return output
        except Exception as e:
            return {"error": str(e), "platform": platform, "action": action}

    # ── Platform Setup ──────────────────────────────────────────────────────

    def platform_setup(self, platforms: list[str] | None = None, headless: bool = False) -> dict:
        """One-time setup: deploy gigs to Fiverr and fill profiles on Upwork/PPH/Guru.

        Fiverr:   generate cover images -> deploy top-4 gigs via Playwright browser
        Upwork:   fill freelancer profile + post top services
        PPH/Guru: fill profile (requires manual login first)

        Args:
            platforms: Subset of ["fiverr", "upwork", "pph", "guru"] (default: all)
            headless:  Run browser in headless mode (requires saved cookies)

        Returns:
            Setup report per platform
        """
        target = platforms or ["fiverr", "upwork", "pph", "guru"]
        report: dict[str, Any] = {
            "started": datetime.now(timezone.utc).isoformat(),
            "platforms": target,
            "results": {},
        }

        print(f"\n[OPENCLAW] Platform Setup — {', '.join(target)}")

        if "fiverr" in target:
            print("\n  [FIVERR] Generating gig images + deploying top-4 gigs...")
            try:
                from automation.fiverr_automation import generate_all_images, deploy_all_browser, DEFAULT_TOP_4
                img_paths = generate_all_images()
                print(f"      {len(img_paths)} cover images generated")
                deploy_all_browser(gig_indices=DEFAULT_TOP_4)
                report["results"]["fiverr"] = {
                    "images_generated": len(img_paths),
                    "gigs_deployed": len(DEFAULT_TOP_4),
                    "gig_indices": DEFAULT_TOP_4,
                    "status": "ok",
                }
            except Exception as e:
                print(f"      ERROR: {e}")
                report["results"]["fiverr"] = {"status": "error", "error": str(e)}

        if "upwork" in target:
            print("\n  [UPWORK] Filling profile + posting services...")
            try:
                from automation.platform_automation import fill_profile, UPWORK_PROFILE
                fill_profile("upwork")
                report["results"]["upwork"] = {"profile_filled": True, "status": "ok"}
            except Exception as e:
                print(f"      ERROR: {e}")
                report["results"]["upwork"] = {"status": "error", "error": str(e)}

        for platform in ["pph", "guru"]:
            if platform in target:
                print(f"\n  [{platform.upper()}] Filling profile...")
                try:
                    from automation.platform_automation import fill_profile
                    fill_profile(platform)
                    report["results"][platform] = {"profile_filled": True, "status": "ok"}
                except Exception as e:
                    print(f"      ERROR: {e}")
                    report["results"][platform] = {"status": "error", "error": str(e)}

        report["finished"] = datetime.now(timezone.utc).isoformat()
        self._log("platform_setup", {"platforms": target, "results": report["results"]})
        ok = sum(1 for r in report["results"].values() if r.get("status") == "ok")
        print(f"\n[OPENCLAW] Platform Setup complete — {ok}/{len(target)} platforms OK")
        return report

    # ── Status ──────────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Current OpenClaw engine status."""
        return {
            "engine": "OpenClaw",
            "version": "1.0.0",
            "state": self.state,
            "pipelines_available": self.list_pipelines(),
            "platforms": PLATFORMS,
            "agent_dispatch": list(AGENT_DISPATCH.keys()),
            "delivery_modules": list(DELIVERY_DISPATCH.keys()),
            "jobhunt_modules": list(JOBHUNT_DISPATCH.keys()),
        }


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenClaw Engine — Bit Rage Labour Automation")
    parser.add_argument("command", choices=["status", "cycle", "pipeline", "revenue", "dispatch", "setup"],
                        help="Command to run")
    parser.add_argument("--pipeline", type=str, help="Pipeline name for 'pipeline' command")
    parser.add_argument("--platforms", type=str, help="Comma-separated platforms for 'cycle' or 'setup'")
    parser.add_argument("--scan-only", action="store_true", help="Aggregate only, don't bid")
    parser.add_argument("--headless", action="store_true", help="Run browser headless for 'setup'")
    parser.add_argument("--agent", type=str, help="Agent name for 'dispatch'")
    parser.add_argument("--inputs", type=str, help="JSON inputs for 'dispatch'")
    parser.add_argument("--provider", type=str, default="openai", help="LLM provider")
    args = parser.parse_args()

    engine = OpenClawEngine()

    if args.command == "status":
        print(json.dumps(engine.status(), indent=2))

    elif args.command == "cycle":
        platforms = args.platforms.split(",") if args.platforms else None
        report = engine.freelance_cycle(platforms=platforms, scan_only=args.scan_only)
        print(json.dumps(report, indent=2))

    elif args.command == "pipeline":
        if not args.pipeline:
            print("Available pipelines:")
            for name in engine.list_pipelines():
                print(f"  {name}")
        else:
            result = engine.run_pipeline(args.pipeline, provider=args.provider)
            print(json.dumps(result, indent=2, default=str))

    elif args.command == "revenue":
        rev = engine.reconcile_revenue()
        print(json.dumps(rev, indent=2))

    elif args.command == "dispatch":
        if not args.agent:
            print("--agent required for dispatch command")
        else:
            inputs = json.loads(args.inputs) if args.inputs else {}
            result = engine.dispatch_to_agent(args.agent, inputs, provider=args.provider)
            print(json.dumps(result, indent=2, default=str))

    elif args.command == "setup":
        platforms = args.platforms.split(",") if args.platforms else None
        result = engine.platform_setup(platforms=platforms, headless=args.headless)
        print(json.dumps(result, indent=2, default=str))
