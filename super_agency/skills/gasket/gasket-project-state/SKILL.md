# gasket-project-state

## Event-Driven Project State Management

**Type**: always-on
**Trigger**: natural language + git hooks + cron (daily standup)
**Model**: any

## Description

Replaces traditional Kanban boards with event-driven project tracking. Talk naturally about progress ("finished auth flow, starting dashboard") and the system logs structured events, updates state, and auto-generates daily standups. Full history of decisions, pivots, blockers, and progress — queryable via natural language.

## Event Types

| Event | Fields | Example |
|-------|--------|---------|
| `progress` | project, task, status, notes | "Finished auth flow for Super-Agency dashboard" |
| `blocker` | project, description, severity | "Git sync blocking operations" |
| `decision` | project, what, why, alternatives | "Decided to migrate to local SSD for git" |
| `pivot` | project, from, to, reason | "Pivoting from Windows-only to cross-platform" |

## State Storage

```
~/repos/Super-Agency/project_state/
├── events.db          # SQLite: full event history
├── STATE.yaml         # Current state (single source of truth)
├── standup/           # Daily auto-generated standups
│   ├── 2026-02-27.md
│   └── ...
└── decisions/         # Decision log (searchable)
```

## Daily Standup Generation (Cron 8:30 AM)

1. Query events from last 24 hours
2. Query git commits (branch patterns, commit messages)
3. Auto-link commits to projects by branch name / message keywords
4. Generate standup: Yesterday / Today / Blockers / Decisions
5. Post to Telegram/Discord

## Natural Language Queries

- "Why did we pivot on the git setup?" → searches decision events
- "What's blocking the deployment?" → queries active blockers
- "Show me all progress on GASKET this week" → filtered event log
- "What decisions were made about OpenClaw?" → decision history

## Integration with GASKET

```python
async def log_project_event(self, event_type: str, project: str, details: dict):
    """Log a structured project event."""
    event = {
        'timestamp': datetime.now().isoformat(),
        'type': event_type,
        'project': project,
        **details
    }
    await self._store_event(event)
    await self._update_state_yaml(project)
```

## Super-Agency Specific

- Projects: Super-Agency, VORTEX-HUNTER, AAC, GASKET, OpenClaw Integration
- Git repos auto-linked: commits → projects → events
- Cross-machine tracking (QUANTUM FORGE + Quantum Quasar)
