#!/usr/bin/env python3
"""
AGENT GASKET Startup Script — OpenClaw Bridge Edition

Initializes the GASKET-OpenClaw bridge, deploys skills to the gateway,
and sends startup instructions to GASKET via the OpenClaw API.

Usage:
  python3 gasket_startup.py           # Full startup (deploy + message)
  python3 gasket_startup.py --deploy  # Deploy skills only
  python3 gasket_startup.py --status  # Bridge status only
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

# Import bridge
sys.path.insert(0, str(Path(__file__).parent))
try:
    from agents.gasket_openclaw_bridge import GasketOpenClawBridge
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False


def send_message_to_gasket(message: str) -> dict:
    """Send a message to AGENT GASKET through the OpenClaw gateway"""
    try:
        # Try the local gateway
        response = requests.post(
            "http://127.0.0.1:18789/api/chat",
            json={"message": message, "agent": "GASKET"},
            timeout=10,
        )
        if response.status_code == 200:
            return {"success": True, "response": response.json()}
    except Exception:
        pass

    # Fallback: create a message file in the GASKET workspace
    workspace_dir = Path.home() / ".openclaw" / "workspace-gasket"
    message_file = workspace_dir / "gasket_instructions.json"

    instruction = {
        "from": "SuperAgency",
        "to": "AGENT GASKET",
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "priority": "high",
    }

    try:
        workspace_dir.mkdir(parents=True, exist_ok=True)
        with open(message_file, "w") as f:
            json.dump(instruction, f, indent=2)
        return {"success": True, "method": "file", "file": str(message_file)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def deploy_bridge():
    """Deploy GASKET skills and workspace to OpenClaw"""
    if not BRIDGE_AVAILABLE:
        print("❌ GASKET-OpenClaw Bridge not available")
        return False

    bridge = GasketOpenClawBridge()

    print("📁 Setting up GASKET workspace...")
    ws_result = bridge.setup_workspace()
    for step in ws_result["steps"]:
        print(f"  ✅ {step}")

    print("\n⚙️  Generating config patch...")
    config_result = bridge.apply_config()
    print(f"  📄 Saved: {config_result['patch_file']}")

    print("\n🌐 Gateway health check...")
    gw = bridge.check_gateway_health()
    if gw["healthy"]:
        print("  ✅ Gateway is healthy")
    else:
        print(f"  ⚠️  Gateway: {gw.get('error', 'not responding')}")
        print("  ℹ️  Start with: openclaw gateway run")

    return True


def show_status():
    """Show bridge status"""
    if not BRIDGE_AVAILABLE:
        print("❌ GASKET-OpenClaw Bridge not available")
        return

    bridge = GasketOpenClawBridge()
    status = bridge.get_full_status()
    print(json.dumps(status, indent=2, default=str))


def main():
    """Send startup instructions to AGENT GASKET via OpenClaw"""
    # Handle CLI args
    if "--deploy" in sys.argv:
        deploy_bridge()
        return
    if "--status" in sys.argv:
        show_status()
        return

    # Full startup: deploy + send message
    if BRIDGE_AVAILABLE:
        print("🔴 GASKET Startup — OpenClaw Bridge Edition")
        print("=" * 50)
        deploy_bridge()
        print()

    message = """
AGENT GASKET v2.1 — Startup Instructions

You are now running with full OpenClaw Gateway integration.

Skills deployed:
- gasket-status: System health monitoring
- gasket-cpu-optimize: CPU resource optimization
- gasket-memory-doctrine: Memory & doctrine management
- gasket-qusar-ops: QUSAR orchestration
- gasket-matrix-maximizer: Performance analytics
- gasket-morning-brief: Daily briefing generator
- gasket-second-brain: Zero-friction knowledge capture
- gasket-self-heal: Self-healing infrastructure

Operational loops:
- CPU optimization (30s interval)
- QUSAR feedback (45s interval)
- Matrix Maximizer (60s interval)
- Memory doctrine (120s interval)
- OpenClaw bridge health (300s interval)

Begin operations. Report status via OpenClaw gateway.
"""

    result = send_message_to_gasket(message)

    if result["success"]:
        print("✅ Startup message delivered to AGENT GASKET")
        if "method" in result:
            print(f"  📄 Method: {result['method']}")
        if "file" in result:
            print(f"  📁 File: {result['file']}")
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
