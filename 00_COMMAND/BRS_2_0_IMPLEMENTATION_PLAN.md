# BRS 2.0 — IMPLEMENTATION PLAN
**Status**: ACTIVE BUILD  
**Doctrine Ref**: BRS_2_0_FRAMEWORK.md  
**Updated**: March 18, 2026

---

## BUILD PHILOSOPHY
> Execution is the product. Structure enables speed. Doctrine precedes deployment.

Build in order of **revenue impact × risk reduction**. Skip nothing. No feature justified without a billing surface.

---

## PHASE 1 — FOUNDATION HARDENING (Week 1–2)
*Insights driving this phase: 5, 13, 15, 16, 23, 33, 67, 86, 95, 99, 192*

These are the structural fixes that make everything else work. Without these, BRS scales chaos.

### P1.1 — Task Lineage & Traceability
**Insight refs**: 99, 100  
**Files**: `dispatcher/router.py`, `kpi/logger.py`, `api/intake.py`
- [x] Generate UUID `lineage_id` at intake, propagate through pipeline to delivery — `create_event()` generates `lineage_id = str(uuid4())`
- [x] Log: `client_id`, `agent`, `doctrine_version=2.0`, `lineage_id` on every task — `_finalize_event()` → `log_task_event()` with all fields
- [x] Enable `GET /trace/{lineage_id}` endpoint on monitor API — `api/intake.py:trace_lineage()`

### P1.2 — Hard Execution Termination
**Insight refs**: 5, 33, 36  
**Files**: `dispatcher/router.py`, `config/agent_registry.json`
- [x] Add `max_execution_seconds` per agent config (default: 30s) — all 30 agents in `agent_registry.json`
- [x] Add `max_retries` per agent config (default: 2, currently ad-hoc) — all 30 agents in `agent_registry.json`
- [x] Terminate and log reason on ceiling breach — no silent continuation — `[HARD_TIMEOUT]` FAIL + early return in `route_task()`

### P1.3 — Fail Closed (No Silent Failures)
**Insight refs**: 95, 192, 208  
**Files**: `dispatcher/router.py`, `api/intake.py`
- [x] Every task produces an artifact: either `status=success` or `status=failed` with `failure_reason` — `_finalize_event()` enforces status ∈ {PASS, FAIL}
- [x] Remove any `try/except: pass` blocks that swallow failures silently — all replaced with `logger.debug()` logging
- [x] Failed tasks still trigger `BillingTracker` with `status=failed, amount=0` — `_finalize_event()` always calls `bt.record_usage()`

### P1.4 — Schema Version Registry
**Insight refs**: 15, 84, 108  
**Files**: `schemas/REGISTRY.md`, `dispatcher/router.py`, `api/intake.py`
- [x] Add `schema_version` field to all agent I/O schemas — `schema_version: "2.0"` in all events via `create_event()`
- [x] Create `schemas/REGISTRY.md` listing all schemas, versions, and owning agents — full registry docs with 30 agents
- [x] Reject intake with schema version mismatch — 422 error in `submit_task()` if `schema_version != "2.0"`

### P1.5 — Billing Surface Audit
**Insight refs**: 23, 161, 162  
**Files**: `billing/tracker.py`, `dispatcher/router.py`, `config/agent_registry.json`
- [x] Confirm every execution path calls `BillingTracker` (success AND failure) — `_finalize_event()` always fires billing
- [x] Add `billing_surface_verified` flag to agent configs — all 30 agents have `billing_surface_verified: true`
- [x] Log all execution paths that do NOT result in a billing event (should be zero) — `[BILLING_SURFACE_GAP]` error on failure

---

## PHASE 2 — AGENT GOVERNANCE (Week 2–3)
*Insights driving this phase: 51, 54, 60, 72, 73, 75, 77*

Lock agents as proper labor units — job descriptions, cost ceilings, failure modes declared.

### P2.1 — Agent Registry
**Insight refs**: 60, 54  
**Files**: `config/agent_registry.json` (new)
```json
{
  "sales_ops": {
    "one_liner": "Researches companies and generates personalized cold outreach sequences",
    "cost_ceiling_usd": 0.10,
    "max_execution_seconds": 45,
    "max_retries": 2,
    "failure_modes": ["llm_timeout", "schema_violation", "qa_fail"],
    "authority_scope": "outreach_generation",
    "disabled": false
  }
}
```
- [ ] Create `config/agent_registry.json` for all 30 agents
- [ ] `dispatcher/router.py` reads registry at startup — rejects disabled agents
- [ ] Add `GET /agents` endpoint returning registry (internal only)

