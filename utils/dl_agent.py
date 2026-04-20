"""DL Agent Core — Production-grade upgrade layer for all 24 agents.

Implements Anthropic's "Building Effective Agents" patterns:
    1. Provider failover with intelligent routing
    2. Chain-of-thought reasoning before generation
    3. Self-reflection / evaluator-optimizer loop
    4. Input validation + token budget enforcement
    5. Structured output with Pydantic auto-repair
    6. Response caching (hash-based dedup)
    7. Quality scoring with configurable thresholds
    8. Cost tracking + token metering
    9. Observability (structured logging, metrics)
   10. Few-shot example injection

Usage in any agent:
    from utils.dl_agent import super_call, SuperConfig

    config = SuperConfig(agent_name="ad_copy", temperature=0.7)
    result = super_call(system_prompt, user_message, config=config)
"""

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.llm_client import call_llm, list_available_providers, get_default_provider

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "agent_cache"

# ── Client context for cost attribution ────────────────────────
# Set via set_active_client() before batch operations to tag cost records.
_ACTIVE_CLIENT_ID: str = ""


def set_active_client(client_id: str) -> None:
    """Set the active client context so _track_cost() can attribute costs."""
    global _ACTIVE_CLIENT_ID
    _ACTIVE_CLIENT_ID = client_id


def clear_active_client() -> None:
    """Clear the active client context after a batch is complete."""
    global _ACTIVE_CLIENT_ID
    _ACTIVE_CLIENT_ID = ""
METRICS_DIR = PROJECT_ROOT / "data" / "agent_metrics"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(parents=True, exist_ok=True)

# ── Token estimation (rough but fast — no tiktoken dependency) ──────────────

def _estimate_tokens(text: str) -> int:
    """~4 chars per token for English text."""
    return max(1, len(text) // 4)


# ── Configuration ───────────────────────────────────────────────────────────

@dataclass
class SuperConfig:
    """Configuration for super-agent enhanced LLM calls."""
    agent_name: str = "unknown"

    # LLM settings
    provider: str | None = None
    temperature: float = 0.7
    json_mode: bool = True

    # Chain-of-thought
    chain_of_thought: bool = True

    # Self-reflection (evaluator-optimizer loop)
    self_reflect: bool = True
    reflect_threshold: float = 7.0  # Score 1-10; below this = re-generate
    max_reflect_rounds: int = 2

    # Quality gate
    min_quality_score: float = 6.0
    quality_dimensions: list[str] = field(default_factory=lambda: [
        "accuracy", "completeness", "clarity", "relevance",
    ])

    # Token budget
    max_input_tokens: int = 12000
    max_output_tokens: int = 4096

    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour

    # Few-shot examples
    few_shot_examples: list[dict] = field(default_factory=list)

    # Provider failover
    failover_enabled: bool = True
    provider_priority: list[str] = field(default_factory=lambda: [
        "openai", "anthropic", "gemini", "grok",
    ])

    # Cost tracking
    track_costs: bool = True


# ── Prompt enhancement ──────────────────────────────────────────────────────

_COT_WRAPPER = """Before producing your final output, think step-by-step:
1. Identify the key requirements from the user's request
2. Plan your approach — what structure and content is needed
3. Consider edge cases or potential quality issues
4. Generate the output

Wrap your reasoning in a "reasoning" field in the JSON, then provide the actual output in the remaining fields.
"""

_REFLECTION_PROMPT = """You are a quality evaluator. Score this agent output on a 1-10 scale.

Evaluate these dimensions:
{dimensions}

For each dimension, give a score 1-10 and brief justification.
Then provide:
- "overall_score": weighted average (float)
- "pass": true if overall_score >= {threshold}
- "improvements": list of specific, actionable improvements (empty if pass=true)
- "critical_issues": list of any factual errors or policy violations

Respond with valid JSON:
{{
    "scores": {{"dimension": {{"score": N, "reason": "..."}}}},
    "overall_score": N.N,
    "pass": true/false,
    "improvements": ["..."],
    "critical_issues": ["..."]
}}
"""

_IMPROVEMENT_INJECTION = """
QUALITY FEEDBACK FROM PREVIOUS ATTEMPT:
Score: {score}/10
Issues to fix:
{improvements}

Critical issues:
{critical}

Regenerate your output addressing ALL of the above feedback. Maintain what was good, fix what was flagged.
"""


def _inject_cot(system_prompt: str) -> str:
    """Add chain-of-thought instructions to system prompt."""
    return system_prompt.rstrip() + "\n\n" + _COT_WRAPPER


def _inject_few_shot(user_message: str, examples: list[dict]) -> str:
    """Prepend few-shot examples to user message."""
    if not examples:
        return user_message
    parts = ["Here are examples of high-quality outputs:\n"]
    for i, ex in enumerate(examples, 1):
        inp = ex.get("input", "")
        out = ex.get("output", "")
        parts.append(f"--- Example {i} ---\nInput: {inp}\nOutput: {out}\n")
    parts.append("--- Your turn ---\n")
    parts.append(user_message)
    return "\n".join(parts)


# ── Input validation ────────────────────────────────────────────────────────

def _validate_input(system_prompt: str, user_message: str, config: SuperConfig) -> str | None:
    """Return error string if input is invalid, None if OK."""
    if not system_prompt.strip():
        return "Empty system prompt"
    if not user_message.strip():
        return "Empty user message"

    total_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_message)
    if total_tokens > config.max_input_tokens:
        return f"Input too large: ~{total_tokens} tokens (max {config.max_input_tokens})"

    return None


