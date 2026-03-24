"""Deploy readiness check for BIT RAGE SYSTEMS.

Validates all components needed for production deployment.

Usage:
    python -m tests.deploy_check
"""

import io
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main():
    print("=" * 60)
    print("BIT RAGE SYSTEMS -- DEPLOY READINESS CHECK")
    print("=" * 60)

    errors = []

    # 1. Core imports
    print("\n[1/7] Core module imports...")
    for mod in ["api.intake", "api.rapidapi", "api.monitor", "api.payments",
                "dispatcher.router", "dispatcher.queue", "delivery.sender",
                "billing.payments", "automation.nerve", "dashboard.health"]:
        try:
            __import__(mod)
            print(f"  OK    {mod}")
        except Exception as e:
            errors.append((mod, str(e)[:80]))
            print(f"  FAIL  {mod}: {e}")

    # 2. Agent imports
    print("\n[2/7] Agent imports...")
    agent_names = [
        "sales_ops", "support", "content_repurpose", "doc_extract",
        "lead_gen", "email_marketing", "seo_content", "social_media",
        "data_entry", "web_scraper", "crm_ops", "bookkeeping",
        "proposal_writer", "product_desc", "resume_writer", "ad_copy",
        "market_research", "business_plan", "press_release", "tech_docs",
        "context_manager", "qa_manager", "production_manager", "automation_manager",
    ]
    ok = 0
    for a in agent_names:
        try:
            __import__(f"agents.{a}.runner")
            ok += 1
        except Exception as e:
            errors.append((f"agents.{a}", str(e)[:80]))
            print(f"  FAIL  agents.{a}: {e}")
    print(f"  {ok}/{len(agent_names)} agents OK")

    # 3. Env vars
    print("\n[3/7] Environment variables...")
    from dotenv import dotenv_values
    env = dotenv_values(PROJECT_ROOT / ".env")
    required = {
        "OPENAI_API_KEY": "LLM provider (primary)",
        "ANTHROPIC_API_KEY": "LLM provider (secondary)",
        "STRIPE_API_KEY": "Billing",
        "SMTP_HOST": "Email delivery",
        "SMTP_USER": "Email delivery",
        "SMTP_PASS": "Email delivery",
    }
    for k, purpose in required.items():
        val = env.get(k, "")
        if val:
            print(f"  OK    {k:25s} ({purpose})")
        else:
            errors.append(("env", f"{k} missing ({purpose})"))
            print(f"  MISS  {k:25s} ({purpose})")

    optional_keys = ["GEMINI_API_KEY", "GROK_API_KEY", "X_BEARER_TOKEN",
                     "STRIPE_WEBHOOK_SECRET", "STRIPE_PUBLIC_KEY"]
    opt_count = sum(1 for k in optional_keys if env.get(k))
    print(f"  {opt_count}/{len(optional_keys)} optional keys set")

    # 4. Dockerfile
    print("\n[4/7] Dockerfile...")
    df = PROJECT_ROOT / "Dockerfile"
    if df.exists():
        content = df.read_text()
        print(f"  OK    Dockerfile ({len(content)} bytes)")
        if "python:3.12" in content:
            print(f"  OK    Base image: Python 3.12")
        else:
            print(f"  WARN  Not using Python 3.12 base image")
        if "EXPOSE" in content:
            port = [l for l in content.splitlines() if "EXPOSE" in l]
            print(f"  OK    {port[0].strip()}")
    else:
        errors.append(("deploy", "No Dockerfile found"))
        print(f"  FAIL  No Dockerfile")

    # 5. fly.toml
    print("\n[5/7] fly.toml...")
    ft = PROJECT_ROOT / "fly.toml"
    if ft.exists():
        content = ft.read_text()
        print(f"  OK    fly.toml exists")
        for line in content.splitlines():
            if "app" in line and "=" in line and not line.strip().startswith("#"):
                print(f"  OK    {line.strip()}")
                break
        if "yyz" in content:
            print(f"  OK    Region: yyz (Toronto)")
    else:
        print(f"  SKIP  No fly.toml")

    # 6. railway.json
    print("\n[6/7] railway.json...")
    rj = PROJECT_ROOT / "railway.json"
    if rj.exists():
        cfg = json.loads(rj.read_text())
        builder = cfg.get("build", {}).get("builder", "?")
        print(f"  OK    railway.json (builder: {builder})")
        hc = cfg.get("deploy", {}).get("healthcheckPath", "")
        if hc:
            print(f"  OK    Healthcheck: {hc}")
    else:
        print(f"  SKIP  No railway.json")

    # 7. requirements.txt
    print("\n[7/7] requirements.txt...")
    req = PROJECT_ROOT / "requirements.txt"
    if req.exists():
        lines = [l.strip() for l in req.read_text().splitlines()
                 if l.strip() and not l.startswith("#")]
        print(f"  OK    {len(lines)} dependencies listed")

        # Check all are installed
        import importlib.metadata
        installed = {d.metadata["Name"].lower() for d in importlib.metadata.distributions()}
        missing = []
        for line in lines:
            pkg = line.split(">=")[0].split("==")[0].split("<")[0].strip().lower()
            pkg_normalized = pkg.replace("-", "_").replace(".", "_")
            if pkg not in installed and pkg_normalized not in installed:
                # Try alternate normalization
                if pkg.replace("_", "-") not in installed:
                    missing.append(pkg)
        if missing:
            print(f"  WARN  {len(missing)} packages may be missing: {', '.join(missing)}")
        else:
            print(f"  OK    All packages installed")
    else:
        errors.append(("deploy", "No requirements.txt"))
        print(f"  FAIL  No requirements.txt")

    # 8. Quick API startup test
    print("\n[BONUS] FastAPI app object test...")
    try:
        from api.intake import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        print(f"  OK    FastAPI app loaded with {len(routes)} routes")
        key_routes = ["/tasks", "/health", "/ops", "/subscribe"]
        for kr in key_routes:
            if kr in routes:
                print(f"  OK    {kr}")
            else:
                print(f"  MISS  {kr}")
    except Exception as e:
        errors.append(("api", f"FastAPI failed to load: {e}"))
        print(f"  FAIL  {e}")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"DEPLOY READINESS: {len(errors)} ISSUE(S)")
        for mod, err in errors:
            print(f"  [{mod}] {err}")
    else:
        print("DEPLOY READINESS: ALL CLEAR")
        print("  Fly.io:   flyctl deploy")
        print("  Railway:  railway up")
        print("  Local:    python -m api.intake")
    print("=" * 60)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
