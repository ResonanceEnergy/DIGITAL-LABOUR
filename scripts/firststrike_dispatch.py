#!/usr/bin/env python3
"""
FirstStrike Dispatch — VS Code → DIGITAL LABOUR Task Pipeline

Sends tasks from VS Code to local dev, production Railway, or Windows
compute node via SASP protocol. Designed to be called from VS Code
tasks.json or run standalone.

Usage:
    python scripts/firststrike_dispatch.py --task-type market_research --target production
    python scripts/firststrike_dispatch.py --task-type business_plan --target local
    python scripts/firststrike_dispatch.py --task-type sales_outreach --target windows --windows-ip 192.168.1.100
"""

import argparse
import json
import os
import sys
import uuid
import hmac
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

# ── Target Configuration ─────────────────────────────────────────
TARGETS = {
    "local": {
        "base_url": "http://localhost:8000",
        "name": "Local Dev Server",
    },
    "production": {
        "base_url": "https://bitrage-labour-api-production.up.railway.app",
        "name": "Railway Production",
    },
    "windows": {
        "base_url": "http://{windows_ip}:9090",
        "name": "Windows Compute Node (SASP)",
        "protocol": "sasp",
    },
}

# ── Task Templates ────────────────────────────────────────────────
TASK_TEMPLATES = {
    "sales_outreach": {
        "inputs": {
            "company": "Acme Corp",
            "role": "Engineering Manager",
            "product": "DIGITAL LABOUR AI Workforce",
        },
        "priority": 5,
    },
    "lead_gen": {
        "inputs": {
            "industry": "technology",
            "location": "US",
            "company_size": "50-500",
        },
        "priority": 5,
    },
    "market_research": {
        "inputs": {
            "topic": "AI automation market trends 2026",
            "depth": "comprehensive",
        },
        "priority": 3,
    },
    "business_plan": {
        "inputs": {
            "company_name": "Bit Rage Labour",
            "industry": "AI Services",
            "stage": "growth",
        },
        "priority": 3,
    },
    "tech_docs": {
        "inputs": {
            "project": "DIGITAL LABOUR",
            "doc_type": "API reference",
            "framework": "FastAPI",
        },
        "priority": 4,
    },
    "grant_writer": {
        "inputs": {
            "program": "SBIR Phase I",
            "topic": "AI-powered workforce automation",
            "agency": "NSF",
        },
        "priority": 2,
    },
    "insurance_appeals": {
        "inputs": {
            "claim_type": "prior_authorization",
            "denial_reason": "medical_necessity",
            "service": "diagnostic imaging",
        },
        "priority": 1,
    },
    "compliance_docs": {
        "inputs": {
            "doc_type": "privacy_policy",
            "industry": "technology",
            "jurisdiction": "US",
        },
        "priority": 3,
    },
    "data_reporter": {
        "inputs": {
            "data_source": "queue_stats",
            "format": "executive_summary",
            "timeframe": "last_7_days",
        },
        "priority": 4,
    },
    "content_repurpose": {
        "inputs": {
            "source_type": "blog_post",
            "target_formats": ["twitter_thread", "linkedin_post", "email_newsletter"],
        },
        "priority": 5,
    },
    "seo_content": {
        "inputs": {
            "keyword": "AI automation services",
            "content_type": "blog_post",
            "word_count": 1500,
        },
        "priority": 4,
    },
    "social_media": {
        "inputs": {
            "platform": "linkedin",
            "topic": "AI workforce automation",
            "tone": "professional",
        },
        "priority": 5,
    },
    "proposal_writer": {
        "inputs": {
            "client": "Enterprise prospect",
            "service": "Full AI workforce deployment",
            "budget_range": "$10k-50k",
        },
        "priority": 2,
    },
    "press_release": {
        "inputs": {
            "headline": "Bit Rage Labour Launches AI Workforce Platform",
            "target_audience": "tech industry",
        },
        "priority": 3,
    },
}


def dispatch_http(target_url: str, task_type: str, inputs: dict, priority: int) -> dict:
    """Dispatch task via HTTP POST to intake API."""
    import urllib.request
    import urllib.error

    payload = {
        "task_type": task_type,
        "client": "firststrike-vscode",
        "provider": "openai",
        "priority": priority,
        "inputs": inputs,
        "sync": False,
        "schema_version": "2.0",
    }

    auth_token = os.environ.get("MATRIX_AUTH_TOKEN", "")
    headers = {
        "Content-Type": "application/json",
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{target_url}/tasks",
        data=data,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return {"status": "dispatched", "response": result}
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"status": "error", "code": e.code, "detail": body}
    except urllib.error.URLError as e:
        return {"status": "error", "detail": str(e.reason)}


