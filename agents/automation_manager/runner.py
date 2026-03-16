"""Automation Manager Agent -- Supervisory agent for autobidder,
platform integrations, NERVE daemon, and automated workflows.

Usage:
    python runner.py --action status --platform all
    python runner.py --action configure --platform freelancer --config '{"max_daily_bids": 20}'
    python runner.py --action report --metrics-window 7d
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env")

from utils.dl_agent import make_bridge
llm_call = make_bridge("automation_manager", self_reflect=False)


# -- Data paths ---------------------------------------------------------------

DATA_DIR = PROJECT_ROOT / "data" / "automation_manager"
CONFIG_DIR = DATA_DIR / "platform_configs"
LOG_DIR = DATA_DIR / "logs"
STATE_FILE = DATA_DIR / "automation_state.json"
NERVE_STATE = PROJECT_ROOT / "data" / "nerve_state.json"
NERVE_LOGS = PROJECT_ROOT / "data" / "nerve_logs"

for d in [DATA_DIR, CONFIG_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# -- Constants ----------------------------------------------------------------

PLATFORMS = [
    "freelancer", "fiverr", "upwork",
    "peopleperhour", "guru", "toptal",
]

DEFAULT_PLATFORM_CONFIG = {
    "active": False,
    "max_daily_bids": 20,
    "max_single_bid_usd": 200,
    "min_profit_margin_pct": 40,
    "polling_interval_minutes": 15,
    "pause_on_consecutive_failures": 5,
    "api_key_configured": False,
    "last_poll": None,
    "total_bids_today": 0,
    "total_wins_today": 0,
    "daily_spend_usd": 0.0,
}

MAX_DAILY_SPEND = 50.0  # USD across all platforms
HUMAN_REVIEW_THRESHOLD = 500.0  # USD -- projects above this need human OK


# -- Models -------------------------------------------------------------------

class PlatformStatus(BaseModel):
    platform: str
    active: bool = False
    bids_today: int = 0
    wins_today: int = 0
    daily_spend: float = 0.0
    health: str = "OK"
    last_poll: str | None = None
    consecutive_failures: int = 0
    api_configured: bool = False


class AutobidderStatus(BaseModel):
    active: bool = True
    total_bids_today: int = 0
    total_spend_today: float = 0.0
    win_rate_7d: float = 0.0
    top_performing_agents: list[str] = []
    paused_categories: list[str] = []


class NERVEStatus(BaseModel):
    last_cycle: str = ""
    cycles_today: int = 0
    health: str = "OK"
    stuck: bool = False
    last_error: str = ""


class AutomationOutput(BaseModel):
    platform_status: dict[str, PlatformStatus] = {}
    autobidder: AutobidderStatus = AutobidderStatus()
    nerve: NERVEStatus = NERVEStatus()
    automations: list[dict] = []
    recommendations: list[str] = []
    alerts: list[str] = []


class AutomationState(BaseModel):
    platforms: dict = {}
    autobidder_history: list[dict] = []
    last_updated: str = ""
    daily_spend_total: float = 0.0


# -- Prompt Loading -----------------------------------------------------------

AGENT_DIR = Path(__file__).parent


def load_prompt() -> str:
    path = AGENT_DIR / "system_prompt.md"
    return path.read_text(encoding="utf-8")


# -- State Persistence --------------------------------------------------------

def load_state() -> AutomationState:
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return AutomationState.model_validate(data)

    # Initialize default state
    state = AutomationState()
    for p in PLATFORMS:
        state.platforms[p] = dict(DEFAULT_PLATFORM_CONFIG)
    return state


def save_state(state: AutomationState) -> None:
    state.last_updated = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def load_platform_config(platform: str) -> dict:
    path = CONFIG_DIR / f"{platform}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return dict(DEFAULT_PLATFORM_CONFIG)


def save_platform_config(platform: str, config: dict) -> None:
    path = CONFIG_DIR / f"{platform}.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


# -- Core Functions -----------------------------------------------------------

def get_platform_status(platform: str) -> PlatformStatus:
    """Get status of a single platform."""
    config = load_platform_config(platform)
    return PlatformStatus(
        platform=platform,
        active=config.get("active", False),
        bids_today=config.get("total_bids_today", 0),
        wins_today=config.get("total_wins_today", 0),
        daily_spend=config.get("daily_spend_usd", 0.0),
        health="OK" if config.get("active") else "INACTIVE",
        last_poll=config.get("last_poll"),
        consecutive_failures=config.get("consecutive_failures", 0),
        api_configured=config.get("api_key_configured", False),
    )


def get_all_status() -> AutomationOutput:
    """Get status of all platforms and automations."""
    state = load_state()
    platform_status = {}

    total_bids = 0
    total_spend = 0.0

    for p in PLATFORMS:
        ps = get_platform_status(p)
        platform_status[p] = ps
        total_bids += ps.bids_today
        total_spend += ps.daily_spend

    # NERVE status
    nerve = _check_nerve_health()

    # Autobidder aggregate
    autobidder = AutobidderStatus(
        active=any(ps.active for ps in platform_status.values()),
        total_bids_today=total_bids,
        total_spend_today=total_spend,
    )

    # Alerts
    alerts = []
    if total_spend >= MAX_DAILY_SPEND * 0.8:
        alerts.append(
            f"WARN: Daily spend at ${total_spend:.2f} / "
            f"${MAX_DAILY_SPEND:.2f} limit"
        )
    if nerve.stuck:
        alerts.append("CRITICAL: NERVE daemon appears stuck")

    for p, ps in platform_status.items():
        if ps.consecutive_failures >= 3:
            alerts.append(
                f"WARN: {p} has {ps.consecutive_failures} "
                f"consecutive failures"
            )

    # Recommendations
    recommendations = []
    inactive = [p for p, ps in platform_status.items() if not ps.active]
    if inactive:
        recommendations.append(
            f"Platforms not yet active: {inactive}. "
            f"Configure API keys to enable."
        )

    return AutomationOutput(
        platform_status=platform_status,
        autobidder=autobidder,
        nerve=nerve,
        alerts=alerts,
        recommendations=recommendations,
    )


def configure_platform(platform: str, config_updates: dict) -> dict:
    """Update configuration for a platform."""
    if platform not in PLATFORMS:
        return {"error": f"Unknown platform: {platform}"}

    config = load_platform_config(platform)
    # Only allow safe config keys
    safe_keys = {
        "active", "max_daily_bids", "max_single_bid_usd",
        "min_profit_margin_pct", "polling_interval_minutes",
        "pause_on_consecutive_failures",
    }
    applied = {}
    for key, value in config_updates.items():
        if key in safe_keys:
            config[key] = value
            applied[key] = value

    save_platform_config(platform, config)
    _log_action("configure", platform, applied)

    return {
        "platform": platform,
        "applied": applied,
        "current_config": config,
    }


def pause_platform(platform: str, reason: str = "") -> dict:
    """Pause a platform's automation."""
    config = load_platform_config(platform)
    config["active"] = False
    save_platform_config(platform, config)
    _log_action("pause", platform, {"reason": reason})
    return {"platform": platform, "status": "paused", "reason": reason}


