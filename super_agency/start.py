#!/usr/bin/env python3
"""
DIGITAL LABOUR - Quick Start
Verifies environment, loads .env, and launches the runtime.
"""

import sys
import os
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))


def _load_env():
    env_file = ROOT / ".env"
    try:
        from dotenv import load_dotenv
        if env_file.exists():
            load_dotenv(env_file)
            print("[OK] .env loaded")
        else:
            print("[WARN] No .env file found "
                  "- copy .env.example to .env")
    except ImportError:
        print("[WARN] python-dotenv not installed")


def _preflight():
    ok = True

    def check(label, condition, hint=""):
        nonlocal ok
        if condition:
            print(f"  [OK] {label}")
        else:
            print(f"  [!!] {label} - {hint}")
            ok = False

    print("\n--- Pre-flight checks ---")
    check("Python >= 3.10",
          sys.version_info >= (3, 10),
          f"Got {sys.version}")
    check("OPENAI_API_KEY set",
          bool(os.getenv("OPENAI_API_KEY")),
          "Set in .env")
    check("GITHUB_TOKEN set",
          bool(os.getenv("GITHUB_TOKEN")),
          "Set in .env (optional)")

    deps = [
        ("flask", "pip install flask"),
        ("quart", "pip install quart"),
        ("psutil", "pip install psutil"),
        ("openai", "pip install openai"),
        ("autogen_agentchat",
         "pip install autogen-agentchat"),
    ]
    for mod, hint in deps:
        found = importlib.util.find_spec(mod) is not None
        check(f"{mod} installed", found, hint)

    print()
    return ok


if __name__ == "__main__":
    _load_env()
    all_ok = _preflight()

    if not os.getenv("OPENAI_API_KEY"):
        print("[FATAL] OPENAI_API_KEY is required. "
              "Set it in .env or system environment.")
        sys.exit(1)
    if not all_ok:
        print("[WARN] Some optional checks failed "
              "- system may run in degraded mode")

    print("--- Launching DIGITAL LABOUR ---\n")
    from run_bit_rage_labour import main  # noqa: E402
    main()
