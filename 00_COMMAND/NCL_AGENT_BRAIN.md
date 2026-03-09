# NCL Agent Portfolio Brain — Specification v2

## Purpose
The Agent Portfolio Brain is the institutional memory for all ALOPS agents. It stores everything needed to reproduce, evaluate, improve, and scale any agent in the system.

---

## Agent Registry (Current)

### Agent #1: Sales Ops
| Field | Value |
|-------|-------|
| **Job Statement** | Given (company, role) → produce (enrichment + 3 cold emails) → QA verified → 13.6s avg |
| **Task Type ID** | `sales_outreach` |
| **Pipeline** | Research Agent → Copywriter Agent → QA Agent (retry once) |
| **Input** | `{ company_name, contact_role, provider? }` |
| **Output** | `{ lead_enrichment: {...}, emails: { primary, follow_up_1, follow_up_2 }, qa: {...} }` |
| **QA Rate** | 80-100% (batch tested, 10 leads) |
| **Avg Speed** | 13.6s (OpenAI), 13.8s (Grok), 28.1s (Anthropic), 86.7s (Gemini) |
| **Pricing** | $2.40/lead, $80/10, $400/50 |
| **LLM Cost** | ~$0.03/lead (3 LLM calls) |
| **Margin** | ~98% |
| **Prompts** | `research_prompt.md`, `copywriter_prompt.md`, `agents/qa/verifier_prompt.md` |
| **Banned Phrases** | "revolutionize", "synergy", "leverage" + 30 more in `config/banned_phrases.txt` |
| **Refusal** | No medical/legal/financial advice, no personal data fabrication |
| **Escalation** | If QA fails twice → flag for human review |
| **Known Failures** | Anthropic wraps JSON in markdown fences (fixed: `_strip_fences()`), word count violations (fixed: explicit prompt constraint) |
| **Demo Packs** | `demos/demo_saas.json`, `demo_local.json`, `demo_b2b.json` |

### Agent #2: Support Resolver
| Field | Value |
|-------|-------|
| **Job Statement** | Given (ticket text, product context) → produce (category + severity + resolution + follow-up) → QA verified → 9.6s avg |
| **Task Type ID** | `support_ticket` |
| **Pipeline** | Classifier + Resolver Agent → QA Agent (retry once) |
| **Input** | `{ ticket_text, product_context?, provider? }` |
| **Output** | `{ category, severity, resolution, follow_up, escalate, qa: {...} }` |
| **QA Rate** | 100% (batch tested, 10 tickets) |
| **Avg Speed** | 9.6s (all providers) |
| **Pricing** | $1.00/ticket |
| **LLM Cost** | ~$0.02/ticket (2 LLM calls) |
| **Margin** | ~98% |
| **Prompts** | `agents/support/resolve_prompt.md`, `agents/support/qa_prompt.md` |
| **Escalation** | severity ≥ 4/5, legal/safety, account deletion, ongoing harassment |
| **Known Failures** | Hallucinated policy citations (fixed: anti-hallucination prompt rules), vague resolutions (fixed: required specific steps) |
| **Demo Packs** | `demos/demo_support.json` |

### Agent #3: Content Repurposer
| Field | Value |
|-------|-------|
| **Job Statement** | Given (source text/blog) → produce (LinkedIn post + Twitter thread + email newsletter + Instagram caption + summary blurb) → QA verified |
| **Task Type ID** | `content_repurpose` |
| **Pipeline** | Analyzer Agent → Writer Agent → QA Agent (retry once) |
| **Input** | `{ source_text, formats[]?, provider? }` |
| **Output** | `{ analysis: {...}, content: { linkedin_post, twitter_thread[], email_newsletter, instagram_caption, summary_blurb }, qa: {...} }` |
| **QA Checks** | Accuracy, format compliance, tone consistency, key points coverage, tweet ≤280 chars |
| **Pricing** | $3.00/piece |
| **LLM Cost** | ~$0.05/piece (3 LLM calls) |
| **Margin** | ~98% |
| **Prompts** | `analyzer_prompt.md`, `writer_prompt.md`, `qa_prompt.md` |
| **Demo Packs** | `demos/demo_content/demo_tech_blog.json`, `demo_agency_post.json`, `demo_product_launch.json` |

