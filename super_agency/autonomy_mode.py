#!/usr/bin/env python3
"""
Autonomy Mode Framework — L0 observe-only enforcement + graduation logic.

Autonomy Levels:
  L0 — Observe only (read, scan, report — no mutations)
  L1 — Propose changes (create fix proposals, issue drafts — human approves)
  L2 — Act with limits (auto-fix low-risk items, issue PRs — receipts required)
  L3 — Full autonomy (council-approved, reserved for highest-trust repos)
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
PORT = ROOT / "portfolio.json"
GRAD_CONFIG = ROOT / "config" / "graduation_criteria.json"
GRAD_LOG = ROOT / "logs" / "graduation.ndjson"
GRAD_LOG.parent.mkdir(parents=True, exist_ok=True)

# Default graduation criteria (overridden by config file)
DEFAULT_CRITERIA = {
    "L0_to_L1": {"min_clean_scans": 3, "min_days_observed": 7, "max_incidents": 0},
    "L1_to_L2": {"min_clean_scans": 10, "min_days_at_L1": 14, "max_incidents": 0,
                 "min_heal_success_rate": 0.9},
    "L2_to_L3": {"requires_council_vote": True, "min_clean_scans": 30,
                 "min_days_at_L2": 30, "max_incidents": 0},
}


def load_criteria():
    if GRAD_CONFIG.exists():
        return json.loads(GRAD_CONFIG.read_text(encoding="utf-8"))
    return DEFAULT_CRITERIA


def save_default_criteria():
    """Write default criteria to config file if it doesn't exist."""
    GRAD_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if not GRAD_CONFIG.exists():
        GRAD_CONFIG.write_text(json.dumps(
            DEFAULT_CRITERIA, indent=2), encoding="utf-8")
        print(f"[OK] Default graduation criteria written to {GRAD_CONFIG}")


def is_action_allowed(repo_name: str, action_type: str = "mutate") -> bool:
    """Check whether an action is allowed under the repo's current autonomy level.

    action_type: 'read', 'propose', 'mutate', 'full'
    """
    portfolio = json.loads(PORT.read_text(encoding="utf-8")
                           ) if PORT.exists() else {"repositories": []}
    repo = next((r for r in portfolio.get("repositories", [])
                if r["name"] == repo_name), None)
    if repo is None:
        return False

    level = repo.get("autonomy_level", "L1")
    allowed = {
        "L0": {"read"},
        "L1": {"read", "propose"},
        "L2": {"read", "propose", "mutate"},
        "L3": {"read", "propose", "mutate", "full"},
    }
    return action_type in allowed.get(level, set())


def check_graduation_eligibility(repo_name: str, scan_stats: dict) -> dict:
    """Check if a repo is eligible for graduation to the next autonomy level.

    scan_stats should contain:
      clean_scans: int, incidents: int, days_at_current: int,
      heal_success_rate: float (0-1)

    Returns: {"eligible": bool, "current": str, "target": str, "reason": str}
    """
    portfolio = json.loads(PORT.read_text(encoding="utf-8")
                           ) if PORT.exists() else {"repositories": []}
    repo = next((r for r in portfolio.get("repositories", [])
                if r["name"] == repo_name), None)
    if repo is None:
        return {"eligible": False, "current": "?", "target": "?", "reason": "repo not found"}

    current = repo.get("autonomy_level", "L1")
    criteria = load_criteria()

    transition_map = {"L0": "L1", "L1": "L2", "L2": "L3"}
    target = transition_map.get(current)
    if target is None:
        return {"eligible": False, "current": current, "target": current, "reason": "already at max level"}

    key = f"{current}_to_{target}"
    reqs = criteria.get(key, {})

    # Check each criterion
    if scan_stats.get("clean_scans", 0) < reqs.get("min_clean_scans", 999):
        return {"eligible": False, "current": current, "target": target,
                "reason": f"need {reqs['min_clean_scans']} clean scans, have {scan_stats.get('clean_scans', 0)}"}

    if scan_stats.get("incidents", 0) > reqs.get("max_incidents", 0):
        return {"eligible": False, "current": current, "target": target,
                "reason": f"too many incidents ({scan_stats['incidents']})"}

    days_key = f"min_days_at_{current}" if f"min_days_at_{current}" in reqs else "min_days_observed"
    if scan_stats.get("days_at_current", 0) < reqs.get(days_key, 0):
        return {"eligible": False, "current": current, "target": target,
                "reason": f"need {reqs[days_key]} days at {current}, have {scan_stats.get('days_at_current', 0)}"}

    if "min_heal_success_rate" in reqs:
        if scan_stats.get(
            "heal_success_rate", 0) <reqs["min_heal_success_rate"]:
            return {"eligible": False, "current": current, "target": target,
                    "reason": f"heal success rate too low ({scan_stats.get('heal_success_rate', 0):.0%})"}

    if reqs.get("requires_council_vote"):
        return {"eligible": True, "current": current, "target": target,
                "reason": "eligible — requires council vote for final approval"}

    return {"eligible": True, "current": current, "target": target, "reason": "all criteria met"}


def graduate_repo(repo_name: str, target_level: str) -> bool:
    """Promote a repo to a new autonomy level and log the graduation."""
    portfolio = json.loads(PORT.read_text(encoding="utf-8")
                           ) if PORT.exists() else {"repositories": []}
    repo = next((r for r in portfolio.get("repositories", [])
                if r["name"] == repo_name), None)
    if repo is None:
        return False

    prev = repo.get("autonomy_level", "L1")
    repo["autonomy_level"] = target_level

    PORT.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")

    entry = {"ts": datetime.now().isoformat(timespec="seconds"),
             "repo": repo_name, "from": prev, "to": target_level}
    with open(GRAD_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[GRADUATED] {repo_name}: {prev} -> {target_level}")
    return True


if __name__ == "__main__":
    save_default_criteria()
    print("Graduation criteria config created/verified.")
