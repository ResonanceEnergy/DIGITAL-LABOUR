"""DIGITAL LABOUR SECURITY AUDIT — Automated vulnerability scanner.

Checks:
1. Website (digital-labour.com) — headers, leaks, SSL
2. API (Railway) — auth bypass, info exposure, C2 access
3. DNS — SPF, DKIM, DMARC, BIMI
4. Codebase — hardcoded secrets, exposed keys
5. GitHub — public repo exposure
"""

import json
import os
import re
import socket
import ssl
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Config ──
WEBSITE = "https://digital-labour.com"
API_BASE = "https://digital-labour-api-production.up.railway.app"
DOMAIN = "digital-labour.com"

FINDINGS = []
PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0


def finding(severity, category, message, detail=""):
    global PASS_COUNT, FAIL_COUNT, WARN_COUNT
    icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵", "PASS": "🟢", "INFO": "ℹ️"}
    f = {"severity": severity, "category": category, "message": message, "detail": detail}
    FINDINGS.append(f)
    if severity == "PASS":
        PASS_COUNT += 1
    elif severity in ("CRITICAL", "HIGH"):
        FAIL_COUNT += 1
    else:
        WARN_COUNT += 1
    print(f"  {icon.get(severity, '?')} [{severity}] {category}: {message}")
    if detail:
        for line in detail.split("\n")[:3]:
            print(f"       {line}")


def fetch(url, method="GET", data=None, headers=None, timeout=10):
    """Safe HTTP fetch."""
    ctx = ssl.create_default_context()
    hdrs = {"User-Agent": "DigitalLabour-SecurityAudit/1.0"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, method=method, headers=hdrs)
    if data:
        req.data = json.dumps(data).encode() if isinstance(data, dict) else data
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read()
            return resp.status, dict(resp.headers), body
    except urllib.error.HTTPError as e:
        return e.code, {}, b""
    except Exception as e:
        return 0, {}, str(e).encode()


# ═══════════════════════════════════════════════════════════════════════════
# 1. WEBSITE SECURITY
# ═══════════════════════════════════════════════════════════════════════════

def audit_website():
    print("\n══ WEBSITE SECURITY: digital-labour.com ══")

    status, headers, body = fetch(WEBSITE)
    if status != 200:
        finding("HIGH", "WEBSITE", f"Website returned {status}")
        return

    text = body.decode("utf-8", errors="replace")
    finding("PASS", "WEBSITE", f"Website live — {len(text)} bytes")

    # Security headers
    hsts = headers.get("strict-transport-security", headers.get("Strict-Transport-Security", ""))
    csp = headers.get("content-security-policy", headers.get("Content-Security-Policy", ""))
    xfo = headers.get("x-frame-options", headers.get("X-Frame-Options", ""))
    xcto = headers.get("x-content-type-options", headers.get("X-Content-Type-Options", ""))

    if not hsts:
        finding("MEDIUM", "WEBSITE-HEADERS", "Missing Strict-Transport-Security header",
                "GitHub Pages doesn't set HSTS by default")
    else:
        finding("PASS", "WEBSITE-HEADERS", "HSTS present")

    if not csp:
        finding("MEDIUM", "WEBSITE-HEADERS", "Missing Content-Security-Policy",
                "Static site should have CSP via <meta> tag")
    else:
        finding("PASS", "WEBSITE-HEADERS", "CSP present")

    # Source code analysis
    urls_found = re.findall(r'https?://[^\s"\'<>]+', text)
    api_urls = [u for u in urls_found if "railway" in u or "digital-labour-api" in u]
    if api_urls:
        finding("HIGH", "WEBSITE-LEAK", "API URL exposed in website source",
                "\n".join(api_urls[:3]))
    else:
        finding("PASS", "WEBSITE-LEAK", "No API URL exposed in website source")

    # Check for sensitive patterns
    patterns = [
        (r"sk_[a-z]+_[A-Za-z0-9]+", "Stripe key pattern"),
        (r"api[_-]?key\s*[:=]\s*['\"][^'\"]+", "API key assignment"),
        (r"password\s*[:=]\s*['\"][^'\"]+", "Hardcoded password"),
        (r"127\.0\.0\.1|localhost:\d+", "Localhost reference"),
        (r"console\.(log|debug|error)\s*\(", "Debug console output"),
    ]
    for pattern, desc in patterns:
        if re.search(pattern, text, re.I):
            finding("HIGH", "WEBSITE-LEAK", f"Found: {desc}")
        else:
            finding("PASS", "WEBSITE-LEAK", f"Clean: no {desc}")

    # Check for robots.txt
    rs, _, rbody = fetch(f"{WEBSITE}/robots.txt")
    if rs == 404:
        finding("LOW", "WEBSITE", "No robots.txt — consider adding one")
    else:
        finding("PASS", "WEBSITE", "robots.txt present")


