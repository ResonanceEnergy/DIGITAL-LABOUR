"""
Fix www.bit-rage-labour.com — Cloudflare redirect to bit-rage-labour.com
========================================================================
bit-rage-labour.com is managed in Cloudflare (verified via NS records).
This script:
  1. Finds the bit-rage-labour.com zone ID
  2. Adds CNAME: www → resonanceenergy.github.io (proxied)
  3. Adds Cloudflare Redirect Rule: both apex + www → https://bit-rage-labour.com

Requirements:
    Add to .env:  CF_API_TOKEN=your_token
    Get token at: https://dash.cloudflare.com/profile/api-tokens
      → Create Token → Edit zone DNS template → Zone: bit-rage-labour.com
      → ALSO add "Zone → Zone Settings → Read" + "Zone → Page Rules → Edit"
      → Or use "Create Custom Token" with Zone:Read + DNS:Edit + Page Rules:Edit

Usage:
    python automation/fix_bitragelabour_dns.py            # Apply fix
    python automation/fix_bitragelabour_dns.py --verify   # Check current state
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

DOMAIN = "bit-rage-labour.com"
REDIRECT_TARGET = "https://bit-rage-labour.com"
GITHUB_PAGES_CNAME = "resonanceenergy.github.io"

API = "https://api.cloudflare.com/client/v4"


def load_token() -> str:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("CF_API_TOKEN=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    return os.environ.get("CF_API_TOKEN", "")


def cf(method: str, path: str, token: str, data=None):
    url = f"{API}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def get_zone_id(token: str) -> str:
    r = cf("GET", f"/zones?name={DOMAIN}", token)
    if not r.get("success") or not r["result"]:
        print(f"ERROR: Zone not found for {DOMAIN}: {r.get('errors')}")
        sys.exit(1)
    zid = r["result"][0]["id"]
    print(f"Zone ID for {DOMAIN}: {zid}")
    return zid


def ensure_www_cname(zone_id: str, token: str):
    """Add CNAME www → resonanceenergy.github.io (proxied via Cloudflare so redirect fires)."""
    existing = cf("GET", f"/zones/{zone_id}/dns_records?type=CNAME&name=www.{DOMAIN}", token)
    if existing.get("result"):
        rec = existing["result"][0]
        print(f"  www CNAME already exists → {rec['content']} (proxied={rec['proxied']})")
        # Update to point to github pages proxied
        if rec["content"] != GITHUB_PAGES_CNAME or not rec["proxied"]:
            r = cf("PATCH", f"/zones/{zone_id}/dns_records/{rec['id']}", token,
                   {"content": GITHUB_PAGES_CNAME, "proxied": True})
            print(f"  Updated www CNAME: {r.get('success')}")
        return

    r = cf("POST", f"/zones/{zone_id}/dns_records", token, {
        "type": "CNAME",
        "name": f"www.{DOMAIN}",
        "content": GITHUB_PAGES_CNAME,
        "proxied": True,
        "ttl": 1,
        "comment": "Redirect via CF → bit-rage-labour.com",
    })
    if r.get("success"):
        print(f"  ✓ Added CNAME www.{DOMAIN} → {GITHUB_PAGES_CNAME} (proxied)")
    else:
        print(f"  ✗ CNAME failed: {r.get('errors')}")


def ensure_apex_proxied(zone_id: str, token: str):
    """Make sure apex A records are proxied so Cloudflare redirect rule fires on root domain."""
    existing = cf("GET", f"/zones/{zone_id}/dns_records?type=A&name={DOMAIN}", token)
    if not existing.get("result"):
        print(f"  No A records found for {DOMAIN}")
        return
    for rec in existing["result"]:
        if not rec["proxied"]:
            r = cf("PATCH", f"/zones/{zone_id}/dns_records/{rec['id']}", token, {"proxied": True})
            print(f"  ✓ Enabled proxy on A record {rec['content']}: {r.get('success')}")
        else:
            print(f"  A record {rec['content']} already proxied ✓")


def add_redirect_rules(zone_id: str, token: str):
    """Add Cloudflare redirect rules for apex + www → bit-rage-labour.com."""
    # Use the Rulesets API (modern approach, replaces Page Rules)
    r = cf("GET", f"/zones/{zone_id}/rulesets?phase=http_request_dynamic_redirect", token)
    if r.get("success") and r["result"]:
        ruleset_id = r["result"][0]["id"]
        # Check existing rules
        rs = cf("GET", f"/zones/{zone_id}/rulesets/{ruleset_id}", token)
        existing_rules = rs.get("result", {}).get("rules", [])
        for rule in existing_rules:
            if "bit-rage-labour" in str(rule.get("expression", "")):
                print(f"  Redirect ruleset already has bit-rage-labour rule ✓")
                return

        # Add rules to existing ruleset
        rules = existing_rules + [_redirect_rule()]
        r2 = cf("PUT", f"/zones/{zone_id}/rulesets/{ruleset_id}", token, {"rules": rules})
        if r2.get("success"):
            print(f"  ✓ Added redirect rule to existing ruleset")
        else:
            print(f"  ✗ Ruleset update failed: {r2.get('errors')}")
            _fallback_page_rule(zone_id, token)
        return

    # Create new redirect ruleset
    r2 = cf("POST", f"/zones/{zone_id}/rulesets", token, {
        "name": "bit-rage-labour redirect",
        "kind": "zone",
        "phase": "http_request_dynamic_redirect",
        "rules": [_redirect_rule()],
    })
    if r2.get("success"):
        print(f"  ✓ Created redirect ruleset")
    else:
        print(f"  ✗ Ruleset creation failed: {r2.get('errors')}")
        _fallback_page_rule(zone_id, token)


def _redirect_rule() -> dict:
    return {
        "expression": f'(http.host eq "{DOMAIN}" or http.host eq "www.{DOMAIN}")',
        "action": "redirect",
        "action_parameters": {
            "from_value": {
                "status_code": 301,
                "target_url": {"value": REDIRECT_TARGET},
                "preserve_query_string": False,
            }
        },
        "description": f"Redirect {DOMAIN} → {REDIRECT_TARGET}",
        "enabled": True,
    }


def _fallback_page_rule(zone_id: str, token: str):
    """Fallback: use classic Page Rules if Rulesets API fails."""
    print("  Trying classic Page Rules as fallback...")
    for pattern in [f"{DOMAIN}/*", f"www.{DOMAIN}/*"]:
        r = cf("POST", f"/zones/{zone_id}/pagerules", token, {
            "targets": [{"target": "url", "constraint": {"operator": "matches", "value": f"http*://{pattern}"}}],
            "actions": [{"id": "forwarding_url", "value": {"url": f"{REDIRECT_TARGET}/$1", "status_code": 301}}],
            "status": "active",
            "priority": 1,
        })
        if r.get("success"):
            print(f"  ✓ Page Rule added for {pattern}")
        else:
            print(f"  ✗ Page Rule failed for {pattern}: {r.get('errors')}")


def verify(zone_id: str, token: str):
    print(f"\n=== DNS Records for {DOMAIN} ===")
    r = cf("GET", f"/zones/{zone_id}/dns_records?per_page=50", token)
    for rec in r.get("result", []):
        print(f"  {rec['type']:6} {rec['name']:40} → {rec['content']} (proxied={rec.get('proxied')})")
    print()
    print("=== Redirect Rulesets ===")
    r2 = cf("GET", f"/zones/{zone_id}/rulesets?phase=http_request_dynamic_redirect", token)
    for rs in r2.get("result", []):
        print(f"  Ruleset: {rs['name']} ({rs['id']})")
        rs_detail = cf("GET", f"/zones/{zone_id}/rulesets/{rs['id']}", token)
        for rule in rs_detail.get("result", {}).get("rules", []):
            print(f"    Rule: {rule.get('description')} — enabled={rule.get('enabled')}")
    print()
    print("=== Page Rules ===")
    r3 = cf("GET", f"/zones/{zone_id}/pagerules?status=active", token)
    for pr in r3.get("result", []):
        print(f"  {pr['targets'][0]['constraint']['value']} → {pr['actions'][0]['value']}")


def main():
    token = load_token()
    if not token:
        print("ERROR: CF_API_TOKEN not found in .env")
        print()
        print("To fix manually in the Cloudflare dashboard:")
        print(f"  1. Go to dash.cloudflare.com → {DOMAIN} → DNS")
        print(f"  2. Add CNAME: www → {GITHUB_PAGES_CNAME} (Proxied: ON)")
        print(f"  3. Enable Proxy (orange cloud) on the A records for {DOMAIN}")
        print(f"  4. Go to Rules → Redirect Rules → Create Rule")
        print(f"     Name: Redirect to bit-rage-labour.com")
        print(f"     When: Hostname equals {DOMAIN} OR www.{DOMAIN}")
        print(f"     Then: Static redirect → {REDIRECT_TARGET} (301)")
        print()
        print("To automate:")
        print("  1. dash.cloudflare.com → Profile → API Tokens → Create Token")
        print("     → Edit zone DNS template → Zone = bit-rage-labour.com")
        print("     → Add Zone:Read permission too")
        print(f"  2. Add to .env: CF_API_TOKEN=<your_token>")
        print(f"  3. Run: python automation/fix_bitragelabour_dns.py")
        sys.exit(1)

    mode = "--verify" in sys.argv
    zone_id = get_zone_id(token)

    if mode:
        verify(zone_id, token)
        return

    print(f"\nApplying fixes to {DOMAIN}...")
    print("\n1. Ensuring www CNAME exists (proxied)...")
    ensure_www_cname(zone_id, token)

    print("\n2. Ensuring apex A records are proxied...")
    ensure_apex_proxied(zone_id, token)

    print("\n3. Setting up 301 redirect rules...")
    add_redirect_rules(zone_id, token)

    print("\n✓ Done. Verifying...")
    verify(zone_id, token)
    print(f"\nTest in 1-2 min: curl -I https://www.bit-rage-labour.com")
    print(f"Expected: 301 Location: {REDIRECT_TARGET}")


if __name__ == "__main__":
    main()
