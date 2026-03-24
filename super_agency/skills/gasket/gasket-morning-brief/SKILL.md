---
name: gasket-morning-brief
description: Generate GASKET morning briefing — system health, tasks, git status, recommendations
metadata: {"openclaw":{"emoji":"☀️","os":["darwin"]}}
---

Generate a comprehensive morning briefing for the Bit Rage Systems operator.

## Briefing Structure

### 1. System Health
- CPU, memory, disk across QUSAR (macOS)
- QFORGE (Windows) connectivity status

### 2. Git Status
```bash
cd ~/repos/Super-Agency && git --no-pager log --oneline -5 && echo "---" && git status --short
```

### 3. Agent Status
- GASKET operational loops (CPU 30s, QUSAR 45s, Matrix 60s, Memory 120s, Bridge 300s)
- OPTIMUS link (QFORGE)
- OpenClaw gateway health:
```bash
curl -s http://127.0.0.1:18789/health || echo "Gateway DOWN"
```

### 4. Task Board
- Search memory for recent tasks and decisions
- Check `repo_depot_status.json` for build progress

### 5. AI Recommendations
Based on system state, recommend:
- Tasks GASKET can complete autonomously
- Infrastructure items needing attention
- Memory doctrine entries to review

## Format
Use clean formatting with section headers, emojis, and actionable items.
Keep it concise — the operator should be able to read it in 60 seconds.
