# OPENCLAW INTEGRATION MAP — DIGITAL LABOUR
## Comprehensive Cross-System Integration Plan v1.0 | 2026-02-27

---

## OVERVIEW

This document maps ALL 30 OpenClaw use cases from the awesome-openclaw-usecases collection
across every agent, department, division, and subsystem in the DIGITAL LABOUR. OpenClaw is
no longer just a GASKET integration — it is a **system-wide AI gateway** serving all 5
departments, 47+ Inner Council agents, 6 Portfolio agents, the NCC/NCL stack, REPO DEPOT,
Matrix Monitor, and all 27 managed repos.

**OpenClaw Gateway**: `ws://127.0.0.1:18789` (Quantum Quasar macOS)
**Skills Directory**: `~/.openclaw/skills/`
**Memory**: Plain Markdown files + vector search

---

## DEPARTMENT → USE CASE MATRIX

| # | Use Case | Primary Department | Agents | Priority |
|---|----------|-------------------|--------|----------|
| 1 | Custom Morning Brief | Operations Command | daily_brief.py, orchestrator.py | CRITICAL |
| 2 | Self-Healing Home Server | Operations Command | repo_sentry.py, GASKET | CRITICAL |
| 3 | Dynamic Dashboard | Operations Command | matrix_monitor, qa_dashboard | HIGH |
| 4 | Project State Management | Technology Infrastructure | REPO DEPOT, backlog_management | HIGH |
| 5 | Autonomous Project Management | Technology Infrastructure | REPO DEPOT flywheel, agent_controller | HIGH |
| 6 | Second Brain | Intelligence Operations | NCL Second Brain, memory_doctrine | CRITICAL |
| 7 | Knowledge Base (RAG) | Intelligence Operations | NCL engine, summarizer | HIGH |
| 8 | Semantic Memory Search | Intelligence Operations | memory_doctrine, memsearch | HIGH |
| 9 | Daily YouTube Digest | Intelligence Operations | YouTube Intelligence Division | HIGH |
| 10 | Daily Reddit Digest | Intelligence Operations | Research Intelligence Division | MEDIUM |
| 11 | Multi-Source Tech News Digest | Intelligence Operations | All research agents | HIGH |
| 12 | YouTube Content Pipeline | Intelligence Operations | YouTube Division + content agents | MEDIUM |
| 13 | Multi-Agent Content Factory | Intelligence Operations | Inner Council (47 agents) | MEDIUM |
| 14 | X Account Analysis | Intelligence Operations | CMO Agent, bird skill | MEDIUM |
| 15 | Multi-Agent Specialized Team | Executive Council | CEO/CFO/CTO/CIO/CMO + AZ | CRITICAL |
| 16 | Autonomous Game Dev Pipeline | Technology Infrastructure | REPO DEPOT builder_agents | LOW |
| 17 | n8n Workflow Orchestration | Technology Infrastructure | conductor_agent, integration_master | HIGH |
| 18 | Todoist Task Manager | Operations Command | show_agent_tasks, backlog_mgmt | MEDIUM |
| 19 | Multi-Channel Assistant | Operations Command | GASKET, NCC orchestrator | HIGH |
| 20 | Multi-Channel Customer Service | Financial Operations | NCC adapters, api_mgmt | MEDIUM |
| 21 | Personal CRM | Financial Operations | portfolio_intel, portfolio_maintainer | MEDIUM |
| 22 | Inbox Declutter | Operations Command | daily_brief, orchestrator | MEDIUM |
| 23 | Phone-Based Personal Assistant | Operations Command | GASKET voice skill | LOW |
| 24 | Event Guest Confirmation | Operations Command | SuperCall, voice | LOW |
| 25 | AI Earnings Tracker | Financial Operations | TESLACALLS2026, future-predictor | HIGH |
| 26 | Market Research & Product Factory | Intelligence Operations | future-predictor-council | HIGH |
| 27 | Polymarket Autopilot | Financial Operations | SUPERSTONK-TRADER | MEDIUM |
| 28 | Health & Symptom Tracker | Operations Command | health monitoring | LOW |
| 29 | Family Calendar & Household Asst | Operations Command | daily_brief | LOW |
| 30 | Goal-Driven Autonomous Tasks | Executive Council | AZ, OPTIMUS, backlog | HIGH |

