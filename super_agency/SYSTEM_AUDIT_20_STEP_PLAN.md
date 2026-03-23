# SYSTEM AUDIT REPORT & 20-STEP ACTION PLAN
## Date: February 26, 2026
## Status: CRITICAL — Immediate Action Required

---

## AUDIT FINDINGS SUMMARY

| Category | Issues Found | Severity |
|---|---|---|
| Python Environment | 1 (interpreter path) | FIXED |
| CI/CD Pipelines | 4 broken workflows | FIXED (python-ci.yml) |
| Git State | 1,288 dirty files, 106 tracked .pyc files | CRITICAL |
| Security | API key exposed in tracked file | CRITICAL |
| Architecture | 4 duplicate Digital-Labour copies | HIGH |
| Dependencies | requirements.txt vs pyproject.toml misaligned | HIGH |
| Configuration | Deprecated VS Code settings, dual pytest config | FIXED |
| File Organization | 152 .py files at root, 402,988 total files | HIGH |
| Git Sync | .pre-commit-config.yaml corrupted | MEDIUM |

---

## FIXES ALREADY APPLIED (This Session)

1. **VS Code interpreter path**: Changed from bare `.venv/Scripts/python.exe` to `${workspaceFolder}/.venv/Scripts/python.exe`
2. **Deprecated terminal settings**: Updated `terminal.integrated.shell.*` -> `terminal.integrated.defaultProfile.*`
3. **Black line-length mismatch**: Aligned VS Code setting to match pyproject.toml (`99`)
4. **python-ci.yml**: Updated checkout@v3→v4, setup-python@v4→v5, pinned Python 3.12, added `pip install -r requirements.txt`
5. **`.gitignore` hardened**: Added `-ResonanceEnergy.env`, `*.pid`, runtime JSON artifacts, `*-ResonanceEnergy.*`
6. **Removed deprecated linting settings**: `python.linting.enabled` and `python.linting.pylintEnabled` (superseded by Ruff)

---

## 20 PRIORITIZED NEXT STEPS

### CRITICAL (Do Now — Security & Pipeline Stability)

**Step 1: Rotate the Exposed Google Gemini API Key**
- File: `-ResonanceEnergy.env` and `.env` both contain `AIzaSyAR9YrwrjvvFZo2UAYYwoUwd8L6KxC-n00`
- Go to Google Cloud Console → API Keys → Regenerate
- This key is on shared git storage = effectively public
- Priority: **IMMEDIATE**

**Step 2: Remove Tracked __pycache__ and .pyc Files from Git**
```powershell
git rm -r --cached **/__pycache__/ 2>$null
git rm --cached *.pyc 2>$null
git rm --cached **/*.pyc 2>$null
git commit -m "chore: remove tracked __pycache__ and .pyc files"
```
- Currently: 106 tracked .pyc files polluting diffs
- Priority: **IMMEDIATE**

**Step 3: Remove Tracked .pid Runtime Files from Git**
```powershell
git rm --cached .matrix_monitor.pid .matrix_monitor_v4.pid .mobile_command_center.pid .operations.pid .operations_api.pid
git commit -m "chore: remove runtime .pid files from tracking"
```
- Priority: **IMMEDIATE**

**Step 4: Fix or Disable `distributed-ci-cd.yml`**
- References non-existent: `requirements-dev.txt`, `super_agency/` dir, `package.json`
- Options: (A) Delete it, (B) Rewrite to match actual project structure
- Priority: **HIGH** — fails on every push

**Step 5: Fix `secondbrain-ingest.yml` Ollama Dependency**
- The enrichment step assumes `localhost:11434` (Ollama) — always fails in CI
- Add a conditional check or skip enrichment in CI environments
- Priority: **HIGH**

### HIGH (This Week — Architecture & Dependencies)

**Step 6: Consolidate 4 Duplicate Digital-Labour Directories**
| Path | Action |
|---|---|
| `./` (root) | Keep as canonical |
| `Digital-Labour/` | DELETE — full copy with own .git |
| `DIGITAL LABOUR/Digital-Labour/` | DELETE — another full copy |
| `repos/Digital-Labour/` | DELETE or convert to git submodule |
- Estimated savings: **~5+ GB** of duplicated files
- Priority: **HIGH**

**Step 7: Reconcile `requirements.txt` with `pyproject.toml`**
- `requirements.txt` has packages not in pyproject.toml (numpy, scikit-learn, azure-ai-openai)
- `pyproject.toml` has packages not in requirements.txt (flask, psutil, streamlit, pyyaml)
- Fix `azure-ai-openai` → correct package name (`openai`)
- Pick **one source of truth** (recommend pyproject.toml)
- Priority: **HIGH**

