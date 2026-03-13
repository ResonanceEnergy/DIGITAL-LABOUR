"""
Cloudflare DNS — DMARC & BIMI record automation
=================================================
Adds the missing DNS TXT records for bit-rage-labour.com.

Requires CF_API_TOKEN in .env  (Cloudflare → My Profile → API Tokens → Create Token
  → "Edit zone DNS" template → Zone = bit-rage-labour.com → Create)

Usage:
    python automation/cloudflare_dns.py              # Add DMARC + BIMI records
    python automation/cloudflare_dns.py --verify     # Verify records live
    python automation/cloudflare_dns.py --list       # List existing TXT records
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

DOMAIN = "bit-rage-labour.com"
DMARC_EMAIL = f"dmarc@{DOMAIN}"
BIMI_LOGO_URL = f"https://{DOMAIN}/.well-known/bimi/logo.svg"

API_BASE = "https://api.cloudflare.com/client/v4"

# Records to create
REQUIRED_RECORDS = [
    {
        "type": "TXT",
        "name": f"_dmarc.{DOMAIN}",
        "content": f"v=DMARC1; p=reject; rua=mailto:{DMARC_EMAIL}; pct=100",
        "label": "DMARC",
    },
    {
        "type": "TXT",
        "name": f"default._bimi.{DOMAIN}",
        "content": f"v=BIMI1; l={BIMI_LOGO_URL}",
        "label": "BIMI",
    },
]


def _load_token() -> str:
    """Load Cloudflare auth token. Checks (in order):
    1. CF_API_TOKEN in .env
    2. CF_API_TOKEN env var
    3. Wrangler OAuth token (from wrangler login)
    """
    # 1. .env file
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("CF_API_TOKEN=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val

    # 2. Environment variable
    token = os.environ.get("CF_API_TOKEN", "")
    if token:
        return token

    # 3. Wrangler OAuth token
    wrangler_paths = [
        Path(os.environ.get("APPDATA", "")) / "xdg.config" / ".wrangler" / "config" / "default.toml",
        Path.home() / ".wrangler" / "config" / "default.toml",
    ]
    for wp in wrangler_paths:
        if wp.exists():
            for line in wp.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("oauth_token"):
                    val = line.split('"')[1] if '"' in line else ""
                    if val:
                        print("  Using wrangler OAuth token")
                        return val

    print("ERROR: No Cloudflare token found.")
    print("  Option A: Run 'wrangler login' to authenticate via browser")
    print("  Option B: Add CF_API_TOKEN=your_token to .env")
    sys.exit(1)


def _api(method: str, path: str, token: str, data: dict | None = None, retries: int = 3) -> dict:
    """Make Cloudflare API request with retry on transient errors."""
    url = f"{API_BASE}{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    import time
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (502, 503, 504) and attempt < retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  API returned {e.code}, retrying in {wait}s... ({attempt + 1}/{retries})")
                time.sleep(wait)
                continue
            try:
                err = json.loads(e.read().decode("utf-8"))
            except Exception:
                err = {"errors": [{"message": f"HTTP {e.code}"}]}
            print(f"  API Error ({e.code}): {json.dumps(err.get('errors', []), indent=2)}")
            return {"success": False, "errors": err.get("errors", []), "result": None}
        except (TimeoutError, OSError) as e:
            if attempt < retries - 1:
                wait = 10 * (attempt + 1)
                print(f"  Timeout/connection error, retrying in {wait}s... ({attempt + 1}/{retries})")
                time.sleep(wait)
                continue
            print(f"  API unreachable after {retries} attempts: {e}")
            print("  Cloudflare API may be experiencing an outage.")
            print("  Check https://www.cloudflarestatus.com/ and retry later.")
            sys.exit(1)


def get_zone_id(token: str) -> str:
    """Find the zone ID for the domain."""
    resp = _api("GET", f"/zones?name={DOMAIN}", token)
    if not resp.get("success") or not resp.get("result"):
        print(f"ERROR: Could not find zone for {DOMAIN}")
        sys.exit(1)
    zone_id = resp["result"][0]["id"]
    print(f"  Zone ID: {zone_id}")
    return zone_id


def list_txt_records(token: str, zone_id: str) -> list:
    """List all TXT records for the zone."""
    resp = _api("GET", f"/zones/{zone_id}/dns_records?type=TXT&per_page=100", token)
    if not resp.get("success"):
        return []
    return resp.get("result", [])


def add_record(token: str, zone_id: str, record: dict) -> bool:
    """Add a DNS TXT record."""
    data = {
        "type": record["type"],
        "name": record["name"],
        "content": record["content"],
        "ttl": 3600,
    }
    resp = _api("POST", f"/zones/{zone_id}/dns_records", token, data)
    if resp.get("success"):
        rec_id = resp["result"]["id"]
        print(f"  [OK] {record['label']}: Created (ID: {rec_id})")
        return True
    errors = resp.get("errors", [])
    if any("already exists" in str(e).lower() for e in errors):
        print(f"  [OK] {record['label']}: Already exists")
        return True
    print(f"  [FAIL] {record['label']}: {errors}")
    return False


def run_add():
    """Add missing DMARC and BIMI records."""
    token = _load_token()
    print(f"\n  Cloudflare DNS — {DOMAIN}")
    print(f"  {'─' * 40}")

    zone_id = get_zone_id(token)
    existing = list_txt_records(token, zone_id)
    existing_names = {r["name"] for r in existing}

    added = 0
    for rec in REQUIRED_RECORDS:
        if rec["name"] in existing_names:
            # Check if content matches
            match = [r for r in existing if r["name"] == rec["name"]]
            if match and match[0]["content"] == rec["content"]:
                print(f"  [OK] {rec['label']}: Already correct")
                added += 1
                continue
            elif match:
                print(f"  [!!] {rec['label']}: Exists but content differs")
                print(f"       Current: {match[0]['content']}")
                print(f"       Wanted:  {rec['content']}")
                # Update existing record
                update_resp = _api(
                    "PUT",
                    f"/zones/{zone_id}/dns_records/{match[0]['id']}",
                    token,
                    {"type": rec["type"], "name": rec["name"], "content": rec["content"], "ttl": 3600},
                )
                if update_resp.get("success"):
                    print(f"  [OK] {rec['label']}: Updated")
                    added += 1
                continue
        if add_record(token, zone_id, rec):
            added += 1

    print(f"\n  Result: {added}/{len(REQUIRED_RECORDS)} records configured\n")


def run_list():
    """List all TXT records."""
    token = _load_token()
    print(f"\n  TXT Records for {DOMAIN}")
    print(f"  {'─' * 50}")
    zone_id = get_zone_id(token)
    records = list_txt_records(token, zone_id)
    if not records:
        print("  No TXT records found")
        return
    for r in records:
        print(f"  {r['name']:40s}  {r['content'][:60]}")
    print(f"\n  Total: {len(records)} TXT records\n")


def run_verify():
    """Verify DNS records are live via nslookup."""
    import subprocess
    print(f"\n  Verifying DNS for {DOMAIN}")
    print(f"  {'─' * 40}")

    checks = [
        ("DMARC", f"_dmarc.{DOMAIN}", "v=DMARC1"),
        ("BIMI", f"default._bimi.{DOMAIN}", "v=BIMI1"),
        ("SPF", DOMAIN, "v=spf1"),
    ]

    for label, name, prefix in checks:
        try:
            result = subprocess.run(
                ["nslookup", "-type=TXT", name],
                capture_output=True, text=True, timeout=10,
            )
            if prefix.lower() in result.stdout.lower():
                print(f"  [OK] {label:8s}  Live")
            else:
                print(f"  [XX] {label:8s}  Not found yet (DNS propagation can take up to 5 min)")
        except Exception:
            print(f"  [??] {label:8s}  Lookup failed")

    print()


if __name__ == "__main__":
    if "--verify" in sys.argv:
        run_verify()
    elif "--list" in sys.argv:
        run_list()
    else:
        run_add()