def dispatch_sasp(windows_ip: str, command: str, parameters: dict) -> dict:
    """Dispatch command via SASP protocol to Windows compute node."""
    import urllib.request
    import urllib.error

    sasp_secret = os.environ.get("SASP_SECRET", "digital-labour-sasp-v1")
    timestamp = datetime.now(timezone.utc).isoformat()
    message_id = str(uuid.uuid4())

    payload = {
        "protocol": "SASP",
        "version": "1.0",
        "timestamp": timestamp,
        "message_id": message_id,
        "sender": {
            "type": "mac",
            "id": "mac-mini-vscode",
        },
        "recipient": {
            "type": "windows",
            "id": "windows-node-1",
        },
        "message_type": "command",
        "payload": {
            "command_id": command,
            "parameters": parameters,
            "callback_url": f"http://localhost:8000/api/callback",
        },
    }

    # HMAC signature
    msg_bytes = json.dumps(payload, sort_keys=True).encode()
    signature = hmac.new(
        sasp_secret.encode(), msg_bytes, hashlib.sha256
    ).hexdigest()
    payload["signature"] = signature

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://{windows_ip}:9090/sasp/command",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            return {"status": "dispatched", "protocol": "SASP", "response": result}
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"status": "error", "protocol": "SASP", "code": e.code, "detail": body}
    except urllib.error.URLError as e:
        return {"status": "error", "protocol": "SASP", "detail": str(e.reason)}


def check_health(target_url: str) -> bool:
    """Quick health check before dispatching."""
    import urllib.request
    try:
        req = urllib.request.Request(f"{target_url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("status") == "operational"
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="FirstStrike Dispatch — Send tasks from VS Code to DIGITAL LABOUR"
    )
    parser.add_argument(
        "--task-type", required=True,
        choices=list(TASK_TEMPLATES.keys()),
        help="Type of task to dispatch",
    )
    parser.add_argument(
        "--target", required=True,
        choices=["local", "production", "windows"],
        help="Dispatch target",
    )
    parser.add_argument(
        "--windows-ip", default="192.168.1.100",
        help="Windows node IP (only for --target windows)",
    )
    parser.add_argument(
        "--inputs", type=str, default=None,
        help="JSON string of custom inputs (overrides template)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show payload without dispatching",
    )

    args = parser.parse_args()
    template = TASK_TEMPLATES[args.task_type]
    inputs = json.loads(args.inputs) if args.inputs else template["inputs"]
    priority = template["priority"]
    target_config = TARGETS[args.target]

    print(f"\n{'='*60}")
    print(f"  FIRSTSTRIKE DISPATCH")
    print(f"{'='*60}")
    print(f"  Task Type : {args.task_type}")
    print(f"  Target    : {target_config['name']}")
    print(f"  Priority  : {priority}")
    print(f"  Inputs    : {json.dumps(inputs, indent=2)}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("[DRY RUN] Payload built but not dispatched.")
        return

    # Dispatch based on target
    if args.target == "windows":
        target_url = target_config["base_url"].format(windows_ip=args.windows_ip)
        print(f"[SASP] Sending to Windows node at {args.windows_ip}...")
        result = dispatch_sasp(
            args.windows_ip,
            command=f"run_agent_{args.task_type}",
            parameters={"task_type": args.task_type, "inputs": inputs, "priority": priority},
        )
    else:
        target_url = target_config["base_url"]
        print(f"[HTTP] Checking health at {target_url}...")
        healthy = check_health(target_url)
        if not healthy:
            print(f"  ⚠️  Target not responding. Dispatching anyway...")
        else:
            print(f"  ✅ Target healthy")

        print(f"[HTTP] Dispatching {args.task_type} to {target_url}/tasks...")
        result = dispatch_http(target_url, args.task_type, inputs, priority)

    # Output result
    print(f"\n{'='*60}")
    if result.get("status") == "dispatched":
        print(f"  ✅ TASK DISPATCHED SUCCESSFULLY")
        if "response" in result:
            resp = result["response"]
            print(f"  Task ID : {resp.get('task_id', 'N/A')}")
            print(f"  Status  : {resp.get('status', 'N/A')}")
            print(f"  Message : {resp.get('message', 'N/A')}")
    else:
        print(f"  ❌ DISPATCH FAILED")
        print(f"  Error   : {result.get('detail', 'Unknown error')}")
        if "code" in result:
            print(f"  Code    : {result['code']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
