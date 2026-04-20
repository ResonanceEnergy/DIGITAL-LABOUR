#!/usr/bin/env python3
"""
SASP Send — Cross-device command dispatch for DIGITAL LABOUR.

Sends SASP protocol messages between Mac Hub and Windows compute node.
Can also run in hub mode to listen for incoming commands.

Usage:
    python scripts/sasp_send.py --target 192.168.1.100 --command deploy_agents_heavy
    python scripts/sasp_send.py --target 192.168.1.100 --command health_check
    python scripts/sasp_send.py --mode hub  # Start listening for SASP commands
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

SASP_SECRET = os.environ.get("SASP_SECRET", "digital-labour-sasp-v1")
SASP_VERSION = "1.0"

COMMANDS = {
    "deploy_agents_heavy": {
        "description": "Deploy heavy compute agents on Windows node",
        "parameters": {"agent_count": 4, "duration": 300, "priority": "high"},
    },
    "health_check": {
        "description": "Check system health across all services",
        "parameters": {"services": ["aac_system", "matrix_maximizer", "agents"]},
    },
    "sync_data": {
        "description": "Synchronize data between Mac hub and Windows node",
        "parameters": {"direction": "bidirectional", "include": ["tasks", "metrics", "logs"]},
    },
    "restart_services": {
        "description": "Restart all DIGITAL LABOUR services on target",
        "parameters": {"services": "all", "graceful": True},
    },
    "run_diagnostics": {
        "description": "Run full system diagnostics",
        "parameters": {"depth": "full", "include_network": True, "include_storage": True},
    },
}


def build_sasp_message(command_id: str, parameters: dict, target_ip: str) -> dict:
    """Build a signed SASP protocol message."""
    timestamp = datetime.now(timezone.utc).isoformat()
    message = {
        "protocol": "SASP",
        "version": SASP_VERSION,
        "timestamp": timestamp,
        "message_id": str(uuid.uuid4()),
        "sender": {
            "type": "mac",
            "id": f"mac-hub-{os.getenv('HOSTNAME', 'mini')}",
            "ip": "0.0.0.0",
        },
        "recipient": {
            "type": "windows",
            "id": "windows-node-1",
            "ip": target_ip,
        },
        "message_type": "command",
        "payload": {
            "command_id": command_id,
            "parameters": parameters,
            "callback_url": f"http://localhost:8000/api/callback",
        },
    }

    # Sign it
    msg_bytes = json.dumps(message, sort_keys=True).encode()
    signature = hmac.new(SASP_SECRET.encode(), msg_bytes, hashlib.sha256).hexdigest()
    message["signature"] = signature

    return message


def send_command(target_ip: str, command_id: str, parameters: dict) -> dict:
    """Send SASP command to target node."""
    import urllib.request
    import urllib.error

    message = build_sasp_message(command_id, parameters, target_ip)
    data = json.dumps(message).encode("utf-8")

    req = urllib.request.Request(
        f"http://{target_ip}:9090/sasp/command",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "code": e.code, "detail": e.read().decode()}
    except urllib.error.URLError as e:
        return {"error": True, "detail": str(e.reason)}


def run_hub_mode():
    """Start a lightweight SASP listener on this Mac for incoming commands."""
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
    except ImportError:
        print("Cannot start hub mode without http.server")
        sys.exit(1)

    class SASPHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                message = json.loads(body)
                print(f"\n[SASP RECEIVED] {message.get('message_type', 'unknown')}")
                print(f"  From    : {message.get('sender', {}).get('type', '?')}")
                print(f"  Command : {message.get('payload', {}).get('command_id', '?')}")
                print(f"  Time    : {message.get('timestamp', '?')}")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "received",
                    "message_id": message.get("message_id"),
                }).encode())
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        def do_GET(self):
            if self.path == "/sasp/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "operational",
                    "node": "mac-hub",
                    "protocol": "SASP",
                    "version": SASP_VERSION,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }).encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # Suppress default logging

    port = int(os.environ.get("SASP_PORT", 9090))
    server = HTTPServer(("0.0.0.0", port), SASPHandler)
    print(f"[SASP HUB] Listening on port {port}...")
    print(f"[SASP HUB] Health endpoint: http://localhost:{port}/sasp/health")
    print(f"[SASP HUB] Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SASP HUB] Shutting down.")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="SASP Send — DIGITAL LABOUR cross-device dispatch")
    parser.add_argument("--target", type=str, help="Target IP address")
    parser.add_argument("--command", type=str, choices=list(COMMANDS.keys()), help="Command to send")
    parser.add_argument("--mode", type=str, choices=["send", "hub"], default="send", help="Run mode")
    parser.add_argument("--params", type=str, default=None, help="Custom params JSON (overrides defaults)")

    args = parser.parse_args()

    if args.mode == "hub":
        run_hub_mode()
        return

    if not args.target or not args.command:
        parser.error("--target and --command are required in send mode")

    cmd = COMMANDS[args.command]
    params = json.loads(args.params) if args.params else cmd["parameters"]

    print(f"\n{'='*50}")
    print(f"  SASP COMMAND DISPATCH")
    print(f"{'='*50}")
    print(f"  Target  : {args.target}")
    print(f"  Command : {args.command}")
    print(f"  Desc    : {cmd['description']}")
    print(f"  Params  : {json.dumps(params)}")
    print(f"{'='*50}\n")

    result = send_command(args.target, args.command, params)

    if result.get("error"):
        print(f"  ❌ Failed: {result.get('detail', 'Unknown')}")
    else:
        print(f"  ✅ Command sent successfully")
        print(f"  Response: {json.dumps(result, indent=2)}")

    print()


if __name__ == "__main__":
    main()
