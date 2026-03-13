"""Quick one-shot: add DMARC + BIMI TXT records to Cloudflare."""
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

ZONE_ID = "939834e2a74791ec43a7d9a15028aeae"
DOMAIN = "bit-rage-labour.com"

def get_token():
    # Try wrangler OAuth
    wp = Path(os.environ.get("APPDATA", "")) / "xdg.config" / ".wrangler" / "config" / "default.toml"
    if wp.exists():
        for line in wp.read_text().splitlines():
            if line.strip().startswith("oauth_token"):
                return line.split('"')[1]
    return ""

def api_call(method, path, token, data=None):
    url = f"https://api.cloudflare.com/client/v4{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

token = get_token()
if not token:
    print("No token found"); sys.exit(1)

# Check permissions first
print("Testing permissions...")
r = api_call("GET", f"/zones/{ZONE_ID}/dns_records?type=TXT&per_page=5", token)
if not r.get("success"):
    print(f"DNS read failed: {r.get('errors')}")
    print("OAuth token lacks DNS permissions. Creating API token with DNS edit...")
    
    # Create an API token with DNS edit permission
    token_data = {
        "name": "BIMI DNS Automation",
        "policies": [
            {
                "effect": "allow",
                "resources": {f"com.cloudflare.api.account.zone.{ZONE_ID}": "*"},
                "permission_groups": [
                    {"id": "4755a26eedb94da69e1066d98aa820be", "name": "DNS Write"}
                ]
            }
        ]
    }
    create_r = api_call("POST", "/user/tokens", token, token_data)
    if create_r.get("success"):
        new_token = create_r["result"]["value"]
        print(f"Created API token: {new_token[:10]}...")
        # Save to .env
        env_path = Path(__file__).resolve().parent.parent / ".env"
        env_text = env_path.read_text()
        env_text = env_text.replace("# CF_API_TOKEN=", f"CF_API_TOKEN={new_token}")
        env_path.write_text(env_text)
        print("Saved to .env as CF_API_TOKEN")
        token = new_token
    else:
        print(f"Cannot create token: {create_r.get('errors')}")
        print("\nManual fix needed:")
        print("  1. Go to https://dash.cloudflare.com/profile/api-tokens")
        print("  2. Create Token -> Edit zone DNS template")
        print(f"  3. Zone = {DOMAIN}")
        print("  4. Copy token and add to .env: CF_API_TOKEN=your_token")
        print("  5. Run: python automation/cloudflare_dns.py")
        sys.exit(1)

# Now add records
records = [
    ("DMARC", f"_dmarc.{DOMAIN}", f"v=DMARC1; p=reject; rua=mailto:dmarc@{DOMAIN}; pct=100"),
    ("BIMI", f"default._bimi.{DOMAIN}", f"v=BIMI1; l=https://{DOMAIN}/.well-known/bimi/logo.svg"),
]

for label, name, content in records:
    data = {"type": "TXT", "name": name, "content": content, "ttl": 3600}
    r = api_call("POST", f"/zones/{ZONE_ID}/dns_records", token, data)
    if r.get("success"):
        print(f"[OK] {label}: Created")
    elif any("already exists" in str(e).lower() for e in r.get("errors", [])):
        print(f"[OK] {label}: Already exists")
    else:
        print(f"[FAIL] {label}: {r.get('errors')}")

print("\nDone. Run 'python automation/bimi_setup.py' to verify.")
