"""Quick live endpoint test."""
import httpx
import json

BASE = "https://digital-labour-api-production.up.railway.app"

# Test unified /v1/run with a support ticket
print("Testing /v1/run with support_ticket agent...")
r = httpx.post(
    f"{BASE}/v1/run",
    json={
        "agent": "support_ticket",
        "inputs": {"ticket_text": "My invoice shows wrong amount, charged 299 instead of 199"},
        "provider": "openai",
    },
    timeout=60,
)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"Agent: {d.get('agent')}")
    print(f"QA: {d.get('qa_status')}")
    print(f"Time: {d.get('processing_time_ms')}ms")
    print(json.dumps(d.get("result", {}), indent=2)[:1000])
else:
    print(f"Error: {r.text[:500]}")

# Test intake sub-app
print("\n\nTesting /intake/tasks with sales_outreach...")
r2 = httpx.post(
    f"{BASE}/intake/tasks",
    json={
        "task_type": "product_desc",
        "inputs": {"product_specs": "Wireless noise-cancelling headphones, 40hr battery, ANC, Bluetooth 5.3"},
        "provider": "openai",
        "sync": True,
    },
    timeout=60,
)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    d2 = r2.json()
    print(f"Task ID: {d2.get('task_id')}")
    print(f"Status: {d2.get('status')}")
    print(f"Message: {d2.get('message')}")
else:
    print(f"Error: {r2.text[:500]}")
