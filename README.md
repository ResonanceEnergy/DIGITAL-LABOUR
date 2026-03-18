# BIT RAGE LABOUR
## AI Labor Operations — Autonomous Agents That Earn

This is not a chatbot. This is not a SaaS product.  
This is **digital labor** — autonomous agents that complete real tasks for real companies and get paid.

## Structure

```
00_COMMAND/          — NCC doctrine, war plan, governance
agents/              — Individual agent modules
  sales_ops/         — Lead enrichment + cold outreach
  support/           — Ticket triage + resolution
  ops_brief/         — Daily executive briefings
  doc_extract/       — Document → structured data
  qa/                — Verifier / QA agent (shared)
api/                 — Intake webhook (FastAPI)
billing/             — Invoice + payment tracking
config/              — LLM config, banned phrases, env
delivery/            — Output delivery (email, file export)
demos/               — Demo output packs (sales proof)
dispatcher/          — Task routing + queue + budget enforcement
kpi/                 — Metrics logging + weekly reports
listings/            — Marketplace listing copy + DM templates
offers/              — Retainer offers + onboarding docs
schemas/             — JSON schemas for all agent I/O
utils/               — Shared utilities (export, validation)
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
