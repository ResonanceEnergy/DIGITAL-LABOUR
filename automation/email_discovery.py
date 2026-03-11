"""Email Discovery Engine — finds real email addresses for prospects.

Uses multiple strategies:
1. Common email pattern generation (first@domain, first.last@domain, etc.)
2. Domain extraction from company name/website
3. LLM-powered contact name + email inference
4. Pattern scoring based on company size and conventions

Usage:
    from automation.email_discovery import discover_email, enrich_prospects_csv
    email = discover_email("Notion", "Head of Growth")
    count = enrich_prospects_csv()
"""

import csv
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from utils.llm_client import call_llm

PROSPECTS_FILE = Path(__file__).parent / "prospects.csv"

# ── Known company domains (high-value cache) ──────────────────

KNOWN_DOMAINS = {
    "gorgias": "gorgias.com",
    "lemlist": "lemlist.com",
    "reply.io": "reply.io",
    "vidyard": "vidyard.com",
    "apollo.io": "apollo.io",
    "outreach": "outreach.io",
    "salesloft": "salesloft.com",
    "zoominfo": "zoominfo.com",
    "pipedrive": "pipedrive.com",
    "close": "close.com",
    "drift": "drift.com",
    "intercom": "intercom.com",
    "zendesk": "zendesk.com",
    "freshdesk": "freshworks.com",
    "help scout": "helpscout.com",
    "front": "front.com",
    "clearbit": "clearbit.com",
    "lusha": "lusha.com",
    "seamless.ai": "seamless.ai",
    "hunter.io": "hunter.io",
    "snov.io": "snov.io",
    "woodpecker": "woodpecker.co",
    "mailshake": "mailshake.com",
    "mixmax": "mixmax.com",
    "yesware": "yesware.com",
    "loom": "loom.com",
    "calendly": "calendly.com",
    "typeform": "typeform.com",
    "unbounce": "unbounce.com",
    "convertkit": "kit.com",
    "single grain": "singlegrain.com",
    "webfx": "webfx.com",
    "directive": "directiveconsulting.com",
    "omniscient digital": "beomniscient.com",
    "siege media": "siegemedia.com",
    "animalz": "animalz.co",
    "grow and convert": "growandconvert.com",
    "foundation marketing": "foundationinc.co",
    "velocity partners": "velocitypartners.com",
    "soapbox": "wistia.com",
    "deel": "deel.com",
    "ramp": "ramp.com",
    "brex": "brex.com",
    "lattice": "lattice.com",
    "rippling": "rippling.com",
    "gusto": "gusto.com",
    "notion": "notion.so",
    "linear": "linear.app",
    "vercel": "vercel.com",
    "supabase": "supabase.com",
}

# ── Email pattern templates ────────────────────────────────────
# Ordered by most common in B2B SaaS
PATTERNS = [
    "{first}@{domain}",                  # jane@company.com
    "{first}.{last}@{domain}",           # jane.doe@company.com
    "{first}{last}@{domain}",            # janedoe@company.com
    "{f}{last}@{domain}",               # jdoe@company.com
    "{first}_{last}@{domain}",           # jane_doe@company.com
    "{first}.{l}@{domain}",             # jane.d@company.com
    "{f}.{last}@{domain}",             # j.doe@company.com
]


def _company_to_domain(company: str) -> str:
    """Convert company name to likely domain."""
    key = company.lower().strip()
    if key in KNOWN_DOMAINS:
        return KNOWN_DOMAINS[key]

    # Simple heuristic: strip common suffixes, make domain
    cleaned = re.sub(r'\s+(inc|llc|ltd|co|corp|group|labs|hq)\.?$', '', key, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^a-z0-9]', '', cleaned)
    return f"{cleaned}.com"


def _generate_patterns(first: str, last: str, domain: str) -> list[str]:
    """Generate candidate emails from name + domain."""
    first = first.lower().strip()
    last = last.lower().strip()
    f = first[0] if first else ""
    l = last[0] if last else ""

    candidates = []
    for pattern in PATTERNS:
        try:
            email = pattern.format(first=first, last=last, f=f, l=l, domain=domain)
            if email and "@" in email and "." in email.split("@")[1]:
                candidates.append(email)
        except (KeyError, IndexError):
            continue
    return candidates


# ── LLM-powered contact discovery ─────────────────────────────

CONTACT_DISCOVERY_PROMPT = """You are an expert B2B sales intelligence agent.

Your task: Find the most likely REAL contact person and email address for this target:
  Company: {company}
  Target Role: {role}
  Company Domain: {domain}

RESEARCH RULES:
1. Identify the most likely person holding this role (or nearest equivalent) at {company}
2. Use COMMON email patterns for that company:
   - Most B2B SaaS companies use: firstname@domain or first.last@domain
   - Some use: firstlast@domain or f.last@domain
3. If you know the actual person's name, use it. If not, make your best inference
   based on the company and role.

OUTPUT (strict JSON, no markdown):
{{
  "contact_name": "First Last",
  "contact_email": "best_guess@domain",
  "email_confidence": 70,
  "alternative_emails": ["alt1@domain", "alt2@domain"],
  "reasoning": "Brief explanation of how you derived this"
}}

IMPORTANT:
- contact_email MUST use the domain: {domain}
- email_confidence is 0-100 (how sure you are this is correct)
- Never use generic role-based addresses like head_of_sales@ or vp.marketing@
- Always use a real person's name pattern
- If you truly cannot determine a name, use the generic info@ or hello@ as contact_email
  and set confidence to 20
"""


