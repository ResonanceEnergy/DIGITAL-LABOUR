#!/usr/bin/env python3
"""
REPO DEPOT FLYWHEEL CONTROLLER - REAL IMPLEMENTATION
=====================================================
Drives continuous autonomous development cycles using OPTIMUS + GASKET agents
across the entire portfolio. No scaffold, no fake tasks, no placeholders.

Cycle procedure:
  1. SCAN    - Discover repos, check staleness, prioritize work
  2. PLAN    - Select repos + task categories for this cycle
  3. EXECUTE - Dispatch OPTIMUS (strategic) and GASKET (implementation) agents
  4. VERIFY  - Validate artifacts, check quality gates
  5. REPORT  - Log results, update metrics, record cycle
"""

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("flywheel")


class CyclePhase(Enum):
    IDLE = "idle"
    SCAN = "scan"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    REPORT = "report"


@dataclass
class CycleResult:
    """Result of one complete flywheel cycle"""
    cycle_number: int
    started_at: str
    finished_at: str = ""
    duration_seconds: float = 0.0
    repos_processed: int = 0
    tasks_dispatched: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    artifacts_created: int = 0
    commits_made: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle": self.cycle_number,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": round(self.duration_seconds, 1),
            "repos_processed": self.repos_processed,
            "tasks_dispatched": self.tasks_dispatched,
            "tasks_succeeded": self.tasks_succeeded,
            "tasks_failed": self.tasks_failed,
            "artifacts_created": self.artifacts_created,
            "commits_made": self.commits_made,
            "errors": self.errors[:10],
        }


@dataclass
class RepoStaleness:
    """How stale a repo is - drives prioritization"""
    name: str
    tier: str
    days_since_agent_commit: float
    has_docs: bool
    has_tests: bool
    has_architecture: bool
    priority_score: float = 0.0