### P2.2 — Cost Ceiling Enforcement
**Insight refs**: 75, 167  
**Files**: `dispatcher/router.py`, `billing/tracker.py`
- [ ] Before execution: estimate cost from model + expected tokens
- [ ] During execution: track cumulative cost
- [ ] On ceiling breach: terminate, log `COST_CEILING_BREACH`, deliver failure artifact

### P2.3 — Declared Failure Modes
**Insight refs**: 72, 73  
**Files**: `config/agent_registry.json`, `dispatcher/router.py`
- [ ] Each agent has `failure_modes` list in registry
- [ ] On failure: match to declared mode, log with mode ID
- [ ] Undeclared failure → `UNKNOWN_FAILURE` → auto-flag for doctrine review

### P2.4 — Instant Agent Disable
**Insight refs**: 60, 43  
**Files**: `config/agent_registry.json`, `dispatcher/router.py`
- [ ] `"disabled": true` in registry → dispatcher rejects all tasks for that agent
- [ ] Add `POST /admin/agents/{name}/disable` endpoint (admin-only)
- [ ] Test: disable agent mid-queue, verify graceful rejection

---

## PHASE 3 — QA HARDENING (Week 3–4)
*Insights driving this phase: 107, 112, 116, 121, 124, 126, 133*

QA is the moat. Harden it or lose the differentiation.

### P3.1 — QA Rule Registry
**Insight refs**: 112, 116  
**Files**: `config/qa_rules.json` (new)
- [x] Create `config/qa_rules.json` with all QA rules, each with a `rule_id`
- [x] QA agent attaches `applied_rules: [rule_ids]` to every QA artifact
- [x] Failed checks return `failed_rule_id` for traceability

### P3.2 — Client QA Profiles
**Insight refs**: 121, 114  
**Files**: `config/client_profiles/` (new dir)
- [x] Per-client JSON: `banned_phrases`, `tone_rules`, `required_fields`, `min_confidence`
- [x] QA agent loads profile by `client_id` at runtime
- [x] Default profile used when no client profile exists

### P3.3 — Confidence Score Standardization
**Insight refs**: 109  
**Files**: `agents/qa/runner.py`, `dispatcher/router.py`
- [x] All QA artifacts emit `confidence: float` (0.00–1.00)
- [x] `confidence < 0.70` → automatic retry via dispatcher
- [x] `confidence < 0.50` after retry → failure artifact

### P3.4 — QA Failure Feedback Loop
**Insight refs**: 133, 134  
**Files**: `kpi/logger.py`, `kpi/qa_debt_report.py`
- [x] Track QA failure counts by rule ID and agent (`kpi/logger.py` → `qa_failures` table)
- [x] Weekly: auto-generate QA debt report to `kpi/reports/qa_debt_YYYY-MM-DD.json`
- [x] Failures that repeat 3+ times → flag for doctrine review (`get_repeat_offenders()`)

---

## PHASE 4 — DELIVERY INFRASTRUCTURE (Week 4–5)
*Insights driving this phase: 138, 139, 147, 153, 157*

Delivery is where clients feel BRS. Make it invisible and trustworthy.

### P4.1 — Delivery Receipt System
**Insight refs**: 147, 153  
**Files**: `delivery/sender.py`
- [x] Every delivered artifact generates a `delivery_receipt.json` (individual file + JSONL)
- [x] Receipt contains: `job_id`, `lineage_id`, `delivered_at`, `channel`, `checksum` (SHA-256)
- [x] Receipts stored immutably in `data/delivery_receipts/`, separate from artifacts

### P4.2 — Delivery Logging (Immutable)
**Insight refs**: 157  
**Files**: `delivery/sender.py`, `kpi/delivery_log.jsonl`
- [x] Delivery events log to append-only JSONL file in `kpi/delivery_log.jsonl`
- [x] Log: `delivered_at`, `channel`, `client_id`, `checksum`, `job_id`, `lineage_id`
- [x] Delivery log retained 90 days minimum (`prune_delivery_log()` with configurable retention)

