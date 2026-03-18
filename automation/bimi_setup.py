"""
BIMI / DMARC / SPF / DKIM — Automated Setup & Verification
============================================================
Checks all email authentication prerequisites for bit-rage-labour.com,
generates the exact DNS records needed, and verifies they're live.

Usage:
    python automation/bimi_setup.py              # Full check + generate records
    python automation/bimi_setup.py --verify     # Verify DNS records are live
    python automation/bimi_setup.py --apply      # Print zone-file-ready records
"""
import subprocess
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

DOMAIN = "bit-rage-labour.com"
BIMI_LOGO_URL = f"https://{DOMAIN}/.well-known/bimi/logo.svg"
DMARC_EMAIL = f"dmarc@{DOMAIN}"
LOGO_LOCAL = Path(__file__).resolve().parent.parent / "site" / ".well-known" / "bimi" / "logo.svg"

# ── DNS Lookup (uses nslookup on Windows, dig on Linux) ──────────

def _dns_txt(name: str) -> list[str]:
    """Query TXT records for a given name. Returns list of TXT values."""
    try:
        result = subprocess.run(
            ["nslookup", "-type=TXT", name],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.splitlines()
        txt_values = []
        for line in lines:
            line = line.strip()
            if line.startswith('"') or "text =" in line.lower():
                # Extract the quoted value
                start = line.find('"')
                if start >= 0:
                    end = line.rfind('"')
                    if end > start:
                        txt_values.append(line[start + 1:end])
        return txt_values
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _dns_mx(name: str) -> list[str]:
    """Query MX records."""
    try:
        result = subprocess.run(
            ["nslookup", "-type=MX", name],
            capture_output=True, text=True, timeout=10,
        )
        mx = []
        for line in result.stdout.splitlines():
            if "mail exchanger" in line.lower() or "mx preference" in line.lower():
                mx.append(line.strip())
        return mx
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


# ── Check Functions ──────────────────────────────────────────────

def check_spf() -> dict:
    """Check SPF record exists and includes Zoho."""
    records = _dns_txt(DOMAIN)
    spf = [r for r in records if r.startswith("v=spf1")]
    if not spf:
        return {
            "name": "SPF",
            "status": "MISSING",
            "detail": "No SPF record found",
            "fix": f'Add TXT record:\n  Host: @\n  Value: v=spf1 include:zohocloud.ca ~all',
        }
    spf_val = spf[0]
    has_zoho = any(z in spf_val for z in ["zoho.com", "zohocloud.ca", "zoho.eu", "zeptomail"])
    if has_zoho:
        return {"name": "SPF", "status": "PASS", "detail": spf_val}
    return {
        "name": "SPF",
        "status": "WARN",
        "detail": f"SPF exists but missing Zoho include: {spf_val}",
        "fix": f'Update SPF to include Zoho:\n  v=spf1 include:zohocloud.ca {spf_val.replace("v=spf1 ", "")}',
    }


def check_dkim() -> dict:
    """Check DKIM selector records for Zoho."""
    # Zoho typically uses selector: zmail._domainkey or default._domainkey
    selectors = ["zmail._domainkey", "default._domainkey", "zoho._domainkey",
                 "1522905413783._domainkey"]
    for sel in selectors:
        records = _dns_txt(f"{sel}.{DOMAIN}")
        dkim = [r for r in records if "DKIM1" in r.upper() or "v=DKIM1" in r]
        if dkim:
            return {"name": "DKIM", "status": "PASS", "detail": f"{sel}: {dkim[0][:80]}..."}
    return {
        "name": "DKIM",
        "status": "WARN",
        "detail": "No DKIM record found (checked zmail, default, zoho selectors)",
        "fix": "In Zoho Mail Admin > Domain > Email Authentication > DKIM:\n"
               "  1. Generate DKIM key\n  2. Copy the CNAME/TXT record\n  3. Add to DNS\n"
               "  4. Click Verify in Zoho",
    }


def check_dmarc() -> dict:
    """Check DMARC record — needs p=quarantine or p=reject for BIMI."""
    records = _dns_txt(f"_dmarc.{DOMAIN}")
    dmarc = [r for r in records if r.startswith("v=DMARC1")]
    if not dmarc:
        return {
            "name": "DMARC",
            "status": "MISSING",
            "detail": "No DMARC record found",
            "fix": f'Add TXT record:\n  Host: _dmarc\n  Value: v=DMARC1; p=reject; rua=mailto:{DMARC_EMAIL}; pct=100',
        }
    val = dmarc[0]
    if "p=reject" in val:
        return {"name": "DMARC", "status": "PASS", "detail": val}
    if "p=quarantine" in val:
        return {
            "name": "DMARC",
            "status": "PASS",
            "detail": f"quarantine is acceptable for BIMI: {val}",
        }
    return {
        "name": "DMARC",
        "status": "WARN",
        "detail": f"DMARC exists but policy too weak for BIMI: {val}",
        "fix": f'Update DMARC to:\n  v=DMARC1; p=reject; rua=mailto:{DMARC_EMAIL}; pct=100',
    }


def check_bimi() -> dict:
    """Check BIMI TXT record."""
    records = _dns_txt(f"default._bimi.{DOMAIN}")
    bimi = [r for r in records if r.startswith("v=BIMI1")]
    if not bimi:
        return {
            "name": "BIMI",
            "status": "MISSING",
            "detail": "No BIMI record found",
            "fix": f'Add TXT record:\n  Host: default._bimi\n  Value: v=BIMI1; l={BIMI_LOGO_URL}',
        }
    val = bimi[0]
    if BIMI_LOGO_URL in val:
        return {"name": "BIMI", "status": "PASS", "detail": val}
    return {
        "name": "BIMI",
        "status": "WARN",
        "detail": f"BIMI exists but URL mismatch: {val}",
        "fix": f'Update BIMI to:\n  v=BIMI1; l={BIMI_LOGO_URL}',
    }


def check_logo_hosted() -> dict:
    """Verify logo.svg is reachable at the BIMI URL."""
    try:
        req = urllib.request.Request(BIMI_LOGO_URL, method="HEAD")
        req.add_header("User-Agent", "BIMI-Checker/1.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            ct = resp.headers.get("Content-Type", "")
            cl = resp.headers.get("Content-Length", "?")
            if "svg" in ct.lower() or "xml" in ct.lower():
                return {"name": "Logo Hosted", "status": "PASS", "detail": f"{BIMI_LOGO_URL} ({cl} bytes, {ct})"}
            return {
                "name": "Logo Hosted",
                "status": "WARN",
                "detail": f"URL reachable but Content-Type is {ct} (expected image/svg+xml)",
                "fix": "Configure server to serve .svg as image/svg+xml",
            }
    except urllib.error.HTTPError as e:
        return {"name": "Logo Hosted", "status": "FAIL", "detail": f"HTTP {e.code}: {BIMI_LOGO_URL}",
                "fix": "Push site/ to GitHub Pages and ensure CNAME is set"}
    except Exception as e:
        return {"name": "Logo Hosted", "status": "FAIL", "detail": str(e),
                "fix": "Ensure GitHub Pages is deployed and CNAME points to bit-rage-labour.com"}


def check_logo_local() -> dict:
    """Verify local SVG file exists and is BIMI-compliant."""
    if not LOGO_LOCAL.exists():
        return {"name": "Logo File", "status": "MISSING", "detail": f"Not found: {LOGO_LOCAL}",
                "fix": "Run: python output/trace_logo.py"}
    data = LOGO_LOCAL.read_text(encoding="utf-8")
    size = LOGO_LOCAL.stat().st_size
    checks = []
    if size > 32768:
        checks.append(f"Too large: {size} bytes (max 32KB)")
    if 'baseProfile="tiny-ps"' not in data:
        checks.append('Missing baseProfile="tiny-ps"')
    if "<script" in data.lower():
        checks.append("Contains <script> (forbidden)")
    if "xlink:href" in data:
        checks.append("Contains external refs (forbidden)")
    if checks:
        return {"name": "Logo File", "status": "FAIL", "detail": "; ".join(checks)}
    return {"name": "Logo File", "status": "PASS", "detail": f"{size:,} bytes, SVG Tiny PS compliant"}


def check_mx() -> dict:
    """Check MX records point to Zoho."""
    mx = _dns_mx(DOMAIN)
    if not mx:
        return {"name": "MX", "status": "WARN", "detail": "No MX records found"}
    mx_text = "; ".join(mx)
    if any("zoho" in m.lower() for m in mx):
        return {"name": "MX", "status": "PASS", "detail": mx_text}
    return {"name": "MX", "status": "INFO", "detail": f"MX not Zoho: {mx_text}"}


# ── Main ─────────────────────────────────────────────────────────

def generate_zone_records() -> str:
    """Generate copy-paste DNS records."""
    return f"""
; ============================================================
; DNS Records for {DOMAIN} — BIMI Email Authentication
; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
; ============================================================

; 1. SPF (if not already set by Zoho)
; Type: TXT | Host: @ | TTL: 3600
{DOMAIN}.  3600  IN  TXT  "v=spf1 include:zohocloud.ca ~all"

; 2. DMARC (required for BIMI — strict policy)
; Type: TXT | Host: _dmarc | TTL: 3600
_dmarc.{DOMAIN}.  3600  IN  TXT  "v=DMARC1; p=reject; rua=mailto:{DMARC_EMAIL}; pct=100"

; 3. BIMI (points to SVG logo — add AFTER DMARC is active)
; Type: TXT | Host: default._bimi | TTL: 3600
default._bimi.{DOMAIN}.  3600  IN  TXT  "v=BIMI1; l={BIMI_LOGO_URL}"

; 4. DKIM — configured via Zoho Mail Admin panel
;    Go to: Zoho Mail Admin > Domains > {DOMAIN} > Email Authentication > DKIM
;    Generate key, add the CNAME/TXT record they provide

; ============================================================
; REGISTRAR QUICK-ADD (for web UI):
; ============================================================
;
; Record 1 — DMARC:
;   Type:  TXT
;   Host:  _dmarc
;   Value: v=DMARC1; p=reject; rua=mailto:{DMARC_EMAIL}; pct=100
;   TTL:   3600
;
; Record 2 — BIMI:
;   Type:  TXT
;   Host:  default._bimi
;   Value: v=BIMI1; l={BIMI_LOGO_URL}
;   TTL:   3600
;
; Record 3 — SPF (if missing):
;   Type:  TXT
;   Host:  @
;   Value: v=spf1 include:zohocloud.ca ~all
;   TTL:   3600
"""


def run(verify_only: bool = False, apply_only: bool = False):
    if apply_only:
        print(generate_zone_records())
        return

    print(f"\n{'='*60}")
    print(f"  BIMI Email Authentication — {DOMAIN}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    checks = [
        check_mx(),
        check_spf(),
        check_dkim(),
        check_dmarc(),
        check_bimi(),
        check_logo_local(),
        check_logo_hosted(),
    ]

    # Status icons
    icons = {"PASS": "[OK]", "WARN": "[!!]", "MISSING": "[XX]", "FAIL": "[XX]", "INFO": "[--]"}
    pass_count = 0
    fixes = []

    for c in checks:
        icon = icons.get(c["status"], "[??]")
        print(f"  {icon} {c['name']:15s}  {c['detail']}")
        if c["status"] == "PASS":
            pass_count += 1
        if "fix" in c:
            fixes.append(c)

    print(f"\n  Score: {pass_count}/{len(checks)} checks passed\n")

    if fixes:
        print(f"{'─'*60}")
        print("  ACTION ITEMS:")
        print(f"{'─'*60}")
        for i, f in enumerate(fixes, 1):
            print(f"\n  {i}. {f['name']} ({f['status']}):")
            for line in f["fix"].split("\n"):
                print(f"     {line}")
        print()

    if pass_count == len(checks):
        print("  ALL CHECKS PASSED — BIMI is fully configured!")
    else:
        print(f"  {len(fixes)} item(s) need attention. Fix them and re-run:")
        print(f"    python automation/bimi_setup.py --verify\n")

    # Generate records file
    zone_file = Path(__file__).resolve().parent.parent / "output" / "bimi_dns_records.txt"
    zone_file.write_text(generate_zone_records(), encoding="utf-8")
    print(f"  DNS records saved to: {zone_file}\n")

    # Save state
    state = {
        "domain": DOMAIN,
        "checked_at": datetime.now().isoformat(),
        "results": {c["name"]: c["status"] for c in checks},
        "score": f"{pass_count}/{len(checks)}",
    }
    state_file = Path(__file__).resolve().parent.parent / "data" / "bimi_state.json"
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


if __name__ == "__main__":
    verify = "--verify" in sys.argv
    apply = "--apply" in sys.argv
    run(verify_only=verify, apply_only=apply)