---

## DEPARTMENT INTEGRATION DETAILS

### 1. EXECUTIVE COUNCIL (Authority: AZ_FINAL)

**Head**: Agent AZ
**OpenClaw Role**: Strategic command interface — CEO/board-level decisions via chat

| Integration | Use Case | Implementation |
|---|---|---|
| Multi-Agent Team | #15 | CEO/CFO/CTO/CIO/CMO as specialized OpenClaw sessions via `sessions_spawn` — each C-suite agent gets its own OpenClaw session with distinct SOUL.md persona, coordinated through shared `GOALS.md` and `DECISIONS.md` |
| Goal-Driven Tasks | #30 | AZ performs daily brain-dump → autonomous task generation for backlog system, tracks on Project State dashboard |
| Morning Strategy Brief | #1 | Executive-level morning brief: portfolio health, market signals, agent performance, doctrine compliance, overnight decisions |
| STATE.yaml Coordination | #5 | Agent AZ coordinates cross-department STATE.yaml for autonomous project management without orchestrator overhead |

**Skills to Deploy**: `exec-council-brief`, `exec-strategic-tasks`, `exec-multi-agent`

---

### 2. INTELLIGENCE OPERATIONS (Authority: HIGH)

**Head**: Intelligence Director
**Subdivisions**: YouTube Intelligence, Research Intelligence

#### YouTube Intelligence Division
**Agents**: joe_rogan_agent, lex_fridman_agent, tom_bilyeu_agent, jordan_peterson_agent

| Integration | Use Case | Implementation |
|---|---|---|
| YouTube Digest | #9 | Each podcast agent monitors its channel via `youtube-full` skill, daily transcript summaries delivered to Intelligence topic |
| YouTube Content Pipeline | #12 | Hourly cron scans breaking AI/tech news, cross-references against 90-day catalog, pitches novel ideas with sources |
| Content Factory | #13 | Multi-agent factory: research agents scout → writing agents draft → content agents produce — each in dedicated channel |
| Knowledge Base RAG | #7 | All podcast transcripts auto-ingested into NCL Second Brain for semantic search across all intelligence |

#### Research Intelligence Division
**Agents**: andrew_huberman_agent, peter_attia_agent, daniel_schmachtenberger_agent, geoffrey_hinton_agent, demis_hassabis_agent

| Integration | Use Case | Implementation |
|---|---|---|
| Second Brain | #6 | All research notes auto-captured in NCL Second Brain — zero-friction text-to-memory via any messaging channel |
| Semantic Memory Search | #8 | Vector-powered semantic search across all research memories via `memsearch` integration |
| Multi-Source News Digest | #11 | 109+ sources (RSS, X, GitHub, web) aggregated daily with quality scoring → delivered to research topic |
| Reddit Digest | #10 | Subreddits relevant to each research agent's specialty curated daily with feedback-based preference learning |
| X Account Analysis | #14 | Research agents analyze X accounts for sentiment, trending topics, engagement patterns |
| Market Research | #26 | `Last 30 Days` skill mines Reddit/X for pain points → future-predictor-council validates → REPO DEPOT builds MVPs |

**Skills to Deploy**: `intel-youtube-digest`, `intel-research-rag`, `intel-news-digest`, `intel-market-research`

---

### 3. OPERATIONS COMMAND (Authority: STANDARD)

**Head**: Operations Commander
**Subdivisions**: System Monitoring, Orchestration Control

#### System Monitoring Division
**Agents**: repo_sentry, daily_brief, orchestrator

