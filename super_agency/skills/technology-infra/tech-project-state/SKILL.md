# SKILL: tech-project-state
## Event-Driven Project State Management (STATE.yaml)

Maintains a living STATE.yaml per repo that tracks milestones, blockers,
decisions, and progress. Updated automatically by agent activity and
commit hooks. Powers autonomous project management across 27 repos.

### Triggers
- Event: Git push to any managed repo → update STATE.yaml
- Event: CI/CD pipeline completes → update build status
- Event: Agent creates/resolves blocker → update blockers section
- Cron: Daily at midnight — full state reconciliation across all repos
- Manual: "project state [repo]", "what's the status of [project]"

### What It Does
1. Maintains `STATE.yaml` at root of each managed repo
2. Listens for events (git push, CI result, agent action, manual update)
3. Automatically updates relevant section of STATE.yaml
4. Tracks: milestones (% complete), blockers (open/resolved), decisions (log),
   active branches, PR status, test coverage, deploy status
5. Cross-references with REPO DEPOT for repo health metrics
6. Generates weekly project progress report across all 27 repos

### STATE.yaml Schema
```yaml
project: Digital-Labour
version: 1.0.0
last_updated: 2026-02-27T06:00:00Z
updated_by: agent/GASKET

milestones:
  - name: "OpenClaw Full Integration"
    target: 2026-03-15
    progress: 65%
    status: on-track
    tasks:
      - "Department skills deployment" — done
      - "Cross-department routing" — in-progress
      - "Voice integration" — not-started

blockers:
  - id: BLK-001
    title: "QUSAR CI failing on main"
    severity: medium
    created: 2026-02-26
    assigned: tech-infra
    status: open

decisions:
  - date: 2026-02-27
    decision: "Migrate from cloud sync to local SSD for git operations"
    rationale: "Cloud sync causing index.lock contention with 15K files"
    decided_by: CEO
    status: implemented

active_work:
  branches: ["main", "ci-enable-tests"]
  open_prs: 2
  last_commit: "131d049"
  test_coverage: 72%
```

### Cross-Repo Aggregation
```
27 Repos → STATE.yaml per repo → Aggregated Project Dashboard
  Digital-Labour ......... 65% ████████░░░░
  QUSAR ................ 80% ██████████░░
  NCL .................. 45% ██████░░░░░░
  TESLACALLS2026 ....... 90% ███████████░
  future-predictor ..... 30% ████░░░░░░░░
  ...
```

### Dependencies
- project-state skill (clawhub install project-state)
- REPO DEPOT github_sync (for commit events)
- Git webhook or polling (for push detection)
- CI/CD pipeline integration (GitHub Actions)
- Development Operations Division agents