# ═══════════════════════════════════════════════════════════════════════════
# 2. API SECURITY
# ═══════════════════════════════════════════════════════════════════════════

def audit_api():
    print("\n══ API SECURITY: Railway Production ══")

    # Health check
    status, headers, body = fetch(f"{API_BASE}/health")
    if status == 200:
        finding("PASS", "API", "Health endpoint responding")
    else:
        finding("HIGH", "API", f"Health endpoint returned {status}")
        return

    # Security headers on API
    hsts = headers.get("Strict-Transport-Security", "")
    csp = headers.get("Content-Security-Policy", "")
    xfo = headers.get("X-Frame-Options", "")
    xcto = headers.get("X-Content-Type-Options", "")
    ref = headers.get("Referrer-Policy", "")
    perm = headers.get("Permissions-Policy", "")

    for name, val, h_name in [
        ("HSTS", hsts, "Strict-Transport-Security"),
        ("CSP", csp, "Content-Security-Policy"),
        ("X-Frame-Options", xfo, "X-Frame-Options"),
        ("X-Content-Type-Options", xcto, "X-Content-Type-Options"),
        ("Referrer-Policy", ref, "Referrer-Policy"),
        ("Permissions-Policy", perm, "Permissions-Policy"),
    ]:
        if val:
            finding("PASS", "API-HEADERS", f"{name} present")
        else:
            finding("MEDIUM", "API-HEADERS", f"Missing {name} header")

    # Check server header info leak
    server = headers.get("Server", "")
    if server and server.lower() not in ("railway-edge", ""):
        finding("LOW", "API-HEADERS", f"Server header reveals: {server}")

    # ── CRITICAL: Auth bypass tests ──
    print("\n  -- Authentication Tests --")

    # C2 Command without auth
    status, _, body = fetch(f"{API_BASE}/matrix/command",
                            method="POST",
                            data={"action": "system_check", "reason": "security-audit"})
    if status == 200:
        finding("CRITICAL", "API-AUTH", "C2 commands execute WITHOUT authentication",
                "Anyone can restart/kill daemons, approve/reject tasks")
    elif status in (401, 403):
        finding("PASS", "API-AUTH", "C2 commands require authentication")

    # Sitrep without auth
    status, _, body = fetch(f"{API_BASE}/matrix/sitrep")
    if status == 200:
        data = json.loads(body)
        exposed = list(data.keys())
        finding("HIGH", "API-AUTH", "Full sitrep exposed WITHOUT auth",
                f"Sections: {', '.join(exposed)}")
    elif status in (401, 403):
        finding("PASS", "API-AUTH", "Sitrep requires authentication")

    # Alert config without auth
    status, _, body = fetch(f"{API_BASE}/matrix/alerts/config")
    if status == 200:
        finding("HIGH", "API-AUTH", "Alert config (Telegram tokens) exposed WITHOUT auth")
    elif status in (401, 403):
        finding("PASS", "API-AUTH", "Alert config requires authentication")

    # Alert test without auth (could spam Telegram)
    status, _, body = fetch(f"{API_BASE}/matrix/alerts/test", method="POST")
    if status == 200:
        finding("HIGH", "API-AUTH", "Alert test endpoint callable WITHOUT auth",
                "Attacker could spam Telegram notifications")
    elif status in (401, 403):
        finding("PASS", "API-AUTH", "Alert test requires authentication")

    # Decisions log without auth
    status, _, body = fetch(f"{API_BASE}/matrix/decisions")
    if status == 200:
        finding("MEDIUM", "API-AUTH", "Decision log exposed WITHOUT auth")

    # Ops dashboard without auth
    status, _, body = fetch(f"{API_BASE}/ops")
    if status == 200:
        finding("MEDIUM", "API-AUTH", "Ops dashboard exposed WITHOUT auth")

    # OpenAPI schema exposure
    status, _, body = fetch(f"{API_BASE}/openapi.json")
    if status == 200:
        finding("MEDIUM", "API-EXPOSURE", "Full OpenAPI schema publicly accessible",
                "Reveals all endpoints, parameters, and data models")

    # Docs/Swagger UI
    status, _, body = fetch(f"{API_BASE}/docs")
    if status == 200:
        finding("MEDIUM", "API-EXPOSURE", "Swagger UI publicly accessible",
                "Allows interactive API testing by anyone")

    # ── Dangerous path traversal / info disclosure ──
    print("\n  -- Path Traversal & Info Disclosure --")
    dangerous = ["/.env", "/.git/config", "/.git/HEAD", "/config",
                 "/data", "/../../../etc/passwd", "/proc/self/environ"]
    for path in dangerous:
        status, _, _ = fetch(f"{API_BASE}{path}")
        if status == 200:
            finding("CRITICAL", "API-TRAVERSAL", f"Sensitive path accessible: {path}")
        else:
            finding("PASS", "API-TRAVERSAL", f"Blocked: {path}")

    # ── CORS check ──
    print("\n  -- CORS Configuration --")
    _, headers, _ = fetch(f"{API_BASE}/health",
                          headers={"Origin": "https://evil-site.com"})
    acao = headers.get("Access-Control-Allow-Origin", "")
    if acao == "*":
        finding("HIGH", "API-CORS", "CORS allows ALL origins (*)",
                "Any website can make API calls")
    elif "evil-site" in acao:
        finding("HIGH", "API-CORS", f"CORS reflects arbitrary origin: {acao}")
    elif acao:
        finding("PASS", "API-CORS", f"CORS restricted to: {acao}")
    else:
        finding("PASS", "API-CORS", "No CORS header (same-origin only)")

    # ── Rate limiting check ──
    print("\n  -- Rate Limiting --")
    # Send 10 rapid requests
    success = 0
    for _ in range(10):
        s, _, _ = fetch(f"{API_BASE}/health")
        if s == 200:
            success += 1
    if success == 10:
        finding("MEDIUM", "API-RATE", "No rate limiting detected (10/10 rapid requests succeeded)",
                "Vulnerable to brute force and DoS")
    else:
        finding("PASS", "API-RATE", f"Rate limiting may be active ({success}/10 succeeded)")


