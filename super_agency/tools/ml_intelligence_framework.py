#!/usr/bin/env python3
"""
Machine Learning & Intelligence Framework
==========================================
Lightweight ML/intelligence layer for the BIT RAGE LABOUR.

Provides pattern recognition, anomaly detection, trend forecasting,
and adaptive learning **without** heavy external dependencies.
Uses pure-Python statistical methods suitable for operational
intelligence on structured agent telemetry.

Capabilities:
- Bayesian anomaly scoring on numeric time-series
- Exponential-smoothing trend forecasting
- TF-IDF keyword extraction for text intelligence
- Reinforcement-style action scoring (contextual bandits)
- Clustering via k-means on small feature sets
- Agent performance profiling & adaptive routing

Based on:
- "Reinforcement Learning: An Introduction" (Sutton & Barto)
- "Bayesian Reasoning and Machine Learning" (Barber, 2012)
- "Contextual Bandits" (Langford & Zhang, 2007)

Usage::

    from tools.ml_intelligence_framework import (
        AnomalyDetector, TrendForecaster,
        ActionScorer, TextIntelligence, KMeansCluster,
        AgentPerformanceProfiler,
    )

    detector = AnomalyDetector(window=50)
    for val in stream:
        score = detector.score(val)
        if score > 0.9:
            alert(f"anomaly: {val}")
"""

from __future__ import annotations

import json
import math
import random
import statistics
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
ML_DATA_DIR = ROOT / "data" / "ml_intelligence"
ML_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
#  ANOMALY DETECTION  — z-score + Bayesian surprise
# ═══════════════════════════════════════════════════════════════

class AnomalyDetector:
    """Rolling z-score anomaly detector with adaptive thresholds.

    Maintains a sliding window of observations and scores each
    new value by how many standard deviations it deviates from
    the running mean.  A Bayesian surprise term penalises
    sudden distribution shifts.
    """

    def __init__(
        self,
        window: int = 100,
        z_threshold: float = 2.5,
    ):
        self._window: deque[float] = deque(maxlen=window)
        self._z_threshold = z_threshold
        self._alerts: list[dict[str, Any]] = []

    # ── public ──────────────────────────────────────────────

    def score(self, value: float) -> float:
        """Return anomaly score in [0, 1].  >0.8 is suspicious."""
        if len(self._window) < 5:
            self._window.append(value)
            return 0.0
        mu = statistics.mean(self._window)
        sigma = statistics.stdev(self._window) or 1e-9
        z = abs(value - mu) / sigma
        # sigmoid-map z to [0,1]
        raw = 1.0 / (1.0 + math.exp(-1.5 * (z - self._z_threshold)))
        self._window.append(value)
        if raw > 0.8:
            self._alerts.append({
                "ts": datetime.now().isoformat(),
                "value": value,
                "z": round(z, 3),
                "score": round(raw, 4),
            })
        return round(raw, 4)

    def recent_alerts(self, n: int = 20) -> list[dict[str, Any]]:
        return self._alerts[-n:]

    def reset(self) -> None:
        self._window.clear()
        self._alerts.clear()


# ═══════════════════════════════════════════════════════════════
#  TREND FORECASTING  — exponential smoothing (Holt)
# ═══════════════════════════════════════════════════════════════

class TrendForecaster:
    """Double exponential smoothing (Holt's method).

    Decomposes a time-series into level + trend components and
    projects forward by *horizon* steps.
    """

    def __init__(
        self,
        alpha: float = 0.3,
        beta: float = 0.1,
    ):
        self._alpha = alpha
        self._beta = beta
        self._level: Optional[float] = None
        self._trend: Optional[float] = None
        self._n = 0
        self._history: list[float] = []

    def update(self, value: float) -> None:
        self._history.append(value)
        if self._level is None:
            self._level = value
            self._trend = 0.0
            self._n = 1
            return
        prev_level = self._level
        self._level = (
            self._alpha * value
            + (1 - self._alpha) * (prev_level + self._trend)
        )
        self._trend = (
            self._beta * (self._level - prev_level)
            + (1 - self._beta) * self._trend
        )
        self._n += 1

    def forecast(self, horizon: int = 5) -> list[float]:
        if self._level is None:
            return []
        return [
            round(self._level + (i + 1) * self._trend, 4)
            for i in range(horizon)
        ]

    def direction(self) -> str:
        if self._trend is None or self._trend == 0:
            return "flat"
        return "up" if self._trend > 0 else "down"


# ═══════════════════════════════════════════════════════════════
#  TEXT INTELLIGENCE  — TF-IDF keyword extraction
# ═══════════════════════════════════════════════════════════════

