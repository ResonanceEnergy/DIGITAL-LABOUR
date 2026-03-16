# SKILL: fin-market-research
## Market Research & Product Factory

Combines market research intelligence with product ideation to identify
opportunities, validate ideas, and track competitive landscapes. Powers
the Financial Operations department's strategic analysis capabilities.

### Triggers
- Cron: Weekly on Monday — market landscape update
- Manual: "research market for [product/sector]", "competitive analysis [company]"
- Event: Intelligence Ops flags emerging market trend → auto-research
- Event: Portfolio company enters new market → landscape analysis

### What It Does
1. **Market Sizing**: TAM/SAM/SOM estimation from multiple data sources
2. **Competitive Mapping**: Identifies competitors, market share, positioning
3. **Trend Analysis**: 30/90/180-day trend tracking with sentiment
4. **Product Ideation**: Identifies gaps in market → generates product concepts
5. **Validation**: Cross-references ideas against Reddit/HN/PH feedback
6. **Risk Assessment**: Market risks, regulatory changes, disruption threats

### Research Framework
```
1. Define Market → sector, geography, customer segment
2. Size Market → TAM from industry reports, bottom-up validation
3. Map Competitors → direct, indirect, potential entrants
4. Analyze Trends → growth vectors, declining segments
5. Identify Gaps → unmet needs, underserved segments
6. Generate Ideas → product concepts for gaps
7. Validate → social media sentiment, user feedback analysis
8. Score & Rank → opportunity score per idea
```

### Data Sources
| Source | Data Type | Update Frequency |
|---|---|---|
| Crunchbase | Funding rounds, company data | Weekly |
| Product Hunt | New launches, traction | Daily |
| Reddit | User sentiment, pain points | Daily |
| Hacker News | Developer sentiment, tech trends | Daily |
| GitHub | Open source adoption, stars velocity | Weekly |
| SEC/EDGAR | Financial filings, industry data | Quarterly |
| Google Trends | Search volume, interest over time | Weekly |
| App Store / Play Store | App rankings, reviews | Weekly |

### Integration with Financial Ops
```
Market Research Skill
  → Feeds competitive data to portfolio analysis
  → Alerts on disruption threats to portfolio companies
  → Validates new investment thesis before execution
  → Powers Warren Buffett Inner Council analysis sessions
  → Feeds Jamie Dimon agent for macro risk assessment
```

### Output Format
```
MARKET RESEARCH REPORT — [sector/product]

MARKET OVERVIEW
  TAM: $47B (2026) → $89B (2030) — CAGR 17.3%
  Key Players: Company A (32%), Company B (24%), Company C (18%)
  Stage: Growth → Early Maturity

COMPETITIVE LANDSCAPE
  ┌──────────────┬──────────┬───────────┬──────────┐
  │ Company      │ Share    │ Funding   │ Momentum │
  ├──────────────┼──────────┼───────────┼──────────┤
  │ Company A    │ 32%      │ $240M     │ ████░    │
  │ Company B    │ 24%      │ $180M     │ █████    │
  │ Company C    │ 18%      │ $95M      │ ███░░    │
  │ Others       │ 26%      │ Various   │ ██░░░    │
  └──────────────┴──────────┴───────────┴──────────┘

TRENDS (Last 90 Days)
  📈 Rising: AI integration (+45%), Self-service (+32%)
  📉 Declining: Legacy approach (-18%), Manual workflows (-22%)
  🆕 Emerging: On-device AI, Privacy-first solutions

OPPORTUNITY GAPS
  [1] Score: 87 — "No-code AI workflow builder for SMBs"
      Gap: Enterprise tools too complex, no SMB-focused solution
      Validation: 340 Reddit mentions, avg sentiment +0.71

  [2] Score: 73 — "AI-powered competitive monitoring for startups"
      Gap: Existing tools cost $500+/mo, startups need $50/mo tier
      Validation: 89 HN comments, avg sentiment +0.64

RISKS
  ⚠️ Regulatory: EU AI Act may require compliance by Q3 2026
  ⚠️ Technical: Foundation model costs declining → commoditization risk
  ⚠️ Market: Potential consolidation wave (3 M&A rumors tracked)
```

### Dependencies
- market-research skill (clawhub install market-research)
- last-30-days skill (for social media mining)
- web_search (built-in)
- Financial Operations Department agents
- Inner Council financial advisors (Warren Buffett, Jamie Dimon agents)
- Portfolio management system
