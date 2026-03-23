# NCC C-SUITE GOVERNANCE DOCTRINE
## DIGITAL LABOUR — Autonomous Executive Layer

**Authority**: NCC — Natrix Command & Control
**Version**: 1.0
**Status**: ACTIVE

---

## THE TRIAD

DIGITAL LABOUR is governed by three autonomous AI executives — the **OpenClaw C-Suite**.
Each executive is an LLM-powered agent that reads real system data, reasons about it,
and produces structured directives. They report to NCC and command the 4 worker agents.

```
                    ┌─────────────────────┐
                    │        NCC          │
                    │  Natrix Command &   │
                    │      Control        │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────▼───────┐ ┌────▼────────┐ ┌────▼────────┐
    │     AXIOM       │ │   VECTIS    │ │   LEDGR     │
    │     CEO         │ │   COO       │ │   CFO       │
    │  Strategy &     │ │  Ops &      │ │  Finance &  │
    │  Growth         │ │  Quality    │ │  Revenue    │
    └─────────┬───────┘ └────┬────────┘ └────┬────────┘
              │              │               │
              └──────────────┼───────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──┐  ┌───────▼────┐  ┌──────▼──────┐
    │ Board Room │  │ Exec Dash  │  │  Scheduler  │
    │ Synthesis  │  │ Command    │  │  Cron       │
    └────────────┘  └────────────┘  └─────────────┘
              │              │              │
    ┌─────────▼──────────────▼──────────────▼─────────┐
    │              WORKER AGENTS                       │
    │  Sales Ops │ Support │ Content │ Doc Extract     │
    └─────────────────────────────────────────────────┘
```

---

## EXECUTIVE ROSTER

### ⚡ AXIOM — Chief Executive Officer
**Full Name**: Autonomous eXecutive Intelligence for Operational Mastery
**File**: `c_suite/axiom.py`
**Class**: `AxiomCEO`

**Mandate**:
- Drive revenue growth above all else
- Identify highest-ROI actions (24h / 7d / 30d horizons)
- Allocate resources across providers and agents
- Kill underperforming initiatives
- Spot market opportunities

**Outputs**:
- Strategic directives (target: VECTIS or LEDGR)
- Growth plays with ROI estimates
- Resource allocation recommendations
- CEO verdict (executive summary)

**Commands**:
```bash
python c_suite/axiom.py              # Full strategic review
python c_suite/axiom.py --brief      # Morning brief (lighter)
python c_suite/axiom.py --provider openai
```

---

### ⚙️ VECTIS — Chief Operating Officer
**Full Name**: Velocity Engine for Continuous Task Intelligence & Scaling
**File**: `c_suite/vectis.py`
**Class**: `VectisCOO`

**Mandate**:
- Keep all 4 worker agents at peak performance
- Monitor QA pass rates (target >90%)
- Monitor latency (target <30s/task)
- Manage task queue, clear backlogs
- Route tasks to optimal providers
- Identify and fix bottlenecks

**Outputs**:
- Agent grades (A through F)
- Provider grades and routing recommendations
- Bottleneck analysis
- Operational directives
- Queue optimization recommendations

**Commands**:
```bash
python c_suite/vectis.py              # Full ops review
python c_suite/vectis.py --check      # Quick ops check
python c_suite/vectis.py --provider grok
```

---

### 💰 LEDGR — Chief Financial Officer
**Full Name**: Lattice Engine for Dynamic Growth & Revenue
**File**: `c_suite/ledgr.py`
**Class**: `LedgrCFO`

**Mandate**:
- Track every dollar in and out
- Maximize gross margin (~97% target)
- Identify unprofitable clients/task types
- Model revenue scenarios
- Issue pricing recommendations
- Generate P&L and financial projections

**Outputs**:
- P&L summary (revenue, costs, margin, trend)
- Per-client profitability analysis
- Pricing recommendations
- Cost alerts
- Revenue forecast (30/60/90 day)
- Financial directives

**Commands**:
```bash
python c_suite/ledgr.py              # Full financial review
python c_suite/ledgr.py --check      # Quick cash check
python c_suite/ledgr.py --provider anthropic
```

---

## THE BOARD ROOM

All three executives convene in the **Board Room** (`c_suite/boardroom.py`).
The synthesizer resolves conflicts, deduplicates directives, and produces
a single ranked execution queue.

**Commands**:
```bash
python c_suite/boardroom.py              # Full board meeting (3 reports + synthesis)
python c_suite/boardroom.py --quick      # Quick standup (lighter reports)
python c_suite/boardroom.py --exec axiom # Run CEO only
```

**Output Structure**:
1. Individual reports from AXIOM, VECTIS, LEDGR
2. Conflict resolution (when executives disagree)
3. Ranked execution queue with owners and deadlines
4. Risk register with mitigations
5. Next meeting schedule

---

## EXECUTIVE DASHBOARD

Real-time command view: `python c_suite/exec_dashboard.py`

Shows:
- All three executives' latest verdicts
- System vitals (providers, queue, KPIs, revenue)
- Last board meeting execution queue
- Available commands

---

## OPERATING CADENCE

| Frequency | Action | Command |
|-----------|--------|---------|
| Daily AM | Morning standup | `python c_suite/boardroom.py --quick` |
| Daily PM | Exec dashboard check | `python c_suite/exec_dashboard.py` |
| Weekly | Full board meeting | `python c_suite/boardroom.py` |
| Weekly | CFO cash check | `python c_suite/ledgr.py --check` |
| On-demand | COO ops check | `python c_suite/vectis.py --check` |
| Monthly | Full strategic review | `python c_suite/boardroom.py` (all reports) |

---

## DATA SOURCES

Each executive reads REAL system data — no hallucinated inputs:

| Data Source | Used By | Location |
|-------------|---------|----------|
| KPI events (SQLite) | ALL | `data/kpi.db` |
| KPI logs (JSONL) | ALL | `kpi/logs/*.jsonl` |
| Billing DB | LEDGR, AXIOM | `data/billing.db` |
| Task queue | VECTIS, AXIOM | `data/task_queue.db` |
| Agent runners | VECTIS | `agents/*/runner.py` |
| Provider configs | VECTIS | `utils/llm_client.py` |
| Client files | ALL | `clients/*.json` |
| Output dirs | VECTIS | `output/*/` |

---

## HIERARCHY OF AUTHORITY

1. **NCC** — Supreme governance. Sets the mandate.
2. **AXIOM (CEO)** — Interprets mandate into strategy. Final say on growth decisions.
3. **VECTIS (COO)** — Executes strategy operationally. Final say on quality/ops.
4. **LEDGR (CFO)** — Guards the money. Veto power on anything unprofitable.
5. **Worker Agents** — Execute tasks. No autonomy beyond their pipeline.

**Conflict Resolution**: When AXIOM and LEDGR disagree (e.g., CEO wants to spend, CFO wants to save), the Board Synthesizer arbitrates based on ROI data. Revenue generation wins ties.

---

## OUTPUT DIRECTORY STRUCTURE

```
output/c_suite/
├── axiom/
│   ├── axiom_directive_20260308_140000.json
│   └── axiom_brief_20260308_080000.json
├── vectis/
│   ├── vectis_ops_review_20260308_140000.json
│   └── vectis_check_20260308_080000.json
├── ledgr/
│   ├── ledgr_financial_review_20260308_140000.json
│   └── ledgr_cash_check_20260308_080000.json
└── board/
    └── board_20260308_140000.json
```

---

*OpenClaw C-Suite — Autonomous Executive Intelligence*
*Authority: NCC — Natrix Command & Control*
*Division: DIGITAL LABOUR — ALOPS*