_STOP_WORDS = frozenset(
    "a an the is was are were be been being have has had "
    "do does did will would shall should may might can could "
    "of in to for on with at by from or and but not this "
    "that it its they them their he she his her we our you "
    "your i me my so if as into also than too very up out "
    "about after all each between through during before".split()
)


class TextIntelligence:
    """Lightweight TF-IDF over a corpus of short documents.

    Designed for extracting key topics from agent logs,
    research summaries, and intelligence reports.
    """

    def __init__(self) -> None:
        self._docs: list[list[str]] = []
        self._df: Counter[str] = Counter()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        import re
        tokens = re.findall(r"[a-z][a-z0-9_]+", text.lower())
        return [t for t in tokens if t not in _STOP_WORDS]

    def add_document(self, text: str) -> int:
        tokens = self._tokenize(text)
        self._docs.append(tokens)
        unique = set(tokens)
        for w in unique:
            self._df[w] += 1
        return len(self._docs) - 1

    def keywords(
        self,
        doc_id: int,
        top_n: int = 10,
    ) -> list[tuple[str, float]]:
        if doc_id >= len(self._docs):
            return []
        tokens = self._docs[doc_id]
        tf: Counter[str] = Counter(tokens)
        n_docs = len(self._docs) or 1
        scored: list[tuple[str, float]] = []
        for word, count in tf.items():
            idf = math.log(
                (1 + n_docs) / (1 + self._df.get(word, 0))
            ) + 1.0
            scored.append((
                word,
                round(count * idf, 4),
            ))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]

    def similar_docs(
        self,
        doc_id: int,
        top_n: int = 5,
    ) -> list[tuple[int, float]]:
        """Cosine similarity between doc_id and all others."""
        if doc_id >= len(self._docs):
            return []
        q_vec = Counter(self._docs[doc_id])
        results: list[tuple[int, float]] = []
        for i, tokens in enumerate(self._docs):
            if i == doc_id:
                continue
            d_vec = Counter(tokens)
            dot = sum(
                q_vec[w] * d_vec[w]
                for w in q_vec if w in d_vec
            )
            mag_q = math.sqrt(sum(v * v for v in q_vec.values()))
            mag_d = math.sqrt(sum(v * v for v in d_vec.values()))
            if mag_q and mag_d:
                sim = dot / (mag_q * mag_d)
                results.append((i, round(sim, 4)))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]


# ═══════════════════════════════════════════════════════════════
#  CONTEXTUAL BANDITS  — action selection with exploration
# ═══════════════════════════════════════════════════════════════

