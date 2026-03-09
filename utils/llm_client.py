"""Multi-provider LLM client — supports OpenAI, Anthropic, Gemini, and Grok.

Usage:
    from utils.llm_client import call_llm

    result = call_llm(system_prompt, user_message)                    # uses DEFAULT_PROVIDER
    result = call_llm(system_prompt, user_message, provider="gemini") # force specific provider
"""

import json
import os
import re
from dotenv import load_dotenv

load_dotenv()


def _strip_fences(text: str) -> str:
    """Strip markdown code fences that some providers wrap around JSON."""
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()

# ── Provider configs ────────────────────────────────────────────────────────

PROVIDERS = {
    "openai": {
        "key_var": "OPENAI_API_KEY",
        "model_var": "OPENAI_MODEL",
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "key_var": "ANTHROPIC_API_KEY",
        "model_var": "ANTHROPIC_MODEL",
        "default_model": "claude-sonnet-4-20250514",
    },
    "gemini": {
        "key_var": "GEMINI_API_KEY",
        "model_var": "GEMINI_MODEL",
        "default_model": "gemini-2.0-flash",
    },
    "grok": {
        "key_var": "GROK_API_KEY",
        "model_var": "GROK_MODEL",
        "default_model": "grok-3",
    },
}


def get_default_provider() -> str:
    """Get configured default, or first provider with a key set."""
    default = os.getenv("DEFAULT_PROVIDER", "").lower()
    if default and default in PROVIDERS:
        cfg = PROVIDERS[default]
        if os.getenv(cfg["key_var"]):
            return default

    # Fallback: first provider that has a key
    for name, cfg in PROVIDERS.items():
        if os.getenv(cfg["key_var"]):
            return name

    raise ValueError("No LLM API key configured. Run: python setup_keys.py")


def _get_model(provider: str) -> str:
    cfg = PROVIDERS[provider]
    return os.getenv(cfg["model_var"], cfg["default_model"])


# ── OpenAI ──────────────────────────────────────────────────────────────────

def _call_openai(system_prompt: str, user_message: str, model: str, temperature: float, json_mode: bool) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


# ── Anthropic ───────────────────────────────────────────────────────────────

def _call_anthropic(system_prompt: str, user_message: str, model: str, temperature: float, json_mode: bool) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt_suffix = "\n\nRespond with valid JSON only. Do NOT wrap in markdown fences." if json_mode else ""
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt + prompt_suffix,
        messages=[{"role": "user", "content": user_message}],
        temperature=temperature,
    )
    text = response.content[0].text
    return _strip_fences(text) if json_mode else text


# ── Gemini ──────────────────────────────────────────────────────────────────

def _call_gemini(system_prompt: str, user_message: str, model: str, temperature: float, json_mode: bool) -> str:
    import httpx
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    generation_config = {"temperature": temperature}
    if json_mode:
        generation_config["responseMimeType"] = "application/json"

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_message}]}],
        "generationConfig": generation_config,
    }

    resp = httpx.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ── Grok (xAI) ──────────────────────────────────────────────────────────────

def _call_grok(system_prompt: str, user_message: str, model: str, temperature: float, json_mode: bool) -> str:
    from openai import OpenAI
    # xAI uses OpenAI-compatible API
    client = OpenAI(
        api_key=os.environ["GROK_API_KEY"],
        base_url="https://api.x.ai/v1",
    )
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


# ── Dispatch ────────────────────────────────────────────────────────────────

_CALLERS = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "gemini": _call_gemini,
    "grok": _call_grok,
}


def call_llm(
    system_prompt: str,
    user_message: str,
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    json_mode: bool = True,
    fallback: bool = True,
) -> str:
    """Call any configured LLM provider with automatic fallback.

    Args:
        system_prompt: System/instruction prompt
        user_message: User input
        provider: "openai" | "anthropic" | "gemini" | "grok" (None = default)
        model: Override model name (None = use env/default)
        temperature: Sampling temperature
        json_mode: Request JSON output format
        fallback: If True, try other providers on failure

    Returns:
        Raw string response from the LLM.
    """
    provider = provider or get_default_provider()
    model = model or _get_model(provider)
    caller = _CALLERS.get(provider)

    if not caller:
        raise ValueError(f"Unknown provider: {provider}. Options: {list(_CALLERS.keys())}")

    try:
        return caller(system_prompt, user_message, model, temperature, json_mode)
    except Exception as e:
        if not fallback:
            raise
        print(f"[FALLBACK] {provider} failed: {e}. Trying alternatives...")
        for alt_name in list_available_providers():
            if alt_name == provider:
                continue
            try:
                alt_model = _get_model(alt_name)
                alt_caller = _CALLERS[alt_name]
                result = alt_caller(system_prompt, user_message, alt_model, temperature, json_mode)
                print(f"[FALLBACK] Succeeded with {alt_name}")
                return result
            except Exception as e2:
                print(f"[FALLBACK] {alt_name} also failed: {e2}")
                continue
        raise ValueError(f"All providers failed. Last error: {e}")


def list_available_providers() -> list[str]:
    """Return list of providers that have API keys configured."""
    available = []
    for name, cfg in PROVIDERS.items():
        if os.getenv(cfg["key_var"]):
            available.append(name)
    return available
