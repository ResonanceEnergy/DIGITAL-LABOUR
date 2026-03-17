"""Order Router — Routes won contracts/orders to agents for fulfillment.

When a bid is accepted or a client order comes in (from any platform),
this module determines the right agent, creates a task in the dispatcher
queue, and triggers fulfillment via the delivery pipeline.

Usage:
    python -m delivery.order_router --process         # Process pending orders
    python -m delivery.order_router --status           # Show order pipeline
    python -m delivery.order_router --add ORDER_JSON   # Add order from JSON file
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from automation.decision_log import log_decision

STATE_FILE = PROJECT_ROOT / "data" / "order_router_state.json"
ORDERS_DIR = PROJECT_ROOT / "data" / "orders"

# Agent routing: platform service type → agent task_type
SERVICE_TO_AGENT = {
    "data_entry": "data_entry",
    "lead_generation": "lead_gen",
    "lead_gen": "lead_gen",
    "content_writing": "content_repurpose",
    "content": "content_repurpose",
    "email_marketing": "email_marketing",
    "seo": "seo_content",
    "seo_content": "seo_content",
    "social_media": "social_media",
    "web_scraping": "web_scraper",
    "customer_support": "support",
    "support": "support",
    "document_extraction": "doc_extract",
    "doc_extract": "doc_extract",
    "market_research": "market_research",
    "product_description": "product_desc",
    "product_desc": "product_desc",
    "ad_copy": "ad_copy",
    "resume_writing": "resume_writer",
    "resume_writer": "resume_writer",
    "proposal_writing": "proposal_writer",
    "press_release": "press_release",
    "tech_docs": "tech_docs",
    "business_plan": "business_plan",
    "bookkeeping": "bookkeeping",
    "crm": "crm_ops",
}


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "orders": [],
        "total_routed": 0,
        "total_fulfilled": 0,
        "total_failed": 0,
    }


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def add_order(order: dict) -> str:
    """Register a new order for routing.

    Args:
        order: Dict with keys: platform, service_type, client_name,
               description, budget, deadline, requirements

    Returns order_id.
    """
    state = _load_state()
    order_id = str(uuid4())[:8]

    entry = {
        "order_id": order_id,
        "platform": order.get("platform", "direct"),
        "service_type": order.get("service_type", ""),
        "client_name": order.get("client_name", ""),
        "description": order.get("description", ""),
        "budget": order.get("budget", 0),
        "deadline": order.get("deadline", ""),
        "requirements": order.get("requirements", ""),
        "status": "pending",
        "agent_type": None,
        "task_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "routed_at": None,
        "fulfilled_at": None,
    }

    state["orders"].append(entry)
    _save_state(state)
    return order_id


def route_order(order_id: str) -> dict:
    """Route a pending order to the correct agent via the dispatcher queue."""
    state = _load_state()
    order = next((o for o in state["orders"] if o["order_id"] == order_id), None)
    if not order:
        return {"error": f"Order {order_id} not found"}

    if order["status"] != "pending":
        return {"error": f"Order {order_id} is {order['status']}, not pending"}

    # Determine agent type
    service = order.get("service_type", "").lower().replace(" ", "_")
    agent_type = SERVICE_TO_AGENT.get(service)

    if not agent_type:
        # Try fuzzy match on keywords
        desc = order.get("description", "").lower()
        for keyword, agent in SERVICE_TO_AGENT.items():
            if keyword.replace("_", " ") in desc:
                agent_type = agent
                break

    if not agent_type:
        order["status"] = "unroutable"
        _save_state(state)
        return {"error": f"Cannot route service type: {service}"}

    # Create task in dispatcher queue
    try:
        from dispatcher.queue import TaskQueue
        q = TaskQueue()
        task_id = q.enqueue(
            task_type=agent_type,
            inputs={
                "description": order.get("description", ""),
                "requirements": order.get("requirements", ""),
                "deadline": order.get("deadline", ""),
                "budget": order.get("budget", 0),
            },
            client=order.get("client_name", ""),
            priority=1 if order.get("budget", 0) > 100 else 0,
        )
    except Exception as e:
        order["status"] = "queue_error"
        _save_state(state)
        return {"error": f"Failed to queue task: {e}"}

    order["status"] = "routed"
    order["agent_type"] = agent_type
    order["task_id"] = task_id
    order["routed_at"] = datetime.now(timezone.utc).isoformat()
    state["total_routed"] += 1
    _save_state(state)

    log_decision(
        actor="ORDER_ROUTER",
        action="route_order",
        reasoning=f"Order {order_id} ({service}) from {order.get('platform', '?')}",
        outcome=f"Routed to {agent_type} as task {task_id}",
    )

    return {
        "order_id": order_id,
        "agent_type": agent_type,
        "task_id": task_id,
        "status": "routed",
    }


def process_pending() -> dict:
    """Route all pending orders."""
    state = _load_state()
    pending = [o for o in state["orders"] if o["status"] == "pending"]

    if not pending:
        print("\n  No pending orders.")
        return {"processed": 0}

    results = []
    for order in pending:
        result = route_order(order["order_id"])
        results.append(result)
        status = "routed" if "task_id" in result else "failed"
        print(f"  [{status.upper()}] {order['order_id']} — {order.get('service_type', '?')} → {result.get('agent_type', 'N/A')}")

    routed = sum(1 for r in results if "task_id" in r)
    return {"processed": len(results), "routed": routed, "failed": len(results) - routed}


def mark_fulfilled(order_id: str):
    """Mark an order as fulfilled after delivery."""
    state = _load_state()
    for o in state["orders"]:
        if o["order_id"] == order_id:
            o["status"] = "fulfilled"
            o["fulfilled_at"] = datetime.now(timezone.utc).isoformat()
            state["total_fulfilled"] += 1
            break
    _save_state(state)


def get_status() -> dict:
    """Get order router statistics."""
    state = _load_state()
    orders = state.get("orders", [])
    by_status = {}
    for o in orders:
        s = o.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

    return {
        "total_orders": len(orders),
        "by_status": by_status,
        "total_routed": state.get("total_routed", 0),
        "total_fulfilled": state.get("total_fulfilled", 0),
    }


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Order Router — Route orders to agents")
    parser.add_argument("--process", action="store_true", help="Process all pending orders")
    parser.add_argument("--status", action="store_true", help="Show order pipeline")
    parser.add_argument("--add", metavar="FILE", help="Add order from JSON file")
    args = parser.parse_args()

    if args.process:
        result = process_pending()
        print(f"\n  Processed: {result['processed']} | Routed: {result['routed']} | Failed: {result['failed']}")
    elif args.status:
        st = get_status()
        print(f"\n  Order Router Status:")
        print(f"    Total orders:    {st['total_orders']}")
        print(f"    Routed:          {st['total_routed']}")
        print(f"    Fulfilled:       {st['total_fulfilled']}")
        for status, count in st.get("by_status", {}).items():
            print(f"    {status:15s}: {count}")
    elif args.add:
        order = json.loads(Path(args.add).read_text(encoding="utf-8"))
        oid = add_order(order)
        print(f"  Added order: {oid}")
        result = route_order(oid)
        print(f"  Routed: {result}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
