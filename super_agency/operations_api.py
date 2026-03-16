#!/usr/bin/env python3
"""
Operations API Server
REST API for programmatic access to DIGITAL LABOUR operations.
Includes: operations, research, second brain, runtime status, & system metrics.
"""

from quart import Quart, request, jsonify
import asyncio
import json
import sys
import os
import socket
import psutil
from datetime import datetime
from functools import wraps
from pathlib import Path

# Add current directory to path for imports
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'agents'))
sys.path.insert(0, str(ROOT / 'tools'))

import hmac  # noqa: E402
import time as _time  # noqa: E402
from collections import defaultdict  # noqa: E402

app = Quart(__name__)

# --------------- CORS ---------------
ALLOWED_ORIGINS = {"http://localhost:8080", "http://127.0.0.1:8080",
                   "http://localhost:5001", "http://127.0.0.1:5001"}


@app.after_request
async def _add_cors(response):
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route('/api/v1/<path:path>', methods=['OPTIONS'])
@app.route('/health', methods=['OPTIONS'])
async def _preflight_handler(**kwargs):
    """Handle CORS preflight requests."""
    return '', 204

# --------------- Rate Limiting ---------------
_RATE_WINDOW = 60          # seconds
_RATE_MAX_REQUESTS = 120   # per window per IP
_rate_buckets: dict = defaultdict(list)


def _check_rate_limit() -> bool:
    """Return True if the request is within rate limits."""
    client_ip = request.remote_addr or "unknown"
    now = _time.monotonic()
    # Prune expired entries
    _rate_buckets[client_ip] = [
        t for t in _rate_buckets[client_ip] if now - t < _RATE_WINDOW]
    if len(_rate_buckets[client_ip]) >= _RATE_MAX_REQUESTS:
        return False
    _rate_buckets[client_ip].append(now)
    return True

# --------------- Request Size Limit ---------------
MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

import logging as _logging
_api_logger = _logging.getLogger("operations_api")

_AUTH_WARNING_EMITTED = False


def requires_api_key(f):
    """Require a valid API key for protected endpoints."""
    @wraps(f)
    async def decorated(*args, **kwargs):
        global _AUTH_WARNING_EMITTED
        # Rate limit check (applies regardless of auth mode)
        if not _check_rate_limit():
            return jsonify({"error": "Rate limit exceeded"}), 429
        api_key = os.getenv("DL_API_KEY")
        if not api_key:
            if not _AUTH_WARNING_EMITTED:
                _api_logger.warning(
                    "DL_API_KEY not set — API auth DISABLED (dev mode). "
                    "Set DL_API_KEY in .env for production.")
                _AUTH_WARNING_EMITTED = True
            return await f(*args, **kwargs)
        token = request.headers.get(
            "Authorization", "").removeprefix("Bearer ").strip()
        if not token or not _safe_compare(token, api_key):
            _api_logger.warning(
                "Auth failure from %s on %s %s",
                request.remote_addr, request.method, request.path,
            )
            return jsonify({"error": "Unauthorized"}), 401
        return await f(*args, **kwargs)
    return decorated


def _safe_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())


@app.route('/api/v1/operations/query', methods=['POST'])
@requires_api_key
async def operations_query():
    """
    POST /api/v1/operations/query
    Body: {"query": "your natural language query", "user_context": {...}}
    """
    try:
        data = await request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' field in request body",
                "example": {
                    "query": "How is NCC doing today?",
                    "user_context": {"role": "executive", "clearance_level": "supreme_command"}
                }
            }), 400

        query = data['query']
        user_context = data.get('user_context', {})

        # Import here to avoid issues
        from operations_command_interface import handle_operations_query
        import asyncio

        # Process the query
        result = await handle_operations_query(query, user_context)

        # Debug: print result type and content
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")

        # Add API metadata
        result['api_version'] = 'v1'
        result['processed_at'] = datetime.now().isoformat()
        result['query'] = query

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": f"Internal server error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/v1/operations/departments', methods=['GET'])
@requires_api_key
async def list_departments():
    """GET /api/v1/operations/departments - List all available departments"""
    try:
        # Import OCI to access departments
        from operations_command_interface import oci

        departments = {}
        for key, dept in oci.departments.items():
            departments[key] = {
                "name": dept["name"],
                "head": dept["head"],
                "capabilities": dept["capabilities"],
                "portfolio_company": dept.get("portfolio_company", False)
            }

        return jsonify({
            "departments": departments,
            "total_count": len(departments),
            "core_departments": len([d for d in departments.values() if not d.get("portfolio_company", False)]),
            "portfolio_companies": len([d for d in departments.values() if d.get("portfolio_company", False)])
        })

    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve departments: {str(e)}"
        }), 500

