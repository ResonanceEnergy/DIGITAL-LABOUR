# NCC AI LABOR OPERATIONS (ALOPS) — Division Doctrine v2

## Classification
**Division**: AI Labor Operations (ALOPS)  
**Parent**: NCC — Natrix Command & Control  
**Status**: ACTIVE — OPERATIONAL  
**Effective**: March 7, 2026  
**Last Updated**: With real operational data  

---

## Mission
Design, deploy, and monetize autonomous AI agents as modular digital labor units. Sell outcomes and completed work — not software, not tokens, not "AI."

## Operating Principles

### 1. Labor, Not Software
We sell what a human would deliver: enriched leads, resolved tickets, repurposed content, structured data extractions. The buyer doesn't need to know or care how it's built.

### 2. QA Is Non-Negotiable
Nothing ships without passing the QA Agent. An output that fails QA is an output that doesn't exist.
- **Sales Ops**: 80-100% pass rate (tested, verified)
- **Support Resolver**: 100% pass rate (tested, verified)
- **Content Repurposer**: QA pipeline active (analyze → write → QA with retry)
- **Doc Extraction**: QA pipeline active (extract → QA with retry)

### 3. Outcome Over Activity
We price on outputs and results, not on compute time or token counts.
| Agent | Unit | Client Price | LLM Cost (est.) | Margin |
|-------|------|-------------|-----------------|--------|
| Sales Ops | Per lead | $2.40 | ~$0.03 | ~98% |
| Support | Per ticket | $1.00 | ~$0.02 | ~98% |
| Content Repurposer | Per piece | $3.00 | ~$0.05 | ~98% |
| Doc Extraction | Per document | $1.50 | ~$0.03 | ~98% |

### 4. Governed Autonomy
Agents act autonomously within defined boundaries. Every agent has:
- A job statement (what it does, what "done" means)
- An input/output schema (Pydantic v2, strict validation)
- Refusal rules (what it will NOT do)
- Escalation rules (when it hands off to humans)
- A budget (daily task limits enforced in dispatcher)
- QA with retry (max 2 attempts before failure)

### 5. Compound, Don't Restart
Each agent plugs into shared infrastructure:
- **Dispatcher**: Routes tasks to correct agent, provider-aware, daily limits
- **Task Queue**: SQLite-backed, priority-weighted FIFO, budget enforcement
- **Intake Webhook**: FastAPI REST API, sync/async modes
- **KPI Logger**: Dual JSONL + SQLite, per-task event tracking
- **Billing Tracker**: Per-task pricing + retainer tiers + auto-invoicing
- **Delivery Module**: File export + email (SMTP) + webhook
- **Cost Tracker**: Token-level pricing × 4 providers with margin analysis
- **Scheduler**: Cron-like retainer task delivery with daily targets
- **Health Dashboard**: Real-time system status, CLI + JSON
- **Alert System**: Desktop + Telegram + Discord notifications

---

## Governance Structure

### Revenue Council
**Mandate**: Packaging, pricing, distribution, client acquisition.  
**Reviews**: Offer docs, pricing changes, marketplace strategy, conversion rates.  
**Cadence**: Weekly.

### Risk Council
**Mandate**: Refusal rules, escalation policies, compliance, audit logging.  
**Reviews**: QA failures, refund incidents, policy violations, safety triggers.  
**Cadence**: Weekly or on-incident.

### Ops Council
**Mandate**: Uptime, cost control, telemetry, pipeline health.  
**Reviews**: KPI dashboards, latency trends, cost-per-task, queue health.  
**Cadence**: Daily check, weekly review.

---

## Agent Roster (Current)

| Agent | Status | Pipeline | QA Rate | Avg Speed |
|-------|--------|----------|---------|-----------|
| Sales Ops | ✅ LIVE | Research → Copy → QA | 80-100% | 13.6s |
| Support Resolver | ✅ LIVE | Classify → Resolve → QA | 100% | 9.6s |
| Content Repurposer | ✅ LIVE | Analyze → Write → QA | - | - |
| Doc Extraction | ✅ LIVE | Extract → QA | - | - |

### Provider Fleet
| Provider | Model | Speed | Cost Tier | Best For |
|----------|-------|-------|-----------|----------|
| OpenAI | gpt-4o | 13.3s | $$$ | Production speed, reliable JSON |
| Grok/xAI | grok-3 | 13.8s | $$ | Fast alternative, good quality |
| Anthropic | Claude Sonnet | 28.1s | $$$ | Nuanced copy, complex reasoning |
| Gemini | 2.0 Flash | 86.7s | $ | Bulk/batch, cheapest |

**Failover**: Auto-fallback across providers if primary fails (`utils/llm_client.py`).

---

## Agent Lifecycle

```
SPEC → BUILD → TEST (10 runs) → QA GATE (≥80%) → DEMO (3 packs) → LIST → SELL → RETAINER → SCALE
```

No agent advances past TEST without meeting the QA gate.  
No agent is listed without 3 demo outputs.  
No agent price is set without unit economics data.

---

## Revenue Model

### Pricing Hierarchy (in order of maturity)
1. **Per execution** — marketplace tasks ($1.00–$3.00/task)
2. **Per batch** — bulk workflows ($80/10 leads, $400/50)
3. **Monthly retainer** — recurring delivery with tier pricing

### Retainer Tiers (Active)
| Tier | Price | Tasks/mo | Overage | Agent Type |
|------|-------|----------|---------|------------|
| Sales Starter | $750 | 50 | $12/ea | Sales Ops |
| Sales Growth | $1,400 | 100 | $10/ea | Sales Ops |
| Sales Scale | $2,500 | 200 | $8/ea | Sales Ops |
| Support Starter | $400 | 200 | $1.50/ea | Support |
| Support Growth | $800 | 500 | $1.20/ea | Support |
| Support Scale | $1,400 | 1000 | $1.00/ea | Support |

### Offer Ladder
- Trial: Free demo → first task at list price
- Core: $400–$2,500/mo per role (SMB)
- Pro: $5k–$15k/mo multi-role + API access
- Enterprise: Setup fee + ongoing + outcome share

---

## Success Metrics

| Metric | Minimum | Target | Current |
|--------|---------|--------|---------|
| QA pass rate | 80% | 90%+ | 80-100% (by agent) |
| Active agent types | 2 | 5+ | 4 ✅ |
| Active providers | 2 | 4 | 4 ✅ |
| Infrastructure modules | - | 10+ | 12 ✅ |
| Retainer clients | 1 | 5+ | Pre-launch |
| Monthly revenue | $750 | $5,000+ | Pre-launch |
| Margin per task | > 50% | > 90% | ~98% (estimated) |

---

## Failure Recovery Protocol
- **Marketplace no traction** → Pivot to direct DMs + community posting
- **QA < 70%** → Stop selling, fix prompts, re-test 10 leads
- **No retainer closes** → Drop price to $499/mo pilot for 1 month
- **Agent costs too high** → Switch to Gemini for bulk, Grok for speed
- **Platform down** → Always on 2+ platforms + direct pipeline
- **Provider down** → Auto-fallback to next available provider

---

*This doctrine is a living document. Updated as the division scales and real revenue data accumulates.*  
*Authority: NCC — Natrix Command & Control*
