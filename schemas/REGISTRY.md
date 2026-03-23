# Agent Registry Schema — REGISTRY.md

**Doctrine Version:** 2.0  
**Source:** `config/agent_registry.json`

---

## Schema Definition

Each key in `agent_registry.json` is an **agent name** (snake_case, matches `task_type` in API).  
Each value is an object with the following fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `one_liner` | string | Yes | Single-sentence description of what the agent does |
| `cost_ceiling_usd` | float | Yes | Max LLM cost per task in USD. Tasks exceed this log a `[CEILING]` warning |
| `max_execution_seconds` | int | Yes | Hard time limit; router fails task with `HARD_TIMEOUT` if exceeded |
| `max_retries` | int | Yes | Max retries on QA fail before marking task FAILED |
| `failure_modes` | string[] | Yes | Known failure modes: `llm_timeout`, `schema_violation`, `qa_fail`, `empty_output`, etc. |
| `authority_scope` | string | Yes | Governance tier: `"internal"` (no external calls) \| `"external_read"` \| `"external_write"` |
| `disabled` | bool | Yes | If `true`, router returns `AGENT_DISABLED` immediately without hitting LLM |
| `billing_surface_verified` | bool | Yes | Confirms every execution path produces a billing event (P1.5 audit) |

---

## Authority Scopes

| Scope | Meaning |
|---|---|
| `internal` | Agent reads/writes only internal data; no external API calls |
| `external_read` | Agent may call external APIs read-only (scraping, search, lookup) |
| `external_write` | Agent may post/submit to external systems (email send, CRM write, social post) |

---

## Failure Modes Reference

| Code | Trigger |
|---|---|
| `llm_timeout` | LLM call exceeded `max_execution_seconds` |
| `schema_violation` | LLM output did not match expected JSON schema |
| `qa_fail` | QA runner returned FAIL (confidence < 0.70) |
| `empty_output` | LLM returned blank or whitespace-only response |
| `empty_company` | Required `company` field missing from input (sales agents) |
| `no_contact` | Required contact / email field missing |
| `rate_limit` | LLM provider returned HTTP 429 |
| `context_overflow` | Input exceeded LLM context window |

---

## 30 Registered Agents (Doctrine 2.0)

| Agent Name | Authority Scope | Cost Ceiling | Max Seconds |
|---|---|---|---|
| `sales_outreach` | external_write | $0.15 | 45s |
| `support_ticket` | internal | $0.10 | 30s |
| `content_repurpose` | internal | $0.20 | 60s |
| `doc_extract` | internal | $0.12 | 45s |
| `lead_gen` | external_read | $0.18 | 60s |
| `email_marketing` | external_write | $0.20 | 60s |
| `seo_content` | internal | $0.25 | 90s |
| `social_media` | external_write | $0.15 | 45s |
| `data_entry` | internal | $0.08 | 30s |
| `web_scraper` | external_read | $0.15 | 60s |
| `crm_ops` | external_write | $0.12 | 45s |
| `bookkeeping` | internal | $0.12 | 45s |
| `proposal_writer` | internal | $0.30 | 90s |
| `product_desc` | internal | $0.15 | 45s |
| `resume_writer` | internal | $0.25 | 75s |
| `ad_copy` | internal | $0.15 | 45s |
| `market_research` | external_read | $0.40 | 120s |
| `business_plan` | internal | $0.50 | 150s |
| `press_release` | internal | $0.20 | 60s |
| `tech_docs` | internal | $0.20 | 60s |
| `ops_brief` | internal | $0.10 | 30s |
| `context_manager` | internal | $0.10 | 30s |
| `qa_manager` | internal | $0.08 | 30s |
| `production_manager` | internal | $0.10 | 30s |
| `automation_manager` | internal | $0.10 | 30s |
| `freelancer_work` | external_write | $0.20 | 60s |
| `upwork_work` | external_write | $0.20 | 60s |
| `fiverr_work` | external_write | $0.20 | 60s |
| `pph_work` | external_write | $0.20 | 60s |
| `guru_work` | external_write | $0.20 | 60s |

---

## Adding a New Agent

1. Add entry to `config/agent_registry.json`
2. Add routing branch to `dispatcher/router.py` → `route_task()`
3. Add pricing entry to `billing/tracker.py` → `PRICING` dict
4. Add entry to this file (REGISTRY.md)
5. Document in `00_COMMAND/DOCTRINE_CHANGELOG.md`

---

*Schema maintained under: `schemas/REGISTRY.md`*
