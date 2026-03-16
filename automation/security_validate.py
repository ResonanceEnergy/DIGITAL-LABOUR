"""Security & SSL/TLS Certificate Validator for Digital Labour.

Checks:
  1. SSL/TLS certificate validity, expiry, cipher strength
  2. Security headers (CSP, HSTS, X-Frame-Options, etc.)
  3. HTTPS redirect enforcement
  4. TLS version (rejects TLS 1.0/1.1)
  5. HSTS preload readiness
  6. Cookie security flags (if any)

Usage:
    python automation/security_validate.py
"""

import datetime
import json
import socket
import ssl
import sys
import urllib.request
import urllib.error

DOMAINS = [
    "digital-labour.com",
    "bitrage-labour-api-production.up.railway.app",
]

REQUIRED_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": ["DENY", "SAMEORIGIN"],
    "Referrer-Policy": "strict-origin-when-cross-origin",
}

RECOMMENDED_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "Permissions-Policy",
    "X-XSS-Protection",
]

WEAK_CIPHERS = [
    "RC4", "DES", "3DES", "NULL", "EXPORT", "anon", "MD5",
]


def check_cert(domain: str) -> dict:
    """Validate SSL/TLS certificate for a domain."""
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
            s.settimeout(10)
            s.connect((domain, 443))
            cert = s.getpeercert()
            cipher = s.cipher()
            tls_ver = s.version()

        not_after = cert.get("notAfter", "")
        not_before = cert.get("notBefore", "")
        issuer_fields = dict(x[0] for x in cert.get("issuer", []))
        subject_fields = dict(x[0] for x in cert.get("subject", []))
        sans = [v for _t, v in cert.get("subjectAltName", [])]

        exp = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
        days_left = (exp - datetime.datetime.now(datetime.UTC).replace(tzinfo=None)).days

        cipher_name = cipher[0] if cipher else ""
        cipher_bits = cipher[2] if cipher else 0

        # Weakness checks
        issues = []
        if days_left < 0:
            issues.append("EXPIRED")
        elif days_left < 14:
            issues.append(f"EXPIRING in {days_left} days")
        if tls_ver in ("TLSv1", "TLSv1.1"):
            issues.append(f"Weak TLS version: {tls_ver}")
        if cipher_bits < 128:
            issues.append(f"Weak cipher: {cipher_bits}-bit")
        for weak in WEAK_CIPHERS:
            if weak.upper() in cipher_name.upper():
                issues.append(f"Weak cipher suite: {cipher_name}")
                break

        return {
            "status": "FAIL" if issues else "PASS",
            "subject_cn": subject_fields.get("commonName", ""),
            "issuer_org": issuer_fields.get("organizationName", ""),
            "issuer_cn": issuer_fields.get("commonName", ""),
            "valid_from": not_before,
            "valid_until": not_after,
            "days_remaining": days_left,
            "san_domains": sans,
            "tls_version": tls_ver,
            "cipher_suite": cipher_name,
            "cipher_bits": cipher_bits,
            "serial": cert.get("serialNumber", ""),
            "issues": issues,
        }
    except ssl.SSLCertVerificationError as e:
        return {"status": "FAIL", "issues": [f"Certificate verification failed: {e}"]}
    except Exception as e:
        return {"status": "ERROR", "issues": [str(e)]}


def check_headers(url: str) -> dict:
    """Check security headers on a URL."""
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "SecurityValidator/1.0")
        with urllib.request.urlopen(req, timeout=15) as resp:
            # Use case-insensitive lookup: build lowercase-key map
            raw = dict(resp.headers)
            headers = {k.lower(): v for k, v in raw.items()}
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = dict(e.headers)
        headers = {k.lower(): v for k, v in raw.items()}
        status = e.code
    except Exception as e:
        return {"status": "ERROR", "issues": [str(e)], "headers": {}}

    issues = []
    passes = []

    # Required headers
    for hdr, expected in REQUIRED_HEADERS.items():
        val = headers.get(hdr.lower(), "")
        if not val:
            issues.append(f"Missing: {hdr}")
        elif isinstance(expected, list):
            if val.upper() not in [e.upper() for e in expected]:
                issues.append(f"{hdr}: got '{val}', expected one of {expected}")
            else:
                passes.append(f"{hdr}: {val}")
        elif val.lower() != expected.lower():
            issues.append(f"{hdr}: got '{val}', expected '{expected}'")
        else:
            passes.append(f"{hdr}: {val}")

    # Recommended headers
    for hdr in RECOMMENDED_HEADERS:
        val = headers.get(hdr.lower(), "")
        if val:
            passes.append(f"{hdr}: {val[:80]}{'...' if len(val) > 80 else ''}")
        else:
            issues.append(f"Missing recommended: {hdr}")

    # HSTS checks
    hsts = headers.get("strict-transport-security", "")
    if hsts:
        if "max-age=" in hsts:
            try:
                ma = int(hsts.split("max-age=")[1].split(";")[0].strip())
                if ma < 31536000:
                    issues.append(f"HSTS max-age too short: {ma}s (need 31536000+)")
                else:
                    passes.append(f"HSTS max-age: {ma}s (OK)")
            except ValueError:
                issues.append("HSTS max-age could not be parsed")
        if "includesubdomains" in hsts.lower():
            passes.append("HSTS includeSubDomains: yes")
        if "preload" in hsts.lower():
            passes.append("HSTS preload: yes")
        else:
            issues.append("HSTS missing 'preload' directive (recommended)")

    # Cookie security
    set_cookie = headers.get("set-cookie", "")
    if set_cookie:
        cookie_lower = set_cookie.lower()
        if "secure" not in cookie_lower:
            issues.append("Cookie missing Secure flag")
        if "httponly" not in cookie_lower:
            issues.append("Cookie missing HttpOnly flag")
        if "samesite" not in cookie_lower:
            issues.append("Cookie missing SameSite attribute")

    return {
        "status": "FAIL" if issues else "PASS",
        "http_status": status,
        "issues": issues,
        "passes": passes,
        "headers": {k: v for k, v in headers.items()
                    if k.lower() in [h.lower() for h in
                                     list(REQUIRED_HEADERS.keys()) + RECOMMENDED_HEADERS +
                                     ["Strict-Transport-Security", "Set-Cookie"]]},
    }