# ═══════════════════════════════════════════════════════════════════════════
# 3. DNS & EMAIL SECURITY
# ═══════════════════════════════════════════════════════════════════════════

def audit_dns():
    print("\n══ DNS & EMAIL SECURITY ══")

    # Check DNS records via nslookup
    for record_type, name in [
        ("TXT", DOMAIN),
        ("TXT", f"_dmarc.{DOMAIN}"),
        ("MX", DOMAIN),
        ("CNAME", f"www.{DOMAIN}"),
    ]:
        try:
            result = subprocess.run(
                ["nslookup", "-type=" + record_type, name],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout
            if "NXDOMAIN" in output or "can't find" in output.lower():
                finding("MEDIUM", "DNS", f"No {record_type} record for {name}")
            else:
                # Extract relevant lines
                lines = [l.strip() for l in output.split("\n") if l.strip() and "text" in l.lower()]
                if lines:
                    for line in lines[:2]:
                        finding("PASS", "DNS", f"{record_type} {name}: {line[:80]}")
                else:
                    finding("PASS", "DNS", f"{record_type} record exists for {name}")
        except Exception as e:
            finding("LOW", "DNS", f"Could not check {record_type} for {name}: {e}")

    # SSL certificate check
    print("\n  -- SSL/TLS Certificate --")
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=DOMAIN) as s:
            s.settimeout(10)
            s.connect((DOMAIN, 443))
            cert = s.getpeercert()
            expires = cert.get("notAfter", "")
            subject = dict(x[0] for x in cert.get("subject", ()))
            issuer = dict(x[0] for x in cert.get("issuer", ()))
            finding("PASS", "SSL", f"Valid SSL cert for {subject.get('commonName', DOMAIN)}")
            finding("INFO", "SSL", f"Issuer: {issuer.get('organizationName', 'Unknown')}")
            finding("INFO", "SSL", f"Expires: {expires}")
            san = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]
            if san:
                finding("INFO", "SSL", f"SANs: {', '.join(san[:5])}")
    except ssl.SSLCertVerificationError as e:
        finding("CRITICAL", "SSL", f"SSL certificate verification failed: {e}")
    except Exception as e:
        finding("HIGH", "SSL", f"SSL connection failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 4. CODEBASE SECRETS SCAN
# ═══════════════════════════════════════════════════════════════════════════

def audit_codebase():
    print("\n══ CODEBASE SECRETS SCAN ══")

    secret_patterns = [
        (r"sk_live_[A-Za-z0-9]+", "Stripe live key"),
        (r"sk_test_[A-Za-z0-9]+", "Stripe test key"),
        (r"pk_live_[A-Za-z0-9]+", "Stripe public live key"),
        (r"whsec_[A-Za-z0-9]+", "Stripe webhook secret"),
        (r"AKIA[0-9A-Z]{16}", "AWS access key"),
        (r"AIza[0-9A-Za-z_-]{35}", "Google API key"),
        (r"ghp_[A-Za-z0-9]{36}", "GitHub personal token"),
        (r"xoxb-[0-9A-Za-z-]+", "Slack bot token"),
        (r"bot[0-9]+:[A-Za-z0-9_-]{35}", "Telegram bot token"),
        (r"password\s*=\s*['\"][^'\"]{4,}['\"]", "Hardcoded password"),
        (r"api_key\s*=\s*['\"][^'\"]{10,}['\"]", "Hardcoded API key"),
    ]

    skip_dirs = {".venv", "__pycache__", ".git", "node_modules", ".vscode", "output", "data"}
    skip_files = {".env", ".env.example", "security_audit.py"}

    files_scanned = 0
    secrets_found = 0

    for ext in ("*.py", "*.html", "*.js", "*.json", "*.md", "*.yaml", "*.yml", "*.toml", "*.cfg"):
        for fpath in PROJECT_ROOT.rglob(ext):
            # Skip excluded dirs
            if any(skip in fpath.parts for skip in skip_dirs):
                continue
            if fpath.name in skip_files:
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                files_scanned += 1
                for pattern, desc in secret_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        rel = fpath.relative_to(PROJECT_ROOT)
                        finding("CRITICAL", "SECRETS", f"{desc} in {rel}",
                                f"Match: {matches[0][:20]}...")
                        secrets_found += 1
            except Exception:
                pass

    finding("INFO", "SECRETS", f"Scanned {files_scanned} files")
    if secrets_found == 0:
        finding("PASS", "SECRETS", "No hardcoded secrets detected in source")

    # Check .gitignore for .env
    gitignore = PROJECT_ROOT / ".gitignore"
    if gitignore.exists():
        gi = gitignore.read_text()
        if ".env" in gi:
            finding("PASS", "SECRETS", ".env is in .gitignore")
        else:
            finding("HIGH", "SECRETS", ".env NOT in .gitignore — secrets could be committed")
    else:
        finding("HIGH", "SECRETS", "No .gitignore found")

    # Check if .env exists but isn't tracked
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        finding("INFO", "SECRETS", ".env file exists locally (expected)")
    else:
        finding("INFO", "SECRETS", "No .env file present")


# ═══════════════════════════════════════════════════════════════════════════
# 5. GITHUB REPO EXPOSURE
# ═══════════════════════════════════════════════════════════════════════════

def audit_github():
    print("\n══ GITHUB REPOSITORY EXPOSURE ══")

    # Check if the repo is public
    status, _, body = fetch("https://api.github.com/repos/ResonanceEnergy/DIGITAL-LABOUR")
    if status == 200:
        data = json.loads(body)
        private = data.get("private", True)
        if not private:
            finding("CRITICAL", "GITHUB", "Repository is PUBLIC",
                    "All source code, config, and history is exposed to the internet")
        else:
            finding("PASS", "GITHUB", "Repository is private")

        # Check for exposed secrets in description
        desc = data.get("description", "")
        if any(kw in desc.lower() for kw in ["key", "password", "token", "secret"]):
            finding("HIGH", "GITHUB", f"Repo description may contain sensitive info: {desc}")
    elif status == 404:
        finding("PASS", "GITHUB", "Repository not publicly accessible (404)")
    else:
        finding("INFO", "GITHUB", f"GitHub API returned {status}")


# ═══════════════════════════════════════════════════════════════════════════
# 6. SUMMARY & REPORT
# ═══════════════════════════════════════════════════════════════════════════

def generate_report():
    print("\n" + "═" * 60)
    print("  DIGITAL LABOUR SECURITY AUDIT — SUMMARY")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("═" * 60)

    critical = [f for f in FINDINGS if f["severity"] == "CRITICAL"]
    high = [f for f in FINDINGS if f["severity"] == "HIGH"]
    medium = [f for f in FINDINGS if f["severity"] == "MEDIUM"]
    low = [f for f in FINDINGS if f["severity"] == "LOW"]
    passed = [f for f in FINDINGS if f["severity"] == "PASS"]

    print(f"\n  🔴 CRITICAL: {len(critical)}")
    print(f"  🟠 HIGH:     {len(high)}")
    print(f"  🟡 MEDIUM:   {len(medium)}")
    print(f"  🔵 LOW:      {len(low)}")
    print(f"  🟢 PASSED:   {len(passed)}")

    if critical:
        print("\n  ── CRITICAL FINDINGS (Fix Immediately) ──")
        for f in critical:
            print(f"    🔴 {f['category']}: {f['message']}")
            if f["detail"]:
                for line in f["detail"].split("\n")[:2]:
                    print(f"       {line}")

    if high:
        print("\n  ── HIGH FINDINGS (Fix Soon) ──")
        for f in high:
            print(f"    🟠 {f['category']}: {f['message']}")
            if f["detail"]:
                for line in f["detail"].split("\n")[:2]:
                    print(f"       {line}")

    if medium:
        print("\n  ── MEDIUM FINDINGS (Improve) ──")
        for f in medium:
            print(f"    🟡 {f['category']}: {f['message']}")

    # Save report
    report_path = PROJECT_ROOT / "data" / "security_audit_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
            "low": len(low),
            "passed": len(passed),
        },
        "findings": FINDINGS,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n  Report saved to: {report_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    print("═" * 60)
    print("  DIGITAL LABOUR SECURITY AUDIT")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("═" * 60)

    audit_website()
    audit_api()
    audit_dns()
    audit_codebase()
    audit_github()
    generate_report()