| Integration | Use Case | Implementation |
|---|---|---|
| Self-Healing Server | #2 | GASKET + repo_sentry use OpenClaw cron jobs for 15-min health checks, auto-restart crashed services, SSH infrastructure management, certificate monitoring |
| Dynamic Dashboard | #3 | Sub-agents spawn in parallel to fetch GitHub stats, system health (CPU/RAM/disk), service status from Matrix Monitor → aggregated dashboard posted to channel |
| Morning Brief | #1 | Unified daily_brief agent sends structured morning report: system health, overnight events, calendar, tasks, portfolio status, agent performance |
| Multi-Channel Assistant | #19 | NCC orchestrator routes requests across Telegram/Discord/Slack topics — different topics for status, alerts, config, projects |
| Todoist Task Manager | #18 | All agent tasks synced to Todoist with In Progress/Waiting/Done sections, sub-step logs as comments, heartbeat stall detection |
| Inbox Declutter | #22 | Daily newsletter digest from subscriptions, priority-sorted with feedback-based preference learning |
| Phone Assistant | #23 | ClawdTalk voice interface for hands-free system queries, calendar checks, status updates |

**Skills to Deploy**: `ops-self-heal`, `ops-dashboard`, `ops-morning-brief`, `ops-task-sync`

---

### 4. TECHNOLOGY INFRASTRUCTURE (Authority: STANDARD)

**Head**: Technology Director
**Subdivisions**: Development Operations

#### Development Operations Division
**Agents**: integrate_cell, ncl_catalog

| Integration | Use Case | Implementation |
|---|---|---|
| Project State Management | #4 | Event-driven project tracking in REPO DEPOT — conversational updates ("finished auth, starting dashboard") → automatic state transitions, git commit linking |
| Autonomous Project Management | #5 | STATE.yaml pattern across 27 repos — subagents work in parallel without orchestrator overhead, daily standups auto-generated from events + commits |
| n8n Workflow Orchestration | #17 | Conductor agent delegates external API calls to n8n workflows via webhooks — credentials stay in n8n, agent only knows webhook URLs |
| Autonomous Game Dev Pipeline | #16 | REPO DEPOT builder_agents manage full lifecycle: backlog selection → implementation → registration → documentation → git workflow |
| Knowledge Base (NCL) | #7 | NCL catalog auto-ingests URLs, tweets, PDFs into searchable knowledge base with semantic RAG |

**Skills to Deploy**: `tech-project-state`, `tech-n8n-proxy`, `tech-auto-build`, `tech-knowledge-base`

---

### 5. FINANCIAL OPERATIONS (Authority: STANDARD)

**Head**: Financial Director

| Integration | Use Case | Implementation |
|---|---|---|
| Earnings Tracker | #25 | Weekly Sunday preview of tech/AI earnings calendar → scheduled one-shot cron jobs for each report → formatted summaries with beat/miss, key metrics, AI highlights |
| Market Research | #26 | `Last 30 Days` skill mines Reddit/X for market pain points → validated by future-predictor-council |
| Polymarket Autopilot | #27 | Paper trading strategies (TAIL/BONDING/SPREAD) on prediction markets → daily P&L reports to Discord |
| Personal CRM | #21 | Portfolio contacts auto-discovered from email/calendar → natural language queries → daily meeting prep briefings |
| Customer Service | #20 | Multi-channel inbox (WhatsApp/Instagram/Email/Reviews) unified with AI auto-responses, human handoff for escalations |

**Skills to Deploy**: `fin-earnings-tracker`, `fin-market-research`, `fin-portfolio-crm`

---

## SUBSYSTEM INTEGRATION MATRIX

