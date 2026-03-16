# gasket-digest

## Multi-Source Digest Pipeline (Reddit / YouTube / Tech News)

**Type**: cron-triggered
**Trigger**: cron (configurable per source)
**Model**: any

## Description

Aggregates, deduplicates, and summarizes content from multiple sources into daily digests. Covers Reddit (5 PM), YouTube (8 AM), and tech news (109+ sources). Learns user preferences over time through feedback loops. Each source type has tailored processing.

## Source Pipelines

### Reddit Digest
- **Skill**: `reddit-readonly` (no auth required)
- **Cron**: daily 5 PM
- **Process**: fetch top posts from configured subreddits → filter by score/type → summarize → deliver
- **Feedback**: "Did you like today's list?" → updates preference memory
- **Rules**: stored in memory (e.g., "no memes", "focus on AI/ML")

### YouTube Digest
- **Skill**: `youtube-full` (TranscriptAPI.com)
- **Cron**: daily 8 AM
- **Two modes**:
  - Channel-based: list of YouTube handles → `channel/latest` (FREE, 0 credits)
  - Keyword-based: topic search → `seen-videos.txt` dedup
- **Cost optimization**: `channel/resolve` and `channel/latest` are free; only transcripts cost 1 credit each
- **Output**: title, channel, duration, key takeaways from transcript

### Tech News Digest
- **Skill**: `tech-news-digest` (ClawHub, draco-agent)
- **Cron**: daily 7 AM
- **Sources**: 46 RSS feeds + 44 Twitter/X KOLs + 19 GitHub repos + 4 web search queries (Brave)
- **Quality scoring**: priority source +3, multi-source confirmation +5, recency +2, engagement +1
- **Dedup**: title similarity matching prevents repeat coverage
- **Env vars**: `X_BEARER_TOKEN`, `BRAVE_API_KEY`, `GITHUB_TOKEN`

## Preference Learning

```python
DIGEST_PREFERENCES = {
    'reddit': {
        'subreddits': ['MachineLearning', 'LocalLLaMA', 'SelfHosted', 'Python'],
        'exclude_types': ['memes', 'hiring'],
        'min_score': 50
    },
    'youtube': {
        'channels': ['@3blue1brown', '@fireship', '@ThePrimeTimeagen'],
        'keywords': ['AI agents', 'LLM', 'self-hosted'],
        'max_transcript_credits_per_day': 10
    },
    'tech_news': {
        'priority_topics': ['AI', 'agents', 'self-hosted', 'macOS'],
        'min_quality_score': 5
    }
}
```

## Integration with GASKET

- Morning brief includes digest summaries from all 3 sources
- Second Brain auto-captures high-value items from digests
- Knowledge Base RAG indexes saved digest items for future retrieval
- Preferences stored in GASKET memory doctrine files

## Digital-Labour Specific

- YouTube channels tracked: AI/ML, productivity, entrepreneurship
- Reddit: r/MachineLearning, r/LocalLLaMA, r/SelfHosted, r/AutoGen
- Tech news: focus on AI agent frameworks, MCP updates, Claude/OpenAI releases