# ── Caching ─────────────────────────────────────────────────────────────────

def _cache_key(system_prompt: str, user_message: str, config: SuperConfig) -> str:
    """Generate deterministic cache key."""
    content = f"{config.agent_name}:{config.provider}:{config.temperature}:{system_prompt}:{user_message}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _cache_get(key: str, ttl: int) -> str | None:
    """Read from cache if exists and not expired."""
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > ttl:
            path.unlink(missing_ok=True)
            return None
        return data.get("response", None)
    except (json.JSONDecodeError, KeyError):
        return None


def _cache_set(key: str, response: str):
    """Write response to cache."""
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps({
        "response": response,
        "cached_at": time.time(),
    }), encoding="utf-8")


# ── Cost tracking ──────────────────────────────────────────────────────────

# Approximate costs per 1K tokens (input/output) — March 2026
_COST_PER_1K = {
    "openai": {"input": 0.0025, "output": 0.01},       # GPT-4o
    "anthropic": {"input": 0.003, "output": 0.015},     # Claude Sonnet
    "gemini": {"input": 0.0001, "output": 0.0004},      # Gemini Flash
    "grok": {"input": 0.005, "output": 0.015},           # Grok-3
}


def _track_cost(agent_name: str, provider: str, input_tokens: int,
                output_tokens: int, duration_s: float, cached: bool):
    """Append cost record to daily metrics file."""
    rates = _COST_PER_1K.get(provider, {"input": 0.005, "output": 0.015})
    cost = (input_tokens / 1000 * rates["input"]) + (output_tokens / 1000 * rates["output"])

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": agent_name,
        "provider": provider,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
        "duration_s": round(duration_s, 2),
        "cached": cached,
    }
    if _ACTIVE_CLIENT_ID:
        record["client"] = _ACTIVE_CLIENT_ID

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    metrics_file = METRICS_DIR / f"costs_{date_str}.jsonl"
    with open(metrics_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return cost


# ── Self-reflection (evaluator-optimizer loop) ─────────────────────────────

def _reflect(response: str, system_prompt: str, user_message: str,
             config: SuperConfig) -> dict:
    """Score the response quality using a separate LLM call."""
    dimensions_str = "\n".join(f"- {d}" for d in config.quality_dimensions)
    reflect_prompt = _REFLECTION_PROMPT.format(
        dimensions=dimensions_str,
        threshold=config.reflect_threshold,
    )

    eval_input = (
        f"SYSTEM PROMPT:\n{system_prompt[:500]}...\n\n"
        f"USER REQUEST:\n{user_message[:500]}...\n\n"
        f"AGENT OUTPUT:\n{response[:3000]}"
    )

    # Use a different provider for evaluation if possible (reduces bias)
    eval_provider = config.provider or get_default_provider()
    available = list_available_providers()
    for alt in ["anthropic", "openai", "gemini"]:
        if alt != eval_provider and alt in available:
            eval_provider = alt
            break

    raw = call_llm(
        system_prompt=reflect_prompt,
        user_message=eval_input,
        provider=eval_provider,
        temperature=0.3,  # Low temp for consistent evaluation
        json_mode=True,
        fallback=True,
    )

    try:
        return json.loads(raw, strict=False)
    except json.JSONDecodeError:
        return {"overall_score": 5.0, "pass": False,
                "improvements": ["Could not parse reflection"], "critical_issues": []}


# ── Output repair ──────────────────────────────────────────────────────────

def _repair_json(raw: str) -> str:
    """Attempt to fix common JSON issues from LLM output."""
    # Strip markdown fences
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', raw, re.DOTALL)
    if m:
        raw = m.group(1)

    # Strip trailing commas before } or ]
    raw = re.sub(r',\s*([}\]])', r'\1', raw)

    # Remove non-whitespace control characters
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)

    return raw.strip()


