# RESONANCE ENERGY — SOURCE OF TRUTH
## Owner: NATRIX | Last Updated: 2026-04-20

---

## What Is This Document

This is the single source of truth for the Resonance Energy project portfolio. Every architectural decision, repo boundary, and system relationship is defined here. If something contradicts this document, this document wins.

---

## The Portfolio

NATRIX operates multiple projects under the **Resonance Energy** umbrella. Each project is its own repo, its own codebase, its own deployment. They are NOT one system — they are separate systems that communicate via APIs.

| Project | Repo | What It Is | Where It Runs |
|---------|------|------------|---------------|
| **NCL** | `ResonanceEnergy/NCL` | NATRIX's second brain. Strategic thinking, intelligence, memory, decision-making. The top of the hierarchy. | Mac Mini M4 Pro (localhost:8787) |
| **Bit Rage Labour (BRL)** | `ResonanceEnergy/DIGITAL-LABOUR` | Autonomous AI labor platform. 46 agents that complete real tasks for real companies and get paid. | Railway (bitrage-labour-api-production.up.railway.app) |
| **AAC** | `ResonanceEnergy/AAC` | Accelerated Arbitrage Corp. AI-powered algorithmic trading platform. | TBD |
| **Other Projects** | Various repos | Crimson Compass, DubForge, Man Up Man Down, AdventureHeroAuto, Archive of Echoes, Resonance Energy Media | Various |

---

## The Hierarchy

```
NATRIX (Human Owner)
  │
  └── NCL (Second Brain — thinks, plans, decides, monitors everything)
        │
        ├── Bit Rage Labour ── standalone, earns money via AI labor
        ├── AAC ── standalone, earns money via trading
        └── Research Projects ── NCL's university/research arm (future)
```

**NCL is the top.** It is NATRIX's interface to the outside world and to all projects. NCL:
- Receives NATRIX's intent via pump prompts (iPhone → Grok → NCL)
- Runs multi-AI council debates to make strategic decisions
- Issues mandates to downstream projects
- Monitors all projects via their APIs
- Maintains institutional memory across everything
- Scans intelligence sources (X, YouTube, Reddit) to stay current
- Only escalates BIG decisions and payments to NATRIX

**Bit Rage Labour is standalone.** It has its own:
- Codebase (DIGITAL-LABOUR repo)
- Deployment (Railway)
- Agent registry (46 agents across 4 divisions)
- C-Suite (AXIOM/VECTIS/LEDGR)
- Dispatcher, billing, delivery, KPIs
- NERVE daemon for 24/7 autonomous operations

NCL talks to Bit Rage via API. NCL does NOT live inside Bit Rage's codebase.

---

## Where Things Belong

### Intelligence / Scrapers → NCL

The scrapers that pull from X, YouTube, and Reddit exist to keep **NCL** informed. They feed NCL's memory and decision-making. They are NOT a Bit Rage feature.

- **NCL repo** already has `runtime/awarebot/scanner.py` — scans X, YouTube, Reddit
- **NCL repo** already has `runtime/awarebot/predictor.py` — ensemble forecasting from signals
- **NCL repo** already has the `intelligence-scan/` workspace with proper staging

The Galactia engine currently sitting inside DIGITAL-LABOUR (`galactia/`) was built in the wrong repo. Its functionality (scraping, truth scoring, ML scoring, knowledge store, research generation) belongs in NCL.

### C-Suite / Executive AI → Bit Rage

AXIOM (CEO), VECTIS (COO), LEDGR (CFO) are Bit Rage's internal executive layer. They manage Bit Rage's own operations. They do NOT manage NCL or AAC.

### NCL Operations Commander → Needs Rethinking

`NCL/ncl_operations_commander.py` currently lives inside DIGITAL-LABOUR. This is wrong. If NCL needs to command Bit Rage operations, it does so by calling Bit Rage's API from the NCL repo — not by embedding NCL code inside Bit Rage.

### Divisions → Bit Rage

The 4 divisions (INS-OPS, GRANT-OPS, CTR-SVC, MUN-SVC) are Bit Rage business units. They stay in DIGITAL-LABOUR.

### Doctrine (00_COMMAND/) → Bit Rage

The doctrine files in `00_COMMAND/` govern Bit Rage operations specifically. NCL has its own governance in its own repo.

---

## Repo Boundaries — What Goes Where

