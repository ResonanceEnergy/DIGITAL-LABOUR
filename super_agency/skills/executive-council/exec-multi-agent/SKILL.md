# SKILL: exec-multi-agent
## Executive Multi-Agent Team Coordination

Enables the C-suite agents (CEO, CFO, CTO, CIO, CMO) to operate as a coordinated
multi-agent team via OpenClaw sessions, following the Multi-Agent Specialized Team pattern.

### Triggers
- Manual: "@ceo", "@cfo", "@cto", "@cio", "@cmo" in any channel
- Cron: Scheduled standup at 9:00 AM daily

### What It Does
1. Each C-suite agent runs as a distinct OpenClaw session with SOUL.md persona
2. Shared memory via GOALS.md, DECISIONS.md, PROJECT_STATUS.md
3. Private context per agent for domain-specific notes
4. Single control plane via Telegram/Discord group chat
5. Agents proactively work on scheduled daily tasks
6. Parallel execution — multiple agents work simultaneously

### Agent Personas
| Agent | Role | Model | Schedule |
|---|---|---|---|
| CEO | Strategic vision, culture | Claude Opus | 8 AM standup, 6 PM recap |
| CFO | Finance, budget, risk | Claude Sonnet | 9 AM metrics pull |
| CTO | Architecture, tech stack | Claude Opus | CI/CD health, PR review |
| CIO | Data, intelligence, analytics | Claude Sonnet | 10 AM intel digest |
| CMO | Marketing, brand, content | Gemini | Content ideas, social monitoring |

### Shared Memory Structure
```
team/
├── GOALS.md         — Current OKRs (all agents read)
├── DECISIONS.md     — Decision log (append-only)
├── PROJECT_STATUS.md — Current state (updated by all)
├── agents/
│   ├── ceo/         — CEO private context
│   ├── cfo/         — CFO private context
│   ├── cto/         — CTO private context
│   ├── cio/         — CIO private context
│   └── cmo/         — CMO private context
```

### Dependencies
- OpenClawSystemBridge.spawn_council_session()
- agents/ceo_agent.py, cfo_agent.py, cto_agent.py, cio_agent.py, cmo_agent.py
- sessions_spawn / sessions_send for multi-agent orchestration
