"""Lead Scorer — Scores prospects by ICP fit, engagement signals, and conversion potential.

Ranks prospects from prospects.csv and inbound leads to prioritize outreach.
Uses company signals, role match, and historical conversion data.

Usage:
    python -m automation.lead_scorer --score            # Score all unscored prospects
    python -m automation.lead_scorer --top 10            # Show top 10 prospects
    python -m automation.lead_scorer --rescore           # Re-score all prospects
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PROSPECTS_FILE = Path(__file__).parent / "prospects.csv"
SCORES_FILE = PROJECT_ROOT / "data" / "lead_scores.json"
SENT_LOG = Path(__file__).parent / "sent_log.json"

# ── ICP (Ideal Customer Profile) ──────────────────────────────

# High-value verticals for AI labor services
HIGH_VALUE_VERTICALS = {
    "saas", "fintech", "ecommerce", "e-commerce", "marketing agency",
    "real estate", "insurance", "consulting", "legal tech", "healthcare",
    "recruitment", "hr tech", "edtech", "logistics", "b2b",
}

# Target roles (decision makers who buy services)
HIGH_VALUE_ROLES = {
    "head of growth", "vp sales", "cmo", "head of marketing",
    "director of sales", "ceo", "founder", "co-founder", "coo",
    "head of operations", "vp operations", "director of operations",
    "head of sales", "chief revenue officer", "cro",
    "vp marketing", "director of marketing", "head of demand gen",
}

# Company size signals (from domain or description)
ENTERPRISE_SIGNALS = [
    "series a", "series b", "series c", "raised", "funding",
    "ipo", "public", "nasdaq", "nyse",
]

SMB_SIGNALS = [
    "startup", "bootstrap", "small team", "freelance",
    "solo", "indie", "early stage",
]


# ── Scoring Engine ─────────────────────────────────────────────

def score_prospect(prospect: dict) -> dict:
    """Score a single prospect (0-100 scale)."""
    score = 50  # Base score
    reasons = []

    company = prospect.get("company", "").lower()
    role = prospect.get("role", "").lower()
    vertical = prospect.get("vertical", "").lower()
    notes = prospect.get("notes", "").lower()
    combined = f"{company} {role} {vertical} {notes}"

    # ─── Vertical match (+20)
    for v in HIGH_VALUE_VERTICALS:
        if v in vertical or v in company:
            score += 20
            reasons.append(f"high-value vertical: {v}")
            break

    # ─── Role match (+15)
    for r in HIGH_VALUE_ROLES:
        if r in role:
            score += 15
            reasons.append(f"decision-maker role: {r}")
            break

    # ─── Company signals
    for sig in ENTERPRISE_SIGNALS:
        if sig in combined:
            score += 10
            reasons.append(f"enterprise signal: {sig}")
            break

    for sig in SMB_SIGNALS:
        if sig in combined:
            score -= 5
            reasons.append(f"SMB signal: {sig}")
            break

    # ─── Email quality (+5 if real domain, -10 if generic)
    email = prospect.get("email", prospect.get("contact_email", ""))
    if email:
        generic_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"]
        domain = email.split("@")[1] if "@" in email else ""
        if domain and domain not in generic_domains:
            score += 5
            reasons.append("corporate email domain")
        elif domain in generic_domains:
            score -= 10
            reasons.append("generic email domain")

    # ─── Has website or LinkedIn (+5)
    if prospect.get("website") or prospect.get("linkedin"):
        score += 5
        reasons.append("has web presence")

    # ─── Priority field bonus
    priority = prospect.get("priority", "").lower()
    if priority == "high":
        score += 10
        reasons.append("marked high priority")
    elif priority == "low":
        score -= 10
        reasons.append("marked low priority")

    # ─── Clamp score
    score = max(0, min(100, score))

    return {
        "company": prospect.get("company", ""),
        "role": prospect.get("role", ""),
        "email": email,
        "score": score,
        "grade": _score_to_grade(score),
        "reasons": reasons,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


def _score_to_grade(score: int) -> str:
    if score >= 80:
        return "A"
    elif score >= 65:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 35:
        return "D"
    return "F"


# ── Batch Operations ──────────────────────────────────────────

def score_all_prospects(rescore: bool = False) -> list[dict]:
    """Score all prospects from CSV."""
    if not PROSPECTS_FILE.exists():
        print("[LEAD SCORER] No prospects.csv found.")
        return []

    # Load existing scores
    existing = {}
    if SCORES_FILE.exists() and not rescore:
        scores = json.loads(SCORES_FILE.read_text(encoding="utf-8"))
        existing = {s["company"].lower(): s for s in scores}

    # Load sent log for already-contacted filter
    contacted = set()
    if SENT_LOG.exists():
        sent = json.loads(SENT_LOG.read_text(encoding="utf-8"))
        contacted = {s.get("company", "").lower() for s in sent}

    results = []
    new_scored = 0

    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_key = row.get("company", "").lower()

            if company_key in existing and not rescore:
                result = existing[company_key]
                result["already_contacted"] = company_key in contacted
                results.append(result)
                continue

            scored = score_prospect(row)
            scored["already_contacted"] = company_key in contacted
            results.append(scored)
            new_scored += 1

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # Save
    SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCORES_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"[LEAD SCORER] Scored {new_scored} new prospects. Total: {len(results)}")
    return results


def get_top_prospects(n: int = 10, uncontacted_only: bool = True) -> list[dict]:
    """Get top N prospects by score."""
    if not SCORES_FILE.exists():
        score_all_prospects()

    scores = json.loads(SCORES_FILE.read_text(encoding="utf-8"))

    if uncontacted_only:
        scores = [s for s in scores if not s.get("already_contacted")]

    return scores[:n]


def show_leaderboard(n: int = 20):
    """Print prospect leaderboard."""
    scores = score_all_prospects()

    print(f"\n{'='*70}")
    print(f"  LEAD SCORER — Top {min(n, len(scores))} Prospects")
    print(f"{'='*70}")
    print(f"  {'#':>3}  {'Score':>5}  {'Grade':>5}  {'Company':<30}  {'Role':<25}  {'Status'}")
    print(f"  {'─'*3}  {'─'*5}  {'─'*5}  {'─'*30}  {'─'*25}  {'─'*10}")

    for i, s in enumerate(scores[:n], 1):
        status = "SENT" if s.get("already_contacted") else ""
        print(f"  {i:>3}  {s['score']:>5}  {s['grade']:>5}  {s['company']:<30}  {s['role']:<25}  {status}")

    # Summary stats
    grades = {}
    for s in scores:
        g = s["grade"]
        grades[g] = grades.get(g, 0) + 1

    print(f"\n  Grade distribution: {grades}")
    print(f"  Uncontacted: {sum(1 for s in scores if not s.get('already_contacted'))}")
    print(f"  Total: {len(scores)}")


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lead Scorer — Rank prospects by ICP fit")
    parser.add_argument("--score", action="store_true", help="Score all unscored prospects")
    parser.add_argument("--rescore", action="store_true", help="Re-score all prospects")
    parser.add_argument("--top", type=int, default=20, help="Show top N prospects")
    args = parser.parse_args()

    if args.rescore:
        score_all_prospects(rescore=True)
        show_leaderboard(args.top)
    elif args.score:
        score_all_prospects()
        show_leaderboard(args.top)
    else:
        show_leaderboard(args.top)