### Agent #4: Document Extraction
| Field | Value |
|-------|-------|
| **Job Statement** | Given (unstructured document text) → produce (doc_type + structured JSON + entity list + summary) → QA verified |
| **Task Type ID** | `doc_extract` |
| **Pipeline** | Extractor Agent → QA Agent (retry once) |
| **Input** | `{ document_text, doc_type?: "auto"|"invoice"|"contract"|"resume"|"report"|"form" }` |
| **Output** | `{ extraction: { doc_type, confidence, extracted: {...}, raw_entities[], summary, warnings[] }, qa: {...} }` |
| **QA Checks** | Completeness, accuracy, no hallucination, entities captured |
| **Pricing** | $1.50/document |
| **LLM Cost** | ~$0.03/document (2 LLM calls) |
| **Margin** | ~98% |
| **Prompts** | `extractor_prompt.md`, `qa_prompt.md` |
| **Demo Packs** | `demos/demo_extract/demo_invoice.json`, `demo_contract.json`, `demo_resume.json` |

---

## Shared Infrastructure

| Component | File | Purpose |
|-----------|------|---------|
| LLM Client | `utils/llm_client.py` | Unified interface, 4 providers, auto-fallback |
| Dispatcher | `dispatcher/router.py` | Routes tasks, enforces limits, logs KPIs |
| Task Queue | `dispatcher/queue.py` | SQLite FIFO, priority, budget enforcement |
| Intake Webhook | `api/intake.py` | FastAPI REST API, sync/async |
| KPI Logger | `kpi/logger.py` | JSONL + SQLite dual-write |
| Weekly Report | `kpi/weekly_report.py` | Markdown KPI reports from logs |
| Billing | `billing/tracker.py` | Usage tracking + invoicing + retainer tiers |
| Cost Tracker | `utils/cost_tracker.py` | Token pricing × 4 providers |
| Delivery | `delivery/sender.py` | File + email + webhook delivery |
| Scheduler | `scheduler/runner.py` | Cron-like retainer delivery |
| Dashboard | `dashboard/health.py` | System status CLI + JSON |
| Alerts | `utils/alerts.py` | Desktop + Telegram + Discord |
| Batch Runners | `utils/batch_runner.py`, `support_batch.py` | Bulk testing tools |

---

## Per-Agent Requirements

### What Every Agent MUST Have
1. **Runner** (`runner.py`) — execution pipeline
2. **Prompts** (`*_prompt.md`) — system, writer/worker, QA
3. **Pydantic models** — strict input/output schemas
4. **QA with retry** — max 2 attempts before failure
5. **Demo packs** — 3 sample outputs in `demos/`
6. **Pricing** — documented in `offers/labor_catalog.md`
7. **Dispatcher routing** — wired into `dispatcher/router.py`

### Failure Library Protocol
- After any QA failure incident, document: pattern, root cause, fix applied
- Update agent's prompt or logic with the fix
- Re-run test batch to verify fix
- If regression, escalate to Ops Council

---

## Directory Structure

```
agents/
  {agent_name}/
    runner.py              — Execution pipeline
    *_prompt.md            — System prompts (analyzer, writer, QA, etc.)
    escalation_rules.md    — Escalation policy (if applicable)
    __init__.py            — Module init
schemas/
  {agent_name}_output.json — Output schema
  event_schema.json        — Standard event wrapper
kpi/
  logs/                    — Daily event logs (JSONL)
  reports/                 — Weekly markdown reports
  logger.py                — Structured event logger
config/
  banned_phrases.txt       — Shared banned phrase list
  llm_config.md            — Provider configuration
billing/
  tracker.py               — Usage + invoicing
  intake_form.py           — Client onboarding CLI
data/
  task_queue.db            — Task queue database
  kpi.db                   — KPI events database
  billing.db               — Billing database
demos/
  demo_saas.json           — Sales ops demo
  demo_local.json          — Sales ops demo
  demo_b2b.json            — Sales ops demo
  demo_support.json        — Support demo
  demo_content/            — Content repurpose demos (3)
  demo_extract/            — Doc extract demos (3)
```

---

*Authority: NCL — Brain Pillar of Resonance Energy*  
*Maintained by: ALOPS Division under NCC*