def resume_platform(platform: str) -> dict:
    """Resume a platform's automation."""
    config = load_platform_config(platform)
    config["active"] = True
    config["consecutive_failures"] = 0
    save_platform_config(platform, config)
    _log_action("resume", platform, {})
    return {"platform": platform, "status": "active"}


def record_bid(platform: str, agent_type: str, bid_usd: float,
               won: bool = False) -> dict:
    """Record a bid for tracking."""
    state = load_state()
    config = load_platform_config(platform)

    config["total_bids_today"] = config.get("total_bids_today", 0) + 1
    config["daily_spend_usd"] = config.get("daily_spend_usd", 0.0) + bid_usd
    if won:
        config["total_wins_today"] = config.get("total_wins_today", 0) + 1
    config["last_poll"] = datetime.now(timezone.utc).isoformat()
    config["consecutive_failures"] = 0

    save_platform_config(platform, config)

    bid_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "platform": platform,
        "agent_type": agent_type,
        "bid_usd": bid_usd,
        "won": won,
    }
    state.autobidder_history.append(bid_entry)
    state.daily_spend_total += bid_usd
    save_state(state)

    _log_action("bid", platform, bid_entry)

    # Check spend cap
    alerts = []
    if state.daily_spend_total >= MAX_DAILY_SPEND:
        alerts.append("DAILY SPEND CAP REACHED -- pausing all autobidding")

    return {"recorded": bid_entry, "alerts": alerts}