def _extract_output(raw: str, config: SuperConfig) -> str:
    """Extract the actual output, removing CoT reasoning if present."""
    if not config.chain_of_thought:
        return raw

    try:
        data = json.loads(_repair_json(raw), strict=False)
        if isinstance(data, dict) and "reasoning" in data:
            # Log reasoning but don't include in final output
            reasoning = data.pop("reasoning", "")
            if reasoning:
                _log(config.agent_name, "REASONING", reasoning[:200])
            return json.dumps(data)
    except (json.JSONDecodeError, TypeError):
        pass

    return raw


# ── Structured logging ─────────────────────────────────────────────────────

def _log(agent: str, level: str, msg: str):
    """Structured agent log line."""
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"  [{ts}] [{agent.upper()}] [{level}] {msg}")


# ── Main super_call ─────────────────────────────────────────────────────────

def super_call(
    system_prompt: str,
    user_message: str,
    config: SuperConfig | None = None,
) -> str:
    """Enhanced LLM call with all super-agent capabilities.

    Drop-in replacement for call_llm() with:
    - Chain-of-thought reasoning
    - Self-reflection quality loop
    - Input validation + token budgets
    - Caching (hash-based dedup)
    - Provider failover
    - Cost tracking
    - JSON auto-repair

    Returns:
        Raw JSON string (same as call_llm).
    """
    config = config or SuperConfig()
    agent = config.agent_name
    start = time.time()

    # 1. Input validation
    err = _validate_input(system_prompt, user_message, config)
    if err:
        _log(agent, "ERROR", f"Input validation failed: {err}")
        raise ValueError(f"[{agent}] {err}")

    # 2. Cache check
    key = ""
    if config.cache_enabled:
        key = _cache_key(system_prompt, user_message, config)
        cached = _cache_get(key, config.cache_ttl_seconds)
        if cached:
            _log(agent, "CACHE", "Hit — returning cached response")
            if config.track_costs:
                _track_cost(agent, config.provider or "cached", 0, 0, 0, True)
            return cached

    # 3. Enhance prompts
    enhanced_system = system_prompt
    if config.chain_of_thought:
        enhanced_system = _inject_cot(system_prompt)

    enhanced_user = user_message
    if config.few_shot_examples:
        enhanced_user = _inject_few_shot(user_message, config.few_shot_examples)

    # 4. Determine provider with failover
    provider = config.provider or get_default_provider()
    if config.failover_enabled:
        available = list_available_providers()
        # Reorder by priority, filtering to available
        ordered = [p for p in config.provider_priority if p in available]
        if provider not in ordered and provider in available:
            ordered.insert(0, provider)
        if not ordered:
            ordered = available
    else:
        ordered = [provider]

    # 5. Make the call (with failover)
    raw = None
    used_provider = provider
    for p in ordered:
        try:
            _log(agent, "CALL", f"→ {p} (temp={config.temperature})")
            raw = call_llm(
                system_prompt=enhanced_system,
                user_message=enhanced_user,
                provider=p,
                temperature=config.temperature,
                json_mode=config.json_mode,
                fallback=False,  # We handle failover ourselves
            )
            used_provider = p
            break
        except Exception as e:
            _log(agent, "FAIL", f"{p}: {e}")
            continue

    if raw is None:
        raise RuntimeError(f"[{agent}] All providers failed: {ordered}")

    # 6. JSON repair
    if config.json_mode:
        raw = _repair_json(raw)

    # 7. Extract output (strip CoT reasoning)
    raw = _extract_output(raw, config)

    # 8. Self-reflection loop
    if config.self_reflect:
        for round_num in range(config.max_reflect_rounds):
            reflection = _reflect(raw, system_prompt, user_message, config)
            score = reflection.get("overall_score", 10.0)
            passed = reflection.get("pass", True)

            _log(agent, "REFLECT", f"Round {round_num + 1}: score={score:.1f}/10 pass={passed}")

            if passed or score >= config.reflect_threshold:
                break

            # Regenerate with improvement feedback
            improvements = reflection.get("improvements", [])
            critical = reflection.get("critical_issues", [])

            if not improvements and not critical:
                break

            improvement_text = _IMPROVEMENT_INJECTION.format(
                score=f"{score:.1f}",
                improvements="\n".join(f"- {i}" for i in improvements),
                critical="\n".join(f"- {c}" for c in critical) if critical else "None",
            )

            _log(agent, "REGEN", f"Regenerating with {len(improvements)} improvements...")
            try:
                raw = call_llm(
                    system_prompt=enhanced_system,
                    user_message=enhanced_user + "\n\n" + improvement_text,
                    provider=used_provider,
                    temperature=max(0.3, config.temperature - 0.1),  # Slightly lower temp for fixes
                    json_mode=config.json_mode,
                    fallback=config.failover_enabled,
                )
                if config.json_mode:
                    raw = _repair_json(raw)
                raw = _extract_output(raw, config)
            except Exception as e:
                _log(agent, "REGEN_FAIL", str(e))
                break

    # 9. Cache the result
    if config.cache_enabled:
        _cache_set(key, raw)

    # 10. Track costs
    duration = time.time() - start
    if config.track_costs:
        input_tokens = _estimate_tokens(enhanced_system) + _estimate_tokens(enhanced_user)
        output_tokens = _estimate_tokens(raw)
        cost = _track_cost(agent, used_provider, input_tokens, output_tokens, duration, False)
        _log(agent, "COST", f"~{input_tokens}in/{output_tokens}out tokens, ${cost:.4f}, {duration:.1f}s")

    _log(agent, "DONE", f"Response ready ({len(raw)} chars, {duration:.1f}s)")
    return raw


