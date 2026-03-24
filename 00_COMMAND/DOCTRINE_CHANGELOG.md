# DOCTRINE CHANGELOG

All breaking and significant changes to the BIT RAGE SYSTEMS (BRS) doctrine are logged here.  
Format: `[VERSION] YYYY-MM-DD — Summary`

---

## [2.0] — Phase 1–7 Implementation

**Released:** 2025-07-xx  
**Status:** ACTIVE

### Phase 1 — Foundation Hardening
- Added `lineage_id` (UUID per task) to all events, KPI logs, and billing records
- Added `schema_version: "2.0"` and `doctrine_version: "2.0"` to all task events
- Fail-closed: `_finalize_event()` now fires on every task termination path (PASS, FAIL, DISABLED, LIMIT)
- Billing surface expanded: `record_usage(status=...)` called for all tasks; charge=0 on FAIL
- Execution ceiling enforcement: logs `[CEILING]` warning when agent exceeds `max_execution_seconds`
- KPI logger schema: added `lineage_id`, `failure_reason`, `doctrine_version` columns + lineage index

### Phase 2 — Agent Registry & Governance
- Created `config/agent_registry.json` — 30 agents with cost ceilings, time budgets, failure modes
- Router loads registry at startup (`_load_registry()`, `_registry_get()`, `save_registry()`)
- Disabled agents return immediately with `failure_reason = "AGENT_DISABLED"`
- New API endpoints: `GET /agents`, `POST /admin/agents/{name}/disable`, `POST /admin/agents/{name}/enable`
- New `GET /trace/{lineage_id}` endpoint for task lineage queries
- Billing: `per_agent_economics()` returns per-agent P&L over N days

### Phase 3 — QA Hardening
- `QAResult` model: added `confidence: float`, `applied_rules: list[str]`, `failed_rule_id: str`
- Created `config/qa_rules.json` — 12 rules (QA-001 through QA-012)
- Created `config/client_profiles/default.json` — per-client QA profile support
- Pre-LLM deterministic checks: QA-001 (non-empty), QA-002 (no placeholders), QA-003 (min length), QA-004 (banned phrases)
- Confidence thresholds: ≥0.70 PASS, ≥0.50 eligible for retry, <0.50 hard FAIL
- `verify()` now accepts `client_id` param for profile-based banned phrases and thresholds

### Phase 4 — Delivery
- Added `_write_delivery_receipt()` — appends immutable receipt to `kpi/delivery_log.jsonl`
- All delivery methods now return `delivery_status: "complete" | "partial" | "failed"` (replacing `"status"`)
- Webhook retry: 3 attempts with 1s / 5s / 30s backoff before marking `delivery_status: "failed"`

### Phase 5 — Financial Observability
- Created `kpi/daily_burn.py` — daily cost monitor
  - Queries per-agent P&L from `BillingTracker.per_agent_economics()`
  - Checks against `config/economics.json` thresholds
  - Alerts: `[BURN_CEILING]`, `[COST_EXPLOSION]`, `[AGENT_CEILING]`, `[MARGIN_ALERT]`
  - Writes `kpi/reports/burn_YYYY-MM-DD.json` with `--report` flag
- Created `config/economics.json`: `min_margin_pct=85`, `max_daily_burn_usd=50`, `cost_explosion_multiplier=2×`

### Phase 6 — Security
- Input sanitization: `sanitize_input()` in `api/intake.py` — strips control chars, enforces 32K field limit, detects injection patterns
- Created `utils/secret_scanner.py` — 15 regex patterns for API keys, PII, credentials
  - `scan_text(text)` → `list[Finding]`
  - `mask_secrets(text)` → redacted copy
  - `has_secrets(text)` → bool
- Created `config/credentials_ttl.json` — API key rotation schedules (90 days LLM keys, 180 days Stripe)

### Phase 7 — Doctrine Enforcement
- Created `00_COMMAND/POST_MORTEM_TEMPLATE.md` — standardised incident review template
- Created `00_COMMAND/DOCTRINE_CHANGELOG.md` (this file)
- Created `schemas/REGISTRY.md` — agent schema field definitions

---

## [1.0] — Initial Release

**Status:** SUPERSEDED by 2.0

- Basic task routing via `dispatcher/router.py`
- File / email / webhook delivery
- Stripe billing
- KPI event logging (JSONL + SQLite)

---

*Maintained under: `00_COMMAND/DOCTRINE_CHANGELOG.md`*
