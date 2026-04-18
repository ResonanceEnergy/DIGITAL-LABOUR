"""Revenue Tracker -- Multi-channel revenue tracking with per-agent economics.

Tracks revenue across all channels (fiverr, api_marketplace, white_label, direct,
cold_email, freelance), per-agent performance, cost-vs-revenue margins, and
client lifetime value.  Stores everything in SQLite at data/revenue.db.

Usage:
    from billing.revenue_tracker import RevenueTracker

    rt = RevenueTracker()
    rt.record_revenue("api_marketplace", "product_desc", "client_42", amount=1.50, cost=0.08)
    summary = rt.get_revenue_summary(days=30)
    print(summary)
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("billing.revenue_tracker")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "revenue.db"

# All recognised revenue channels
CHANNELS = {"fiverr", "api_marketplace", "white_label", "direct", "cold_email", "freelance"}

# All agent task types that can generate revenue
AGENT_TYPES = {
    "sales_outreach", "support_ticket", "content_repurpose", "doc_extract",
    "lead_gen", "email_marketing", "seo_content", "social_media",
    "data_entry", "web_scraper", "crm_ops", "bookkeeping",
    "proposal_writer", "product_desc", "resume_writer", "ad_copy",
    "market_research", "business_plan", "press_release", "tech_docs",
    "context_manager", "qa_manager", "production_manager", "automation_manager",
    "freelancer_work", "upwork_work", "fiverr_work", "pph_work", "guru_work",
}


class RevenueTracker:
    """SQLite-backed revenue tracking with channel, agent, and client dimensions."""

    def __init__(self, db_path: Optional[Path | str] = None):
        if db_path and str(db_path) == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path) if db_path else DB_PATH
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    # ── Database Setup ────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        """Create a new connection with row_factory and WAL mode."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        """Create the schema if it does not exist."""
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS revenue_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                channel     TEXT NOT NULL,
                agent       TEXT NOT NULL,
                client_id   TEXT NOT NULL DEFAULT 'anonymous',
                amount_usd  REAL NOT NULL DEFAULT 0.0,
                cost_usd    REAL NOT NULL DEFAULT 0.0,
                currency    TEXT NOT NULL DEFAULT 'USD',
                description TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS client_metrics (
                client_id     TEXT PRIMARY KEY,
                first_seen    TEXT NOT NULL,
                total_revenue REAL NOT NULL DEFAULT 0.0,
                total_tasks   INTEGER NOT NULL DEFAULT 0,
                last_active   TEXT NOT NULL,
                channel       TEXT NOT NULL DEFAULT 'direct'
            );

            CREATE TABLE IF NOT EXISTS daily_summaries (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       TEXT NOT NULL,
                channel    TEXT NOT NULL,
                revenue    REAL NOT NULL DEFAULT 0.0,
                costs      REAL NOT NULL DEFAULT 0.0,
                profit     REAL NOT NULL DEFAULT 0.0,
                task_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(date, channel)
            );

            -- Indexes for fast lookups
            CREATE INDEX IF NOT EXISTS idx_rev_timestamp ON revenue_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_rev_channel   ON revenue_events(channel);
            CREATE INDEX IF NOT EXISTS idx_rev_agent     ON revenue_events(agent);
            CREATE INDEX IF NOT EXISTS idx_rev_client    ON revenue_events(client_id);
            CREATE INDEX IF NOT EXISTS idx_daily_date    ON daily_summaries(date);
            CREATE INDEX IF NOT EXISTS idx_client_ltv    ON client_metrics(total_revenue DESC);
        """)
        conn.commit()
        conn.close()
        logger.debug("[REVENUE] Database initialized at %s", self.db_path)

    # ── Core Recording ────────────────────────────────────────────────────────

    def record_revenue(
        self,
        channel: str,
        agent: str,
        client_id: str,
        amount: float,
        cost: float = 0.0,
        description: str = "",
        currency: str = "USD",
    ) -> dict:
        """Record a revenue event and update all derived tables.

        Args:
            channel:     Revenue channel (fiverr, api_marketplace, white_label, direct, cold_email, freelance).
            agent:       Agent task type that performed the work (e.g. product_desc).
            client_id:   Unique client identifier for LTV tracking.
            amount:      Revenue amount in USD (what the client paid).
            cost:        LLM/infrastructure cost in USD.
            description: Human-readable note (e.g. "5x product descriptions for Amazon store").
            currency:    Currency code (default USD).

        Returns:
            Dict with event_id, profit, and margin_pct.
        """
        if channel not in CHANNELS:
            logger.warning("[REVENUE] Unknown channel '%s' — recording anyway", channel)
        if agent not in AGENT_TYPES:
            logger.warning("[REVENUE] Unknown agent '%s' — recording anyway", agent)
        if amount < 0:
            raise ValueError("Revenue amount cannot be negative")
        if cost < 0:
            raise ValueError("Cost cannot be negative")

        now = datetime.now(timezone.utc).isoformat()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        profit = round(amount - cost, 4)
        margin_pct = round((profit / amount * 100), 1) if amount > 0 else 0.0

        with self._lock:
            conn = self._conn()
            try:
                # 1. Insert the revenue event
                cursor = conn.execute(
                    """INSERT INTO revenue_events
                       (timestamp, channel, agent, client_id, amount_usd, cost_usd, currency, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (now, channel, agent, client_id, amount, cost, currency, description),
                )
                event_id = cursor.lastrowid

                # 2. Upsert client_metrics
                conn.execute(
                    """INSERT INTO client_metrics (client_id, first_seen, total_revenue, total_tasks, last_active, channel)
                       VALUES (?, ?, ?, 1, ?, ?)
                       ON CONFLICT(client_id) DO UPDATE SET
                           total_revenue = total_revenue + ?,
                           total_tasks = total_tasks + 1,
                           last_active = ?,
                           channel = CASE WHEN excluded.channel != '' THEN excluded.channel ELSE client_metrics.channel END""",
                    (client_id, now, amount, now, channel, amount, now),
                )

                # 3. Upsert daily_summaries
                conn.execute(
                    """INSERT INTO daily_summaries (date, channel, revenue, costs, profit, task_count)
                       VALUES (?, ?, ?, ?, ?, 1)
                       ON CONFLICT(date, channel) DO UPDATE SET
                           revenue = revenue + ?,
                           costs = costs + ?,
                           profit = profit + ?,
                           task_count = task_count + 1""",
                    (today, channel, amount, cost, profit, amount, cost, profit),
                )

                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        logger.info(
            "[REVENUE] +$%.2f (cost $%.4f) | %s/%s | client=%s | margin=%.1f%%",
            amount, cost, channel, agent, client_id, margin_pct,
        )

        return {
            "event_id": event_id,
            "amount": amount,
            "cost": cost,
            "profit": profit,
            "margin_pct": margin_pct,
            "channel": channel,
            "agent": agent,
            "client_id": client_id,
        }

    # ── Revenue Summary ───────────────────────────────────────────────────────

    def get_revenue_summary(self, days: int = 30) -> dict:
        """Get an overall revenue summary for the last N days.

        Returns total revenue, costs, profit, margin, task count, and
        breakdowns by day.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        conn = self._conn()

        # Aggregates from daily_summaries
        row = conn.execute(
            """SELECT
                   COALESCE(SUM(revenue), 0) as total_revenue,
                   COALESCE(SUM(costs), 0) as total_costs,
                   COALESCE(SUM(profit), 0) as total_profit,
                   COALESCE(SUM(task_count), 0) as total_tasks
               FROM daily_summaries
               WHERE date >= ?""",
            (cutoff,),
        ).fetchone()

        total_revenue = row["total_revenue"]
        total_costs = row["total_costs"]
        total_profit = row["total_profit"]
        total_tasks = row["total_tasks"]

        # Daily breakdown
        daily_rows = conn.execute(
            """SELECT date,
                      SUM(revenue) as revenue,
                      SUM(costs) as costs,
                      SUM(profit) as profit,
                      SUM(task_count) as tasks
               FROM daily_summaries
               WHERE date >= ?
               GROUP BY date
               ORDER BY date DESC""",
            (cutoff,),
        ).fetchall()

        daily = [
            {
                "date": r["date"],
                "revenue": round(r["revenue"], 2),
                "costs": round(r["costs"], 4),
                "profit": round(r["profit"], 2),
                "tasks": r["tasks"],
            }
            for r in daily_rows
        ]

        conn.close()

        avg_daily = round(total_revenue / max(days, 1), 2)
        margin_pct = round((total_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0

        return {
            "period_days": days,
            "total_revenue": round(total_revenue, 2),
            "total_costs": round(total_costs, 4),
            "total_profit": round(total_profit, 2),
            "margin_pct": margin_pct,
            "total_tasks": total_tasks,
            "avg_daily_revenue": avg_daily,
            "projected_monthly": round(avg_daily * 30, 2),
            "daily": daily,
        }

    # ── Agent Performance ─────────────────────────────────────────────────────

    def get_agent_performance(self, days: int = 30) -> dict:
        """Get revenue and margin breakdown per agent.

        Returns a dict keyed by agent name with tasks, revenue, cost, profit,
        margin, and avg_revenue_per_task.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = self._conn()

        rows = conn.execute(
            """SELECT agent,
                      COUNT(*) as tasks,
                      COALESCE(SUM(amount_usd), 0) as revenue,
                      COALESCE(SUM(cost_usd), 0) as cost
               FROM revenue_events
               WHERE timestamp >= ?
               GROUP BY agent
               ORDER BY revenue DESC""",
            (cutoff,),
        ).fetchall()
        conn.close()

        agents = {}
        for r in rows:
            revenue = r["revenue"]
            cost = r["cost"]
            profit = revenue - cost
            margin = round((profit / revenue * 100), 1) if revenue > 0 else 0.0
            avg_rev = round(revenue / r["tasks"], 2) if r["tasks"] > 0 else 0.0
            agents[r["agent"]] = {
                "tasks": r["tasks"],
                "revenue": round(revenue, 2),
                "cost": round(cost, 4),
                "profit": round(profit, 2),
                "margin_pct": margin,
                "avg_revenue_per_task": avg_rev,
            }

        return {
            "period_days": days,
            "agent_count": len(agents),
            "agents": agents,
        }

    # ── Channel Breakdown ─────────────────────────────────────────────────────

    def get_channel_breakdown(self, days: int = 30) -> dict:
        """Get revenue breakdown by channel.

        Returns per-channel revenue, costs, profit, task count, and
        percentage of total revenue.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        conn = self._conn()

        rows = conn.execute(
            """SELECT channel,
                      COALESCE(SUM(revenue), 0) as revenue,
                      COALESCE(SUM(costs), 0) as costs,
                      COALESCE(SUM(profit), 0) as profit,
                      COALESCE(SUM(task_count), 0) as tasks
               FROM daily_summaries
               WHERE date >= ?
               GROUP BY channel
               ORDER BY revenue DESC""",
            (cutoff,),
        ).fetchall()

        # Total for percentage calculation
        total_rev = sum(r["revenue"] for r in rows) or 1.0

        conn.close()

        channels = {}
        for r in rows:
            channels[r["channel"]] = {
                "revenue": round(r["revenue"], 2),
                "costs": round(r["costs"], 4),
                "profit": round(r["profit"], 2),
                "tasks": r["tasks"],
                "pct_of_total": round(r["revenue"] / total_rev * 100, 1),
            }

        return {
            "period_days": days,
            "total_revenue": round(sum(r["revenue"] for r in rows), 2),
            "channels": channels,
        }

    # ── Client Lifetime Value ─────────────────────────────────────────────────

    def get_client_ltv(self, client_id: str) -> dict:
        """Get lifetime value metrics for a specific client.

        Returns total revenue, total tasks, average revenue per task,
        first seen, last active, tenure days, and channel.
        """
        conn = self._conn()

        client_row = conn.execute(
            "SELECT * FROM client_metrics WHERE client_id = ?", (client_id,)
        ).fetchone()

        if not client_row:
            conn.close()
            return {
                "client_id": client_id,
                "found": False,
                "total_revenue": 0.0,
                "total_tasks": 0,
            }

        # Per-agent breakdown for this client
        agent_rows = conn.execute(
            """SELECT agent,
                      COUNT(*) as tasks,
                      COALESCE(SUM(amount_usd), 0) as revenue
               FROM revenue_events
               WHERE client_id = ?
               GROUP BY agent
               ORDER BY revenue DESC""",
            (client_id,),
        ).fetchall()

        # Monthly revenue trend
        monthly_rows = conn.execute(
            """SELECT strftime('%Y-%m', timestamp) as month,
                      COALESCE(SUM(amount_usd), 0) as revenue,
                      COUNT(*) as tasks
               FROM revenue_events
               WHERE client_id = ?
               GROUP BY month
               ORDER BY month DESC
               LIMIT 12""",
            (client_id,),
        ).fetchall()

        conn.close()

        total_revenue = client_row["total_revenue"]
        total_tasks = client_row["total_tasks"]
        first_seen = client_row["first_seen"]
        last_active = client_row["last_active"]

        # Calculate tenure
        try:
            first_dt = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
            last_dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
            tenure_days = max((last_dt - first_dt).days, 1)
        except (ValueError, AttributeError):
            tenure_days = 1

        avg_per_task = round(total_revenue / total_tasks, 2) if total_tasks > 0 else 0.0
        monthly_avg = round(total_revenue / max(tenure_days / 30, 1), 2)

        return {
            "client_id": client_id,
            "found": True,
            "total_revenue": round(total_revenue, 2),
            "total_tasks": total_tasks,
            "avg_revenue_per_task": avg_per_task,
            "monthly_avg_revenue": monthly_avg,
            "first_seen": first_seen,
            "last_active": last_active,
            "tenure_days": tenure_days,
            "channel": client_row["channel"],
            "agents_used": {
                r["agent"]: {"tasks": r["tasks"], "revenue": round(r["revenue"], 2)}
                for r in agent_rows
            },
            "monthly_trend": [
                {"month": r["month"], "revenue": round(r["revenue"], 2), "tasks": r["tasks"]}
                for r in monthly_rows
            ],
        }

    # ── Client Rankings ───────────────────────────────────────────────────────

    def get_client_rankings(self, limit: int = 50) -> list[dict]:
        """Return top clients ranked by total lifetime revenue."""
        conn = self._conn()
        rows = conn.execute(
            """SELECT client_id, total_revenue, total_tasks, first_seen, last_active, channel
               FROM client_metrics
               ORDER BY total_revenue DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()

        return [
            {
                "client_id": r["client_id"],
                "total_revenue": round(r["total_revenue"], 2),
                "total_tasks": r["total_tasks"],
                "avg_per_task": round(r["total_revenue"] / max(r["total_tasks"], 1), 2),
                "first_seen": r["first_seen"],
                "last_active": r["last_active"],
                "channel": r["channel"],
            }
            for r in rows
        ]

    # ── Weekly / Monthly Summaries ────────────────────────────────────────────

    def get_weekly_summary(self, weeks: int = 4) -> list[dict]:
        """Get revenue summaries aggregated by ISO week."""
        cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
        conn = self._conn()
        rows = conn.execute(
            """SELECT strftime('%Y-W%W', date) as week,
                      SUM(revenue) as revenue,
                      SUM(costs) as costs,
                      SUM(profit) as profit,
                      SUM(task_count) as tasks
               FROM daily_summaries
               WHERE date >= ?
               GROUP BY week
               ORDER BY week DESC""",
            (cutoff,),
        ).fetchall()
        conn.close()

        return [
            {
                "week": r["week"],
                "revenue": round(r["revenue"], 2),
                "costs": round(r["costs"], 4),
                "profit": round(r["profit"], 2),
                "tasks": r["tasks"],
                "margin_pct": round(r["profit"] / r["revenue"] * 100, 1) if r["revenue"] > 0 else 0.0,
            }
            for r in rows
        ]

    def get_monthly_summary(self, months: int = 6) -> list[dict]:
        """Get revenue summaries aggregated by month."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=months * 30)).strftime("%Y-%m-%d")
        conn = self._conn()
        rows = conn.execute(
            """SELECT strftime('%Y-%m', date) as month,
                      SUM(revenue) as revenue,
                      SUM(costs) as costs,
                      SUM(profit) as profit,
                      SUM(task_count) as tasks
               FROM daily_summaries
               WHERE date >= ?
               GROUP BY month
               ORDER BY month DESC""",
            (cutoff,),
        ).fetchall()
        conn.close()

        return [
            {
                "month": r["month"],
                "revenue": round(r["revenue"], 2),
                "costs": round(r["costs"], 4),
                "profit": round(r["profit"], 2),
                "tasks": r["tasks"],
                "margin_pct": round(r["profit"] / r["revenue"] * 100, 1) if r["revenue"] > 0 else 0.0,
            }
            for r in rows
        ]

    # ── Rebuild Daily Summaries ───────────────────────────────────────────────

    def rebuild_daily_summaries(self) -> int:
        """Rebuild daily_summaries from revenue_events (idempotent repair tool).

        Returns the number of summary rows created.
        """
        conn = self._conn()
        conn.execute("DELETE FROM daily_summaries")
        conn.execute(
            """INSERT INTO daily_summaries (date, channel, revenue, costs, profit, task_count)
               SELECT
                   strftime('%Y-%m-%d', timestamp) as date,
                   channel,
                   SUM(amount_usd) as revenue,
                   SUM(cost_usd) as costs,
                   SUM(amount_usd - cost_usd) as profit,
                   COUNT(*) as task_count
               FROM revenue_events
               GROUP BY date, channel"""
        )
        count = conn.execute("SELECT COUNT(*) FROM daily_summaries").fetchone()[0]
        conn.commit()
        conn.close()
        logger.info("[REVENUE] Rebuilt %d daily summary rows", count)
        return count


# ── Module-level convenience functions ────────────────────────────────────────

_default_tracker: Optional[RevenueTracker] = None
_tracker_lock = threading.Lock()


def _get_tracker() -> RevenueTracker:
    """Lazy singleton for the default tracker instance."""
    global _default_tracker
    if _default_tracker is None:
        with _tracker_lock:
            if _default_tracker is None:
                _default_tracker = RevenueTracker()
    return _default_tracker


def record_revenue(
    channel: str,
    agent: str,
    client_id: str,
    amount: float,
    cost: float = 0.0,
    description: str = "",
) -> dict:
    """Record a revenue event using the default tracker instance."""
    return _get_tracker().record_revenue(
        channel=channel, agent=agent, client_id=client_id,
        amount=amount, cost=cost, description=description,
    )


def get_revenue_summary(days: int = 30) -> dict:
    """Get overall revenue summary using the default tracker instance."""
    return _get_tracker().get_revenue_summary(days=days)


def get_agent_performance(days: int = 30) -> dict:
    """Get per-agent performance using the default tracker instance."""
    return _get_tracker().get_agent_performance(days=days)


def get_channel_breakdown(days: int = 30) -> dict:
    """Get per-channel revenue breakdown using the default tracker instance."""
    return _get_tracker().get_channel_breakdown(days=days)


def get_client_ltv(client_id: str) -> dict:
    """Get lifetime value for a specific client using the default tracker instance."""
    return _get_tracker().get_client_ltv(client_id=client_id)


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DIGITAL LABOUR Revenue Tracker")
    parser.add_argument("--summary", action="store_true", help="Revenue summary")
    parser.add_argument("--agents", action="store_true", help="Agent performance")
    parser.add_argument("--channels", action="store_true", help="Channel breakdown")
    parser.add_argument("--client", type=str, help="Client LTV lookup")
    parser.add_argument("--rankings", action="store_true", help="Client LTV rankings")
    parser.add_argument("--weekly", action="store_true", help="Weekly summaries")
    parser.add_argument("--monthly", action="store_true", help="Monthly summaries")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild daily summaries from events")
    parser.add_argument("--days", type=int, default=30, help="Lookback period in days")
    args = parser.parse_args()

    rt = RevenueTracker()

    if args.summary:
        print(json.dumps(rt.get_revenue_summary(days=args.days), indent=2))
    elif args.agents:
        print(json.dumps(rt.get_agent_performance(days=args.days), indent=2))
    elif args.channels:
        print(json.dumps(rt.get_channel_breakdown(days=args.days), indent=2))
    elif args.client:
        print(json.dumps(rt.get_client_ltv(args.client), indent=2))
    elif args.rankings:
        print(json.dumps(rt.get_client_rankings(), indent=2))
    elif args.weekly:
        print(json.dumps(rt.get_weekly_summary(), indent=2))
    elif args.monthly:
        print(json.dumps(rt.get_monthly_summary(), indent=2))
    elif args.rebuild:
        count = rt.rebuild_daily_summaries()
        print(f"Rebuilt {count} daily summary rows.")
    else:
        parser.print_help()
