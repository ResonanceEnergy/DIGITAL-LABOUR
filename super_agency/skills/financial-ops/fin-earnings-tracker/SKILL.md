# SKILL: fin-earnings-tracker
## AI Earnings Tracker

Monitors earnings calendars, tracks pre/post earnings price action,
generates AI-powered analysis of earnings calls, and alerts on portfolio-
relevant events. Integrates with TESLACALLS2026 and Financial Operations.

### Triggers
- Cron: Daily at 5:00 AM — check today's earnings calendar
- Event: Earnings released for tracked company → analysis pipeline
- Event: Portfolio holding reports earnings → priority alert
- Manual: "earnings today", "when does [TICKER] report", "analyze [TICKER] earnings"

### What It Does
1. Pulls earnings calendar for next 7 days (Yahoo Finance, Nasdaq API)
2. Cross-references with portfolio holdings (auto-prioritize)
3. Pre-earnings: historical beat/miss rate, analyst consensus, options flow
4. Post-earnings: price reaction, revenue/EPS vs estimates, guidance changes
5. Earnings call analysis: key quotes, sentiment shifts, forward guidance
6. Summarizes into actionable intelligence for Financial Ops department
7. Updates portfolio risk flags based on earnings results

### Tracked Metrics
| Metric | Source | Frequency |
|---|---|---|
| EPS (actual vs estimate) | Yahoo Finance | Per earnings |
| Revenue (actual vs estimate) | Yahoo Finance | Per earnings |
| Guidance (raised/lowered/maintained) | Earnings call transcript | Per earnings |
| Price reaction (AH + next day) | Market data | Per earnings |
| Options implied move vs actual | Options chain | Per earnings |
| Analyst rating changes | Tipranks, Zacks | Post earnings |

### Portfolio Integration
```
Portfolio Holdings (from portfolio.json)
  ├── TSLA — reports Q4 on [date]
  │     Pre: Consensus EPS $0.73, Revenue $25.9B
  │     Options imply ±8.2% move
  │
  ├── NVDA — reports Q4 on [date]
  │     Pre: Consensus EPS $5.41, Revenue $38.1B
  │     Last 4 quarters: Beat by avg 12%
  │
  └── [other holdings...]
```

### Output Format
```
EARNINGS TRACKER — [date]

📅 TODAY'S EARNINGS
  Before Market:
    [PORTFOLIO] TSLA — Tesla Inc — Consensus: EPS $0.73 / Rev $25.9B
    WMT — Walmart Inc — Consensus: EPS $1.52 / Rev $164B

  After Market:
    [PORTFOLIO] NVDA — NVIDIA Corp — Consensus: EPS $5.41 / Rev $38.1B

📊 YESTERDAY'S RESULTS
  MSFT — Beat — EPS $3.12 vs $2.98 est (+4.7%)
    Revenue: $65.6B vs $64.5B est (+1.7%)
    Guidance: Raised FY26 outlook
    Price: +3.2% after hours
    Key quote: "AI revenue grew 157% YoY..."

⚠️ PORTFOLIO ALERTS
  TSLA reporting today — Options imply ±8.2% move
  Recommendation: Review position size before close

📅 THIS WEEK
  Wed: META, QCOM
  Thu: AMZN, AAPL [PORTFOLIO]
  Fri: None
```

### Dependencies
- ai-earnings-tracker skill (clawhub install ai-earnings-tracker)
- Yahoo Finance API / yfinance
- Portfolio holdings data (portfolio.json)
- TESLACALLS2026 repo integration
- Financial Operations Department agents
- Earnings call transcript source (optional)