def discover_email(company: str, role: str, domain: str | None = None) -> dict:
    """Discover the most likely email address for a prospect.
    
    Returns:
        {
            "contact_name": str,
            "contact_email": str,
            "email_confidence": int,
            "alternative_emails": list[str],
            "domain": str,
        }
    """
    if not domain:
        domain = _company_to_domain(company)

    prompt = CONTACT_DISCOVERY_PROMPT.format(
        company=company,
        role=role,
        domain=domain,
    )

    try:
        raw = call_llm(
            system_prompt="You are a B2B sales intelligence agent. Output ONLY valid JSON.",
            user_message=prompt,
        )

        cleaned = re.sub(r'```(?:json)?\s*\n?', '', raw).strip().rstrip('`')
        result = json.loads(cleaned)

        # Validate the email uses the correct domain
        email = result.get("contact_email", "")
        if email and "@" in email:
            email_domain = email.split("@")[1].lower()
            if email_domain != domain.lower():
                # Fix domain mismatch
                local = email.split("@")[0]
                email = f"{local}@{domain}"
                result["contact_email"] = email

        # Generate additional patterns if we have a name
        name = result.get("contact_name", "")
        if name and " " in name:
            parts = name.split()
            first, last = parts[0], parts[-1]
            patterns = _generate_patterns(first, last, domain)
            # Add patterns not already in alternatives
            existing = {result.get("contact_email", "").lower()} | {
                e.lower() for e in result.get("alternative_emails", [])
            }
            for p in patterns:
                if p.lower() not in existing:
                    result.setdefault("alternative_emails", []).append(p)
                    existing.add(p.lower())

        result["domain"] = domain
        return result

    except Exception as e:
        # Fallback: generate pattern-based guesses
        return {
            "contact_name": "",
            "contact_email": f"hello@{domain}",
            "email_confidence": 15,
            "alternative_emails": [f"info@{domain}", f"team@{domain}"],
            "domain": domain,
            "error": str(e),
        }


# ── Batch operations ──────────────────────────────────────────

def enrich_prospects_csv() -> int:
    """Add email addresses to all prospects in CSV that don't have one."""
    if not PROSPECTS_FILE.exists():
        print("[EMAIL DISCOVERY] No prospects.csv found.")
        return 0

    rows = []
    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    # Ensure email columns exist
    needed_cols = ["contact_name", "contact_email", "email_confidence", "domain"]
    for col in needed_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    enriched = 0
    import time

    for i, row in enumerate(rows):
        if row.get("contact_email") and "@" in row.get("contact_email", ""):
            continue  # Already has email

        company = row.get("company", "")
        role = row.get("role", "")
        if not company:
            continue

        print(f"[{i + 1}/{len(rows)}] Discovering email for {company} / {role}...")

        result = discover_email(company, role)
        row["contact_name"] = result.get("contact_name", "")
        row["contact_email"] = result.get("contact_email", "")
        row["email_confidence"] = str(result.get("email_confidence", 0))
        row["domain"] = result.get("domain", "")
        enriched += 1

        if i < len(rows) - 1:
            time.sleep(1)  # Rate limit

    # Write back
    with open(PROSPECTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[EMAIL DISCOVERY] Enriched {enriched} prospects with email addresses")
    return enriched


def re_enrich_meta_outreach() -> int:
    """Re-enrich existing meta outreach files with discovered emails."""
    meta_dir = PROJECT_ROOT / "output" / "meta_outreach"
    if not meta_dir.exists():
        return 0

    updated = 0
    import time

    for f in sorted(meta_dir.glob("meta_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        enrichment = data.get("enrichment", {})
        current_email = enrichment.get("contact_email_guess", "")

        # Skip if already has a good email (not role-based)
        if (current_email and "@" in current_email
                and not any(x in current_email.lower() for x in
                            ["head_of", "vp.", "director_", "ceo@", "cto@", "cfo@"])):
            continue

        company = data.get("target", {}).get("company", "")
        role = data.get("target", {}).get("role", "")
        website = enrichment.get("company_website", "")

        # Extract domain from website if available
        domain = None
        if website:
            parsed = urlparse(website)
            host = parsed.hostname or ""
            if host.startswith("www."):
                host = host[4:]
            if host:
                domain = host

        result = discover_email(company, role, domain)

        # Update enrichment
        enrichment["contact_name"] = result.get("contact_name") or enrichment.get("contact_name", "")
        enrichment["contact_email_guess"] = result.get("contact_email", "")
        enrichment["email_confidence"] = result.get("email_confidence", 0)
        enrichment["alternative_emails"] = result.get("alternative_emails", [])
        data["enrichment"] = enrichment

        # Reset send status so it can be re-sent
        data["send_status"] = "pending_review"

        f.write_text(json.dumps(data, indent=2), encoding="utf-8")
        updated += 1
        print(f"  [ENRICHED] {company} → {result.get('contact_email', '?')}")

        time.sleep(1)

    print(f"\n[EMAIL DISCOVERY] Re-enriched {updated} meta outreach files")
    return updated


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Email Discovery Engine")
    parser.add_argument("--enrich-csv", action="store_true", help="Enrich prospects CSV with emails")
    parser.add_argument("--enrich-meta", action="store_true", help="Re-enrich meta outreach files")
    parser.add_argument("--lookup", type=str, help="Lookup email for company:role")
    args = parser.parse_args()

    if args.enrich_csv:
        enrich_prospects_csv()
    elif args.enrich_meta:
        re_enrich_meta_outreach()
    elif args.lookup:
        parts = args.lookup.split(":", 1)
        company = parts[0]
        role = parts[1] if len(parts) > 1 else "CEO"
        result = discover_email(company, role)
        print(json.dumps(result, indent=2))
    else:
        # Default: enrich both
        enrich_prospects_csv()
        re_enrich_meta_outreach()
