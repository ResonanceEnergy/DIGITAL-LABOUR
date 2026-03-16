# SUPER AGENCY → DIGITAL LABOUR — Full Integration Roadmap

**Date:** 2026-03-15
**Objective:** Complete and absolute merger of DIGITAL-LABOUR into DIGITAL LABOUR.
**Policy:** Zero data loss. Zero degradation. Full integration. Orphan source repo.

---

## SITUATION REPORT

| Metric | Value |
|--------|-------|
| DIGITAL-LABOUR total files | 12,183 |
| Digital Labour Core files (excl repos/venv/git) | 1,678 |
| DL super_agency/ current files | 826 |
| Missing from DL | ~853 files |
| "Digital Labour" refs in SA | ~1,018 |
| "Digital Labour/Digital Labour" refs in DL root | ~200+ |
| Rename target | Digital Labour → DIGITAL LABOUR |

---

## PHASE 1: FILE SYNC (Zero Data Loss)
**Goal:** Every file in DIGITAL-LABOUR (except exclusions) exists in DL super_agency/

### Copy target directories:
- `inner_council/` (154 files)
- `companies/` (86 files)
- `cicd_workflows/` (73 files)
- `archive/` (158 files)
- `sasp/` (36 files)
- `repo_depot/` (30 files)
- `proposals/` (29 files)
- `github_integration/` (28 files)
- `nextjs-openai-integration/` (27 files)
- `audit_logs/` (25 files)
- `static/` (20 files)
- `demo_repo_depot/` (18 files)
- `ncl_second_brain/` (16 files)
- `templates/` (12 files)
- `matrix_monitor/` (8 files)
- `MATRIX_MAXIMIZER/` (4 files)
- `memory_hot_reload_vscode/` (9 files)
- `daily_policy_directives/` (6 files)
- `backups/` (5 files)
- `ncc_logs/` (4 files)
- `az_decisions/` (3 files)
- `oversight_logs/` (3 files)
- `qforge/` (2 files)
- `qusar/` (2 files)
- `dashboard_data/` (1 file)
- Root scripts (~40 .ps1/.sh/.bat files)
- Investment dirs: buffett_investments, cohen_retail, dimon_finance, musk_innovations, executive_council_results

### Exclusions (NOT copied):
- `.git/` — SA repo git history
- `.venv/` — SA virtual environment
- `repos/` (10,676 files) — cloned repos (not SA core)
- `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `.ncl/`
- `backup_logs/`, `repo_backups/` — transient

---

## PHASE 2: RENAME — Digital Labour → DIGITAL LABOUR
**Goal:** All display names, codenames, docstrings reference "DIGITAL LABOUR"

### In super_agency/:
- `__init__.py`: `__codename__` → "DIGITAL LABOUR"
- All Python docstrings & comments
- All Markdown docs
- All JSON/YAML config files
- dl_manifest.json → DL_MANIFEST.json

### In DL root files:
- `matrix_boot.py`: "Digital Labour MATRIX" → "DIGITAL LABOUR MATRIX"
- `api/matrix_monitor.py`: "Digital Labour MATRIX" → "DIGITAL LABOUR MATRIX"
- `api/matrix_dashboard.html`: "Digital Labour MATRIX" → "DIGITAL LABOUR MATRIX"

### PRESERVE (do NOT rename):
- `site/` — "Digital Labour" is the customer-facing BRAND name
- `campaign/` — marketing copy references Digital Labour brand
- `income/freelance_listings.py` — platform profile content
- `automation/` — outreach templates (Digital Labour brand)
- Domain URLs: digital-labour.com (real domain)
- Email addresses: sales@digital-labour.com (real email)
- Railway URL: digital-labour-api-production (real deployment)
- Fly.io: digital-labour-api (real deployment)
- Freelancer/Upwork/Fiverr usernames (real accounts)

---

## PHASE 3: UPDATE IMPORTS & PATHS
**Goal:** All hardcoded DIGITAL LABOUR paths point to DL's super_agency/

- `~/repos/Digital-Labour` → relative paths within DL
- `DL_ROOT` env var → documented as deprecated (backward compat)
- `DL_REPO` env var → documented as deprecated
- `DIGITAL-LABOUR/` path refs → `super_agency/`
- gasket_openclaw_bridge.py paths
- data_collector.py WORKSPACE path

---

## PHASE 4: UPDATE MANIFESTS & IDENTITY
- Rebuild dl_manifest.json → DL_MANIFEST.json (new counts, new branding)
- Update super_agency/__init__.py fully
- Update super_agency/README.md
- Update super_agency/IDENTITY.md
- Update super_agency/SOUL.md

---

## PHASE 5: VERIFY ZERO DATA LOSS
- Count files: SA core (excl exclusions) == DL super_agency/
- Diff key config files
- Verify no broken imports

---

## PHASE 6: TEST & VALIDATE
- Run DL test suite
- Import smoke test for super_agency module
- Verify API still starts

---

## PHASE 7: ORPHAN SUPER AGENCY REPO
- Add ARCHIVED.md to DIGITAL-LABOUR root
- Update README.md: "ARCHIVED — Merged into DIGITAL LABOUR"
- Final commit + push to DIGITAL-LABOUR
- Remove from active development

---

## PHASE 8: UPDATE DOCUMENTATION
- Update DL README.md
- Update copilot-instructions.md
- Update repo memory notes
- Update NCC doctrine references