### P4.3 — Webhook Retry Logic
**Insight refs**: 139, 153  
**Files**: `delivery/sender.py`
- [x] On webhook failure: retry 3× with exponential backoff (1s, 5s, 30s)
- [x] After 3 failures: fall back to email delivery via `email_fallback` param
- [x] Log all retry attempts and final channel used (receipt tracks `attempt` count)

### P4.4 — Partial Delivery Labeling
**Insight refs**: 96, 146  
**Files**: `dispatcher/router.py`, `delivery/sender.py`, `billing/tracker.py`
- [x] Add `delivery_status: complete | partial | failed` to all artifacts
- [x] Partial: list `completed_components` and `missing_components`
- [x] Billing logic: partial tasks billed at 50% of full price (`status=PARTIAL`)

---

## PHASE 5 — FINANCIAL OBSERVABILITY (Week 5–6)
*Insights driving this phase: 168, 169, 175, 228*

Unit economics visible at agent level. Daily burn visible. Margins tracked per role.

### P5.1 — Per-Agent P&L
**Insight refs**: 168, 169  
**Files**: `kpi/logger.py`, `billing/tracker.py`
- [x] Track per-execution: `llm_cost`, `runtime_cost_est`, `billed_amount`, `margin` — `billing/tracker.py:per_agent_economics()` returns all fields; `runtime_cost_per_task_usd` in `config/economics.json`
- [x] `billing/tracker.py` stores `agent_economics` dict keyed by agent name
- [x] `GET /monitor/financials/agents` returns per-agent margin summary — `api/monitor.py`

### P5.2 — Daily Burn Report
**Insight refs**: 228, 175  
**Files**: `kpi/` (new script: `kpi/daily_burn.py`)
- [x] Runs at 23:59 daily via scheduler — `scheduler/runner.py:_maybe_run_daily_burn()` triggers after 23:50 UTC
- [x] Outputs `kpi/reports/burn_YYYY-MM-DD.json`: total cost, revenue, margin, by agent
- [x] Anomaly check: if cost > 2× yesterday → alert (email or log-level CRITICAL)

### P5.3 — Margin Alert System
**Insight refs**: 175, 206  
**Files**: `kpi/daily_burn.py`, `config/economics.json` (new)
- [x] `config/economics.json`: `min_margin_pct`, `max_daily_burn_usd`, `cost_explosion_multiplier`, `runtime_cost_per_task_usd`
- [x] Trigger `COST_EXPLOSION` alert if agent exceeds spending threshold — `[AGENT_COST_EXPLOSION]` per-agent + `[COST_EXPLOSION]` aggregate
- [x] Negative margin agents flagged in daily report — `[NEGATIVE_MARGIN]` alert per agent

---

## PHASE 6 — SECURITY HARDENING (Week 6–7)
*Insights driving this phase: 186, 187, 188, 192, 196, 199*

Prevent the collapse. These are structural, not cosmetic.

### P6.1 — Input Sanitization Layer
**Insight refs**: 186  
**Files**: `api/intake.py`
- [x] Add `sanitize_input()` function: strip control chars, limit field lengths, detect injection patterns — `api/intake.py:sanitize_input()`
- [x] Log `SUSPICIOUS_INPUT` when patterns detected (prompt injection, SQL, script tags) — `[SUSPICIOUS_INPUT]` + `[REJECTED_INPUT]` logging
- [x] Reject inputs exceeding size limits with 413 error — 32K field limit enforced

### P6.2 — Secret Scan in Logs
**Insight refs**: 187  
**Files**: `utils/secret_scanner.py`
- [x] Pattern-match logs for: API key formats, passwords, tokens, PII patterns — 15 regex patterns in `secret_scanner.py`
- [x] Runs on log write in dev; runs as nightly scan in prod — `scan_log_files()` + `--scan-logs` CLI, nightly via `scheduler/runner.py:_maybe_nightly_secret_scan()`
- [x] On detection: mask value, log `SECRET_LEAK_DETECTED` alert — critical log in `scan_text()`

