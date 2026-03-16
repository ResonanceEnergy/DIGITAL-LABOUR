# Legacy Directories

These directories are retained for reference but are **not part of the active runtime**.

## `archive/`
Historical code snapshots, old dashboard versions, dead code.
Preserved for git archaeology; nothing imports from here.

## `demo_repo_depot/`
Scaffold demos generated during initial REPO DEPOT development.
All three projects (ai_chat_api, data_visualization_dashboard, ml_model_service)
are placeholder stubs with TODO comments — they were never completed.
Now excluded from git tracking via `.gitignore`.

## Legacy Streamlit Files
- `streamlit_matrix_maximizer.py` — Original Streamlit dashboard (superseded by Flask `matrix_maximizer.py`)
- `MATRIX_MAXIMIZER/dashboard.py` — Alternate Streamlit version
- `matrix_monitor/` — Early monitoring prototype

These remain importable by `agent_gasket.py` (guarded import, graceful fallback), but are
no longer the primary dashboard. The active dashboard is the Flask-based `matrix_maximizer.py`.

---

*Tagged: March 2026*
