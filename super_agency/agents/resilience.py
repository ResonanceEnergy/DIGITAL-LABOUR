#!/usr/bin/env python3
"""
Resilience utilities — retry with exponential backoff and circuit breaker.

Usage:
    from agents.resilience import retry, CircuitBreaker, circuit_breakers

    @retry(max_attempts=3, base_delay=1.0)
    def flaky_call():
        ...

    cb = CircuitBreaker("my_service", threshold=3)
    if cb.allow():
        try:
            do_work()
            cb.record_success()
        except Exception:
            cb.record_failure()
"""

import functools
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
_ALERT_LOG = ROOT / "logs" / "alerts.ndjson"
_ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)


# ── Retry decorator ─────────────────────────────────────────────────────

def retry(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0,
          backoff_factor: float = 2.0, exceptions: tuple = (Exception,)):
    """Retry with exponential backoff.

    Parameters
    ----------
    max_attempts : int
        Total attempts (including the first).
    base_delay : float
        Initial delay in seconds before the first retry.
    max_delay : float
        Cap on delay between retries.
    backoff_factor : float
        Multiplier applied to delay after each failure.
    exceptions : tuple
        Exception types that trigger a retry.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.error(
                            f"[RETRY] {fn.__name__} failed after {max_attempts} attempts: {exc}")
                        raise
                    logger.warning(
                        f"[RETRY] {fn.__name__} attempt {attempt}/{max_attempts} failed: {exc} — retrying in {delay:.1f}s")
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            raise last_exc  # unreachable but satisfies type checkers
        return wrapper
    return decorator


# ── Circuit Breaker ──────────────────────────────────────────────────────

class CircuitBreaker:
    """Per-service circuit breaker.

    States:
        CLOSED  — requests flow normally.
        OPEN    — requests blocked (service considered down).
        HALF    — one probe request allowed to test recovery.

    Transition rules:
        CLOSED → OPEN    when ``threshold`` consecutive failures reached.
        OPEN   → HALF    after ``recovery_timeout`` seconds.
        HALF   → CLOSED  on success.
        HALF   → OPEN    on failure (resets timeout).
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF = "HALF_OPEN"

    def __init__(
            self, name: str, threshold: int=3, recovery_timeout: float=300.0):
        self.name = name
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout

        self._lock = threading.Lock()
        self._state = self.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: Optional[float] = None
        self._total_failures = 0
        self._total_successes = 0

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN and self._last_failure_time:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = self.HALF
            return self._state

    def allow(self) -> bool:
        """Return True if the request should proceed."""
        s = self.state
        return s in (self.CLOSED, self.HALF)

    def record_success(self):
        with self._lock:
            self._consecutive_failures = 0
            self._total_successes += 1
            if self._state == self.HALF:
                logger.info(
                    f"[CB] {self.name}: HALF_OPEN → CLOSED (recovered)")
                self._state = self.CLOSED

    def record_failure(self):
        with self._lock:
            self._consecutive_failures += 1
            self._total_failures += 1
            self._last_failure_time = time.time()
            if self._state == self.HALF:
                logger.warning(
                    f"[CB] {self.name}: HALF_OPEN → OPEN (probe failed)")
                self._state = self.OPEN
            elif self._consecutive_failures >= self.threshold:
                if self._state != self.OPEN:
                    logger.error(
                        f"[CB] {self.name}: CLOSED → OPEN after {self._consecutive_failures} consecutive failures")
                    self._state = self.OPEN
                    _emit_alert("circuit_breaker_open", f"Circuit breaker opened for {self.name}",
                                severity="HIGH", component=self.name)

    def stats(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "state": self._state,
                "consecutive_failures": self._consecutive_failures,
                "total_failures": self._total_failures,
                "total_successes": self._total_successes,
                "threshold": self.threshold,
                "recovery_timeout": self.recovery_timeout,
            }


# ── Global circuit breaker registry ─────────────────────────────────────

_breakers_lock = threading.Lock()
_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str, threshold: int = 3, recovery_timeout: float = 300.0) -> CircuitBreaker:
    """Get or create a named circuit breaker."""
    with _breakers_lock:
        if name not in _breakers:
            _breakers[name] = CircuitBreaker(name, threshold, recovery_timeout)
        return _breakers[name]


def all_breaker_stats() -> list[dict]:
    """Return stats for every registered breaker."""
    with _breakers_lock:
        return [cb.stats() for cb in _breakers.values()]


# ── Alert helper ────────────────────────────────────────────────────────

def _emit_alert(
        alert_type: str, message: str, severity: str="MEDIUM", **extra):
    """Write a structured alert to the NDJSON alert log."""
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "type": alert_type,
        "severity": severity,
        "message": message,
        **extra,
    }
    try:
        with open(_ALERT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    logger.warning(f"[ALERT] [{severity}] {message}")
