# SKILL: intel-news-digest
## Multi-Source Tech News Digest

Aggregates, scores, and delivers tech/AI news from 109+ sources across RSS,
Twitter/X, GitHub releases, and web search.

### Triggers
- Cron: Daily at 9:00 AM
- Manual: "tech news", "what happened in AI today"

### What It Does
1. RSS Feeds (46+ sources) — OpenAI, Hacker News, MIT Tech Review, Anthropic
2. Twitter/X KOLs (44+ accounts) — @karpathy, @sama, researchers
3. GitHub Releases (19+ repos) — vLLM, LangChain, Ollama, Dify
4. Web Search (Brave API) — trending AI/tech topics
5. All articles merged, deduped by title similarity
6. Quality-scored (priority source +3, multi-source +5, recency +2)
7. Final digest delivered to intelligence channel

### Quality Scoring
| Factor | Points | Description |
|---|---|---|
| Priority Source | +3 | From curated high-quality source list |
| Multi-Source | +5 | Mentioned across multiple sources |
| Recency | +2 | Published within last 6 hours |
| Engagement | +1 | High engagement on social media |

### Sources Configuration
Sources can be customized via natural language:
```
Add these to my tech digest:
- RSS: https://blog.anthropic.com/feed
- Twitter: @ClaudeAI
- GitHub: anthropics/claude-code
```

### Output Format
```
TECH NEWS DIGEST — [date] — [count] stories

[1] [SCORE: 11] "Title of Top Story"
    Source: Hacker News + Twitter + RSS
    Summary: ...
    Link: ...

[2] [SCORE: 8] "Another Important Story"
    Source: MIT Tech Review
    Summary: ...
    Link: ...
```

### Dependencies
- tech-news-digest skill (clawhub install tech-news-digest)
- web_search (built-in)
- bird skill for Twitter/X (optional)
- Brave API key (optional, for web search layer)
