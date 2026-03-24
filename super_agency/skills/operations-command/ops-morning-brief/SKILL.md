# SKILL: ops-morning-brief
## Unified Operations Morning Brief

Aggregates overnight activity from every department, subsystem, and agent
into a single CEO-ready morning brief delivered at startup.

### Triggers
- Cron: Daily at 6:00 AM (before CEO morning review)
- Manual: "morning brief", "overnight report", "what happened"
- Event: First terminal open of the day

### What It Does
1. Queries each department for overnight activity summary
2. Pulls REPO DEPOT overnight commits across 27 repos
3. Checks Memory Doctrine for new persistent entries
4. Reviews Matrix Monitor for agent anomalies
5. Scans NCC command log for overnight executions
6. Checks build pipeline (QForge) for completed/failed builds
7. Pulls Calendar events for today
8. Aggregates into priority-sorted brief
9. Delivers via OpenClaw chat + optional voice synthesis

### Brief Sections
| Section | Source | Priority |
|---|---|---|
| Critical Alerts | Self-heal log, Matrix Monitor | P0 |
| Overnight Commits | REPO DEPOT github_sync | P1 |
| Build Results | QForge, CI/CD pipelines | P1 |
| Department Reports | 5 department overnight summaries | P2 |
| Market Moves | Financial Ops overnight scan | P2 |
| News Highlights | Intel Ops digest (top 5) | P3 |
| Today's Schedule | Calendar integration | P3 |
| Agent Health | Matrix Monitor performance | P3 |

### Cross-Department Aggregation
```
Operations Command Morning Brief Collector
  → Executive Council: strategic decisions pending
  → Intelligence Ops: overnight research findings
  → Operations Command: system health + self-heal actions
  → Tech Infrastructure: builds, deploys, PRs merged
  → Financial Ops: market movers, earnings alerts
```

### Output Format
```
GOOD MORNING — [date] — SUPER-AGENCY DAILY BRIEF

🔴 CRITICAL (0)
   No critical issues overnight.

🟡 ATTENTION (2)
   [1] REPO DEPOT: 3 repos have failing CI — QUSAR, NCL, VORTEX-HUNTER
   [2] Memory: Persistent storage at 78% capacity

📊 OVERNIGHT ACTIVITY
   Commits: 14 across 7 repos
   Builds: 11 succeeded, 2 failed
   Agents: 47 healthy, 0 degraded
   Documents: 23 new NCL entries ingested
   Commands: 8 NCC commands executed (all success)

📰 TOP NEWS
   [1] "OpenAI releases GPT-5 preview" — Score: 11
   [2] "Anthropic Claude Code v2 launched" — Score: 9

📅 TODAY'S SCHEDULE
   09:00  Council strategy review
   14:00  Portfolio rebalance window

💰 MARKET
   TSLA: +2.3% premarket | SPY: +0.4%
   Earnings today: NVDA (after hours)
```

### Dependencies
- morning-brief skill (clawhub install morning-brief)
- All 5 department query endpoints
- REPO DEPOT status.json + github_sync
- Matrix Monitor API
- Memory Doctrine health check
- NCC command log
- Calendar API (optional)
