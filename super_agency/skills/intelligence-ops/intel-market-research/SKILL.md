# SKILL: intel-market-research
## Last-30-Days Market Research Intelligence

Mines Reddit, X (Twitter), forums, and news for brand/product intelligence
over a rolling 30-day window. Maps sentiment, competitor activity, and
emerging trends for any target topic.

### Triggers
- Cron: Weekly on Monday at 7:00 AM
- Manual: "research [topic]", "what are people saying about [product]"
- Event: New portfolio company added → auto-research

### What It Does
1. Accepts target topic (company, product, technology, competitor)
2. Searches Reddit (top subreddits), X/Twitter, Hacker News, Product Hunt
3. Collects last 30 days of mentions, discussions, and sentiment
4. Clusters related discussions by theme
5. Scores sentiment per cluster (positive/negative/neutral)
6. Identifies emerging competitors and alternative products
7. Produces structured research report

### Data Sources
| Source | Method | Coverage |
|---|---|---|
| Reddit | API search + subreddit scan | r/LocalLLaMA, r/artificial, r/MachineLearning |
| Twitter/X | KOL monitoring + search | Industry accounts, trending hashtags |
| Hacker News | API + Algolia search | Show HN, Ask HN, comments |
| Product Hunt | Web search | New launches, competitor products |
| GitHub | Trending repos + stars velocity | Open source alternatives |

### Output Format
```
MARKET RESEARCH REPORT — [topic] — Last 30 Days

SENTIMENT OVERVIEW
  Positive: 64%  |  Neutral: 22%  |  Negative: 14%

TOP THEMES
[1] "Theme Name" — 47 mentions — Sentiment: +0.72
    Summary: ...
    Key quotes: ...

[2] "Theme Name" — 31 mentions — Sentiment: -0.15
    Summary: ...

COMPETITOR LANDSCAPE
- Competitor A: 128 mentions, sentiment +0.45, growing
- Competitor B: 89 mentions, sentiment +0.31, stable

EMERGING SIGNALS
- Signal 1: Early buzz about [feature] — 12 mentions this week vs 2 last month
- Signal 2: ...

RAW DATA: [link to full dataset]
```

### Dependencies
- last-30-days skill (clawhub install last-30-days)
- web_search (built-in)
- bird skill for X/Twitter (optional)
- Research Intelligence Division agents for deep analysis