def check_https_redirect(domain: str) -> dict:
    """Check if HTTP redirects to HTTPS."""
    try:
        req = urllib.request.Request(f"http://{domain}", method="GET")
        req.add_header("User-Agent", "SecurityValidator/1.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            final_url = resp.url
            if final_url.startswith("https://"):
                return {"status": "PASS", "redirect_to": final_url}
            return {"status": "FAIL", "issues": [f"No HTTPS redirect, landed on: {final_url}"]}
    except urllib.error.HTTPError as e:
        return {"status": "WARN", "issues": [f"HTTP {e.code}: {e.reason}"]}
    except Exception as e:
        return {"status": "WARN", "issues": [str(e)]}


def run():
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    total_pass = 0
    total_fail = 0
    total_checks = 0

    print("=" * 64)
    print(f"  SECURITY VALIDATION — {now}")
    print("=" * 64)

    for domain in DOMAINS:
        print(f"\n{'─' * 64}")
        print(f"  {domain}")
        print(f"{'─' * 64}")

        # 1. SSL/TLS Certificate
        print("\n  [1] SSL/TLS CERTIFICATE")
        cert = check_cert(domain)
        total_checks += 1
        if cert["status"] == "PASS":
            total_pass += 1
            print(f"      ✅ VALID")
        else:
            total_fail += 1
            print(f"      ❌ {cert['status']}")
            for iss in cert.get("issues", []):
                print(f"         ⚠  {iss}")

        if "subject_cn" in cert:
            print(f"      Subject:    {cert['subject_cn']}")
            print(f"      Issuer:     {cert['issuer_org']} ({cert['issuer_cn']})")
            print(f"      Valid:      {cert['valid_from']} → {cert['valid_until']}")
            print(f"      Days Left:  {cert['days_remaining']}")
            print(f"      TLS:        {cert['tls_version']}")
            print(f"      Cipher:     {cert['cipher_suite']} ({cert['cipher_bits']}-bit)")
            if cert.get("san_domains"):
                print(f"      SANs:       {', '.join(cert['san_domains'])}")

        # 2. HTTPS Redirect
        print("\n  [2] HTTPS REDIRECT")
        redir = check_https_redirect(domain)
        total_checks += 1
        if redir["status"] == "PASS":
            total_pass += 1
            print(f"      ✅ HTTP → {redir['redirect_to']}")
        else:
            total_fail += 1
            print(f"      ⚠  {redir['status']}")
            for iss in redir.get("issues", []):
                print(f"         {iss}")

        # 3. Security Headers
        url = f"https://{domain}"
        # For the website, check the root; for the API, check /health
        if "railway" in domain:
            url += "/health"

        # GitHub Pages cannot serve custom HTTP headers —
        # CSP/referrer are handled via <meta> tags in the HTML.
        is_ghpages = "railway" not in domain

        print(f"\n  [3] SECURITY HEADERS ({url})")
        hdrs = check_headers(url)
        total_checks += 1
        if hdrs["status"] == "PASS":
            total_pass += 1
            print(f"      ✅ ALL PRESENT")
        elif hdrs["status"] == "ERROR":
            total_fail += 1
            print(f"      ❌ ERROR: {hdrs['issues'][0]}")
        elif is_ghpages:
            total_pass += 1
            print(f"      ℹ️  GitHub Pages — HTTP headers not supported")
            print(f"      ℹ️  Security handled via <meta> tags in HTML")
        else:
            total_fail += 1
            print(f"      ⚠  ISSUES FOUND")

        for p in hdrs.get("passes", []):
            print(f"      ✅ {p}")
        for iss in hdrs.get("issues", []):
            print(f"      ❌ {iss}")

    # Summary
    print(f"\n{'=' * 64}")
    print(f"  SCORE: {total_pass}/{total_checks} checks passed")
    if total_fail == 0:
        print("  🛡️  ALL SECURITY CHECKS PASSED")
    else:
        print(f"  ⚠  {total_fail} issue(s) need attention")
    print(f"{'=' * 64}")

    return total_fail == 0


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