# ── Utility: get daily cost summary ────────────────────────────────────────

def get_daily_costs(date_str: str | None = None) -> dict:
    """Get cost summary for a date (default: today)."""
    date_str = date_str or datetime.now(timezone.utc).strftime("%Y%m%d")
    metrics_file = METRICS_DIR / f"costs_{date_str}.jsonl"

    if not metrics_file.exists():
        return {"date": date_str, "total_cost": 0, "calls": 0, "by_agent": {}}

    total_cost = 0
    total_calls = 0
    by_agent: dict[str, dict[str, Any]] = {}
    by_provider: dict[str, float] = {}

    for line in metrics_file.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        rec = json.loads(line)
        total_cost += rec["cost_usd"]
        total_calls += 1

        agent = rec["agent"]
        if agent not in by_agent:
            by_agent[agent] = {"cost": 0, "calls": 0, "cached": 0}
        by_agent[agent]["cost"] += rec["cost_usd"]
        by_agent[agent]["calls"] += 1
        if rec.get("cached"):
            by_agent[agent]["cached"] += 1

        prov = rec["provider"]
        by_provider[prov] = by_provider.get(prov, 0) + rec["cost_usd"]

    return {
        "date": date_str,
        "total_cost": round(total_cost, 4),
        "calls": total_calls,
        "by_agent": {k: {kk: round(vv, 4) if isinstance(vv, float) else vv
                         for kk, vv in v.items()} for k, v in by_agent.items()},
        "by_provider": {k: round(v, 4) for k, v in by_provider.items()},
    }


# ── Quick upgrade helper ───────────────────────────────────────────────────

def make_super(agent_name: str, temperature: float = 0.7,
               few_shots: list[dict] | None = None,
               quality_dims: list[str] | None = None,
               reflect_threshold: float = 7.0) -> SuperConfig:
    """Quick factory for agent-specific SuperConfig."""
    return SuperConfig(
        agent_name=agent_name,
        temperature=temperature,
        few_shot_examples=few_shots or [],
        quality_dimensions=quality_dims or [
            "accuracy", "completeness", "clarity", "relevance",
        ],
        reflect_threshold=reflect_threshold,
    )


