# BIT RAGE SYSTEMS
## AI Labor Operations — Autonomous Agents That Earn

This is not a chatbot. This is not a SaaS product.  
This is **digital labor** — autonomous agents that complete real tasks for real companies and get paid.

**BIT RAGE SYSTEMS** unifies BIT RAGE SYSTEMS (execution) + Super Agency (orchestration) under one command.

## Structure

```
bitrage.py           — Master launcher & control panel (THE ONE COMMAND)
00_COMMAND/          — NCC doctrine, war plan, governance
agents/              — 25 individual agent modules (sales, support, content, etc.)
super_agency/        — Super Agency (orchestration, C-Suite, departments, tools)
  agents/            — 40+ SA agents (CEO, CFO, CIO, CMO, CTO, specialists)
  departments/       — Organizational structure (executive, intel, ops, finance, tech)
  tools/             — Utility functions and engines
  NCC/               — Neural Command Center (governance layer)
  NCL/               — Neural Cognitive Layer (second brain)
api/                 — Intake webhook (FastAPI) + Matrix Monitor C2
automation/          — NERVE daemon, outreach, orchestrator, job aggregators
billing/             — Stripe integration, invoicing, payment tracking
c_suite/             — Executive agents (AXIOM CEO, LEDGR CFO, VECTIS COO)
campaign/            — Go-to-market, freelance deployment, social content
config/              — LLM config, banned phrases, env
delivery/            — Output delivery (email, file export)
dispatcher/          — Task routing + queue + budget enforcement
income/              — Revenue tracking, freelance listings, proposals
kpi/                 — Metrics logging + weekly reports
openclaw/            — OpenClaw dispatch engine
resonance/           — NCC/NCL/AAC cross-pillar sync bridges
scheduler/           — Retainer task runner
utils/               — Shared utilities (alerts, export, validation)
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/ResonanceEnergy/DIGITAL-LABOUR.git
cd DIGITAL-LABOUR

# 2. Setup
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env    # Add your API keys

# 3. Run Sales Ops Agent (single lead)
python agents/sales_ops/runner.py --company "Acme Corp" --role "Head of Growth"

# 4. Run full pipeline
python dispatcher/router.py
```

## Income Targets
- **Day 5**: First paid task
- **Day 12**: First retainer ($750+/mo)
- **Day 30**: $3,000/mo run rate
- **Month 2**: $5,000+/mo

## Doctrine
This project operates under **NCC AI LABOR OPERATIONS (ALOPS)**.  
See `00_COMMAND/` for governance, war plan, and doctrine.