### P6.3 — Credential TTL Enforcement
**Insight refs**: 199  
**Files**: `config/credentials_ttl.json`, `utils/credential_ttl.py`
- [x] Define TTL per key type in config — `config/credentials_ttl.json` (90d LLM, 180d Stripe)
- [x] On startup: check age of each key, warn if > TTL — `check_credential_ttl()` called from `api/intake.py` startup
- [x] Log `STALE_CREDENTIAL` warning — do not auto-fail, do alert — `[STALE_CREDENTIAL]` warnings per key

### P6.4 — Post-Mortem Template
**Insight refs**: 209  
**Files**: `00_COMMAND/POST_MORTEM_TEMPLATE.md`
- [x] Standard sections: What happened, Impact, Root cause, Doctrine gap, Fix applied, Doctrine update — 10-section template in place
- [x] Every incident > P2 severity requires completed post-mortem within 48 hours — documented in template
- [x] Post-mortems stored in `00_COMMAND/post_mortems/` — directory created with naming convention README

---

## PHASE 7 — DOCTRINE ENFORCEMENT (Week 7–8)
*Insights driving this phase: 29, 39, 40, 241*

Doctrine as infrastructure. Versioned. Referenced. Required.

### P7.1 — Doctrine Version in All Runs
**Insight refs**: 29, 40  
**Files**: `config/constants.py`, `dispatcher/router.py`, `kpi/logger.py`, `billing/tracker.py`
- [x] Add `DOCTRINE_VERSION = "2.0"` to `config/constants.py` — canonical source, imported by router + logger
- [x] All task log entries include `doctrine_version` — `kpi/logger.py` imports from `config.constants`
- [x] All billing events include `doctrine_version` — `billing/tracker.py` usage table has `doctrine_version` column

### P7.2 — Doctrine Changelog
**Insight refs**: 40  
**Files**: `00_COMMAND/DOCTRINE_CHANGELOG.md`
- [x] Semver entries per doctrine change — comprehensive changelog in place
- [x] Required fields: version, date, changed insights, system impact — all entries include these
- [x] Linked to from `BRS_2_0_FRAMEWORK.md` — LINKED DOCUMENTS section added

### P7.3 — Quarterly Doctrine Review
**Insight refs**: 241  
**Files**: `scheduler/runner.py`
- [x] Q2 2026: first scheduled review — `_maybe_quarterly_review_reminder()` triggers months 1,4,7,10 day 1
- [x] Review agenda: failed insights vs reality, new patterns emerging, sunset candidates — logged in reminder
- [x] Output: updated framework + changelog entry — reminder includes agenda items

---

## PRIORITY MATRIX

| Priority | Phase | Key Capability | Revenue Impact | Risk Reduction |
|----------|-------|---------------|---------------|----------------|
| P0 | 1 | Task lineage + traceability | HIGH | HIGH |
| P0 | 1 | Fail closed (no silent failures) | HIGH | HIGH |
| P0 | 1 | Billing surface audit | HIGH | MEDIUM |
| P1 | 2 | Agent registry + cost ceilings | MEDIUM | HIGH |
| P1 | 3 | QA rule registry + confidence scores | HIGH | HIGH |
| P1 | 4 | Delivery receipts + webhook retry | MEDIUM | MEDIUM |
| P2 | 5 | Per-agent P&L + daily burn | MEDIUM | MEDIUM |
| P2 | 6 | Input sanitization + secret scan | LOW | HIGH |
| P3 | 7 | Doctrine versioning + changelog | LOW | LOW |

---

## WHAT BRS 2.0 WILL NEVER BE
*From Insight 243, 237, 221*

- A dashboard product
- A SaaS platform with seats
- A chatbot or assistant
- A general-purpose AI tool
- An agent that decides to help
- A system that requires client training
- A system that stores client data permanently
- A system that bypasses QA for speed

---

## SUCCESS METRICS
*From Insight 224, 128, 249*

| Metric | Target | Measured By |
|--------|--------|-------------|
| QA Pass Rate | ≥ 92% per agent | `kpi/logger.py` |
| Task Lineage Coverage | 100% of tasks | `dispatcher/router.py` |
| Silent Failure Rate | 0% | absence of tasks without artifacts |
| Per-Agent Margin | ≥ 90% | `billing/tracker.py` |
| Delivery-to-Receipt Gap | < 5s | `delivery/` logs |
| Repeat Client Rate | > 40% by Month 2 | `billing/tracker.py` |
| Cost Explosion Events | 0 | `kpi/daily_burn.py` |