# ── Drop-in bridge: replaces call_llm with zero call-site changes ──────────

def make_bridge(agent_name: str, default_temperature: float = 0.7,
                self_reflect: bool | None = None, chain_of_thought: bool = True,
                cache_enabled: bool = True, reflect_threshold: float = 7.0,
                quality_dims: list[str] | None = None):
    """Create a call_llm-compatible function that routes through super_call.

    Usage in any agent runner:
        from utils.dl_agent import make_bridge
        call_llm = make_bridge("ad_copy")       # replaces 'from utils.llm_client import call_llm'

    All existing call_llm(...) calls work unchanged — they now get:
    chain-of-thought, self-reflection, caching, failover, cost tracking.
    """
    # Resolve self_reflect: explicit arg wins; otherwise read DL_REFLECT env var (default off)
    _self_reflect = self_reflect if self_reflect is not None else os.getenv("DL_REFLECT", "false").lower() == "true"

    def bridge(system_prompt: str = "", user_prompt: str = "",
               user_message: str = "", provider: str | None = None,
               temperature: float = default_temperature,
               json_mode: bool = True, fallback: bool = True, **_kw) -> str:
        cfg = SuperConfig(
            agent_name=agent_name,
            provider=provider,
            temperature=temperature,
            json_mode=json_mode,
            failover_enabled=fallback,
            self_reflect=_self_reflect,
            chain_of_thought=chain_of_thought,
            cache_enabled=cache_enabled,
            reflect_threshold=reflect_threshold,
            quality_dimensions=quality_dims or [
                "accuracy", "completeness", "clarity", "relevance",
            ],
        )
        return super_call(system_prompt, user_prompt or user_message, config=cfg)

    bridge.__doc__ = f"Super-agent enhanced LLM call for {agent_name}"
    bridge.__name__ = "call_llm"
    return bridge


# ── Safe Pydantic validation with auto-repair ──────────────────────────────