class FlywheelController:
    """
    Real flywheel that drives continuous development cycles.

    Wired to:
      - PortfolioRunner -> manages repo list + prioritization
      - AgentDispatcher -> routes to OPTIMUS (strategic) and GASKET (implementation)
      - Git -> commits and tracks progress
    """

    def __init__(self, workspace: Path, config: Dict[str, Any] = None):
        self.workspace = workspace
        self.repos_dir = workspace / "repos"
        self.state_dir = workspace / "state" / "flywheel"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        cfg = config or {}
        self.cycle_interval = cfg.get("cycle_interval_seconds", 300)
        self.max_repos_per_cycle = cfg.get("max_repos_per_cycle", 3)
        self.cooldown_hours = cfg.get("cooldown_hours", 24)
        self.agent_type = cfg.get("agent_type", "both")
        self.tier_weights = cfg.get("tier_weights", {"L": 100, "M": 50, "S": 10})

        self.cycle_count = self._load_cycle_count()
        self.is_running = False
        self.active_phase = CyclePhase.IDLE
        self.last_cycle_result = None
        self._runner = None

        logger.info(f"FlywheelController initialized - workspace: {workspace}")
        logger.info(f"  cycle_interval={self.cycle_interval}s, max_repos={self.max_repos_per_cycle}")
        logger.info(f"  cooldown={self.cooldown_hours}h, agent_type={self.agent_type}")
        logger.info(f"  cycle_count (resumed): {self.cycle_count}")

    def _get_runner(self):
        if self._runner is None:
            from repo_depot.core.portfolio_runner import PortfolioRunner
            self._runner = PortfolioRunner(self.workspace)
            logger.info(f"PortfolioRunner loaded - {len(self._runner.repos)} repos")
        return self._runner

    def _get_portfolio(self):
        pf = self.workspace / "portfolio.json"
        if pf.exists():
            with open(pf) as f:
                data = json.load(f)
            return data.get("repositories", [])
        return []

    def _load_cycle_count(self):
        f = self.state_dir / "cycle_count.txt"
        if f.exists():
            try:
                return int(f.read_text().strip())
            except Exception:
                pass
        return 0

    def _save_cycle_count(self):
        (self.state_dir / "cycle_count.txt").write_text(str(self.cycle_count))

    def _save_cycle_result(self, result):
        log_file = self.state_dir / "cycle_log.jsonl"
        data = json.dumps(result.to_dict()) + "\n"
        # Retry up to 5x for file lock issues
        for attempt in range(5):
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(data)
                break
            except (IOError, OSError) as e:
                if attempt < 4:
                    time.sleep(1.0)
                else:
                    logger.error(f"Failed to write cycle log after 5 attempts: {e}")
                    # Fallback: write to a temp file
                    fallback = self.state_dir / f"cycle_{result.cycle_number}_fallback.json"
                    try:
                        fallback.write_text(data, encoding="utf-8")
                        logger.info(f"Cycle result saved to fallback: {fallback}")
                    except Exception:
                        pass

    # ---- SCAN ----

    def scan_repos(self):
        """Scan all local repos and score them by staleness."""
        self.active_phase = CyclePhase.SCAN
        portfolio = self._get_portfolio()
        results = []

        for repo_entry in portfolio:
            name = repo_entry.get("name", "")
            tier = repo_entry.get("tier", "S")
            repo_path = self.repos_dir / name

            if not repo_path.exists():
                continue

            days_since = self._days_since_agent_commit(repo_path)
            has_docs = (repo_path / "docs").exists() or (repo_path / "README.md").exists()
            has_tests = (repo_path / "tests").exists()
            has_arch = (repo_path / "docs" / "ARCHITECTURE.md").exists()

            base_weight = self.tier_weights.get(tier, 10)
            staleness_bonus = min(days_since * 10, 200)
            missing_bonus = 0
            if not has_docs:
                missing_bonus += 30
            if not has_tests:
                missing_bonus += 30
            if not has_arch:
                missing_bonus += 20

            score = base_weight + staleness_bonus + missing_bonus

            if days_since < (self.cooldown_hours / 24.0):
                score = score * 0.1

            results.append(RepoStaleness(
                name=name, tier=tier,
                days_since_agent_commit=round(days_since, 1),
                has_docs=has_docs, has_tests=has_tests,
                has_architecture=has_arch,
                priority_score=round(score, 1),
            ))

        results.sort(key=lambda r: r.priority_score, reverse=True)
        return results

    def _days_since_agent_commit(self, repo_path):
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ci", "--author=OPTIMUS", "--author=GASKET", "--author=ResonanceEnergy", "--author=re-repo-bot"],
                cwd=repo_path, capture_output=True, text=True, timeout=10,
            )
            if result.stdout.strip():
                ts = result.stdout.strip()
                dt = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
                delta = datetime.now() - dt
                return delta.total_seconds() / 86400.0
        except Exception:
            pass
        return 9999.0

    # ---- PLAN ----

    def plan_cycle(self, staleness_list):
        """Select top N repos and decide what work to do on each."""
        self.active_phase = CyclePhase.PLAN
        work_items = []

        for repo_info in staleness_list[:self.max_repos_per_cycle]:
            run_optimus = self.agent_type in ("optimus", "both")
            run_gasket = self.agent_type in ("gasket", "both")

            reason_parts = []
            if not repo_info.has_architecture:
                reason_parts.append("needs architecture")
                run_optimus = True
            if not repo_info.has_docs:
                reason_parts.append("needs docs")
                run_gasket = True
            if not repo_info.has_tests:
                reason_parts.append("needs tests")
                run_gasket = True
            if repo_info.days_since_agent_commit > 7:
                reason_parts.append("stale (" + str(int(repo_info.days_since_agent_commit)) + "d)")

            reason = ", ".join(reason_parts) if reason_parts else "scheduled maintenance"

            work_items.append({
                "repo": repo_info.name, "tier": repo_info.tier,
                "score": repo_info.priority_score,
                "run_optimus": run_optimus, "run_gasket": run_gasket,
                "reason": reason,
            })

        return work_items

    # ---- EXECUTE ----

    def execute_work(self, work_items):
        """Execute planned work via PortfolioRunner -> AgentDispatcher."""
        self.active_phase = CyclePhase.EXECUTE
        result = CycleResult(
            cycle_number=self.cycle_count,
            started_at=datetime.now().isoformat(),
        )

        runner = self._get_runner()

        for item in work_items:
            repo_name = item["repo"]
            run_optimus = item["run_optimus"]
            run_gasket = item["run_gasket"]

            logger.info(
                "  [" + item["tier"] + "] " + repo_name + " - "
                + "OPTIMUS=" + ("ON" if run_optimus else "OFF") + " "
                + "GASKET=" + ("ON" if run_gasket else "OFF") + " "
                + "(" + item["reason"] + ")"
            )

            repo_config = None
            for rc in runner.repos:
                if rc.name == repo_name:
                    repo_config = rc
                    break

            if not repo_config:
                logger.warning("  Repo " + repo_name + " not in runner portfolio, skipping")
                result.errors.append(repo_name + ": not in portfolio")
                continue

            try:
                agent_results = runner.run_with_agents(
                    repo_config, run_optimus=run_optimus, run_gasket=run_gasket
                )

                result.repos_processed += 1

                for ar in agent_results:
                    result.tasks_dispatched += 1
                    if ar.success:
                        result.tasks_succeeded += 1
                        result.artifacts_created += len(ar.artifacts)
                        if ar.commit_sha:
                            result.commits_made += 1
                    else:
                        result.tasks_failed += 1
                        for err in ar.errors:
                            result.errors.append(repo_name + "/" + ar.agent.value + ": " + err)

            except Exception as e:
                logger.error("  Error on " + repo_name + ": " + str(e))
                result.errors.append(repo_name + ": " + str(e)[:200])

        return result

    # ---- VERIFY ----

    def verify_artifacts(self, result):
        """Check committed Python files for syntax errors."""
        self.active_phase = CyclePhase.VERIFY
        runner = self._get_runner()
        verified = 0

        for rc in runner.repos:
            repo_path = self.repos_dir / rc.name
            if not repo_path.exists() or not (repo_path / ".git").exists():
                continue

            try:
                git_result = subprocess.run(
                    ["git", "diff", "--name-only", "--diff-filter=AM",
                     "HEAD~3", "HEAD", "--", "*.py"],
                    cwd=repo_path, capture_output=True, text=True, timeout=10,
                )
                if git_result.returncode != 0:
                    continue

                for filename in git_result.stdout.strip().splitlines():
                    filepath = repo_path / filename
                    if filepath.exists():
                        try:
                            compile(filepath.read_text(), str(filepath), "exec")
                            verified += 1
                        except SyntaxError as e:
                            result.errors.append("SyntaxError in " + rc.name + "/" + filename + ": " + str(e))
            except Exception:
                pass

        logger.info("  Verified " + str(verified) + " Python files - syntax OK")
        return result

    # ---- REPORT ----

    def report_cycle(self, result):
        """Finalize and persist cycle result."""
        self.active_phase = CyclePhase.REPORT

        result.finished_at = datetime.now().isoformat()
        start = datetime.fromisoformat(result.started_at)
        finish = datetime.fromisoformat(result.finished_at)
        result.duration_seconds = (finish - start).total_seconds()

        logger.info("=" * 60)
        logger.info("CYCLE " + str(result.cycle_number) + " COMPLETE")
        logger.info("  Duration:   " + str(round(result.duration_seconds, 1)) + "s")
        logger.info("  Repos:      " + str(result.repos_processed))
        logger.info("  Tasks:      " + str(result.tasks_succeeded) + "/" + str(result.tasks_dispatched) + " succeeded")
        logger.info("  Artifacts:  " + str(result.artifacts_created))
        logger.info("  Commits:    " + str(result.commits_made))
        if result.errors:
            logger.info("  Errors:     " + str(len(result.errors)))
            for err in result.errors[:5]:
                logger.info("    - " + err)
        logger.info("=" * 60)

        self._save_cycle_result(result)
        self.last_cycle_result = result

    # ---- MAIN LOOP ----

    def run_one_cycle(self):
        """Execute a single complete flywheel cycle."""
        self.cycle_count += 1
        self._save_cycle_count()

        logger.info("")
        logger.info("=" * 60)
        logger.info("FLYWHEEL CYCLE " + str(self.cycle_count))
        logger.info("=" * 60)

        logger.info("")
        logger.info("[1/5] SCAN - discovering repos and staleness...")
        staleness = self.scan_repos()
        logger.info("  Found " + str(len(staleness)) + " local repos")
        for s in staleness[:5]:
            logger.info(
                "  [" + s.tier + "] " + s.name + ": score=" + str(s.priority_score)
                + " (stale " + str(int(s.days_since_agent_commit)) + "d, "
                + "docs=" + ("Y" if s.has_docs else "N") + " "
                + "tests=" + ("Y" if s.has_tests else "N") + " "
                + "arch=" + ("Y" if s.has_architecture else "N") + ")"
            )

        logger.info("")
        logger.info("[2/5] PLAN - selecting top " + str(self.max_repos_per_cycle) + " repos...")
        work_items = self.plan_cycle(staleness)
        for item in work_items:
            logger.info("  -> " + item["repo"] + " [" + item["tier"] + "] score=" + str(item["score"]) + " - " + item["reason"])

        if not work_items:
            logger.info("  No work to do this cycle (all repos within cooldown)")
            result = CycleResult(cycle_number=self.cycle_count, started_at=datetime.now().isoformat())
            self.report_cycle(result)
            return result

        logger.info("")
        logger.info("[3/5] EXECUTE - dispatching agents...")
        result = self.execute_work(work_items)

        logger.info("")
        logger.info("[4/5] VERIFY - checking artifact quality...")
        result = self.verify_artifacts(result)

        logger.info("")
        logger.info("[5/5] REPORT - logging results...")
        self.report_cycle(result)

        self.active_phase = CyclePhase.IDLE
        return result

    def start(self):
        """Start continuous flywheel loop (blocking)."""
        self.is_running = True
        logger.info("FLYWHEEL STARTED - interval=" + str(self.cycle_interval) + "s")

        while self.is_running:
            try:
                self.run_one_cycle()
                if not self.is_running:
                    break
                logger.info("")
                logger.info("Next cycle in " + str(self.cycle_interval) + "s (" + str(round(self.cycle_interval / 60, 1)) + " min)...")
                logger.info("")
                for _ in range(self.cycle_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("FLYWHEEL STOPPED (keyboard interrupt)")
                self.is_running = False
            except Exception as e:
                logger.error("CYCLE ERROR: " + str(e))
                error_wait = min(self.cycle_interval * 2, 600)
                logger.info("Waiting " + str(error_wait) + "s after error...")
                for _ in range(error_wait):
                    if not self.is_running:
                        break
                    time.sleep(1)

        self.active_phase = CyclePhase.IDLE
        logger.info("FLYWHEEL STOPPED")

    def stop(self):
        self.is_running = False
        logger.info("FLYWHEEL STOP REQUESTED")

    def get_status(self):
        """Current flywheel status for dashboards."""
        status = {
            "is_running": self.is_running,
            "active_phase": self.active_phase.value,
            "cycle_count": self.cycle_count,
            "cycle_interval_seconds": self.cycle_interval,
            "max_repos_per_cycle": self.max_repos_per_cycle,
            "cooldown_hours": self.cooldown_hours,
            "agent_type": self.agent_type,
        }

        if self.last_cycle_result:
            status["last_cycle"] = self.last_cycle_result.to_dict()

        log_file = self.state_dir / "cycle_log.jsonl"
        if log_file.exists():
            try:
                lines = log_file.read_text().strip().splitlines()
                recent = [json.loads(l) for l in lines[-5:]]
                status["recent_cycles"] = recent
                status["total_tasks_succeeded"] = sum(c.get("tasks_succeeded", 0) for c in recent)
                status["total_artifacts"] = sum(c.get("artifacts_created", 0) for c in recent)
                status["total_commits"] = sum(c.get("commits_made", 0) for c in recent)
            except Exception:
                pass

        return status


def main():
    import argparse
    parser = argparse.ArgumentParser(description="REPO DEPOT Flywheel Controller")
    parser.add_argument("--workspace", type=str, default=".")
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--max-repos", type=int, default=3)
    parser.add_argument("--cooldown", type=float, default=24.0)
    parser.add_argument("--agent", type=str, choices=["optimus", "gasket", "both"], default="both")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--scan", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not (workspace / "portfolio.json").exists():
        alt = Path("$HOME/repos/DIGITAL-LABOUR")
        if (alt / "portfolio.json").exists():
            workspace = alt

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [FLYWHEEL] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    config = {
        "cycle_interval_seconds": args.interval,
        "max_repos_per_cycle": args.max_repos,
        "cooldown_hours": args.cooldown,
        "agent_type": args.agent,
    }

    controller = FlywheelController(workspace, config)

    if args.status:
        print(json.dumps(controller.get_status(), indent=2))
        return

    if args.scan:
        staleness = controller.scan_repos()
        hdr = "Repo".ljust(35) + "Tier".ljust(5) + "Score".ljust(8) + "Stale(d)".ljust(10) + "Docs".ljust(5) + "Tests".ljust(6) + "Arch".ljust(5)
        print("")
        print(hdr)
        print("-" * 80)
        for s in staleness:
            d = "Y" if s.has_docs else "N"
            t = "Y" if s.has_tests else "N"
            a = "Y" if s.has_architecture else "N"
            print(s.name.ljust(35) + s.tier.ljust(5) + str(s.priority_score).ljust(8) + str(s.days_since_agent_commit).ljust(10) + d.ljust(5) + t.ljust(6) + a.ljust(5))
        return

    if args.once:
        controller.run_one_cycle()
    else:
        controller.start()


if __name__ == "__main__":
    main()
