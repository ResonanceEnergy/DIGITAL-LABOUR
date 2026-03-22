"""Referral Tracker — Track and reward client referrals.

Manages a referral program where existing clients earn credits/discounts
for referring new paying clients. Tracks referral codes, conversions,
and payouts.

Integrates with:
- automation/crm_tracker.py for client lookup
- billing/tracker.py for revenue attribution

Usage:
    python -m automation.referral_tracker --status        # Show referral program stats
    python -m automation.referral_tracker --generate "Acme"  # Generate referral code
    python -m automation.referral_tracker --redeem CODE    # Record a referral conversion
    python -m automation.referral_tracker --leaderboard    # Top referrers
"""

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "referrals.db"
STATE_FILE = PROJECT_ROOT / "data" / "referral_state.json"

# ── Referral Config ────────────────────────────────────────────
REFERRER_REWARD_PCT = 10       # 10% credit on referred client's first month
REFEREE_DISCOUNT_PCT = 15      # New client gets 15% off first month
MIN_SPEND_TO_REFER = 10.0     # Referrer must have spent at least $10


# ── Database ───────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    """Create referral tables."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS referral_codes (
            code         TEXT PRIMARY KEY,
            referrer_id  TEXT NOT NULL,
            company      TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            active       INTEGER DEFAULT 1,
            uses         INTEGER DEFAULT 0,
            max_uses     INTEGER DEFAULT 10
        );

        CREATE TABLE IF NOT EXISTS referral_conversions (
            conversion_id  TEXT PRIMARY KEY,
            code           TEXT NOT NULL,
            referrer_id    TEXT NOT NULL,
            referee_id     TEXT NOT NULL,
            referee_email  TEXT DEFAULT '',
            converted_at   TEXT NOT NULL,
            referee_spend  REAL DEFAULT 0.0,
            referrer_credit REAL DEFAULT 0.0,
            referee_discount REAL DEFAULT 0.0,
            status         TEXT DEFAULT 'converted',
            FOREIGN KEY (code) REFERENCES referral_codes(code)
        );

        CREATE TABLE IF NOT EXISTS referral_payouts (
            payout_id    TEXT PRIMARY KEY,
            referrer_id  TEXT NOT NULL,
            amount       REAL NOT NULL,
            method       TEXT DEFAULT 'credit',
            created_at   TEXT NOT NULL,
            status       TEXT DEFAULT 'pending'
        );

        CREATE INDEX IF NOT EXISTS idx_code_referrer ON referral_codes(referrer_id);
        CREATE INDEX IF NOT EXISTS idx_conv_code ON referral_conversions(code);
        CREATE INDEX IF NOT EXISTS idx_payout_referrer ON referral_payouts(referrer_id);
    """)
    conn.commit()
    conn.close()


# ── Code Generation ────────────────────────────────────────────

def generate_code(referrer_id: str, company: str) -> dict:
    """Generate a unique referral code for a client."""
    init_db()
    conn = _get_conn()

    # Check if they already have an active code
    existing = conn.execute(
        "SELECT code FROM referral_codes WHERE referrer_id = ? AND active = 1",
        (referrer_id,)
    ).fetchone()

    if existing:
        conn.close()
        return {"code": existing["code"], "status": "existing"}

    # Generate code: DL-{first4_of_company}-{short_hash}
    short = company[:4].upper().replace(" ", "")
    hash_input = f"{referrer_id}{company}{uuid4().hex[:8]}"
    short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:6].upper()
    code = f"DL-{short}-{short_hash}"

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO referral_codes (code, referrer_id, company, created_at) VALUES (?, ?, ?, ?)",
        (code, referrer_id, company, now)
    )
    conn.commit()
    conn.close()

    return {"code": code, "status": "created", "referrer": referrer_id, "company": company}


def get_code_info(code: str) -> dict | None:
    """Look up a referral code."""
    init_db()
    conn = _get_conn()
    row = conn.execute("SELECT * FROM referral_codes WHERE code = ?", (code,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Conversion Tracking ────────────────────────────────────────

def record_conversion(code: str, referee_id: str, referee_email: str = "",
                      referee_spend: float = 0.0) -> dict:
    """Record a referral conversion when a referred client pays."""
    init_db()
    conn = _get_conn()

    # Validate code
    code_info = conn.execute(
        "SELECT * FROM referral_codes WHERE code = ? AND active = 1",
        (code,)
    ).fetchone()

    if not code_info:
        conn.close()
        return {"status": "error", "reason": "Invalid or inactive referral code"}

    if code_info["uses"] >= code_info["max_uses"]:
        conn.close()
        return {"status": "error", "reason": "Referral code has reached max uses"}

    # Calculate rewards
    referrer_credit = referee_spend * (REFERRER_REWARD_PCT / 100)
    referee_discount = referee_spend * (REFEREE_DISCOUNT_PCT / 100)

    conversion_id = uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()

    conn.execute("""
        INSERT INTO referral_conversions
            (conversion_id, code, referrer_id, referee_id, referee_email,
             converted_at, referee_spend, referrer_credit, referee_discount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'converted')
    """, (conversion_id, code, code_info["referrer_id"], referee_id,
          referee_email, now, referee_spend, referrer_credit, referee_discount))

    # Increment uses
    conn.execute("UPDATE referral_codes SET uses = uses + 1 WHERE code = ?", (code,))

    # Create pending payout
    payout_id = uuid4().hex[:12]
    conn.execute("""
        INSERT INTO referral_payouts (payout_id, referrer_id, amount, method, created_at, status)
        VALUES (?, ?, ?, 'credit', ?, 'pending')
    """, (payout_id, code_info["referrer_id"], referrer_credit, now))

    conn.commit()
    conn.close()

    return {
        "status": "converted",
        "conversion_id": conversion_id,
        "referrer_id": code_info["referrer_id"],
        "referee_id": referee_id,
        "referrer_credit": round(referrer_credit, 2),
        "referee_discount": round(referee_discount, 2),
    }


# ── Leaderboard & Stats ───────────────────────────────────────

def get_leaderboard(limit: int = 10) -> list[dict]:
    """Get top referrers by conversions and credits earned."""
    init_db()
    conn = _get_conn()

    rows = conn.execute("""
        SELECT
            rc.referrer_id,
            rc.company,
            rc.code,
            COUNT(cv.conversion_id) as conversions,
            COALESCE(SUM(cv.referrer_credit), 0) as total_credit
        FROM referral_codes rc
        LEFT JOIN referral_conversions cv ON rc.code = cv.code
        GROUP BY rc.referrer_id
        ORDER BY conversions DESC, total_credit DESC
        LIMIT ?
    """, (limit,)).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """Get overall referral program stats."""
    init_db()
    conn = _get_conn()

    codes = conn.execute("SELECT COUNT(*) as n FROM referral_codes WHERE active = 1").fetchone()["n"]
    conversions = conn.execute("SELECT COUNT(*) as n FROM referral_conversions").fetchone()["n"]
    total_credit = conn.execute(
        "SELECT COALESCE(SUM(referrer_credit), 0) as n FROM referral_conversions"
    ).fetchone()["n"]
    pending_payouts = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as n FROM referral_payouts WHERE status = 'pending'"
    ).fetchone()["n"]

    conn.close()

    return {
        "active_codes": codes,
        "total_conversions": conversions,
        "total_credit_earned": round(total_credit, 2),
        "pending_payouts": round(pending_payouts, 2),
    }


# ── Status Report ──────────────────────────────────────────────

def show_status() -> dict:
    """Display referral program status."""
    stats = get_stats()
    leaderboard = get_leaderboard(5)

    print(f"\n{'='*50}")
    print(f"  REFERRAL PROGRAM STATUS")
    print(f"{'='*50}")
    print(f"  Active codes:       {stats['active_codes']}")
    print(f"  Total conversions:  {stats['total_conversions']}")
    print(f"  Credit earned:      ${stats['total_credit_earned']:.2f}")
    print(f"  Pending payouts:    ${stats['pending_payouts']:.2f}")
    print(f"  Referrer reward:    {REFERRER_REWARD_PCT}% credit")
    print(f"  Referee discount:   {REFEREE_DISCOUNT_PCT}% off first month")

    if leaderboard:
        print(f"\n  Top Referrers:")
        for r in leaderboard:
            print(f"    {r['company']} ({r['code']}): "
                  f"{r['conversions']} conversions, ${r['total_credit']:.2f} earned")

    print(f"{'='*50}\n")
    return stats


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Referral Tracker")
    parser.add_argument("--status", action="store_true", help="Show referral program stats")
    parser.add_argument("--generate", type=str, metavar="COMPANY", help="Generate referral code")
    parser.add_argument("--referrer-id", type=str, default="", help="Referrer ID (with --generate)")
    parser.add_argument("--redeem", type=str, metavar="CODE", help="Record a referral conversion")
    parser.add_argument("--referee-id", type=str, default="", help="Referee client ID (with --redeem)")
    parser.add_argument("--spend", type=float, default=0.0, help="Referee spend amount (with --redeem)")
    parser.add_argument("--leaderboard", action="store_true", help="Show top referrers")
    args = parser.parse_args()

    if args.generate:
        referrer_id = args.referrer_id or args.generate.lower().replace(" ", "_")
        result = generate_code(referrer_id, args.generate)
        print(f"Referral code: {result['code']} ({result['status']})")
    elif args.redeem:
        if not args.referee_id:
            print("ERROR: --referee-id required with --redeem")
            return
        result = record_conversion(args.redeem, args.referee_id, referee_spend=args.spend)
        print(json.dumps(result, indent=2))
    elif args.leaderboard:
        board = get_leaderboard()
        for r in board:
            print(f"  {r['company']}: {r['conversions']} conversions, ${r['total_credit']:.2f}")
    elif args.status:
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