def safe_validate(model_cls, data: dict | str, *, agent_name: str = "unknown") -> Any:
    """Validate LLM output against a Pydantic model with auto-repair.

    Handles common LLM output issues:
    1. JSON wrapped in markdown fences or extra nesting
    2. Misnamed keys (snake_case variants, common synonyms)
    3. Missing required string fields → filled with "N/A"
    4. Extra fields silently ignored

    Returns a validated model instance.
    Raises ValidationError only if repair completely fails.
    """
    from pydantic import ValidationError

    # If data is a string, parse it
    if isinstance(data, str):
        data = json.loads(_repair_json(data), strict=False)

    # Pre-repair: coerce dict items in list[str] fields (LLMs return {issue, description} objects)
    for field_name, field_info in model_cls.model_fields.items():
        if field_name not in data:
            continue
        annotation = field_info.annotation
        origin = getattr(annotation, '__origin__', None)
        args = getattr(annotation, '__args__', ())
        if origin is list and args and args[0] is str:
            val = data[field_name]
            if isinstance(val, list) and any(isinstance(item, dict) for item in val):
                data[field_name] = [
                    (f"{item.get('issue', item.get('type', 'Issue'))}: {item.get('description', item.get('detail', str(item)))}"
                     if isinstance(item, dict) else str(item))
                    for item in val
                ]
                _log(agent_name, "REPAIR", f"Coerced dict items to strings in '{field_name}'")

    # Attempt 1: direct validation
    try:
        return model_cls.model_validate(data)
    except ValidationError:
        pass

    # Attempt 2: unwrap common LLM nesting patterns
    # LLMs sometimes wrap output: {"result": {...}}, {"output": {...}}, {"data": {...}}
    for wrapper_key in ("result", "output", "data", "response"):
        if wrapper_key in data and isinstance(data[wrapper_key], dict):
            try:
                result = model_cls.model_validate(data[wrapper_key])
                _log(agent_name, "REPAIR", f"Unwrapped nested '{wrapper_key}' key")
                return result
            except ValidationError:
                pass

    # Attempt 3: key coercion — normalize keys to match model fields
    model_fields = set(model_cls.model_fields.keys())
    coerced = {}
    used_keys = set()

    for field_name in model_fields:
        if field_name in data:
            coerced[field_name] = data[field_name]
            used_keys.add(field_name)
        else:
            # Try common variations
            variants = _key_variants(field_name)
            for v in variants:
                if v in data:
                    coerced[field_name] = data[v]
                    used_keys.add(v)
                    _log(agent_name, "REPAIR", f"Mapped key '{v}' → '{field_name}'")
                    break

    # Attempt 3b: coerce list[str] items — LLMs often return dicts instead of strings
    for field_name, field_info in model_cls.model_fields.items():
        if field_name not in coerced:
            continue
        annotation = field_info.annotation
        # Check if field is list[str]
        origin = getattr(annotation, '__origin__', None)
        args = getattr(annotation, '__args__', ())
        if origin is list and args and args[0] is str:
            val = coerced[field_name]
            if isinstance(val, list) and any(isinstance(item, dict) for item in val):
                coerced[field_name] = [
                    (f"{item.get('issue', item.get('type', 'Issue'))}: {item.get('description', item.get('detail', str(item)))}"
                     if isinstance(item, dict) else str(item))
                    for item in val
                ]
                _log(agent_name, "REPAIR", f"Coerced dict items to strings in '{field_name}'")

    # Attempt 4: fill missing required string fields with "N/A"
    for field_name, field_info in model_cls.model_fields.items():
        if field_name in coerced:
            continue
        if field_info.is_required():
            annotation = field_info.annotation
            if annotation is str or (hasattr(annotation, '__origin__') and annotation is str):
                coerced[field_name] = "N/A"
                _log(agent_name, "REPAIR", f"Filled missing required field '{field_name}' with 'N/A'")

    try:
        result = model_cls.model_validate(coerced)
        _log(agent_name, "REPAIR", "Validation succeeded after key coercion")
        return result
    except ValidationError:
        pass

    # Attempt 5: last resort — construct with all defaults where possible
    for field_name, field_info in model_cls.model_fields.items():
        if field_name not in coerced:
            if not field_info.is_required():
                continue
            annotation = field_info.annotation
            # Fill primitives with sensible defaults
            if annotation is str:
                coerced[field_name] = "N/A"
            elif annotation is int:
                coerced[field_name] = 0
            elif annotation is float:
                coerced[field_name] = 0.0
            elif annotation is bool:
                coerced[field_name] = False
            elif annotation is list or (hasattr(annotation, '__origin__') and getattr(annotation, '__origin__', None) is list):
                coerced[field_name] = []

    result = model_cls.model_validate(coerced)
    _log(agent_name, "REPAIR", "Validation succeeded after filling all defaults")
    return result


def _key_variants(field_name: str) -> list[str]:
    """Generate common key name variants for fuzzy matching."""
    variants = []
    # camelCase
    parts = field_name.split("_")
    camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
    variants.append(camel)
    # No underscores
    variants.append(field_name.replace("_", ""))
    # With hyphens
    variants.append(field_name.replace("_", "-"))
    # Common synonyms
    synonyms = {
        "company_name": ["company", "name", "org", "organization"],
        "recent_signal": ["signal", "news", "recent_news", "latest_signal"],
        "personalization_angle": ["angle", "personalization", "hook", "outreach_angle"],
        "company_website": ["website", "url", "domain", "site"],
        "company_size_estimate": ["size", "company_size", "employees", "headcount"],
        "contact_name": ["name", "contact", "person"],
        "contact_role": ["role", "title", "job_title", "position"],
        "contact_email_guess": ["email", "email_guess", "contact_email"],
        "draft_reply": ["reply", "response", "draft_response", "message"],
        "severity": ["priority", "urgency"],
        "sentiment": ["tone", "customer_sentiment", "mood"],
        "category": ["type", "issue_type", "ticket_type", "classification"],
        "summary": ["description", "overview", "issue_summary"],
        "signal_source": ["source", "reference"],
        "role_relevant_pain": ["pain_point", "pain", "challenge"],
        "linkedin_url": ["linkedin", "profile_url"],
    }
    if field_name in synonyms:
        variants.extend(synonyms[field_name])
    return variants
