# SKILL: exec-council-brief
## Executive Council Morning Strategy Brief

Generates a CEO-level morning strategy briefing for Agent AZ and the Executive Council.

### Triggers
- Cron: Daily at 7:00 AM
- Manual: "executive brief" or "strategy brief"

### What It Does
1. Aggregates overnight intelligence from all 5 departments
2. Highlights CRITICAL decisions requiring AZ_FINAL authority
3. Summarizes portfolio health across 27 repos
4. Reports agent performance metrics (GASKET, OPTIMUS, AZ)
5. Surfaces strategic opportunities from Intelligence Operations
6. Lists doctrine compliance status

### Data Sources
- All department routers via OpenClawSystemBridge
- portfolio.json — repo health, risk levels
- agent_mandates.json — target vs actual performance
- agent_protocols.json — escalation chain status
- repo_depot_status.json — build/deploy metrics
- unified_memory_doctrine.json — memory health

### Output Format
```
EXECUTIVE COUNCIL BRIEF — [date]

CRITICAL DECISIONS PENDING: [count]
[list of items requiring AZ_FINAL authority]

PORTFOLIO: [total repos] repos | [healthy]/[warning]/[critical]
TOP MOVERS: [repos with significant changes]

AGENT PERFORMANCE:
  GASKET: [uptime]% uptime | [tasks] tasks
  OPTIMUS: [completion]% completion rate
  AZ: [decisions] decisions | [escalations] escalations

INTELLIGENCE HIGHLIGHTS:
[top 3 insights from YouTube + Research divisions]

RECOMMENDED ACTIONS:
[AI-generated strategic recommendations]
```

### Dependencies
- OpenClawSystemBridge
- All department config.json files
- agent_mandates.json, agent_protocols.json
