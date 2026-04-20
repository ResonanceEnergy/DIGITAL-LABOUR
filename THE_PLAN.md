# THE PLAN — Untangle NCL and Bit Rage
## Single Unified Action Plan | 2026-04-20
## References: RESONANCE_ENERGY_SOT.md

---

## Goal

Make Bit Rage (DIGITAL-LABOUR) a clean, standalone AI labor platform with no NCL/NCC code embedded in it. NCL monitors and directs Bit Rage from the outside via API. Intelligence/scrapers move to where they belong (NCL).

---

## Phase 1: Clean DIGITAL-LABOUR (Remove What Doesn't Belong)

These items are currently inside DIGITAL-LABOUR but belong elsewhere per the SOT.

### 1A. Remove `NCL/` directory from DIGITAL-LABOUR

**What's there now:** `NCL/__init__.py`, `NCL/ncl_operations_commander.py`, `NCL/events.ndjson`

**Action:** Delete the `NCL/` directory from DIGITAL-LABOUR. The NCL Operations Commander concept (pushing daily ops cadence, weekly goals, delegating task lists) should be rebuilt in the NCL repo, calling Bit Rage's API from the outside.

**Risk:** Check if anything in DIGITAL-LABOUR imports from `NCL/`. If so, remove those imports too.

### 1B. Remove `NCC/` directory from DIGITAL-LABOUR

**What's there now:** NCC integration files.

**Action:** Delete the `NCC/` directory. NCC governance concepts are part of NCL's world, not Bit Rage's.

**Risk:** Same — check for imports.

### 1C. Remove `ncl_router` from API

**What's there now:** `api/intake.py` imports and mounts an `ncl_router`. Bit Rage is serving NCL API endpoints, which is backwards.

**Action:** Remove the `ncl_router` import and mount from `api/intake.py`. If Bit Rage needs to expose data for NCL to consume, that's done through Bit Rage's own endpoints (`/v1/metrics`, `/v1/agents`, `/health`, `/v1/errors`), not through NCL-branded routes.

### 1D. Clean `.env.example`

**What's there now:** `NCC_RELAY_URL=http://127.0.0.1:8787` and `NCL_DATA_PATH=` in Bit Rage's env config.

**Action:** Remove `NCC_RELAY_URL` and `NCL_DATA_PATH`. If Bit Rage needs to call back to NCL, add a clean `NCL_API_URL` variable instead (optional, for feedback reporting).

### 1E. Update doctrine references

**What's there now:** `00_COMMAND/NCC_ALOPS_DOCTRINE.md` says "Parent: NCC — Natrix Command & Control". Other doctrine files reference NCC governance.

**Action:** Update Bit Rage doctrine to be self-contained. Bit Rage operates under its own BRS 2.0 framework. Remove NCC parent references. Bit Rage's relationship with NCL is: "NCL monitors and directs via API mandates." That's it.

---

## Phase 2: Decide Galactia's Future

Galactia (`galactia/` in DIGITAL-LABOUR) is the most significant piece of misplaced code. It's a full intelligence engine (Reddit/X/YouTube scraping, truth scoring, ML scoring, knowledge graphs, research generation) that labels itself "NCL's Intelligence Engine."

Meanwhile, the NCL repo already has `runtime/awarebot/scanner.py` doing X/YouTube/Reddit scanning.

### Options

**Option A: Move Galactia to NCL repo (full migration)**
- Take the Galactia modules (reddit_pipeline, x_pipeline, youtube_pipeline, truth_engine, ml_scorer, knowledge_store, context_governor, research_gen) and integrate them into NCL's existing Awarebot-FPC architecture
- Galactia's capabilities are MORE advanced than Awarebot (truth scoring, ML, knowledge graphs) — so this is an upgrade to NCL
- Delete `galactia/` from DIGITAL-LABOUR after migration
- Bit Rage no longer has any intelligence engine — it receives intelligence from NCL via mandates

