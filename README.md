# BIT RAGE LABOUR
## AI Labor Operations — Autonomous Agents That Earn

This is not a chatbot. This is not a SaaS product.  
This is **digital labor** — autonomous agents that complete real tasks for real companies and get paid.

**Part of the Resonance Energy portfolio. Monitored by NCL (separate repo).**  
See `RESONANCE_ENERGY_SOT.md` for system boundaries and architecture.

## Structure

```
00_COMMAND/          — BRL doctrine, operations framework, governance
agents/              — 46 agent modules across 4 divisions
api/                 — Intake webhook (FastAPI) + routers
automation/          — NERVE daemon, email tracking, job discovery
billing/             — Invoice + payment tracking (Stripe)
c_suite/             — Executive AI (AXIOM CEO, VECTIS COO, LEDGR CFO)
config/              — LLM config, agent registry, banned phrases
delivery/            — Output delivery (email, file export, webhooks)
dispatcher/          — Task routing + queue + budget + ops commander
galactia/            — Intelligence engine (NCL-bound, temporary — see SOT)
kpi/                 — Metrics logging + weekly reports
```

## 4 Divisions

| Division | Code | Head | TAM | Agents |
|----------|------|------|-----|--------|
| Insurance Operations | INS-OPS | AXIOM | $500B | insurance_appeals, insurance_qa, insurance_compliance |
| Grant Operations | GRANT-OPS | AXIOM | $150B | grant_writer, grant_qa, grant_researcher |
| Contractor Services | CTR-SVC | VECTIS | $2T | contractor_doc_writer, contractor_qa, contractor_compliance |
| Municipal Services | MUN-SVC | VECTIS | $400B | municipal_doc_writer, municipal_qa, municipal_compliance |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/ResonanceEnergy/DIGITAL-LABOUR.git
cd DIGITAL-LABOUR

# 2. Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # Add your API keys

# 3. Run single agent
python agents/sales_ops/runner.py --company "Acme Corp" --role "Head of Growth"

# 4. Run full API
python bitrage.py start

# 5. Master launcher
python bitrage.py          # Interactive menu
python bitrage.py status   # System status
python bitrage.py health   # Health dashboard
```

## Deployment

Production: Railway — `bitrage-labour-api-production.up.railway.app`

```bash
git push origin main    # Auto-deploys via Railway
```

## Doctrine

This project governs itself under **BRS 2.0 Framework**.  
See `00_COMMAND/` for operations doctrine and action plans.  
See `RESONANCE_ENERGY_SOT.md` for how this fits into the broader Resonance Energy portfolio.