def record_failure(platform: str, error: str) -> dict:
    """Record an API failure for a platform."""
    config = load_platform_config(platform)
    config["consecutive_failures"] = (
        config.get("consecutive_failures", 0) + 1
    )
    threshold = config.get("pause_on_consecutive_failures", 5)
    auto_paused = False

    if config["consecutive_failures"] >= threshold:
        config["active"] = False
        auto_paused = True

    save_platform_config(platform, config)
    _log_action("failure", platform, {
        "error": error,
        "consecutive": config["consecutive_failures"],
        "auto_paused": auto_paused,
    })

    return {
        "platform": platform,
        "consecutive_failures": config["consecutive_failures"],
        "auto_paused": auto_paused,
    }


def _check_nerve_health() -> NERVEStatus:
    """Check NERVE daemon health."""
    status = NERVEStatus()

    if NERVE_STATE.exists():
        try:
            data = json.loads(NERVE_STATE.read_text(encoding="utf-8"))
            status.last_cycle = data.get("last_cycle", "")
            status.cycles_today = data.get("cycles_today", 0)

            if status.last_cycle:
                last = datetime.fromisoformat(status.last_cycle)
                now = datetime.now(timezone.utc)
                minutes_since = (now - last).total_seconds() / 60
                if minutes_since > 120:
                    status.stuck = True
                    status.health = "STUCK"
        except (json.JSONDecodeError, ValueError):
            status.health = "ERROR"
            status.last_error = "Could not parse nerve_state.json"
    else:
        status.health = "NOT_RUNNING"

    return status


def generate_report(metrics_window: str = "7d",
                    provider: str | None = None) -> dict:
    """Generate automation report."""
    output = get_all_status()
    state = load_state()

    # Count bids by platform in history
    platform_bids: dict[str, int] = {}
    platform_wins: dict[str, int] = {}
    for entry in state.autobidder_history[-200:]:
        p = entry.get("platform", "unknown")
        platform_bids[p] = platform_bids.get(p, 0) + 1
        if entry.get("won"):
            platform_wins[p] = platform_wins.get(p, 0) + 1

    win_rates = {}
    for p in PLATFORMS:
        bids = platform_bids.get(p, 0)
        wins = platform_wins.get(p, 0)
        win_rates[p] = round(wins / bids, 3) if bids else 0.0

    return {
        "report_date": datetime.now(timezone.utc).isoformat(),
        "metrics_window": metrics_window,
        "platform_summary": {
            p: ps.model_dump()
            for p, ps in output.platform_status.items()
        },
        "autobidder": output.autobidder.model_dump(),
        "nerve": output.nerve.model_dump(),
        "win_rates": win_rates,
        "daily_spend_total": state.daily_spend_total,
        "max_daily_spend": MAX_DAILY_SPEND,
        "alerts": output.alerts,
        "recommendations": output.recommendations,
    }


# -- Logging ------------------------------------------------------------------

def _log_action(action: str, platform: str, data: dict) -> None:
    log_file = LOG_DIR / (
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    )
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "platform": platform,
        "data": data,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# -- Pipeline (for dispatcher integration) ------------------------------------

def run_pipeline(
    action: str = "status",
    platform: str = "all",
    config: dict | None = None,
    metrics_window: str = "7d",
    provider: str | None = None,
    **kwargs,
) -> AutomationOutput | dict:
    """Main entry point for dispatcher routing."""
    if action == "status":
        return get_all_status()
    elif action == "configure":
        return configure_platform(platform, config or {})
    elif action == "pause":
        reason = (config or {}).get("reason", "Manual pause")
        return pause_platform(platform, reason)
    elif action == "resume":
        return resume_platform(platform)
    elif action == "report":
        return generate_report(metrics_window, provider)
    else:
        return AutomationOutput(
            alerts=[f"Unknown action: {action}"],
        )


# -- CLI -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Automation Manager -- Supervisory Agent"
    )
    parser.add_argument(
        "--action", required=True,
        choices=["status", "configure", "pause", "resume", "report"],
    )
    parser.add_argument(
        "--platform", default="all",
        choices=PLATFORMS + ["all"],
    )
    parser.add_argument("--config", default="{}", help="JSON config updates")
    parser.add_argument(
        "--metrics-window", default="7d",
        choices=["24h", "7d", "30d"],
    )
    parser.add_argument(
        "--provider", default=None,
        choices=["openai", "anthropic", "gemini", "grok"],
    )
    args = parser.parse_args()

    config = json.loads(args.config)
    result = run_pipeline(
        action=args.action,
        platform=args.platform,
        config=config,
        metrics_window=args.metrics_window,
        provider=args.provider,
    )

    if isinstance(result, dict):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