| Subsystem | OpenClaw Integration Point | Use Cases |
|---|---|---|
| NCC (Neural Command Center) | Gateway WebSocket → NCC orchestrator, command routing per channel | #19, #20 |
| NCL (Neural Command Layer) / Second Brain | Memory ingestion pipeline, semantic RAG, memsearch | #6, #7, #8 |
| REPO DEPOT | Project state events, flywheel status, builder agent orchestration | #4, #5, #16 |
| Matrix Monitor | Dashboard data provider, health metrics, alert triggers | #2, #3 |
| Inner Council (47 agents) | Each persona agent as OpenClaw session, content factory pipeline | #13, #15 |
| QForge (Windows) | Remote execution bridge, cross-platform sync via OpenClaw | #2 |
| QUSAR (macOS) | Local orchestration, native OpenClaw gateway host | #2, #19 |
| SASP (Security) | Credential isolation, skill auditing, n8n proxy pattern | #17 |
| Memory Doctrine | 3-layer memory ↔ OpenClaw markdown memory sync, vector search | #6, #8 |
| Flywheel | Automated build cycles, continuous deployment via OpenClaw cron | #5, #16 |
| Portfolio (27 repos) | Per-repo health monitoring, auto-PR, cross-repo intelligence | #4, #21 |

---

## CROSS-DEPARTMENT WORKFLOWS

### Workflow 1: Intelligence → Executive → Technology Pipeline
1. Intelligence Operations scans YouTube/Reddit/X for market signals (#9, #10, #11)
2. Research agents synthesize findings through Knowledge Base RAG (#7)
3. Executive Council reviews morning brief with intelligence summary (#1)
4. Agent AZ generates strategic tasks based on signals (#30)
5. Technology Infrastructure creates project states and deploys via REPO DEPOT (#4, #5)

### Workflow 2: Self-Healing Infrastructure Loop
1. Operations Command runs 15-min health cron via OpenClaw (#2)
2. Matrix Monitor provides real-time metrics to Dynamic Dashboard (#3)
3. GASKET self-heal detects anomalies, auto-restarts services
4. repo_sentry monitors all 27 repos for failed CI/CD
5. Operations logs events to Todoist (#18) and posts to morning brief (#1)

### Workflow 3: Content Intelligence Pipeline
1. YouTube Intelligence Division processes new podcast episodes daily (#9)
2. Transcripts auto-ingested into NCL Second Brain (#6)
3. Semantic search enables cross-episode intelligence queries (#8)
4. Content Factory agents produce derivative content (#13)
5. CMO Agent analyzes social performance (#14)
6. Market Research validates product opportunities (#26)

---

## IMPLEMENTATION FILES

| File | Purpose |
|---|---|
| `agents/openclaw_system_bridge.py` | System-wide OpenClaw bridge — serves ALL departments |
| `skills/executive_council/` | Executive Council skills (brief, strategy, multi-agent) |
| `skills/intelligence_ops/` | Intelligence Operations skills (youtube, research, news) |
| `skills/operations_command/` | Operations Command skills (self-heal, dashboard, tasks) |
| `skills/technology_infra/` | Technology Infrastructure skills (project-state, n8n, builds) |
| `skills/financial_ops/` | Financial Operations skills (earnings, CRM, market-research) |
| `doctrine/OPENCLAW_DOCTRINE.md` | Updated v5.0 with cross-system integration |

---

## SECURITY BOUNDARIES

Per OpenClaw best practices and SASP protocol:
- Dedicated OpenClaw sessions per department — no credential sharing
- n8n proxy pattern for ALL external API calls — agents never touch raw API keys
- Read-only access where write isn't needed
- Pre-push TruffleHog hooks on all 27 repos
- Daily automated security audits via Operations Command
- Cost monitoring and budget limits per department
- Skill source code review required before deployment
- SASP keypairs for inter-agent authentication

---

## DEPLOYMENT SCHEDULE

| Phase | Target | Scope |
|---|---|---|
| Phase 1 (DONE) | GASKET v3.0 | GASKET + OpenClaw bridge, 14 skills, REPO DEPOT + Memory integration |
| Phase 2 (NOW) | System Bridge v1.0 | System-wide bridge, all 5 department skills, updated doctrine v5.0 |
| Phase 3 (Next) | NCC Integration | NCC orchestrator ↔ OpenClaw gateway routing, multi-channel command |
| Phase 4 (Future) | Inner Council | 47 persona agents as OpenClaw sessions, content factory pipeline |
| Phase 5 (Future) | Full Autonomy | All 30 use cases live, cross-department workflows automated |
