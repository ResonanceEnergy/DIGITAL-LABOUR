"""BRL Task Manager — Orchestrates task lifecycle with NCL + Paperclip + NERVE integration.

The central brain that:
  1. Ingests tasks from all sources (manual, NCL, C-Suite, NERVE, scheduler)
  2. Prioritizes using NCL intelligence signals
  3. Routes to human or AI agents
  4. Tracks progress and syncs with the dispatcher queue
  5. Generates daily summaries for the Command Center

Usage:
    from task_management.manager import TaskManager

    mgr = TaskManager()
    task_id = mgr.create_task("Fix client landing page", category="client_work", client="acme")
    mgr.ingest_from_ncl()       # Pull tasks from NCL intelligence
    mgr.ingest_from_csuite()    # Pull tasks from C-Suite directives
    mgr.sync_with_dispatcher()  # Sync AI tasks to/from dispatcher queue
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from task_management.store import TaskStore

logger = logging.getLogger("brl.task_manager")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TaskManager:
    """Central task orchestration layer for BRL."""

    def __init__(self, store: TaskStore | None = None):
        self.store = store or TaskStore()

    # ── Manual Task Creation ──────────────────────────────────────

    def create_task(
        self,
        title: str,
        description: str = "",
        category: str = "internal",
        subcategory: str = "",
        priority: int = 5,
        owner_type: str = "human",
        owner_name: str = "",
        assigned_agent: str = "",
        client: str = "",
        due_date: str = "",
        tags: list[str] | None = None,
        estimated_hours: float = 0.0,
    ) -> str:
        """Create a task manually (from API, dashboard, or human input)."""
        task_id = self.store.create(
            title=title,
            description=description,
            category=category,
            subcategory=subcategory,
            priority=priority,
            owner_type=owner_type,
            owner_name=owner_name,
            assigned_agent=assigned_agent,
            client=client,
            source="manual",
            due_date=due_date,
            tags=tags,
            estimated_hours=estimated_hours,
        )
        logger.info("[TASK] Created %s: %s (category=%s, owner=%s)", task_id, title, category, owner_type)
        return task_id

    # ── NCL Intelligence Ingestion ────────────────────────────────

    def ingest_from_ncl(self) -> list[str]:
        """Pull intelligence from NCL bridge and create actionable tasks.

        Reads NCL daily briefs, event stream, and trinity health to
        generate tasks that need attention.
        """
        created = []
        try:
            from resonance.ncl_bridge import ncl

            if not ncl.available:
                logger.warning("[NCL] NCL data not available — skipping ingestion")
                return created

            # Check data freshness — stale data generates lower-priority tasks
            freshness = ncl.data_freshness()
            priority_boost = 0 if freshness.get("stale") else 2

            # Ingest from event stream
            events = ncl.recent_events(limit=20)
            for event in events:
                event_id = event.get("event_id", event.get("id", ""))
                event_type = event.get("type", event.get("event_type", "unknown"))
                summary = event.get("summary", event.get("title", "NCL event"))

                # Skip if we already have a task for this event
                existing = self.store.list_tasks(source="ncl")
                if any(t.get("ncl_event_id") == event_id for t in existing):
                    continue

                # Determine category from event type
                cat_map = {
                    "market_signal": "biz_dev",
                    "client_alert": "client_work",
                    "ops_alert": "internal",
                    "growth_opp": "biz_dev",
                    "outreach_trigger": "outreach",
                    "risk_alert": "internal",
                }
                category = cat_map.get(event_type, "internal")

                # Determine if AI can handle this or needs human
                ai_types = {"market_signal", "outreach_trigger", "growth_opp"}
                owner_type = "ai" if event_type in ai_types else "hybrid"

                task_id = self.store.create(
                    title=f"[NCL] {summary}",
                    description=f"Auto-generated from NCL event: {event_type}\n\nEvent data: {json.dumps(event, default=str)[:500]}",
                    category=category,
                    priority=5 + priority_boost + event.get("priority", 0),
                    owner_type=owner_type,
                    source="ncl",
                    source_ref=f"ncl:event:{event_id}",
                    ncl_event_id=event_id,
                    tags=["ncl", "auto-generated", event_type],
                )
                created.append(task_id)
                logger.info("[NCL→TASK] %s from event %s (%s)", task_id, event_id, event_type)

            # Check trinity health — drift triggers tasks
            health = ncl.trinity_health()
            if health and health.get("drift_count", 0) > 0:
                pillar_dirty = health.get("pillar_dirty", {})
                for pillar, score in pillar_dirty.items():
                    if score and score > 0:
                        task_id = self.store.create(
                            title=f"[NCL] Trinity drift: {pillar} pillar needs attention (score: {score})",
                            description=f"Trinity health check detected drift in {pillar} pillar.\nHealth score: {health.get('health_score', 'unknown')}",
                            category="internal",
                            subcategory="governance",
                            priority=7 + score,
                            owner_type="hybrid",
                            source="ncl",
                            source_ref=f"ncl:trinity:{pillar}",
                            tags=["ncl", "trinity", "governance", pillar.lower()],
                        )
                        created.append(task_id)

        except Exception as e:
            logger.error("[NCL] Ingestion failed: %s", e)

        return created

    # ── C-Suite Directive Ingestion ────────────────────────────────

    def ingest_from_csuite(self) -> list[str]:
        """Pull board directives and convert to trackable tasks.

        Reads the latest board session output (execution_queue)
        and creates tasks for each directive.
        """
        created = []
        try:
            board_output = PROJECT_ROOT / "data" / "board_output.json"
            if not board_output.exists():
                return created

            data = json.loads(board_output.read_text("utf-8"))
            execution_queue = data.get("execution_queue", [])

            for directive in execution_queue:
                dir_id = directive.get("id", directive.get("directive_id", ""))

                # Skip duplicates
                existing = self.store.list_tasks(source="c_suite")
                if any(t.get("directive_id") == dir_id for t in existing):
                    continue

                owner = directive.get("owner", "VECTIS")
                action = directive.get("action", directive.get("directive", "Board directive"))
                deadline = directive.get("deadline", "")
                rank = directive.get("rank", 5)

                # Map C-Suite owner to category
                cat_map = {"AXIOM": "biz_dev", "VECTIS": "internal", "LEDGR": "internal"}
                category = cat_map.get(owner, "internal")

                # Board directives are high-priority AI tasks
                task_id = self.store.create(
                    title=f"[{owner}] {action}",
                    description=f"C-Suite board directive.\nOwner: {owner}\nRank: {rank}\nSession: {data.get('session', 'unknown')}",
                    category=category,
                    priority=10 - rank + 1,  # rank 1 = priority 10
                    owner_type="ai",
                    assigned_agent=owner.lower(),
                    source="c_suite",
                    source_ref=f"csuite:board:{dir_id}",
                    directive_id=dir_id,
                    due_date=deadline,
                    tags=["c_suite", "board_directive", owner.lower()],
                )
                created.append(task_id)
                logger.info("[CSUITE→TASK] %s from directive %s (%s)", task_id, dir_id, owner)

        except Exception as e:
            logger.error("[CSUITE] Ingestion failed: %s", e)

        return created

    # ── NERVE Integration ─────────────────────────────────────────

    def ingest_from_nerve(self) -> list[str]:
        """Pull NERVE decisions and create/update tasks.

        NERVE runs autonomous cycles — its decisions become tasks
        or updates to existing tasks.
        """
        created = []
        try:
            decision_log = PROJECT_ROOT / "data" / "nerve_decisions.jsonl"
            if not decision_log.exists():
                return created

            lines = decision_log.read_text("utf-8").strip().splitlines()
            # Only process recent decisions (last 20)
            for line in lines[-20:]:
                try:
                    decision = json.loads(line)
                except json.JSONDecodeError:
                    continue

                cycle_id = decision.get("cycle_id", "")
                action = decision.get("action", "")
                detail = decision.get("detail", "")
                dtype = decision.get("type", "")

                # Skip non-actionable decisions
                if dtype in ("info", "log", "check"):
                    continue

                # Skip if already tracked
                existing = self.store.list_tasks(source="nerve")
                if any(t.get("nerve_cycle_id") == cycle_id and action in t.get("title", "") for t in existing):
                    continue

                # NERVE tasks are AI-owned by default
                task_id = self.store.create(
                    title=f"[NERVE] {action}",
                    description=f"NERVE autonomous decision.\nType: {dtype}\nDetail: {detail}\nCycle: {cycle_id}",
                    category="internal" if dtype != "outreach" else "outreach",
                    priority=6,
                    owner_type="ai",
                    source="nerve",
                    source_ref=f"nerve:decision:{cycle_id}",
                    nerve_cycle_id=cycle_id,
                    tags=["nerve", "autonomous", dtype],
                )
                created.append(task_id)

        except Exception as e:
            logger.error("[NERVE] Ingestion failed: %s", e)

        return created

    # ── Paperclip/Scheduler Integration ───────────────────────────

    def ingest_from_scheduler(self) -> list[str]:
        """Pull scheduled tasks from the scheduler runner.

        Reads client profiles and retainer schedules to create
        recurring deliverable tasks.
        """
        created = []
        try:
            clients_dir = PROJECT_ROOT / "clients"
            if not clients_dir.exists():
                return created

            for profile_path in clients_dir.glob("*/profile.json"):
                try:
                    profile = json.loads(profile_path.read_text("utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue

                client_id = profile.get("client_id", profile_path.parent.name)
                retainer = profile.get("retainer", {})
                deliverables = retainer.get("deliverables", [])

                for deliv in deliverables:
                    task_type = deliv.get("type", "content")
                    frequency = deliv.get("frequency", "weekly")
                    title = f"Client deliverable: {task_type} for {client_id}"

                    # Skip duplicates (check by title + client)
                    existing = self.store.list_tasks(client=client_id, source="scheduler")
                    if any(task_type in t.get("title", "") and t["status"] in ("pending", "in_progress") for t in existing):
                        continue

                    task_id = self.store.create(
                        title=title,
                        description=f"Retainer deliverable: {task_type}\nFrequency: {frequency}",
                        category="client_work",
                        priority=7,
                        owner_type="ai",
                        assigned_agent=task_type,
                        client=client_id,
                        source="scheduler",
                        recurrence=frequency,
                        tags=["retainer", "deliverable", task_type],
                    )
                    created.append(task_id)

        except Exception as e:
            logger.error("[SCHEDULER] Ingestion failed: %s", e)

        return created

    # ── Dispatcher Queue Sync ─────────────────────────────────────

    def sync_with_dispatcher(self) -> dict:
        """Two-way sync between task manager and dispatcher queue.

        - AI tasks in task_manager → enqueued in dispatcher if not already
        - Completed dispatcher tasks → update task_manager status
        """
        synced = {"pushed": 0, "pulled": 0}
        try:
            from dispatcher.queue import TaskQueue
            dq = TaskQueue()

            # Push: AI tasks pending → dispatcher queue
            ai_tasks = self.store.list_tasks(owner_type="ai", status="pending")
            for task in ai_tasks:
                if not task.get("assigned_agent"):
                    continue
                # Check if already in dispatcher
                dq_task = dq.list_tasks(client=task.get("client", ""), limit=100)
                already_queued = any(
                    t.get("task_type") == task.get("assigned_agent")
                    and t.get("status") in ("queued", "running")
                    for t in dq_task
                )
                if not already_queued:
                    dq.enqueue(
                        task_type=task["assigned_agent"],
                        inputs=task.get("inputs", {}),
                        client=task.get("client", ""),
                        priority=task.get("priority", 0),
                    )
                    self.store.update(task["task_id"], actor="dispatcher_sync", status="in_progress")
                    synced["pushed"] += 1

            # Pull: completed dispatcher tasks → update our records
            completed = dq.list_tasks(status="completed", limit=50)
            for dt in completed:
                # Find matching task in our store
                our_tasks = self.store.list_tasks(status="in_progress")
                for ot in our_tasks:
                    if (ot.get("assigned_agent") == dt.get("task_type") and
                            ot.get("client", "") == dt.get("client", "") and
                            ot.get("status") == "in_progress"):
                        self.store.update(
                            ot["task_id"],
                            actor="dispatcher_sync",
                            status="completed",
                            outputs=json.loads(dt["outputs"]) if isinstance(dt["outputs"], str) else dt["outputs"],
                            cost_usd=dt.get("cost_usd", 0.0),
                        )
                        synced["pulled"] += 1
                        break

        except Exception as e:
            logger.error("[SYNC] Dispatcher sync failed: %s", e)

        return synced

    # ── Full Ingestion Cycle ──────────────────────────────────────

    def run_ingestion_cycle(self) -> dict:
        """Run a full ingestion cycle from all sources.

        Called by NERVE during its hourly cycle, or manually via API.
        """
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ncl": [],
            "c_suite": [],
            "nerve": [],
            "scheduler": [],
            "sync": {},
        }

        results["ncl"] = self.ingest_from_ncl()
        results["c_suite"] = self.ingest_from_csuite()
        results["nerve"] = self.ingest_from_nerve()
        results["scheduler"] = self.ingest_from_scheduler()
        results["sync"] = self.sync_with_dispatcher()

        total = sum(len(v) for k, v in results.items() if isinstance(v, list))
        logger.info(
            "[CYCLE] Ingestion complete — %d new tasks (NCL:%d, C-Suite:%d, NERVE:%d, Sched:%d) | Sync: %s",
            total, len(results["ncl"]), len(results["c_suite"]),
            len(results["nerve"]), len(results["scheduler"]),
            results["sync"],
        )
        return results

    # ── Daily Summary ─────────────────────────────────────────────

    def daily_summary(self) -> dict:
        """Generate a daily summary for the Command Center dashboard."""
        stats = self.store.stats()
        overdue = self.store.overdue_tasks()
        human_tasks = self.store.list_tasks(owner_type="human", status="in_progress")
        ai_active = self.store.list_tasks(owner_type="ai", status="in_progress")

        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "stats": stats,
            "overdue_count": len(overdue),
            "overdue_tasks": [{"id": t["task_id"], "title": t["title"], "due": t["due_date"]} for t in overdue[:10]],
            "human_in_progress": len(human_tasks),
            "human_tasks": [{"id": t["task_id"], "title": t["title"], "priority": t["priority"]} for t in human_tasks[:10]],
            "ai_active": len(ai_active),
            "ai_tasks": [{"id": t["task_id"], "title": t["title"], "agent": t["assigned_agent"]} for t in ai_active[:10]],
        }
