# SKILL: ops-task-sync
## Todoist Task Visibility & Sync

Provides bidirectional sync between Super-Agency backlog systems and Todoist,
giving CEO full visibility into agent-generated tasks, manual tasks, and
department work items from any device.

### Triggers
- Cron: Every 15 minutes (sync cycle)
- Event: New task created in backlog system
- Event: Task completed in Todoist
- Manual: "sync tasks", "show my tasks", "what's on the list"

### What It Does
1. Pulls tasks from all Super-Agency backlog sources:
   - `backlog_management_system.py` — Agent-generated backlog items
   - `backlog_intelligence_system.py` — Intelligence-flagged items
   - Department task queues — Per-department work items
   - REPO DEPOT build tasks — Failed builds needing attention
   - Self-heal unresolved items — Manual intervention needed
2. Transforms into Todoist-compatible format with labels and priorities
3. Pushes to Todoist via API (creates/updates/completes)
4. Pulls manually-created Todoist tasks back into agent backlog
5. Assigns to appropriate department based on labels

### Task Mapping
| Source | Todoist Project | Priority |
|---|---|---|
| Self-heal failures | Operations / Critical | P1 |
| Failed builds | Technology / Builds | P2 |
| Intelligence alerts | Intelligence / Alerts | P2 |
| Backlog items | Backlog / [Department] | P3 |
| Agent suggestions | Suggestions / Review | P4 |
| Manual Todoist entries | Inbox → Auto-route | As set |

### Label Schema
```
@department/executive-council
@department/intelligence-ops
@department/operations-command
@department/tech-infra
@department/financial-ops
@agent/GASKET
@agent/OPTIMUS
@agent/AZ
@source/self-heal
@source/repo-depot
@source/matrix-monitor
@needs-review
@auto-generated
```

### Bidirectional Flow
```
Super-Agency Backlog ←→ OpenClaw Skill ←→ Todoist API
        ↑                                      ↓
 Agent creates task              CEO marks complete on phone
        ↓                                      ↑
 Appears in Todoist              Task marked done in backlog
```

### Output Format
```
TASK SYNC REPORT — [timestamp]

Synced: 47 tasks across 5 projects
  Created in Todoist: 3 new
  Updated: 8 status changes
  Completed: 2 marked done (from Todoist)

New Tasks:
  [P1] Fix QUSAR CI failure — @department/tech-infra @source/repo-depot
  [P2] Review intel alert: GPT-5 impact — @department/intelligence-ops
  [P3] Rebalance portfolio tier weights — @department/financial-ops

Completed:
  ✅ Update Memory Doctrine backup schedule
  ✅ Review REPO DEPOT flywheel config
```

### Dependencies
- todoist skill (clawhub install todoist)
- Todoist API token (TODOIST_API_KEY)
- backlog_management_system.py
- backlog_intelligence_system.py
- Department task queue endpoints
