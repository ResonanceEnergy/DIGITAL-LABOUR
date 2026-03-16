# SKILL: tech-knowledge-base
## NCL Knowledge Base Integration

Bridges OpenClaw with the NCL Second Brain system, enabling semantic search
across all ingested content (YouTube transcripts, documents, research papers,
code documentation) via natural language queries.

### Triggers
- Manual: "search knowledge base for [topic]", "what do we know about [subject]"
- Manual: "ingest [URL]", "add this to the brain"
- Event: New document added to NCL → auto-index for OpenClaw search
- Cron: Daily knowledge base health check and re-indexing

### What It Does
1. **Search Mode**: Natural language query → NCL semantic search → ranked results
2. **Ingest Mode**: URL or file → NCL processing pipeline → indexed and searchable
3. **Context Mode**: Provides relevant knowledge base context to other skills
4. **Audit Mode**: Reports knowledge base statistics, coverage gaps, stale entries

### Search Flow
```
User: "What did we learn about multi-agent architectures?"
  ↓
OpenClaw routes to tech-knowledge-base skill
  ↓
NCL semantic search across all indexed content
  ↓
Results ranked by relevance + recency
  ↓
Top 5 results returned with source attribution
```

### Ingest Flow
```
User: "Ingest this video: https://youtube.com/watch?v=..."
  ↓
OpenClaw routes to tech-knowledge-base skill
  ↓
NCL engine: download → transcribe → chunk → embed → store
  ↓
Confirmation: "Ingested: 'Video Title' — 47 chunks, 12,340 tokens"
```

### Knowledge Base Coverage
| Content Type | Source | Count | Auto-Ingest |
|---|---|---|---|
| YouTube Transcripts | YouTube Intelligence Division | 500+ | Yes (daily) |
| Research Papers | Intelligence Ops research agents | 200+ | Yes (weekly) |
| Code Documentation | REPO DEPOT across 27 repos | 1000+ | Yes (on commit) |
| Meeting Notes | Executive Council sessions | 100+ | Manual |
| Market Reports | Financial Ops analysis | 150+ | Yes (weekly) |
| Web Articles | Tech news digest results | 2000+ | Yes (daily) |

### Integration with Other Skills
```
Morning Brief → queries knowledge base for relevant context
Market Research → searches for historical analysis on topics
Auto-Build → retrieves code patterns and documentation
Project State → links decisions to supporting knowledge
Dashboard → shows knowledge base health metrics
```

### Output Format (Search)
```
KNOWLEDGE BASE SEARCH — "[query]"
Results: 5 of 127 matches (showing top 5)

[1] Relevance: 0.94 — "Multi-Agent Architecture Patterns"
    Source: YouTube transcript — Lex Fridman #412
    Date: 2026-01-15
    Excerpt: "The key insight is that multi-agent systems work best
    when agents have clear role separation and a shared memory layer..."

[2] Relevance: 0.89 — "AutoGen Multi-Agent Framework"
    Source: Research paper — Microsoft Research
    Date: 2026-02-01
    Excerpt: "We propose a framework for building multi-agent conversations..."

[3] ...
```

### Output Format (Stats)
```
KNOWLEDGE BASE STATUS
Total Documents: 3,847
Total Chunks: 89,234
Storage: 2.3 GB / 10 GB
Last Indexed: 4 minutes ago
Health: GOOD

By Type:
  YouTube: 512 docs (13,456 chunks)
  Research: 234 docs (8,901 chunks)
  Code: 1,891 docs (52,334 chunks)
  Articles: 1,210 docs (14,543 chunks)
```

### Dependencies
- knowledge-base-rag skill (clawhub install knowledge-base-rag)
- NCL Second Brain engine + adapters
- Embedding model (local or API)
- Vector store (ChromaDB / Pinecone / local)
- YouTube Intelligence Division (for auto-ingest pipeline)
- REPO DEPOT (for code documentation indexing)