@app.route('/health', methods=['GET'])
@app.route('/api/v1/health', methods=['GET'])
async def health_check():
    """GET /api/v1/health - API health check"""
    return jsonify({
        "status": "healthy",
        "service": "DIGITAL LABOUR Operations API",
        "version": "v1",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/v1/operations/status', methods=['GET'])
@requires_api_key
async def system_status():
    """GET /api/v1/operations/status - Overall system status"""
    try:
        from operations_command_interface import oci

        # Get basic system metrics
        try:
            with open('portfolio.json', 'r') as pf:
                portfolio = json.load(pf)
        except (FileNotFoundError, json.JSONDecodeError):
            portfolio = {"repositories": []}
        total_companies = len(portfolio.get('repositories', []))

        return jsonify({
            "system_status": "operational",
            "total_departments": len(oci.departments),
            "portfolio_companies": total_companies,
            "oci_queries_processed": len(oci.conversation_history),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "system_status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


# ── Research Project Management ──────────────────────────────────────────

@app.route('/api/v1/research/projects', methods=['GET'])
@requires_api_key
async def research_projects():
    """GET /api/v1/research/projects — Status of all research projects."""
    try:
        from research_manager import get_all_project_statuses
        date = request.args.get("date")
        statuses = get_all_project_statuses(date)
        return jsonify(
            {"projects": statuses, "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/research/projects/<project_id>', methods=['GET'])
@requires_api_key
async def research_project_detail(project_id):
    """GET /api/v1/research/projects/<id> — Detailed status of one project."""
    try:
        from research_manager import get_all_project_statuses
        date = request.args.get("date")
        statuses = get_all_project_statuses(date)
        match = [s for s in statuses if s["project_id"] == project_id]
        if not match:
            return jsonify({"error": f"Project '{project_id}' not found"}), 404
        return jsonify(match[0])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/research/report', methods=['POST'])
@requires_api_key
async def generate_research_report_endpoint():
    """POST /api/v1/research/report — Generate a fresh research report."""
    try:
        from research_manager import generate_research_report
        data = await request.get_json() or {}
        date = data.get("date")
        path = generate_research_report(date)
        return jsonify(
            {"report_path": path, "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Second Brain Pipeline ────────────────────────────────────────────────

@app.route('/api/v1/secondbrain/ingest', methods=['POST'])
@requires_api_key
async def secondbrain_ingest():
    """POST /api/v1/secondbrain/ingest — Ingest a YouTube URL through the pipeline."""
    try:
        data = await request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "Missing 'url' field"}), 400

        url = data['url']
        full = data.get('full', True)

        from secondbrain_pipeline import ingest as sb_ingest, run_full_pipeline

        if full:
            result = await asyncio.to_thread(run_full_pipeline, url)
        else:
            result = await asyncio.to_thread(sb_ingest, url)

        return jsonify({**result, "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/secondbrain/queue', methods=['POST'])
@requires_api_key
async def secondbrain_queue():
    """POST /api/v1/secondbrain/queue — Add a URL to the pending queue (processed next orchestrator run)."""
    try:
        data = await request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "Missing 'url' field"}), 400

        queue_file = ROOT / "knowledge" / "secondbrain" / "pending.json"
        queue_file.parent.mkdir(parents=True, exist_ok=True)

        pending = []
        if queue_file.exists():
            try:
                pending = json.loads(queue_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pending = []

        pending.append(
            {"url": data["url"], "queued_at": datetime.now().isoformat()})
        queue_file.write_text(json.dumps(pending, indent=2), encoding="utf-8")

        return jsonify({"queued": True, "position": len(pending),
                        "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/secondbrain/recent', methods=['GET'])
@requires_api_key
async def secondbrain_recent():
    """GET /api/v1/secondbrain/recent — List recently ingested videos."""
    try:
        from secondbrain_pipeline import list_ingested
        entries = list_ingested()
        return jsonify(
            {"entries": entries[-20:],
             "total": len(entries),
             "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Runtime Status ───────────────────────────────────────────────────────

@app.route('/api/v1/runtime/status', methods=['GET'])
@requires_api_key
async def runtime_status():
    """GET /api/v1/runtime/status — Full runtime state from watchdog."""
    try:
        from run_digital_labour import get_runtime_state
        state = get_runtime_state()
        return jsonify({**state, "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({
            "warning": "Runtime state unavailable (API may be running standalone)",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


# ── System Metrics ───────────────────────────────────────────────────────

@app.route('/api/v1/metrics/system', methods=['GET'])
@requires_api_key
async def system_metrics():
    """GET /api/v1/metrics/system — CPU, memory, disk."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(ROOT))

        return jsonify({
            "cpu_percent": cpu,
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "percent": round(disk.percent, 1),
            },
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/metrics/portfolio', methods=['GET'])
@requires_api_key
async def portfolio_metrics():
    """GET /api/v1/metrics/portfolio — Portfolio summary by tier and risk."""
    try:
        pf = ROOT / "portfolio.json"
        if not pf.exists():
            return jsonify({"error": "portfolio.json not found"}), 404
        data = json.loads(pf.read_text(encoding="utf-8"))
        repos = data.get("repositories", [])

        by_tier = {}
        by_risk = {}
        for r in repos:
            t = r.get("tier", "unknown")
            rk = r.get("risk_tier", "unknown")
            by_tier[t] = by_tier.get(t, 0) + 1
            by_risk[rk] = by_risk.get(rk, 0) + 1

        return jsonify({
            "total_repos": len(repos),
            "by_tier": by_tier,
            "by_risk": by_risk,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Service Liveness ─────────────────────────────────────────────────────

@app.route('/api/v1/services/liveness', methods=['GET'])
async def services_liveness():
    """GET /api/v1/services/liveness — Check all service ports (no auth)."""
    services = {}
    for name, port in [("Matrix", 8080), ("Mobile", 8081), ("OpsAPI", 5001)]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", port))
            s.close()
            services[name] = {"port": port, "status": "UP"}
        except OSError:
            services[name] = {"port": port, "status": "DOWN"}
    return jsonify(
        {"services": services, "timestamp": datetime.now().isoformat()})


# ── Message Bus ──────────────────────────────────────────────────────────

@app.route('/api/v1/bus/recent', methods=['GET'])
@requires_api_key
async def bus_recent():
    """GET /api/v1/bus/recent?topic=*&limit=20 — Recent bus messages."""
    try:
        from agents.message_bus import bus
        topic = request.args.get("topic", "*")
        limit = min(int(request.args.get("limit", 20)), 100)
        return jsonify({"messages": bus.recent(topic, limit),
                        "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/bus/publish', methods=['POST'])
@requires_api_key
async def bus_publish():
    """POST /api/v1/bus/publish — Publish a message to the bus."""
    try:
        from agents.message_bus import bus
        data = await request.get_json()
        if not data or 'topic' not in data:
            return jsonify({"error": "Missing 'topic' field"}), 400
        bus.publish(data['topic'], data.get('payload', {}),
                    source=data.get('source', 'api'))
        return jsonify(
            {"published": True, "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/bus/stats', methods=['GET'])
@requires_api_key
async def bus_stats():
    """GET /api/v1/bus/stats — Bus subscriber/message statistics."""
    try:
        from agents.message_bus import bus
        return jsonify(
            {**bus.stats(),
             "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """not_found handler."""
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": [
            "POST /api/v1/operations/query",
            "GET  /api/v1/operations/departments",
            "GET  /api/v1/operations/status",
            "GET  /api/v1/research/projects",
            "GET  /api/v1/research/projects/<id>",
            "POST /api/v1/research/report",
            "POST /api/v1/secondbrain/ingest",
            "POST /api/v1/secondbrain/queue",
            "GET  /api/v1/secondbrain/recent",
            "GET  /api/v1/runtime/status",
            "GET  /api/v1/metrics/system",
            "GET  /api/v1/metrics/portfolio",
            "GET  /api/v1/services/liveness",
            "GET  /api/v1/bus/recent",
            "POST /api/v1/bus/publish",
            "GET  /api/v1/bus/stats",
            "GET  /api/v1/health",
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """internal_error handler."""
    return jsonify({
        "error": "Internal server error",
        "message": "Please try again later"
    }), 500

if __name__ == '__main__':
    print("[LAUNCH] Starting DIGITAL LABOUR Operations API Server...")
    print("[API] Available endpoints:")
    print("   POST /api/v1/operations/query     - Process operational queries")
    print("   GET  /api/v1/operations/departments - List all departments")
    print("   GET  /api/v1/operations/status    - System status")
    print("   GET  /api/v1/health               - Health check")
    print("\n[NET] Server running on http://localhost:5001")

    # Run with Quart (async Flask)
    app.run(host='localhost', port=5001, debug=False)