### NCL Repo (`ResonanceEnergy/NCL`)
- Brain service (FastAPI on :8787)
- Council engine (multi-AI debate)
- Memory system (episodic → semantic)
- Intelligence scanning (Awarebot-FPC: X, YouTube, Reddit scrapers)
- Future prediction (ensemble forecasting)
- Mandate generation and tracking
- Feedback synthesis from all downstream projects
- Workstation / dashboard for NATRIX
- Paperclip integration (issue tracking, cost accounting)

### DIGITAL-LABOUR Repo (`ResonanceEnergy/DIGITAL-LABOUR`)
- Bit Rage Labour API (FastAPI on Railway)
- 46 agent modules
- 4 divisions (INS-OPS, GRANT-OPS, CTR-SVC, MUN-SVC)
- C-Suite (AXIOM, VECTIS, LEDGR, Boardroom)
- Dispatcher (router, queue, budget enforcement)
- NERVE daemon (24/7 autonomous operations)
- Billing (Stripe, invoicing, retainers)
- Delivery (email, file export, webhooks)
- KPI tracking and reporting
- Client-facing site and marketing
- Freelance platform automation (Upwork, Fiverr, etc.)

### What Should NOT Be in DIGITAL-LABOUR
- `NCL/` directory — NCL code does not belong here
- `NCC/` directory — NCC governance lives in NCL or its own context
- `galactia/` — Intelligence engine belongs in NCL (as Awarebot-FPC or enhanced version)
- Any code that "commands" Bit Rage from within — NCL commands via API, not embedded code

---

## How NCL Talks to Bit Rage

NCL communicates with Bit Rage via Bit Rage's existing REST API:

```
NCL (Mac Mini :8787)
  │
  │  HTTP calls to Railway API
  │
  ├── POST /v1/run          → Submit tasks to Bit Rage
  ├── GET  /health           → Check if Bit Rage is alive
  ├── GET  /v1/metrics       → Pull performance metrics
  ├── GET  /v1/agents        → See agent status
  ├── GET  /v1/errors        → Check for problems
  └── POST /mandates/...     → (future) mandate-driven task submission
```

Bit Rage reports back to NCL via NCL's feedback endpoint:

```
Bit Rage (Railway)
  │
  │  HTTP calls to NCL API
  │
  └── POST :8787/feedback    → Report execution results, KPIs, issues
```

This is a clean API boundary. No shared code. No embedded modules.

---

## Current State of Drift (Honest Assessment)

| Issue | Where | Impact |
|-------|-------|--------|
| `galactia/` inside DIGITAL-LABOUR | DIGITAL-LABOUR repo | Intelligence engine built in wrong repo |
| `NCL/` directory inside DIGITAL-LABOUR | DIGITAL-LABOUR repo | NCL code embedded in Bit Rage |
| `NCC/` directory inside DIGITAL-LABOUR | DIGITAL-LABOUR repo | Governance code embedded in Bit Rage |
| `ncl_operations_commander.py` in DIGITAL-LABOUR | DIGITAL-LABOUR repo | NCL commanding from inside Bit Rage |
| Galactia duplicates Awarebot-FPC functionality | Both repos | Two intelligence scanners doing the same job |
| `00_COMMAND/NCC_ALOPS_DOCTRINE.md` references NCC as parent | DIGITAL-LABOUR repo | Bit Rage doctrine references external governance |
| `api/intake.py` imports `ncl_router` | DIGITAL-LABOUR repo | NCL API routes served from Bit Rage |
| `.env.example` has `NCC_RELAY_URL` | DIGITAL-LABOUR repo | Bit Rage config referencing NCC |

---

## Principles Going Forward

1. **Each project is its own repo, its own deployment, its own codebase.** No cross-embedding.
2. **NCL is the brain. Projects are the body.** NCL thinks and decides. Projects execute.
3. **Communication is via API only.** No shared modules, no importing across repos.
4. **Intelligence belongs to NCL.** Scrapers, scoring, knowledge graphs — all NCL.
5. **Bit Rage is self-sufficient.** It runs its own agents, its own C-Suite, its own operations. NCL monitors and directs from outside.
6. **One SOT, one plan.** This document is the SOT. THE_PLAN.md is the plan. Everything else is execution.

---

*Authority: NATRIX — Resonance Energy*
*This document supersedes all prior architecture docs, doctrine fragments, and roadmaps where they conflict.*