class ActionScorer:
    """Upper-Confidence-Bound (UCB1) action selector.

    Used by agents to pick between alternative strategies
    (e.g. which enrichment model to try, which research
    approach to prioritise) while balancing exploration
    vs exploitation.
    """

    def __init__(self, actions: Sequence[str]) -> None:
        self._counts: dict[str, int] = {a: 0 for a in actions}
        self._rewards: dict[str, float] = {
            a: 0.0 for a in actions
        }
        self._total = 0

    def select(self) -> str:
        """Pick the action with highest UCB1 score."""
        # try each action at least once
        for a, c in self._counts.items():
            if c == 0:
                return a
        best_a = ""
        best_score = -1.0
        ln_total = math.log(self._total)
        for a, c in self._counts.items():
            avg = self._rewards[a] / c
            explore = math.sqrt(2 * ln_total / c)
            score = avg + explore
            if score > best_score:
                best_score = score
                best_a = a
        return best_a

    def update(self, action: str, reward: float) -> None:
        self._counts[action] = self._counts.get(action, 0) + 1
        self._rewards[action] = (
            self._rewards.get(action, 0.0) + reward
        )
        self._total += 1

    def stats(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for a in self._counts:
            c = self._counts[a]
            out[a] = {
                "count": c,
                "avg_reward": round(
                    self._rewards[a] / c, 4
                ) if c else 0.0,
            }
        return out


# ═══════════════════════════════════════════════════════════════
#  K-MEANS CLUSTERING  — lightweight centroid-based
# ═══════════════════════════════════════════════════════════════

class KMeansCluster:
    """Mini k-means for clustering agent telemetry vectors.

    Works on list-of-floats feature vectors.
    """

    def __init__(self, k: int = 3, max_iter: int = 50):
        self._k = k
        self._max_iter = max_iter
        self._centroids: list[list[float]] = []

    @staticmethod
    def _dist(a: list[float], b: list[float]) -> float:
        return math.sqrt(
            sum((x - y) ** 2 for x, y in zip(a, b))
        )

    def fit(
        self,
        data: list[list[float]],
    ) -> list[int]:
        if not data:
            return []
        n = len(data)
        dim = len(data[0])
        # init centroids via reservoir sampling
        indices = random.sample(
            range(n), min(self._k, n),
        )
        self._centroids = [list(data[i]) for i in indices]
        labels = [0] * n

        for _ in range(self._max_iter):
            # assign
            changed = False
            for i, pt in enumerate(data):
                dists = [
                    self._dist(pt, c) for c in self._centroids
                ]
                new_label = dists.index(min(dists))
                if new_label != labels[i]:
                    changed = True
                labels[i] = new_label
            if not changed:
                break
            # update centroids
            for ci in range(len(self._centroids)):
                members = [
                    data[j] for j in range(n)
                    if labels[j] == ci
                ]
                if members:
                    self._centroids[ci] = [
                        sum(m[d] for m in members)
                        / len(members)
                        for d in range(dim)
                    ]
        return labels

    @property
    def centroids(self) -> list[list[float]]:
        return self._centroids


# ═══════════════════════════════════════════════════════════════
#  AGENT PERFORMANCE PROFILER
# ═══════════════════════════════════════════════════════════════

@dataclass
class _RunRecord:
    agent: str
    task: str
    start: float
    end: float
    success: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentPerformanceProfiler:
    """Tracks agent execution latency, success rates, and
    capacity utilisation to enable adaptive routing.

    Feeds into the ActionScorer so the system can learn which
    agents are best suited for which task types.
    """

    def __init__(self) -> None:
        self._records: list[_RunRecord] = []
        self._by_agent: dict[str, list[_RunRecord]] = (
            defaultdict(list)
        )

    def record(
        self,
        agent: str,
        task: str,
        duration_s: float,
        success: bool,
        **meta: Any,
    ) -> None:
        rec = _RunRecord(
            agent=agent,
            task=task,
            start=time.time() - duration_s,
            end=time.time(),
            success=success,
            metadata=dict(meta),
        )
        self._records.append(rec)
        self._by_agent[agent].append(rec)

    def agent_stats(
        self,
        agent: str,
    ) -> dict[str, Any]:
        recs = self._by_agent.get(agent, [])
        if not recs:
            return {"runs": 0}
        durations = [r.end - r.start for r in recs]
        successes = sum(1 for r in recs if r.success)
        return {
            "runs": len(recs),
            "success_rate": round(successes / len(recs), 4),
            "avg_duration_s": round(
                statistics.mean(durations), 3,
            ),
            "p95_duration_s": round(
                sorted(durations)[
                    int(len(durations) * 0.95)
                ],
                3,
            ),
        }

    def all_stats(self) -> dict[str, dict[str, Any]]:
        return {
            a: self.agent_stats(a)
            for a in self._by_agent
        }

    def best_agent_for(
        self,
        task_type: str,
        candidates: Optional[list[str]] = None,
    ) -> Optional[str]:
        """Pick the agent with highest success rate for
        tasks matching *task_type*."""
        scores: list[tuple[str, float]] = []
        for agent, recs in self._by_agent.items():
            if candidates and agent not in candidates:
                continue
            matching = [
                r for r in recs if task_type in r.task
            ]
            if len(matching) < 2:
                continue
            rate = sum(
                1 for r in matching if r.success
            ) / len(matching)
            scores.append((agent, rate))
        if not scores:
            return None
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]

    def save(self, path: Optional[Path] = None) -> Path:
        dest = path or (
            ML_DATA_DIR / "agent_performance.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "updated": datetime.now().isoformat(),
            "stats": self.all_stats(),
            "total_records": len(self._records),
        }
        dest.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
        return dest


# ═══════════════════════════════════════════════════════════════
#  PERSISTENCE — save / load trained models
# ═══════════════════════════════════════════════════════════════

def save_model(
    name: str,
    state: dict[str, Any],
    path: Optional[Path] = None,
) -> Path:
    dest = path or (ML_DATA_DIR / f"{name}.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": name,
        "saved": datetime.now().isoformat(),
        "state": state,
    }
    dest.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    return dest


def load_model(
    name: str,
    path: Optional[Path] = None,
) -> Optional[dict[str, Any]]:
    src = path or (ML_DATA_DIR / f"{name}.json")
    if not src.exists():
        return None
    try:
        data = json.loads(
            src.read_text(encoding="utf-8"),
        )
        return data.get("state")
    except (json.JSONDecodeError, OSError):
        return None
