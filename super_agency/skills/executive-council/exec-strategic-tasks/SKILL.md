# SKILL: exec-strategic-tasks
## Goal-Driven Autonomous Strategic Tasks

Implements the "brain dump your goals → autonomous daily tasks" pattern for
Agent AZ and the Executive Council.

### Triggers
- Cron: Daily at 8:00 AM — generate and schedule tasks
- Manual: "generate tasks", "what should I work on today"
- Event: When GOALS.md is updated

### What It Does
1. Reads stored goals and missions from memory
2. Cross-references with Intelligence Operations findings
3. Generates 4-5 autonomous tasks for the day
4. Distributes tasks to appropriate departments
5. Tracks completion on Kanban board / backlog system
6. Builds surprise mini-apps overnight for goal acceleration

### Goal Categories
- Business: Revenue targets, partnerships, portfolio growth
- Technical: System improvements, automation percentage
- Research: Intelligence gathering, trend analysis
- Operational: Uptime targets, process improvements

### Example Output
```
DAILY TASKS — [date]

1. [INTEL] Research competitor analysis for VORTEX-HUNTER niche → Intelligence Ops
2. [TECH] Implement auto-PR for failing CI repos → Technology Infrastructure
3. [FIN] Update earnings calendar for next week → Financial Operations
4. [OPS] Optimize Matrix Monitor dashboard → Operations Command
5. [SURPRISE] Build MVP price alert tool → overnight build via REPO DEPOT
```

### Dependencies
- OpenClawSystemBridge
- backlog_management_system.py
- agent_mandates.json (goals section)
- All department routers for task distribution
