"""Credential TTL enforcement — Phase 6 Security.

Checks .env file age against config/credentials_ttl.json thresholds.
Logs STALE_CREDENTIAL warnings on startup — does NOT auto-fail.

Usage:
    from utils.credential_ttl import check_credential_ttl
    check_credential_ttl()  # logs warnings for stale keys
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("utils.credential_ttl")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TTL_CONFIG = PROJECT_ROOT / "config" / "credentials_ttl.json"
_ENV_PATH = PROJECT_ROOT / ".env"


def _load_ttl_config() -> dict:
    if _TTL_CONFIG.exists():
        try:
            return json.loads(_TTL_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"ttl_days": {"default": 90}}


def check_credential_ttl() -> list[dict]:
    """Check all configured credential TTLs against .env file modification time.

    Returns list of stale credential warnings (also logs each as STALE_CREDENTIAL).
    """
    ttl_config = _load_ttl_config()
    ttl_days = ttl_config.get("ttl_days", {})
    default_ttl = ttl_days.get("default", 90)

    if not _ENV_PATH.exists():
        logger.info("[CREDENTIAL_TTL] No .env file found — skipping TTL check")
        return []

    # Use .env file modification time as proxy for last key rotation
    env_mtime = datetime.fromtimestamp(_ENV_PATH.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    age_days = (now - env_mtime).days

    stale: list[dict] = []

    for key_var, ttl in ttl_days.items():
        if key_var == "default":
            continue
        # Check if the key is actually set in environment
        val = os.environ.get(key_var, "")
        if not val:
            continue

        if age_days > ttl:
            warning = {
                "key": key_var,
                "age_days": age_days,
                "ttl_days": ttl,
                "status": "STALE",
            }
            logger.warning(
                "[STALE_CREDENTIAL] %s is %d days old (TTL: %d days) — rotate recommended",
                key_var, age_days, ttl,
            )
            stale.append(warning)

    # Check any other env vars that look like keys but aren't in config
    for key_var in os.environ:
        if key_var.endswith("_API_KEY") and key_var not in ttl_days:
            if age_days > default_ttl:
                warning = {
                    "key": key_var,
                    "age_days": age_days,
                    "ttl_days": default_ttl,
                    "status": "STALE",
                }
                logger.warning(
                    "[STALE_CREDENTIAL] %s is %d days old (default TTL: %d days)",
                    key_var, age_days, default_ttl,
                )
                stale.append(warning)

    if not stale:
        logger.info("[CREDENTIAL_TTL] All credentials within TTL (%d days since last .env update)", age_days)

    return stale
