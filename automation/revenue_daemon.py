"""Revenue Daemon — Monitors Stripe payments and updates income tracker.

Polls Stripe for new charges/payments, logs revenue to income tracker,
sends alerts on new sales. Runs as daemon or one-shot check.

Usage:
    python -m automation.revenue_daemon              # One-shot check
    python -m automation.revenue_daemon --daemon     # Continuous monitoring (every 30 min)
    python -m automation.revenue_daemon --summary    # Revenue summary
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

REVENUE_STATE = PROJECT_ROOT / "data" / "revenue_state.json"
CHECK_INTERVAL_MINUTES = 30


def _load_state() -> dict:
    if REVENUE_STATE.exists():
        return json.loads(REVENUE_STATE.read_text(encoding="utf-8"))
    return {"last_check": None, "total_logged": 0, "charges": []}


def _save_state(state: dict):
    REVENUE_STATE.parent.mkdir(parents=True, exist_ok=True)
    REVENUE_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def check_stripe_revenue() -> dict:
    """Check Stripe for recent charges and log new ones."""
    import stripe

    api_key = os.getenv("STRIPE_API_KEY", "")
    if not api_key:
        print("  [WARN] No STRIPE_API_KEY set")
        return {"total": 0, "new_charges": 0}

    stripe.api_key = api_key
    state = _load_state()

    # Look back 24 hours or since last check
    since = None
    if state.get("last_check"):
        since = int(datetime.fromisoformat(state["last_check"]).timestamp())
    else:
        since = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())

    try:
        charges = stripe.Charge.list(created={"gte": since}, limit=100)
    except stripe.AuthenticationError:
        print("  [WARN] Stripe auth failed — key may be invalid")
        return {"total": 0, "new_charges": 0}
    except Exception as e:
        print(f"  [WARN] Stripe API error: {e}")
        return {"total": 0, "new_charges": 0}

    known_ids = {c["id"] for c in state.get("charges", [])}
    new_charges = []

    for charge in charges.data:
        if charge.id not in known_ids and charge.paid and charge.status == "succeeded":
            entry = {
                "id": charge.id,
                "amount": charge.amount / 100,  # cents → dollars
                "currency": charge.currency,
                "description": charge.description or "",
                "created": datetime.fromtimestamp(charge.created, tz=timezone.utc).isoformat(),
                "customer_email": getattr(charge, "receipt_email", "") or "",
            }
            new_charges.append(entry)
            state["charges"].append(entry)
            state["total_logged"] += entry["amount"]

    # Update income tracker for each new charge
    if new_charges:
        try:
            from income.tracker import log_revenue
            for c in new_charges:
                log_revenue("stripe_direct", c["amount"],
                            f"Stripe charge {c['id']}: {c['description']}")
                print(f"  [NEW] ${c['amount']:.2f} — {c['description'] or 'Stripe payment'}")
        except Exception as e:
            print(f"  [WARN] Could not update income tracker: {e}")

    state["last_check"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)

    total = sum(c["amount"] for c in state.get("charges", []))
    return {"total": total, "new_charges": len(new_charges), "charges": new_charges}


def check_all_revenue() -> dict:
    """Check revenue across all automated sources."""
    results = {}

    # Stripe
    print(f"\n── Stripe ──")
    results["stripe"] = check_stripe_revenue()
    print(f"  Total: ${results['stripe']['total']:.2f} | New: {results['stripe']['new_charges']}")

    # Future: add Freelancer API, Fiverr API, bot platform revenue checks here

    return results


def show_summary():
    """Display revenue summary."""
    state = _load_state()
    print(f"\n{'='*60}")
    print(f"  REVENUE DASHBOARD")
    print(f"{'='*60}")
    print(f"  Total logged: ${state.get('total_logged', 0):.2f}")
    print(f"  Charges tracked: {len(state.get('charges', []))}")
    print(f"  Last check: {state.get('last_check', 'never')}")

    # Recent charges
    charges = state.get("charges", [])
    if charges:
        print(f"\n── Recent Charges ──")
        for c in charges[-10:]:
            print(f"  ${c['amount']:.2f}  {c.get('created', '')[:16]}  {c.get('description', '')}")


def daemon_loop():
    """Run revenue monitoring continuously."""
    print(f"\n{'#'*60}")
    print(f"  REVENUE DAEMON ONLINE")
    print(f"  Check interval: {CHECK_INTERVAL_MINUTES} minutes")
    print(f"{'#'*60}")

    while True:
        try:
            check_all_revenue()
        except KeyboardInterrupt:
            print("\n[REVENUE] Daemon stopped.")
            break
        except Exception as e:
            print(f"  [ERROR] Revenue check failed: {e}")

        try:
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("\n[REVENUE] Daemon stopped.")
            break


def main():
    parser = argparse.ArgumentParser(description="Revenue Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--summary", action="store_true", help="Revenue summary")
    args = parser.parse_args()

    if args.daemon:
        daemon_loop()
    elif args.summary:
        show_summary()
    else:
        check_all_revenue()


if __name__ == "__main__":
    main()
