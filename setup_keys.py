"""DEPRECATED — Use bitrage.py setup or 'BIT RAGE.exe' instead.

This file is kept for backwards compatibility. All functionality has been
consolidated into bitrage.py (the master launcher).

Replacement command:
    bitrage.py setup       # replaces: python setup_keys.py

Original description:
    Setup script — paste your API keys and this writes your .env file.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

PROVIDERS = [
    {
        "name": "OpenAI",
        "key_var": "OPENAI_API_KEY",
        "model_var": "OPENAI_MODEL",
        "default_model": "gpt-4o",
        "prefix": "sk-",
        "docs": "https://platform.openai.com/api-keys",
    },
    {
        "name": "Anthropic (Claude)",
        "key_var": "ANTHROPIC_API_KEY",
        "model_var": "ANTHROPIC_MODEL",
        "default_model": "claude-sonnet-4-20250514",
        "prefix": "sk-ant-",
        "docs": "https://console.anthropic.com/settings/keys",
    },
    {
        "name": "Google Gemini",
        "key_var": "GEMINI_API_KEY",
        "model_var": "GEMINI_MODEL",
        "default_model": "gemini-2.0-flash",
        "prefix": "AI",
        "docs": "https://aistudio.google.com/apikey",
    },
    {
        "name": "Grok (xAI)",
        "key_var": "GROK_API_KEY",
        "model_var": "GROK_MODEL",
        "default_model": "grok-3",
        "prefix": "xai-",
        "docs": "https://console.x.ai",
    },
]

EXTRA_VARS = """
# Optional: Groq (cheap inference, different from Grok/xAI)
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

# Delivery
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=

# Billing
STRIPE_API_KEY=

# Default provider for agents (openai | anthropic | gemini | grok)
DEFAULT_PROVIDER=openai
"""


def main():
    print("=" * 50)
    print("  DIGITAL LABOUR — API Key Setup")
    print("=" * 50)
    print()
    print("Paste each API key when prompted.")
    print("Press Enter to skip any provider you don't have yet.")
    print()

    lines = []
    configured = []

    for p in PROVIDERS:
        print(f"--- {p['name']} ---")
        print(f"  Get key: {p['docs']}")
        key = input(f"  {p['key_var']}: ").strip()

        if key:
            lines.append(f"# {p['name']}")
            lines.append(f"{p['key_var']}={key}")
            lines.append(f"{p['model_var']}={p['default_model']}")
            lines.append("")
            configured.append(p['name'])
            print(f"  ✓ {p['name']} configured")
        else:
            lines.append(f"# {p['name']} (not configured)")
            lines.append(f"{p['key_var']}=")
            lines.append(f"{p['model_var']}={p['default_model']}")
            lines.append("")
            print(f"  - Skipped")
        print()

    # Add extra vars
    lines.append(EXTRA_VARS.strip())

    # Write .env
    env_content = "\n".join(lines) + "\n"
    ENV_PATH.write_text(env_content, encoding="utf-8")

    print()
    print("=" * 50)
    print(f"  .env written to: {ENV_PATH}")
    print(f"  Configured: {', '.join(configured) if configured else 'None'}")
    print("=" * 50)
    print()

    if configured:
        print("Next: python agents/sales_ops/runner.py --company \"Stripe\" --role \"Head of Growth\"")
    else:
        print("Add at least one API key and re-run this script.")


if __name__ == "__main__":
    main()
