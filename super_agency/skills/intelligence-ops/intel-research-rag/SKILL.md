# SKILL: intel-research-rag
## Research Intelligence RAG Knowledge Base

Semantic search and retrieval-augmented generation across all Research Intelligence
Division content — papers, notes, transcripts, web articles.

### Triggers
- Event: URL/content dropped in knowledge-base topic → auto-ingest
- Manual: "search knowledge base for [query]", "what do I know about [topic]"
- Cron: Every 6 hours — reindex new content

### What It Does
1. Ingests URLs, tweets, PDFs, YouTube transcripts into NCL Second Brain
2. Vector-powered semantic search via memsearch integration
3. Hybrid search (dense vectors + BM25) with RRF reranking
4. SHA-256 content hashing — unchanged files never re-embedded
5. File watcher auto-reindexes on memory file changes
6. Cross-references with Research Intelligence agent specializations

### Research Agent Specializations
| Agent | Domain | Ingest Sources |
|---|---|---|
| Andrew Huberman | Neuroscience, health | Podcast transcripts, papers |
| Peter Attia | Longevity, medicine | Clinical research, protocols |
| Daniel Schmachtenberger | Systems thinking | Lectures, essays |
| Geoffrey Hinton | Deep learning | Papers, interviews |
| Demis Hassabis | AGI, DeepMind | Papers, talks |

### Query Examples
- "What caching solution did we pick for the API layer?"
- "Andrew Huberman's recommendations on sleep optimization"
- "Geoffrey Hinton's latest concerns about AI safety"
- "What did Peter Attia say about Zone 2 training?"

### Integration with Other Skills
- intel-youtube-digest → transcripts auto-ingested
- intel-news-digest → articles auto-ingested
- exec-council-brief → top insights surfaced in morning brief
- tech-project-state → research linked to project decisions

### Dependencies
- memsearch (pip install memsearch)
- NCL Second Brain engine (ncl_second_brain/engine/)
- memory_doctrine_system.py
- departments/intelligence_operations/research_intelligence/ agents
