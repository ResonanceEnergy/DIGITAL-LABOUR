# YouTube Drop + Second Brain Integration

This directory contains the complete integration between YouTube Drop transcript fetching and the NCL Second Brain enrichment pipeline.

## Quick Start

### VS Code Integration
1. Open Command Palette (`Ctrl+Shift+P`)
2. Run "Tasks: Run Task" → "SECONDBRAIN: Ingest YouTube URL"
3. Enter a YouTube URL when prompted

### Command Line
```bash
# Full pipeline
make -C tools all URL="https://www.youtube.com/watch?v=0TpON5T-Sw4"

# Individual steps
make -C tools ingest URL="https://..."
make -C tools enrich
make -C tools commit
make -C tools brief
```

### GitHub Actions
Trigger the "Second Brain - YouTube Ingest" workflow with your desired YouTube URL.

## Pipeline Stages

### 1. Ingest (`make ingest`)
- Fetches transcript from YouTube URL using `youtube-transcript-api`
- Extracts video ID from URL
- Creates output directory: `knowledge/secondbrain/YYYY/MM/VIDEO_ID/`
- Produces: `raw.vtt`, `raw.txt`, `segments.json`

### 2. Enrich (`make enrich`)
- Runs LLM analysis on transcript using local LLM (Ollama)
- Extracts insights, claims, entities, actions
- Maps to Resonance Energy doctrine principles
- Produces: `enrich.json`, `enrich.md`

### 3. Catalog Commit (`make commit`)
- Indexes enrichment into NCL Catalog with knowledge graph connections
- Creates graph edges for doctrine mapping and entity relationships
- Updates search indices

### 4. Ops Brief (`make brief`)
- Registers video in tomorrow's daily operations brief
- Creates briefing tile for human review
- Queues follow-up actions

## Output Structure

```
knowledge/secondbrain/2026/02/0TpON5T-Sw4/
├── raw.vtt          # WebVTT transcript
├── raw.txt          # Plain text transcript
├── segments.json    # Timestamped segments
├── enrich.json      # Structured enrichment data
└── enrich.md        # Human-readable enrichment
```

## Configuration

### Local LLM Setup
Set these environment variables for LLM enrichment:

```bash
export LOCAL_LLM_URL="http://localhost:11434/api/generate"  # Ollama default
export LOCAL_LLM_MODEL="llama2"  # Your model name
```

### Transcript Fetching
The fetcher uses `youtube-transcript-api` which supports:
- Automatic captions (preferred)
- Manual transcripts (fallback)
- Multiple languages (defaults to English)

## Dependencies

- Python 3.8+
- `youtube-transcript-api` for transcript fetching
- `requests` for LLM API calls
- Local LLM server (Ollama recommended)

## Schema

Enrichment output follows `ncl_second_brain/contracts/enrich.schema.json` for consistency.

## Integration Points

- **NCL Catalog**: `agents/ncl_catalog.py` manages knowledge graph
- **Ops Brief**: `agents/daily_brief.py` handles briefing queue
- **Doctrine Mapping**: Automatic mapping to Resonance Energy principles
- **Provenance**: Full audit trail with timestamps and initiators