**Step 8: Delete All `-ResonanceEnergy` Variant Files**
- 20+ files with `-ResonanceEnergy` suffix (configs, tests, workflows, tools)
- These are file-copy "branches" — use actual git branches instead
- Priority: **HIGH**

**Step 9: Create Working `.env.example`**
- Current `.env.example` is corrupted (sync issue)
- Create with ALL required variables documented:
  ```
  GEMINI_API_KEY=your_gemini_key
  OPENAI_API_KEY=your_openai_key
  ANTHROPIC_API_KEY=your_anthropic_key
  GITHUB_TOKEN=your_github_token
  LOCAL_LLM_URL=http://localhost:11434
  LOCAL_LLM_MODEL=llama3
  ```
- Priority: **HIGH**

**Step 10: Remove Root-Level ZIP Archives**
- 6 ZIP backup files at workspace root (multi-GB)
- Move to external backup or delete — they bloat git sync
- Priority: **HIGH**

### MEDIUM (This Sprint — Code Organization)

**Step 11: Move 13 Root-Level Test Files into `tests/`**
- `test_agent_z.py`, `test_api_setup.py`, `test_flask_matrix_monitor.py`, etc.
- Should be in `tests/` directory for consistent discovery
- Priority: **MEDIUM**

**Step 12: Remove Dual pytest Configuration**
- Delete `pytest.ini` (it overrides the richer `pyproject.toml` settings silently)
- `pyproject.toml` already has `[tool.pytest.ini_options]` — keep that
- Priority: **MEDIUM**

**Step 13: Fix `config/global.yaml` Extension**
- Contains JSON content but has `.yaml` extension
- Rename to `config/global.json` or convert content to actual YAML
- Priority: **MEDIUM**

**Step 14: Move macOS plist Files to `config/launchd/`**
- 7 `.plist` files cluttering workspace root
- Create `config/launchd/` and move them there
- Priority: **MEDIUM**

**Step 15: Remove Stale Runtime Artifacts from Root**
- `operations_centers_activation_*.json` (5+ files)
- `operations_status_*.json` (6+ files)
- `comprehensive_monitoring_activation_*.json`
- Already in .gitignore — just delete the existing files
- Priority: **MEDIUM**

**Step 16: Re-enable Meaningful Pylance Diagnostics**
- ALL 15 diagnostic overrides are set to `"none"` — defeats type checking
- Enable at least: `reportMissingImports: "warning"`, `reportUndefinedVariable: "warning"`
- Priority: **MEDIUM**

### LOWER (Next Sprint — Structure & Hardening)

**Step 17: Organize 152 Root `.py` Files into Package Directories**
- Create proper package structure:
  - `agents/` (already exists — move agent_*.py into it)
  - `operations/` (operations_*.py)
  - `monitoring/` (matrix_*, comprehensive_*)
  - `memory/` (memory_*, doctrine_*)
  - `tools/` (already exists)
- Add `__init__.py` files
- Priority: **LOWER** (big refactor, needs careful testing)

**Step 18: Pin Dependency Versions**
- Neither `requirements.txt` nor `pyproject.toml` has version pins
- Run `pip freeze > requirements.lock` for reproducible builds
- Priority: **LOWER**

**Step 19: Add Branch Protection & PR Requirements**
- `config/github_config.json` defines rules but nothing enforces them
- Apply via GitHub API or manual settings
- Require PR reviews before merge to main
- Priority: **LOWER**

**Step 20: Fix Git Sync Corruption**
- `.pre-commit-config.yaml` — "cloud file provider exited unexpectedly"
- `.env.example` — inaccessible
- Check git sync status, re-download or recreate these files
- Priority: **LOWER**

---

## WORKSPACE HEALTH METRICS

| Metric | Value | Status |
|---|---|---|
| Total files | 402,988 | BLOATED |
| Python files | 17,844 | Extremely high (mostly in repos/) |
| Markdown files | 24,987 | Extremely high |
| Git dirty files | 1,288 | CRITICAL |
| Tracked .pyc files | 106 | Should be 0 |
| Tracked .pid files | 4 | Should be 0 |
| Root-level .py files | 152 | Should be <20 |
| Root-level .zip files | 6 | Should be 0 |
| Duplicate Digital-Labour copies | 4 | Should be 1 |
| Core module imports | 16/16 passing | GOOD |
| CI/CD pipeline | BROKEN | First 2 fixed |

---

## ESTIMATED EFFORT

| Steps | Time | Impact |
|---|---|---|
| Steps 1-5 (Critical) | ~2 hours | Fixes security + CI pipeline |
| Steps 6-10 (High) | ~4 hours | Removes ~5GB bloat, aligns deps |
| Steps 11-16 (Medium) | ~3 hours | Cleans structure, enables tools |
| Steps 17-20 (Lower) | ~1-2 days | Major refactor, reproducibility |
