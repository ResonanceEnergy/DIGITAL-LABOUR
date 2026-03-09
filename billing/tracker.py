"""Billing tracker — tracks client usage and generates invoices.

Usage:
    from billing.tracker import BillingTracker

    bt = BillingTracker()
    bt.record_usage("client-1", "sales_outreach", cost_usd=0.15)
    invoice = bt.generate_invoice("client-1")
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "billing.db"

# Pricing per task type (what we charge the client, not our LLM cost)
PRICING = {
    "sales_outreach": {"per_task": 2.40, "currency": "USD"},
    "support_ticket": {"per_task": 1.00, "currency": "USD"},
    "content_repurpose": {"per_task": 3.00, "currency": "USD"},
    "doc_extract": {"per_task": 1.50, "currency": "USD"},
}

# Retainer tiers (monthly)
RETAINER_TIERS = {
    "sales_starter": {"price": 750, "tasks": 50, "type": "sales_outreach", "overage": 12.00},
    "sales_growth": {"price": 1400, "tasks": 100, "type": "sales_outreach", "overage": 10.00},
    "sales_scale": {"price": 2500, "tasks": 200, "type": "sales_outreach", "overage": 8.00},
    "support_starter": {"price": 400, "tasks": 200, "type": "support_ticket", "overage": 1.50},
    "support_growth": {"price": 800, "tasks": 500, "type": "support_ticket", "overage": 1.20},
    "support_scale": {"price": 1400, "tasks": 1000, "type": "support_ticket", "overage": 1.00},
}


class BillingTracker:

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS usage (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                client      TEXT NOT NULL,
                task_type   TEXT NOT NULL,
                task_id     TEXT DEFAULT '',
                llm_cost    REAL DEFAULT 0.0,
                charge      REAL DEFAULT 0.0,
                timestamp   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clients (
                client      TEXT PRIMARY KEY,
                name        TEXT DEFAULT '',
                email       TEXT DEFAULT '',
                retainer    TEXT DEFAULT '',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                client      TEXT NOT NULL,
                period      TEXT NOT NULL,
                total       REAL NOT NULL,
                tasks_count INTEGER DEFAULT 0,
                llm_cost    REAL DEFAULT 0.0,
                margin      REAL DEFAULT 0.0,
                status      TEXT DEFAULT 'draft',
                created_at  TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_usage_client ON usage(client);
            CREATE INDEX IF NOT EXISTS idx_usage_time ON usage(timestamp);
        """)
        conn.commit()
        conn.close()

    def add_client(self, client: str, name: str = "", email: str = "", retainer: str = ""):
        """Register or update a client."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._conn()
        conn.execute(
            """INSERT INTO clients (client, name, email, retainer, created_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(client) DO UPDATE SET name=?, email=?, retainer=?""",
            (client, name, email, retainer, now, name, email, retainer),
        )
        conn.commit()
        conn.close()

    def record_usage(
        self, client: str, task_type: str, task_id: str = "", llm_cost: float = 0.0
    ) -> dict:
        """Record a billable task. Calculates charge based on pricing."""
        charge = PRICING.get(task_type, {}).get("per_task", 0.0)
        now = datetime.now(timezone.utc).isoformat()

        conn = self._conn()
        conn.execute(
            "INSERT INTO usage (client, task_type, task_id, llm_cost, charge, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (client, task_type, task_id, llm_cost, charge, now),
        )
        conn.commit()
        conn.close()

        return {"client": client, "task_type": task_type, "charge": charge, "llm_cost": llm_cost}

    def client_summary(self, client: str, days: int = 30) -> dict:
        """Get a client's usage summary."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = self._conn()

        rows = conn.execute(
            "SELECT * FROM usage WHERE client = ? AND timestamp >= ? ORDER BY timestamp DESC",
            (client, cutoff),
        ).fetchall()
        conn.close()

        total_charge = sum(r["charge"] for r in rows)
        total_llm_cost = sum(r["llm_cost"] for r in rows)
        by_type: dict[str, int] = {}
        for r in rows:
            by_type[r["task_type"]] = by_type.get(r["task_type"], 0) + 1

        return {
            "client": client,
            "period_days": days,
            "total_tasks": len(rows),
            "total_charge": round(total_charge, 2),
            "total_llm_cost": round(total_llm_cost, 4),
            "margin": round(total_charge - total_llm_cost, 2),
            "by_type": by_type,
        }

    def generate_invoice(self, client: str, days: int = 30) -> dict:
        """Generate a billing invoice for a client."""
        summary = self.client_summary(client, days=days)
        now = datetime.now(timezone.utc)
        period = f"{(now - timedelta(days=days)).strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}"

        # Check for retainer
        conn = self._conn()
        client_row = conn.execute("SELECT * FROM clients WHERE client = ?", (client,)).fetchone()
        retainer_name = client_row["retainer"] if client_row else ""

        invoice = {
            "client": client,
            "period": period,
            "tasks_count": summary["total_tasks"],
            "total_charge": summary["total_charge"],
            "llm_cost": summary["total_llm_cost"],
            "margin": summary["margin"],
            "retainer": retainer_name,
        }

        # Apply retainer pricing if applicable
        if retainer_name and retainer_name in RETAINER_TIERS:
            tier = RETAINER_TIERS[retainer_name]
            included = tier["tasks"]
            overage_count = max(0, summary["total_tasks"] - included)
            overage_charge = overage_count * tier["overage"]
            invoice["base_price"] = tier["price"]
            invoice["included_tasks"] = included
            invoice["overage_count"] = overage_count
            invoice["overage_charge"] = round(overage_charge, 2)
            invoice["total_charge"] = round(tier["price"] + overage_charge, 2)

        # Save to DB
        conn.execute(
            """INSERT INTO invoices (client, period, total, tasks_count, llm_cost, margin, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'draft', ?)""",
            (client, period, invoice["total_charge"], invoice["tasks_count"],
             invoice["llm_cost"], invoice["margin"], now.isoformat()),
        )
        conn.commit()

        # Save to file
        invoice_dir = PROJECT_ROOT / "output" / "invoices"
        invoice_dir.mkdir(parents=True, exist_ok=True)
        filepath = invoice_dir / f"invoice_{client}_{now.strftime('%Y%m%d')}.json"
        filepath.write_text(json.dumps(invoice, indent=2), encoding="utf-8")
        invoice["file"] = str(filepath)

        conn.close()
        return invoice

    def revenue_report(self, days: int = 30) -> dict:
        """Generate a revenue report across all clients."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = self._conn()

        rows = conn.execute(
            "SELECT * FROM usage WHERE timestamp >= ?", (cutoff,)
        ).fetchall()
        conn.close()

        by_client: dict[str, float] = {}
        by_type: dict[str, float] = {}
        total_charge = 0.0
        total_cost = 0.0

        for r in rows:
            by_client[r["client"]] = by_client.get(r["client"], 0) + r["charge"]
            by_type[r["task_type"]] = by_type.get(r["task_type"], 0) + r["charge"]
            total_charge += r["charge"]
            total_cost += r["llm_cost"]

        return {
            "period_days": days,
            "total_revenue": round(total_charge, 2),
            "total_cost": round(total_cost, 4),
            "gross_margin": round(total_charge - total_cost, 2),
            "total_tasks": len(rows),
            "by_client": {k: round(v, 2) for k, v in by_client.items()},
            "by_type": {k: round(v, 2) for k, v in by_type.items()},
        }

    def auto_invoice_all(self, days: int = 30) -> list[dict]:
        """Auto-generate invoices for all clients with unbilled usage."""
        conn = self._conn()
        clients = conn.execute("SELECT DISTINCT client FROM usage").fetchall()
        conn.close()

        invoices = []
        for row in clients:
            client = row["client"]
            summary = self.client_summary(client, days=days)
            if summary["total_tasks"] > 0 and summary["total_charge"] > 0:
                inv = self.generate_invoice(client, days=days)
                invoices.append(inv)
                print(f"[BILLING] Invoice for {client}: ${inv['total_charge']:.2f} ({inv['tasks_count']} tasks)")

        return invoices

    def record_and_bill(
        self, client: str, task_type: str, task_id: str = "", llm_cost: float = 0.0
    ) -> dict:
        """Record usage and return billing details — call from dispatcher after task completion."""
        result = self.record_usage(client, task_type, task_id=task_id, llm_cost=llm_cost)

        # Check if client has a retainer — track against tier limits
        conn = self._conn()
        client_row = conn.execute("SELECT retainer FROM clients WHERE client = ?", (client,)).fetchone()
        conn.close()

        if client_row and client_row["retainer"]:
            tier_name = client_row["retainer"]
            tier = RETAINER_TIERS.get(tier_name)
            if tier:
                summary = self.client_summary(client, days=30)
                used = summary["total_tasks"]
                included = tier["tasks"]
                result["retainer_tier"] = tier_name
                result["tasks_used"] = used
                result["tasks_included"] = included
                result["overage"] = max(0, used - included)
                if used >= int(included * 0.9) and used < included:
                    result["warning"] = f"Approaching tier limit: {used}/{included} tasks used"

        return result


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Digital Labour Billing")
    parser.add_argument("--invoice", type=str, help="Generate invoice for client")
    parser.add_argument("--invoice-all", action="store_true", help="Auto-generate all invoices")
    parser.add_argument("--report", action="store_true", help="Revenue report")
    parser.add_argument("--days", type=int, default=30, help="Period in days")
    parser.add_argument("--summary", type=str, help="Client summary")
    args = parser.parse_args()

    bt = BillingTracker()

    if args.invoice:
        inv = bt.generate_invoice(args.invoice, days=args.days)
        print(json.dumps(inv, indent=2))
    elif args.invoice_all:
        invoices = bt.auto_invoice_all(days=args.days)
        print(f"\n{len(invoices)} invoices generated.")
    elif args.report:
        report = bt.revenue_report(days=args.days)
        print(json.dumps(report, indent=2))
    elif args.summary:
        s = bt.client_summary(args.summary, days=args.days)
        print(json.dumps(s, indent=2))
    else:
        parser.print_help()
