# SKILL: fin-portfolio-crm
## Portfolio CRM & Relationship Tracker

Central relationship management system for all portfolio companies, contacts,
investment thesis tracking, and interaction logging. Powers the Financial
Operations department's portfolio oversight.

### Triggers
- Event: New company added to portfolio.json → auto-create CRM entry
- Event: Earnings reported for portfolio company → update records
- Event: News mention of portfolio company → log and analyze
- Cron: Weekly — portfolio health check and contact follow-up reminders
- Manual: "portfolio status", "show me [company] CRM", "log interaction with [contact]"

### What It Does
1. **Company Profiles**: Maintains rich profiles for each portfolio company
2. **Contact Management**: Tracks key contacts per company (IR, CEO, analysts)
3. **Thesis Tracking**: Original investment thesis + ongoing validation
4. **Interaction Log**: Records all research, calls, notes, agent analyses
5. **Health Scoring**: Composite score based on financials, sentiment, momentum
6. **Follow-Up Engine**: Auto-generates follow-up reminders based on events
7. **Cross-Reference**: Links portfolio companies to Inner Council analysis

### Portfolio Company Profile
```yaml
company: Tesla Inc
ticker: TSLA
sector: EVs / Energy / AI
added: 2024-01-15
thesis: "AI + robotics optionality undervalued; FSD monetization catalyst"
tier: 1  # From portfolio_autotier

health_score: 82/100
  fundamentals: 78  # Revenue growth, margins, cash flow
  sentiment: 85     # Social media, analyst sentiment
  momentum: 83      # Price action, relative strength
  thesis_valid: 80  # Is original thesis still intact?

contacts:
  - name: "Investor Relations"
    role: IR
    last_contact: 2026-02-15
    notes: "Q4 earnings call"

interactions:
  - date: 2026-02-27
    type: research
    agent: warren_buffett_agent
    summary: "Buffett analysis: margins improving, thesis intact"
  - date: 2026-02-26
    type: earnings
    agent: fin-earnings-tracker
    summary: "Beat EPS by 8.2%, raised guidance"

alerts:
  - "Earnings in 14 days — prepare analysis"
  - "Insider buying detected — CFO purchased 5K shares"
```

### CRM Features
| Feature | Description |
|---|---|
| Auto-Discovery | portfolio_autodiscover adds new companies automatically |
| Auto-Tier | portfolio_autotier assigns priority tiers (1-5) |
| Thesis Validation | Quarterly check: is investment thesis still valid? |
| Contact Follow-ups | Reminds to review after earnings, news events |
| Agent Integration | Inner Council advisors contribute analysis to CRM |
| News Integration | Auto-logs relevant news mentions per company |
| Earnings Integration | Auto-updates financials after each earnings report |

### Portfolio Dashboard
```
PORTFOLIO CRM — [date]

PORTFOLIO OVERVIEW
  Companies: 12 | Tier 1: 3 | Tier 2: 4 | Tier 3: 5
  Avg Health Score: 76/100
  Thesis Validity: 83% (10/12 intact)

COMPANY HEALTH
  ┌─────────┬──────┬───────┬──────────┬────────────────────┐
  │ Ticker  │ Tier │ Score │ Thesis   │ Next Event         │
  ├─────────┼──────┼───────┼──────────┼────────────────────┤
  │ TSLA    │ 1    │ 82    │ ✅ Valid  │ Earnings Mar 15    │
  │ NVDA    │ 1    │ 91    │ ✅ Valid  │ GTC Conference     │
  │ AAPL    │ 1    │ 75    │ ⚠️ Watch │ WWDC June          │
  │ MSFT    │ 2    │ 88    │ ✅ Valid  │ Build Conference   │
  │ ...     │      │       │          │                    │
  └─────────┴──────┴───────┴──────────┴────────────────────┘

ACTION ITEMS
  [P1] Review AAPL thesis — China revenue declining 3 quarters
  [P2] TSLA earnings prep — Run Inner Council analysis
  [P3] Add new company — PLTR flagged by portfolio_autodiscover

RECENT INTERACTIONS (Last 7 Days)
  Feb 27 — TSLA — Buffett agent analysis: margins improving
  Feb 26 — NVDA — Earnings beat, guidance raised
  Feb 25 — Portfolio rebalance executed — 3 positions adjusted
```

### Dependencies
- personal-crm skill (clawhub install personal-crm)
- Portfolio management system (portfolio.json, portfolio_*.py)
- Inner Council financial advisors (Warren Buffett, Jamie Dimon, Ryan Cohen)
- fin-earnings-tracker skill (for earnings data)
- fin-market-research skill (for competitive context)
- portfolio_autodiscover + portfolio_autotier agents
- TESLACALLS2026 repo (for TSLA-specific analysis)
