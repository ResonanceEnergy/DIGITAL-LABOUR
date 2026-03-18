---
name: gasket-memory-doctrine
description: Manage GASKET memory doctrine — read, search, update system memory and doctrine files
metadata: {"openclaw":{"emoji":"🧠","os":["darwin"]}}
---

GASKET Memory Doctrine manages the BIT RAGE LABOUR knowledge base.

## Memory Locations
- `{baseDir}/../memory/` — Daily logs (`memory/YYYY-MM-DD.md`)
- `{baseDir}/../MEMORY.md` — Curated long-term memory
- `~/repos/Digital-Labour/doctrine/` — System doctrines (OPENCLAW_DOCTRINE.md, etc.)

## When Asked to Remember Something

1. Use `memory_search` to find relevant existing memories
2. Use `memory_get` to read specific files
3. Write new memories to `memory/YYYY-MM-DD.md` (today's date)
4. For durable facts (preferences, decisions), also append to `MEMORY.md`

## Doctrine Files

Check `~/repos/Digital-Labour/doctrine/` for:
- **OPENCLAW_DOCTRINE.md** — OpenClaw knowledge base (v4.0 GASKET Integration Edition)
- Other doctrine files as they are created

## Key Principles
- **Write it down.** Never keep important info in RAM only.
- No folders, no tags, no complex organization — just text and search.
- Timestamp every entry.
- Include context (who said it, where, why it matters).
- For links, include a brief description of what/why.

## Memory Maintenance (runs every 2 minutes)
- Check RAM usage via psutil
- Scan doctrine directory for new/modified files
- Update memory index if files changed
- Log maintenance results to daily memory file