**Option B: Keep scrapers running from Bit Rage temporarily, plan migration later**
- The scrapers work RIGHT NOW on Railway (PullPush + Arctic Shift for Reddit, YouTube RSS)
- NCL repo needs work to absorb Galactia's advanced features
- Short-term: leave scrapers running but acknowledge they're serving NCL, not Bit Rage
- Medium-term: migrate to NCL repo when NCL is being actively developed

**Recommendation:** Option B for now. The scrapers work today. Breaking them to move repos mid-stream creates risk for no immediate gain. But the SOT is clear: intelligence belongs to NCL. When we work on NCL next, Galactia migrates there.

---

## Phase 3: Make Bit Rage Self-Sufficient

After removing NCL/NCC code, ensure Bit Rage still runs cleanly on its own.

### 3A. Verify no broken imports

After removing `NCL/`, `NCC/`, and `ncl_router`, run a full import check across the codebase. Fix any `ImportError` or broken references.

### 3B. Verify Railway deployment still works

Push changes, confirm the Railway build succeeds, `/health` returns 200, agents dispatch correctly.

### 3C. Update README.md

Bit Rage's README should describe Bit Rage only. No NCL architecture diagrams. No NCC governance chains. Just: what Bit Rage is, how to run it, how to deploy it.

### 3D. Update REPO_INDEX.md / REPO_INDEX.json

Remove references to NCL/NCC modules. Index should reflect what's actually in the repo.

---

## Phase 4: Define the NCL ↔ Bit Rage API Contract

Once Bit Rage is clean, define the formal interface between NCL and Bit Rage.

### NCL calls Bit Rage (monitoring + mandates):
```
GET  /health                    → Is Bit Rage alive?
GET  /v1/metrics                → Agent performance, queue depth, costs
GET  /v1/agents                 → Agent status and capabilities
GET  /v1/errors                 → Recent errors
POST /v1/run                    → Submit task (mandate execution)
```

### Bit Rage calls NCL (feedback):
```
POST :8787/feedback             → Report results, KPIs, issues back to NCL
```

### What to build (later, not now):
- NCL-side: A "Bit Rage monitor" module in NCL repo that polls Bit Rage's endpoints
- NCL-side: A mandate-to-task translator that converts NCL mandates into Bit Rage `/v1/run` calls
- Bit Rage-side: A lightweight feedback reporter that POSTs execution results to NCL's `/feedback` endpoint (optional `NCL_API_URL` env var)

---

## Execution Order

| Step | What | Priority | Risk |
|------|------|----------|------|
| 1A | Remove `NCL/` from DIGITAL-LABOUR | HIGH | Check imports first |
| 1B | Remove `NCC/` from DIGITAL-LABOUR | HIGH | Check imports first |
| 1C | Remove `ncl_router` from intake.py | HIGH | Verify no essential endpoints lost |
| 1D | Clean `.env.example` | LOW | Safe |
| 1E | Update doctrine references | MEDIUM | Text only |
| 2 | Galactia — leave in place for now, migrate to NCL later | DEFERRED | Acknowledged in SOT |
| 3A | Verify imports after cleanup | HIGH | Must pass before deploy |
| 3B | Verify Railway deployment | HIGH | Must pass |
| 3C | Update README | MEDIUM | Text only |
| 3D | Update REPO_INDEX | LOW | Housekeeping |
| 4 | Define API contract | DEFERRED | When NCL development resumes |

---

## What This Plan Does NOT Cover (Intentionally)

- **AAC integration with NCL** — you said to add this later
- **NCL university/research arm** — you said to add this later
- **New feature development** — this plan is about untangling, not building
- **Revenue targets or marketing** — that's Bit Rage's own business plan (`MASTER_ACTION_PLAN.md`)
- **NCL repo development** — we're focused on cleaning DIGITAL-LABOUR first

---

## Success Criteria

When this plan is done:
1. DIGITAL-LABOUR contains zero NCL or NCC code
2. DIGITAL-LABOUR builds and deploys to Railway cleanly
3. All 46 agents still dispatch correctly
4. The SOT accurately describes the system as it exists in code
5. Galactia is acknowledged as NCL-bound but left functional until migration

---

*This is THE plan. One plan. If new work doesn't fit here, it goes in a new plan or it waits.*
*Authority: NATRIX — Resonance Energy*
