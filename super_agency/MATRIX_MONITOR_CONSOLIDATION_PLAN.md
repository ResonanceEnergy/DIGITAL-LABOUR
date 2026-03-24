# Matrix Monitor Consolidation Plan
## Zero-Data-Loss Strategy

### Overview
This document outlines the consolidation of 25+ Matrix Monitor implementations into a single authoritative source.

---

## File Inventory

### TIER 1: PRODUCTION (KEEP)
| File | Lines | Purpose | Action |
|------|-------|---------|--------|
| `flask_matrix_monitor.py` | 755 | **PRIMARY** - Running on port 8501, Flask web UI + API | KEEP as base |
| `matrix_monitor.py` | 110 | **CORE** - MatrixMonitor class, import dependency for agents | KEEP as module |

### TIER 2: FEATURES TO MERGE INTO PRIMARY
| File | Lines | Unique Features | Action |
|------|-------|-----------------|--------|
| `streamlit_matrix_monitor.py` | 1186 | Plotly charts, Agent chatbot, Analytics UI | Extract features → merge |
| `matrix_monitor_workstation.py` | 229 | QFORGE terminal UI, SASP protocol | ARCHIVE (different purpose) |
| `aac_matrix_monitor_enhanced.py` | 70 | AAC enhanced console output | Already integrated via delegate |

### TIER 3: DUPLICATES (DELETE)
| File | Identical To | Action |
|------|--------------|--------|
| `Super-Agency/matrix_monitor.py` | `matrix_monitor.py` | DELETE |
| `repos/Super-Agency/matrix_monitor.py` | `matrix_monitor.py` (with syntax errors) | DELETE |
| `repos/Super-Agency/test_matrix_monitor.py` | `test_matrix_monitor.py` | DELETE |
| `Super-Agency/test_matrix_monitor.py` | `test_matrix_monitor.py` | DELETE |

### TIER 4: SUPPORT FILES (ARCHIVE)
| File | Purpose | Action |
|------|---------|--------|
| `matrix_monitor_project_selector.py` | Project selection demo | ARCHIVE |
| `matrix_monitor_selection_demo.py` | Selection UI demo | ARCHIVE |
| `qusar_matrix_monitor_sync.py` | QUSAR sync | ARCHIVE |
| `run_matrix_monitor_unit*.py` | Manual test runners | ARCHIVE |

### TIER 5: TESTS (KEEP SEPARATE)
| File | Purpose | Action |
|------|---------|--------|
| `test_matrix_monitor.py` | Core tests | KEEP |
| `test_flask_matrix_monitor.py` | Flask tests | KEEP |
| `tests/test_matrix_monitor_unit.py` | Unit tests | KEEP |

---

## Architecture After Consolidation

```
Matrix Monitor Architecture
═══════════════════════════

┌─────────────────────────────────────────────────────────────┐
│                     PRIMARY: flask_matrix_monitor.py         │
│              Running on port 8501 (NSSM Service)            │
├─────────────────────────────────────────────────────────────┤
│  Routes:                                                     │
│  - GET /              → Web Dashboard (HTML)                │
│  - GET /api/status    → JSON API (CPU, RAM, Agents, Repos)  │
│  - GET /api/agents    → NEW: Agent activity endpoint        │
│  - GET /api/charts    → NEW: Chart data endpoint            │
├─────────────────────────────────────────────────────────────┤
│  Features (merged from Streamlit):                          │
│  - Agent OPTIMUS/GASKET progress bars                       │
│  - QFORGE/QUSAR status                                      │
│  - Repo Depot metrics                                       │
│  - Real-time CPU/RAM/Disk monitoring                        │
│  - Chart.js integration for analytics                       │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ matrix_monitor.py│    │ agents/         │
│ (Core Module)   │◄───┤ agent_optimus.py│
│                 │    │ agent_gasket.py │
│ - InnerCouncil  │     └─────────────────┘
│ - AACDelegate   │
│ - AzureChatbot  │
└─────────────────┘
```

---

## Execution Steps

### Phase 1: Delete Duplicates
1. Remove `Super-Agency/matrix_monitor.py`
2. Remove `Super-Agency/test_matrix_monitor.py`
3. Remove `repos/Super-Agency/matrix_monitor.py`
4. Remove `repos/Super-Agency/test_matrix_monitor.py`

### Phase 2: Archive Demo/Obsolete Files
1. Create `archive/matrix_monitor_legacy/` directory
2. Move `matrix_monitor_workstation.py` → archive
3. Move `matrix_monitor_project_selector.py` → archive
4. Move `matrix_monitor_selection_demo.py` → archive
5. Move `run_matrix_monitor_unit*.py` → archive
6. Move `qusar_matrix_monitor_sync.py` → archive
7. Move `streamlit_matrix_monitor.py` → archive (features already extracted to Flask)

### Phase 3: Enhance Primary (flask_matrix_monitor.py)
1. Add `/api/agents` endpoint with full agent data
2. Add `/api/charts` endpoint for analytics data
3. Add Chart.js CDN for visual charts in HTML
4. Add agent chatbot interface in HTML (calls OPTIMUS)

### Phase 4: Update References
1. Update all imports to use primary files
2. Update documentation
3. Test all dependent agents still work

---

## Feature Matrix (Zero Data Loss Verification)

| Feature | flask_matrix_monitor | streamlit_matrix_monitor | matrix_monitor.py | Preserved In |
|---------|---------------------|-------------------------|-------------------|--------------|
| Web Dashboard | ✅ | ✅ | ❌ | flask_matrix_monitor.py |
| JSON API | ✅ | ❌ | ❌ | flask_matrix_monitor.py |
| Agent Progress | ✅ | ✅ | ❌ | flask_matrix_monitor.py |
| OPTIMUS Integration | ✅ | ✅ | ❌ | flask_matrix_monitor.py |
| GASKET Integration | ✅ | ✅ | ❌ | flask_matrix_monitor.py |
| Repo Depot Status | ✅ | ✅ | ❌ | flask_matrix_monitor.py |
| Charts/Analytics | ❌ | ✅ | ❌ | flask_matrix_monitor.py (add) |
| Agent Chatbot | ❌ | ✅ | ✅ | flask_matrix_monitor.py (add) |
| InnerCouncil Deploy | ❌ | ❌ | ✅ | matrix_monitor.py |
| AAC Delegate | ❌ | ❌ | ✅ | matrix_monitor.py |
| Global Network | ❌ | ❌ | ✅ | matrix_monitor.py |
| Console Output | ❌ | ❌ | ✅ | matrix_monitor.py |

---

## Rollback Plan

If issues occur:
1. All deleted files preserved in `archive/matrix_monitor_legacy/`
2. Git history maintains all versions
3. Flask monitor continues running unchanged during transition

---

## Generated
- Date: 2025-06-14
- By: GitHub Copilot Agent
- Status: READY FOR EXECUTION
