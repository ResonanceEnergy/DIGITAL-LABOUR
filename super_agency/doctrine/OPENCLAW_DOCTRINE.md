# OPENCLAW DOCTRINE - KNOWLEDGE BASE REFERENCE
## Ingested from docs.openclaw.ai + openclaw.ai + awesome-openclaw-usecases | 2026-02-27
## System-Wide Integration Doctrine v5.0

---

## WHAT IS OPENCLAW

OpenClaw is a **self-hosted gateway** that connects chat apps (WhatsApp, Telegram, Discord, iMessage, Slack, Signal) to AI coding agents. You run a single Gateway process on your own machine and it becomes the bridge between your messaging apps and an always-available AI assistant.

- **Self-hosted**: runs on YOUR hardware, YOUR rules
- **Multi-channel**: one Gateway serves all chat apps simultaneously
- **Agent-native**: built for coding agents with tool use, sessions, memory, multi-agent routing
- **Open source**: MIT licensed, community-driven
- **Creator**: Peter Steinberger (@steipete) + community
- **Mascot**: Molty, a space lobster AI
- **Install**: `curl -fsSL https://openclaw.ai/install.sh | bash`
- **Prereqs**: Node 22+
- **Formerly known as**: Clawdbot / Moltbot

---

## ARCHITECTURE

```
Chat apps + plugins → GATEWAY (WebSocket :18789) → Pi agent
                                ↕
                    CLI / Web Control UI / macOS app
                                ↕
                    iOS and Android nodes
```

**Gateway is the single source of truth** for sessions, routing, and channel connections.

### Key Components
| Component | Description |
|-----------|-------------|
| Gateway | WebSocket server on port 18789 - channels, nodes, sessions, hooks |
| Pi Agent | Coding agent in RPC mode with tool streaming |
| Channels | WhatsApp (Baileys), Telegram (grammY), Discord, iMessage, Slack, Signal |
| Nodes | Companion devices (macOS/iOS/Android/headless) connected via WS |
| Skills | AgentSkills-compatible SKILL.md folders |
| Control UI | Browser dashboard at http://127.0.0.1:18789/ |
| ClawHub | Public skills registry at https://clawhub.com |
| Memory | Plain Markdown files + vector search index |

---

## GATEWAY

### Configuration
- Config file: `~/.openclaw/openclaw.json`
- Default port: **18789**
- Bind modes: `loopback` (default), `lan`, `tailnet`, `auto`, `custom`
- Auth modes: `token`, `password`, `trusted-proxy`
- Discovery: Bonjour mDNS `_openclaw-gw._tcp`

### CLI Commands
```bash
openclaw gateway                    # Run gateway (foreground)
openclaw gateway run               # Foreground alias
openclaw gateway health --url ws://127.0.0.1:18789
openclaw gateway status [--json]
openclaw gateway probe [--json]     # Debug everything command
openclaw gateway install            # Install as service
openclaw gateway start/stop/restart # Service lifecycle
openclaw gateway discover           # Scan for Gateway beacons
openclaw gateway call <method>      # Low-level RPC helper
openclaw onboard --install-daemon   # First-time setup wizard
openclaw dashboard                  # Open Control UI in browser
```

### Gateway Options
- `--port <port>`: WebSocket port
- `--bind <mode>`: listener bind mode
- `--auth <token|password>`: auth mode
- `--token <token>`: token override
- `--tailscale <off|serve|funnel>`: expose via Tailscale
- `--force`: kill existing listener on port
- `--verbose`: verbose logs

### Environment Variables
- `OPENCLAW_HOME`: home directory for internal path resolution
- `OPENCLAW_STATE_DIR`: override state directory
- `OPENCLAW_CONFIG_PATH`: override config file path

---

## CHANNELS

### Supported Channels
WhatsApp, Telegram, Discord, iMessage, Slack, Signal, Mattermost (plugin), MS Teams

### DM Policies
| Policy | Behavior |
|--------|----------|
| `pairing` (default) | Unknown senders get short code, bot ignores until approved. Codes expire 1 hour. |
| `allowlist` | Unknown senders blocked, no pairing handshake |
| `open` | Allow anyone (requires `"*"` in allowlist) |
| `disabled` | Ignore inbound DMs entirely |

### CLI Commands
```bash
openclaw channels list              # List all channels
openclaw channels status             # Runtime status
openclaw channels capabilities       # Feature support probe
openclaw channels add --channel <ch> --token <token>
openclaw channels remove --channel <ch> --delete
openclaw channels login --channel <ch>
openclaw channels logout --channel <ch>
openclaw channels resolve --channel <ch> <name>
openclaw channels logs --channel all
```

---

## MEMORY SYSTEM (DEEP DIVE)

### Memory Files (Markdown)
Two memory layers in the workspace (`~/.openclaw/workspace`):
- `memory/YYYY-MM-DD.md` — Daily log (append-only), read today + yesterday at session start
- `MEMORY.md` — Curated long-term memory, only loaded in main private session

### Memory Tools
- `memory_search` — semantic recall over indexed snippets
- `memory_get` — targeted read of a specific Markdown file/line range

### Writing Memory
- Decisions, preferences, durable facts → `MEMORY.md`
- Day-to-day notes, running context → `memory/YYYY-MM-DD.md`
- If someone says "remember this", write it down (do NOT keep in RAM)

### Vector Memory Search
- Builds vector index over `MEMORY.md` + `memory/*.md`
- Enabled by default, watches for file changes
- Providers: OpenAI, Gemini, Voyage, Mistral, local (node-llama-cpp GGUF)
- Auto-selects provider based on available API keys
- SQLite storage at `~/.openclaw/memory/<agentId>.sqlite`
- Hybrid search: BM25 keyword + vector semantic (configurable weights)
- MMR re-ranking for diversity (reduces duplicate snippets)
- Temporal decay for recency boost (half-life configurable, default 30 days)

### QMD Backend (Experimental)
- Local-first search sidecar: BM25 + vectors + reranking
- Fully local via Bun + node-llama-cpp (no Ollama needed)
- Auto-downloads GGUF models from HuggingFace on first use
- `memory.backend = "qmd"` in config to enable
- Periodic updates configurable (`memory.qmd.update.interval`, default 5m)

### Memory Config Example
```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "query": {
          "hybrid": {
            "enabled": true,
            "vectorWeight": 0.7,
            "textWeight": 0.3,
            "mmr": { "enabled": true, "lambda": 0.7 },
            "temporalDecay": { "enabled": true, "halfLifeDays": 30 }
          }
        },
        "cache": { "enabled": true, "maxEntries": 50000 }
      }
    }
  }
}
```

### Pre-Compaction Memory Flush
When session nears auto-compaction, OpenClaw triggers a silent turn to store durable notes before context is compacted. Controlled by `agents.defaults.compaction.memoryFlush`.

---

## COMPACTION

### What It Is
Summarizes older conversation into a compact summary entry, keeps recent messages intact. The summary persists in session JSONL history.

### Auto-Compaction
Triggers when session nears or exceeds model context window. Before compaction, a memory flush preserves durable notes.

### Manual Compaction
```
/compact Focus on decisions and open questions
```

### Compaction vs Pruning
- **Compaction**: summarizes and persists in JSONL
- **Session pruning**: trims old tool results only, in-memory, per request

---

## TOOLS (FULL INVENTORY)

### Tool Groups
| Group | Tools |
|-------|-------|
| `group:runtime` | `exec`, `bash`, `process` |
| `group:fs` | `read`, `write`, `edit`, `apply_patch` |
| `group:sessions` | `sessions_list`, `sessions_history`, `sessions_send`, `sessions_spawn`, `session_status` |
| `group:memory` | `memory_search`, `memory_get` |
| `group:web` | `web_search`, `web_fetch` |
| `group:ui` | `browser`, `canvas` |
| `group:automation` | `cron`, `gateway` |
| `group:messaging` | `message` |
| `group:nodes` | `nodes` |
| `group:openclaw` | all built-in OpenClaw tools |

### Tool Profiles
| Profile | Tools |
|---------|-------|
| `minimal` | `session_status` only |
| `coding` | `group:fs`, `group:runtime`, `group:sessions`, `group:memory`, `image` |
| `messaging` | `group:messaging`, session tools |
| `full` | no restriction |

### Key Tools

#### `exec` — Run shell commands
- `command` (required), `yieldMs`, `background`, `timeout` (default 1800s)
- `host`: `sandbox | gateway | node`
- `security`: `deny | allowlist | full`
- PTY support: `pty: true`

#### `browser` — Chrome automation
- Actions: `status`, `start`, `stop`, `tabs`, `open`, `focus`, `close`, `snapshot`, `screenshot`, `act`, `navigate`
- Profile management: `profiles`, `create-profile`, `delete-profile`, `reset-profile`
- Multi-instance via `profile` parameter

#### `message` — Cross-platform messaging
- Channels: Discord, Google Chat, Slack, Telegram, WhatsApp, Signal, iMessage, MS Teams
- Actions: `send`, `poll`, `react`, `edit`, `delete`, `pin`, `thread-create`, `search`, `role-add`, `event-create`

#### `cron` — Scheduled jobs
- Actions: `status`, `list`, `add`, `update`, `remove`, `run`, `runs`
- `wake` for system events + immediate heartbeat

#### `sessions_spawn` — Subagent orchestration
- `task`, `label`, `runtime` (`subagent` | `acp`), `agentId`, `model`
- One-shot (`mode: "run"`) or persistent thread-bound (`mode: "session"`)
- Non-blocking, returns `status: "accepted"` immediately

#### `nodes` — Device control
- Actions: `status`, `describe`, `notify`, `run`, `camera_snap`, `camera_clip`, `screen_record`, `location_get`

#### `web_search` / `web_fetch` — Web access
- Brave Search API for search; HTML→markdown for fetch
- Cached (default 15 min)

### Loop Detection
Blocks repetitive no-progress tool-call loops. Detectors: `genericRepeat`, `knownPollNoProgress`, `pingPong`.

---

## BROWSER CONTROL

### Profiles
- `openclaw`: dedicated OpenClaw-managed Chrome instance (isolated)
- `chrome`: controls existing Chrome tabs via extension relay

### CLI Commands
```bash
openclaw browser tabs                  # List tabs
openclaw browser open <url>            # Open new tab
openclaw browser focus <targetId>      # Focus tab
openclaw browser close <targetId>      # Close tab
openclaw browser snapshot              # DOM snapshot
openclaw browser screenshot            # Visual screenshot
openclaw browser navigate <url>        # Navigate
openclaw browser click <ref>           # Click element
openclaw browser type <ref> "text"     # Type into element
openclaw browser profiles              # List profiles
openclaw browser create-profile --name <n>
openclaw browser --browser-profile <p> start
```

### Chrome Extension
```bash
openclaw browser extension install     # Install unpacked extension
openclaw browser extension path        # Get extension path
```

---

## SKILLS

### Structure
- SKILL.md with YAML frontmatter + instructions
- Locations: bundled > `~/.openclaw/skills` > `<workspace>/skills`
- Precedence: workspace (highest) → managed → bundled (lowest)
- Per-agent: `<workspace>/skills` scoped to that agent only
- Shared: `~/.openclaw/skills` visible to all agents
- Extra dirs: `skills.load.extraDirs` in config

### SKILL.md Format
```yaml
---
name: skill-name
description: What the skill does
metadata:
  {"openclaw": {"requires": {"bins": ["tool"], "env": ["API_KEY"]}, "primaryEnv": "API_KEY"}}
---
Instructions for the agent (use {baseDir} for skill folder path)...
```

### Optional Frontmatter Keys
- `homepage` — URL surfaced in macOS Skills UI
- `user-invocable` — `true|false` (default: true)
- `disable-model-invocation` — exclude from model prompt
- `command-dispatch: tool` — bypass model, dispatch directly to tool
- `command-tool` — tool name for dispatch
- `command-arg-mode: raw` — forward raw args string

### Gating (Load-Time Filters)
```yaml
metadata:
  {"openclaw": {
    "always": true,
    "emoji": "🔧",
    "os": ["darwin"],
    "requires": {"bins": ["uv"], "env": ["API_KEY"], "config": ["browser.enabled"]},
    "install": [{"id": "brew", "kind": "brew", "formula": "package", "bins": ["cmd"]}]
  }}
```

### ClawHub Registry
```bash
clawhub install <skill-slug>    # Install skill
clawhub update --all             # Update all
clawhub sync --all               # Scan + publish
```

### Plugins + Skills
Plugins can ship their own skills via `openclaw.plugin.json`. Plugin skills load when plugin is enabled.

### Skills Watcher
Auto-refresh on `SKILL.md` changes (configurable debounce, default 250ms).

### Token Impact
Per skill: ~97 chars + name + description + location in system prompt (~24 tokens per skill).

---

## SESSION MANAGEMENT

### DM Scope Modes
| Mode | Behavior |
|------|----------|
| `main` (default) | All DMs share one session for continuity |
| `per-peer` | Isolate by sender ID across channels |
| `per-channel-peer` | Isolate by channel + sender (recommended multi-user) |
| `per-account-channel-peer` | Isolate by account + channel + sender |

### Identity Links
Map provider-prefixed peer IDs to canonical identity so same person shares session across channels:
```json
{
  "session": {
    "identityLinks": {
      "alice": ["telegram:123456789", "discord:987654321012345678"]
    }
  }
}
```

### State Paths
- Store: `~/.openclaw/agents/<agentId>/sessions/sessions.json`
- Transcripts: `~/.openclaw/agents/<agentId>/sessions/<SessionId>.jsonl`

### Session Keys
- Direct: `agent:<agentId>:<mainKey>`
- Group: `agent:<agentId>:<channel>:group:<id>`
- Cron: `cron:<job.id>`
- Webhook: `hook:<uuid>`
- Node runs: `node-<nodeId>`

### Chat Commands
- `/new` or `/reset` — fresh session (accepts model alias: `/new claude`)
- `/status` — reachability + context usage + WhatsApp cred freshness
- `/context list` or `/context detail` — system prompt contents + biggest context contributors
- `/stop` — abort current run + clear queued followups + stop sub-agent runs
- `/compact` — summarize older context (optional instructions)
- `/send on|off|inherit` — toggle delivery for this session

### Lifecycle
- Daily reset: 4:00 AM local (configurable `session.reset.atHour`)
- Idle reset: optional `idleMinutes` sliding window
- Per-type overrides: `resetByType` for `direct`, `group`, `thread`
- Per-channel overrides: `resetByChannel`
- Reset triggers: `/new`, `/reset` (custom via `resetTriggers`)

### Maintenance
- Modes: `warn` (default) or `enforce`
- `pruneAfter`: 30d default
- `maxEntries`: 500 default
- `rotateBytes`: 10mb default
- `maxDiskBytes`: hard upper bound (optional)
- `highWaterBytes`: defaults to 80% of maxDiskBytes

### Send Policy
Block delivery for specific session types without listing individual IDs:
```json
{
  "session": {
    "sendPolicy": {
      "rules": [
        { "action": "deny", "match": { "channel": "discord", "chatType": "group" } },
        { "action": "deny", "match": { "keyPrefix": "cron:" } }
      ],
      "default": "allow"
    }
  }
}
```

---

## MULTI-AGENT ROUTING

### Concept
Each agent = fully scoped brain with own workspace, state dir, session store, auth profiles.

### Paths
- Config: `~/.openclaw/openclaw.json`
- Workspace: `~/.openclaw/workspace-<agentId>`
- Agent dir: `~/.openclaw/agents/<agentId>/agent`
- Sessions: `~/.openclaw/agents/<agentId>/sessions`

### Routing Priority (most-specific wins)
1. `peer` match (exact DM/group/channel id)
2. `parentPeer` match (thread inheritance)
3. `guildId + roles` (Discord role routing)
4. `guildId` (Discord)
5. `teamId` (Slack)
6. `accountId` match for channel
7. Channel-level match (`accountId: "*"`)
8. Fallback to default agent

### CLI Commands
```bash
openclaw agents add <name>           # Create new agent
openclaw agents list --bindings      # List agents + routing
openclaw channels login --channel <ch> --account <id>
```

### Multi-Agent Config Example
```json
{
  "agents": {
    "list": [
      {"id": "main", "workspace": "~/.openclaw/workspace-main"},
      {"id": "gasket", "workspace": "~/.openclaw/workspace-gasket"}
    ]
  },
  "bindings": [
    {"agentId": "main", "match": {"channel": "discord", "accountId": "default"}},
    {"agentId": "gasket", "match": {"channel": "telegram"}}
  ]
}
```

---

## SECURITY

### Trust Model
**Personal assistant model**: one trusted operator boundary per gateway.

### Core Principle
> Identity FIRST → Scope NEXT → Model LAST
> Assume the model can be manipulated; limit blast radius.

### Quick Audit
```bash
openclaw security audit              # Basic check
openclaw security audit --deep       # Full probe
openclaw security audit --fix        # Auto-fix
```

### Hardened Baseline
```json
{
  "gateway": {
    "mode": "local",
    "bind": "loopback",
    "auth": {"mode": "token", "token": "long-random-token"}
  },
  "session": {"dmScope": "per-channel-peer"},
  "tools": {
    "profile": "messaging",
    "deny": ["group:automation", "group:runtime", "group:fs"],
    "fs": {"workspaceOnly": true},
    "exec": {"security": "deny", "ask": "always"}
  },
  "channels": {
    "whatsapp": {"dmPolicy": "pairing", "groups": {"*": {"requireMention": true}}}
  }
}
```

### Critical Security Warnings
- **900+ exposed servers** found publicly leaking API keys
- AI will happily hardcode secrets in code — enforce pre-push hooks (TruffleHog)
- Prompt injection via group chats is a real attack vector
- **Never run on primary machines** or with access to real accounts without sandboxing
- Cost exposure: $80-300+/day with unrestricted API access
- Use dedicated burner accounts for all services

### Credential Storage
| Credential | Path |
|------------|------|
| WhatsApp creds | `~/.openclaw/credentials/whatsapp/<accountId>/creds.json` |
| Pairing allowlists | `~/.openclaw/credentials/<channel>-allowFrom.json` |
| Auth profiles | `~/.openclaw/agents/<agentId>/agent/auth-profiles.json` |
| Secrets payload | `~/.openclaw/secrets.json` (optional) |

### Sandboxing
- Docker-based tool isolation
- Scopes: `agent` (default), `session`, `shared`
- Workspace access: `none` (default), `ro`, `rw`
- `setupCommand` runs once after container creation
- Requires network egress + writable root FS + root user for package installs

---

## NODES (DEVICES)

### What Are Nodes
Companion devices (macOS/iOS/Android/headless) connected to Gateway WebSocket with `role: "node"`.

### Capabilities
- Canvas: snapshot, present, navigate, eval
- Camera: snap (photo), clip (video), list
- Screen: record (mp4)
- Location: get (lat/lon/accuracy)
- SMS: send (Android only)
- System: run (shell commands), notify, which

### CLI Commands
```bash
openclaw devices list                                    # List devices
openclaw devices approve <requestId>                     # Approve pairing
openclaw nodes status                                    # Node status
openclaw nodes describe --node <id>                      # Node details
openclaw nodes run --node <id> -- <command>              # Run command
openclaw nodes camera snap --node <id>                   # Take photo
openclaw nodes camera clip --node <id> --duration 10s    # Record video
openclaw nodes canvas snapshot --node <id>               # Canvas screenshot
openclaw nodes canvas present --node <id> --target <url> # Show URL
openclaw nodes location get --node <id>                  # Get location
openclaw nodes screen record --node <id> --duration 10s  # Screen record
openclaw node run --host <gw> --port 18789               # Start headless node
openclaw node install --host <gw> --port 18789           # Install as service
```

### Remote macOS Nodes
If Gateway runs on Linux but a macOS node is connected with `system.run` allowed, macOS-only skills become eligible. Agent executes via `nodes.run`.

---

## PAIRING PROTOCOL

### How It Works
1. Unknown sender DMs the bot
2. Bot generates short pairing code (expires 1 hour, max 3 pending per channel)
3. Operator approves via CLI
4. Sender is added to allowlist

### CLI Commands
```bash
openclaw pairing list <channel>         # List pending requests
openclaw pairing approve <channel> <code>  # Approve pairing
```

### Our Discord Config
- Discord ID: `1472532435219775560`
- Pairing Code: `736NHRN8`
- DM Policy: `pairing`
- Group Policy: `allowlist`

---

## CRON JOBS & AUTOMATION

### Configuration
```json
{
  "cron": {
    "jobs": [
      {
        "id": "morning-brief",
        "schedule": "0 8 * * *",
        "task": "Generate morning briefing",
        "agentId": "gasket"
      },
      {
        "id": "health-check",
        "schedule": "*/15 * * * *",
        "task": "Run system health check",
        "agentId": "gasket"
      }
    ]
  }
}
```

### Session Keys for Cron
- Isolated cron jobs always mint a fresh `sessionId` per run (no idle reuse)
- Session key: `cron:<job.id>`

---

## OUR Digital-Labour INTEGRATION

### Dual-Agent System
```
QFORGE (Windows) ──── AGENT OPTIMUS ──── MATRIX MONITOR   (real-time telemetry)
QUSAR  (macOS)   ──── AGENT GASKET  ──── MATRIX MAXIMIZER (intervention/intelligence)
```

### OpenClaw in OPTIMUS DEPOT
- **Subsystem 5**: OpenClawBridge
- **Gateway**: ws://127.0.0.1:18789
- **CLI Path (Windows)**: `C:\Users\gripa\AppData\Roaming\npm\openclaw.cmd`
- **Version**: v2026.2.25 (config from 2026.2.26)
- **Features Active**: Gateway launch, browser control, Discord channel

### GASKET → OpenClaw Communication
- Primary: `POST http://127.0.0.1:18789/api/chat` with `{"message": "...", "agent": "GASKET"}`
- Fallback: write to `~/.openclaw/workspace/gasket_instructions.json`

### QFORGE Network
- QFORGE (Windows): 192.168.1.200
- QUSAR (macOS): 192.168.1.100
- Gateway Port: 18789
- SASP Protocol Port: 8888

### OpenClaw Agent IDs for GASKET
```json
{
  "agents": {
    "list": [
      {"id": "gasket", "workspace": "~/.openclaw/workspace-gasket"},
      {"id": "optimus", "workspace": "~/.openclaw/workspace-optimus"}
    ]
  },
  "bindings": [
    {"agentId": "gasket", "match": {"channel": "discord", "peer": "GASKET_DM"}},
    {"agentId": "gasket", "match": {"channel": "telegram"}}
  ]
}
```

---

## AWESOME USE CASES — FULL CATALOG (30 Community Patterns)

### 1. Second Brain (Zero-Friction Capture)
Text anything to OpenClaw via Telegram/iMessage/Discord — it remembers instantly. Build a searchable Next.js dashboard with `Cmd+K` search. No folders, no tags — just text and search. Key: capture should be as easy as texting.

### 2. Self-Healing Infrastructure
Cron-based health checks on services. SSH + kubectl + Terraform + Ansible access. Auto-restart pods, scale resources, fix configs. Morning briefings with system health. **Critical**: TruffleHog pre-push hooks mandatory; local Gitea for staging; human review before main merges; dedicated 1Password vault for agent.

### 3. Multi-Agent Specialized Team
Multiple agents with distinct roles (Strategy Lead, Business Analyst, Marketing, Dev). Each has own personality, model, and scheduled tasks. Shared memory (GOALS.md, DECISIONS.md, PROJECT_STATUS.md) + private context per agent. All accessible through one Telegram group chat with @-tagging. Real value: scheduled proactive tasks, not just reactive.

### 4. Autonomous Project Management (STATE.yaml)
Decentralized coordination via `STATE.yaml` files (single source of truth). Main session = coordinator only (spawn/send, 0-2 tool calls). PM subagents own their STATE.yaml and update status. Git as audit log. Pattern: `sessions_spawn(label="pm-xxx", task="...")`.

### 5. Semantic Memory Search (memsearch)
Vector-powered search over OpenClaw markdown memory files. `pip install memsearch` → `memsearch index ~/memory/` → `memsearch search "query"`. SHA-256 content hashing — unchanged files never re-embedded. Hybrid: dense vectors + BM25 + RRF reranking. File watcher for live sync.

### 6. Custom Morning Brief
Daily structured report at 8:00 AM via Telegram/Discord. Overnight news research, task review, actionable content drafts (not just ideas). AI-recommended tasks = most powerful section — proactive help. Fully customizable via text ("add weather to my morning brief").

### 7. YouTube Content Pipeline
Hourly cron scans breaking AI news (web + X/Twitter) and pitches video ideas to Telegram. Maintains 90-day video catalog with view counts to avoid re-covering topics. SQLite + vector embeddings for semantic dedup. Link sharing in Slack → researches topic, searches X, queries knowledge base, creates Asana card with full outline. Skills: `x-research-v2`, `knowledge-base`, `gog` CLI, Asana.

### 8. Overnight App Builder (Goal-Driven Autonomous Tasks)
Brain dump all goals to OpenClaw. Every morning it generates 4-5 tasks it can complete autonomously. Goes beyond apps: research, scripts, features, content. Tracks on a self-built Kanban board. Overnight: builds surprise MVP mini-apps. Pattern: `sessions_spawn` for task execution, Next.js Kanban for tracking. **Key**: the brain dump is everything — more context = better daily tasks.

### 9. Multi-Agent Content Factory
Pipeline across Discord channels: Research Agent (#research) scans trending topics → Writing Agent (#scripts) produces full drafts → Thumbnail Agent (#thumbnails) generates AI images. Runs automatically on schedule. Chained agents where output feeds next stage. Local image gen (Nano Banana) keeps costs down. Adaptable for tweets, newsletters, LinkedIn, podcasts.

### 10. Knowledge Base RAG
Drop any URL into Telegram/Slack → auto-ingests (articles, tweets, YouTube transcripts, PDFs). Semantic search: "What did I save about agent memory?" Returns ranked results with sources. Feeds into other workflows (video pipeline queries KB for relevant saved content). Skills: `knowledge-base` from ClawHub, `web_fetch`.

### 11. Autonomous Game Dev Pipeline
One-game-every-7-minutes production pipeline. Agent manages full lifecycle: select from queue → implement HTML5/CSS3/JS → register in games-list.json → document → Git workflow (feature branch, commit, merge). **Bugs First** policy: check/fix bugs before new features. Round-robin strategy across age groups. Design rules enforced (no frameworks, mobile-first, offline-capable). Real product: [elbebe.co](https://elbebe.co/).

### 12. Daily Reddit Digest
Cron at 5 PM: top posts from favorite subreddits. Skill: `reddit-readonly` (no auth needed). Agent learns preferences over time via feedback loop — "did you like today's list?" Rules saved to memory (e.g., "no memes"). Read-only: browsing, searching posts, pulling comments.

### 13. Daily YouTube Digest
Morning digest of new videos from favorite channels. Skill: `youtube-full` from ClawHub (TranscriptAPI.com — works everywhere, no yt-dlp). `channel/latest` and `channel/resolve` are **free** (0 credits), only transcripts cost 1 credit each. Two modes: channel-based (list of handles) or keyword-based (topic search + `seen-videos.txt` dedup).

### 14. Dynamic Dashboard (Sub-Agent Spawning)
Spawns sub-agents in parallel to fetch data from multiple sources (GitHub, Twitter, Polymarket, system health). Aggregates into unified dashboard (text/HTML/Canvas). Updates every N minutes via cron. Alert thresholds (stars change > 50/hr, CPU > 90%). Stores historical metrics in PostgreSQL. **Key pattern**: `sessions_spawn` for parallel data fetching avoids sequential blocking and rate limits.

### 15. Earnings Tracker
Weekly Sunday preview: scans earnings calendar, filters tech/AI companies (NVDA, MSFT, GOOGL, META, etc.), posts to Telegram. User picks companies → one-shot cron jobs scheduled for each earnings date. After report drops: search for results, format summary (beat/miss, EPS, revenue, AI highlights, guidance). Learns which companies you typically track.

### 16. Event Guest Confirmation (Voice Calls)
Uses `SuperCall` plugin for AI phone calls. Iterates guest list, calls each person as "event coordinator for [name]". Confirms attendance, collects dietary needs, plus-ones. Compiles summary: confirmed/declined/no-answer/notes. **Key**: SuperCall is sandboxed — AI persona has NO access to gateway agent, files, or tools. Safety from prompt injection. Requires Twilio + OpenAI Realtime API + ngrok. Transcripts logged to `~/clawd/supercall-logs`.

### 17. Family Calendar & Household Assistant
Aggregates 5+ calendars (work, family, school, camp) from different platforms. **Ambient message monitoring** (killer feature): watches iMessages passively, detects appointment patterns ("Your appointment is confirmed for..."), auto-creates calendar events with 30-min driving buffers. Photo-based input: snap school calendar PDF → OCR → events. Household inventory: photo of fridge/pantry → structured data. Grocery lists that dedup across recipes. Best on Mac Mini (always-on iMessage). Skills: `ical`, `imessage`.

### 18. Health & Symptom Tracker
Log food + symptoms via Telegram topic. 3x daily cron reminders (8 AM/1 PM/7 PM). Markdown log file with timestamps. Weekly Sunday analysis: correlate foods with symptoms, time-of-day patterns, trigger identification. Memory file tracks known triggers and updates as patterns emerge.

### 19. Inbox De-clutter (Newsletter Digest)
Skill: `gmail-oauth`. Daily 8 PM cron: read all newsletter emails from past 24 hours, extract most important bits with links. Feedback loop: ask if digest was good, update memory with preferences for improved future curation. Optional: dedicated Gmail for OpenClaw, subscribe newsletters there only.

### 20. Market Research & Product Factory
Skill: `Last 30 Days` — mines Reddit and X for real pain points over 30 days. Surfaces complaints, feature requests, gaps. Then: "Build me an MVP that solves [pain point]." Full research-to-prototype pipeline. Weekly Monday cron for ongoing market intelligence. **Entrepreneurship on autopilot**: find problems → validate demand → build solutions, all through text.

### 21. Multi-Channel Personal Assistant
Single AI unifying Telegram (topic-based), Slack, Google Workspace, Todoist, Asana. Context-based routing: "Add to todo" → Todoist, "Schedule meeting" → `gog` Calendar, "Email about..." → Gmail draft, "Upload to Drive" → `gog drive`. Automated reminders (trash day, weekly company letter). Skills: `gog` CLI, Slack (app + user tokens), Todoist API, Asana API.

### 22. Multi-Channel Customer Service
Unified inbox: WhatsApp Business + Instagram DMs + Gmail + Google Reviews. AI auto-responds to FAQs, appointment requests. Human handoff for complaints/refunds. Test mode (prefix `[TEST]`, log but don't send). Auto-detect customer language (ES/EN/UA). Heartbeat: check for unanswered messages > 5 min. **Real result**: restaurant reduced response from 4+ hours to under 2 minutes, 80% automated.

### 23. Multi-Source Tech News Digest
Four-layer pipeline: RSS (46 sources) + Twitter/X KOLs (44 accounts) + GitHub Releases (19 repos) + Web Search (4 queries via Brave). Merged, deduplicated by title similarity, quality-scored (priority source +3, multi-source +5, recency +2, engagement +1). Delivered to Discord/email/Telegram. Skill: `tech-news-digest` from ClawHub. Env vars: `X_BEARER_TOKEN`, `BRAVE_API_KEY`, `GITHUB_TOKEN`.

### 24. n8n Workflow Orchestration (Security Proxy)
**Pattern**: OpenClaw delegates ALL external API interactions to n8n via webhooks. Agent NEVER touches credentials. Flow: agent designs workflow → builds via n8n API → user adds credentials manually → user locks workflow → agent calls webhook URL. Three wins: observability (visual n8n UI), security (credential isolation), performance (deterministic workflows don't burn LLM tokens). Docker stack: [openclaw-n8n-stack](https://github.com/caprihan/openclaw-n8n-stack). n8n has 400+ integrations. **Key AGENTS.md rule**: "NEVER store API keys in my environment or skill files."

### 25. Phone-Based Personal Assistant (ClawdTalk)
Any phone becomes AI gateway. Call a number → speak with your AI agent. Calendar queries, Jira updates, web search via voice. Skill: [ClawdTalk](https://github.com/team-telnyx/clawdtalk-client) + Telnyx. SMS support coming. Hands-free: driving, walking, busy hands.

### 26. Polymarket Autopilot (Paper Trading)
Automated paper trading on prediction markets. Strategies: TAIL (trend-follow on volume spikes), BONDING (contrarian on overreactions), SPREAD (arBit Rage Labour when YES+NO > 1.05). PostgreSQL for trade logs and portfolio. Starting capital simulation: $10,000. Cron every 15 min. Daily Discord summary: trades, P&L, win rate, strategy performance. Sub-agents for parallel market analysis. **Paper trading only**.

### 27. Project State Management (Event-Driven)
Replaces Kanban with event-driven system. Talk naturally: "Finished auth flow, starting dashboard" → logs event, updates state. Events: progress, blocker, decision, pivot — all with context. Daily standup auto-generated from events + git commits. Natural language queries: "Why did we pivot on X?" → searches decision history. Git commits auto-linked to projects by branch/message. PostgreSQL tracks full history.

### 28. Personal CRM
Daily 6 AM cron scans email + calendar for new contacts/interactions. Stores in SQLite: name, email, first_seen, last_contact, interaction count, notes. Morning 7 AM meeting prep: for each external attendee, pulls CRM + email history, delivers briefing via Telegram. Natural language: "What do I know about [person]?", "Who needs follow-up?". Skills: `gog` CLI (Gmail + Calendar).

### 29. Todoist Task Manager (Agent Visibility)
Syncs agent's internal reasoning to Todoist for transparency. Sections: 🟡 In Progress → 🟠 Waiting → 🟢 Done. Agent posts its PLAN as task description, sub-step completions as comments. Heartbeat script detects stalled tasks. Bash scripts: `todoist_api.sh` (curl wrapper), `sync_task.sh` (create/move tasks), `add_comment.sh` (progress logs). Makes long-running agent work inspectable.

### 30. X Account Analysis (Bird Skill)
Qualitative analysis of X/Twitter account beyond basic analytics. Skill: `bird` (pre-bundled, `clawhub install bird`). Auth via Chrome cookies (`auth-token`, `ct0`). Insights: viral post patterns, engagement by topic, what causes <5 likes vs 1000+ likes. Create dedicated ClawdBot X account for security isolation.

---

## KEY SKILLS & PLUGINS REFERENCED

| Skill | Source | Purpose |
|-------|--------|---------|
| `youtube-full` | ClawHub (therohitdas) | YouTube transcripts, channel data |
| `reddit-readonly` | ClawHub (buksan1950) | Reddit browsing, no auth |
| `knowledge-base` | ClawHub | RAG ingestion and semantic search |
| `x-research-v2` | ClawHub | X/Twitter research and monitoring |
| `bird` | Pre-bundled | X/Twitter account access and analysis |
| `tech-news-digest` | ClawHub (draco-agent) | 109+ source news aggregation |
| `Last 30 Days` | GitHub (matvanhorde) | Reddit + X market research |
| `gmail-oauth` | ClawHub (kai-jar) | Gmail read/write access |
| `gog` CLI | - | Google Workspace (Calendar, Gmail, Drive) |
| `SuperCall` | ClawHub (xonder) | AI voice phone calls via Twilio |
| `ClawdTalk` | GitHub (team-telnyx) | Phone-based voice assistant |
| `memsearch` | pip | Vector search over memory files |
| `imessage` | Built-in | macOS iMessage integration |
| `ical` | Built-in | Calendar integration |

---

## INTEGRATIONS (50+)
WhatsApp, Telegram, Discord, Slack, Signal, iMessage, Claude, GPT, Spotify, Hue, Obsidian, Twitter, Browser, Gmail, GitHub, MS Teams, Google Chat, 1Password, Todoist, Apple Reminders, Asana... and more via plugins.

---

## KEY REFERENCES
- Documentation: https://docs.openclaw.ai
- GitHub: https://github.com/openclaw/openclaw
- ClawHub: https://clawhub.com
- Trust: https://trust.openclaw.ai
- Discord Community: https://discord.com/invite/clawd
- Showcase: https://openclaw.ai/showcase
- Blog: https://openclaw.ai/blog
- Getting Started: https://docs.openclaw.ai/start/getting-started
- Skills: https://docs.openclaw.ai/tools/skills
- Memory: https://docs.openclaw.ai/concepts/memory
- Session: https://docs.openclaw.ai/concepts/session
- Tools: https://docs.openclaw.ai/tools
- Compaction: https://docs.openclaw.ai/concepts/compaction
- memsearch: https://github.com/zilliztech/memsearch

---

*This doctrine was auto-generated from OpenClaw docs, website scraping, and awesome-openclaw-usecases.*
*Saved to the Bit Rage Labour Memory doctrine system.*
*Doctrine Version: 5.0 | Last Updated: 2026-02-27 | System-Wide Integration Edition*

---

## SYSTEM-WIDE INTEGRATION (v5.0)

### Overview
OpenClaw integration expanded from GASKET-only (v2.0-v4.0) to full system-wide
coverage across all 5 departments, 47+ Inner Council agents, 27 managed repos,
and every core subsystem. Coordinated by `openclaw_system_bridge.py`.

### Department Integration Matrix

| Department | Skills | Use Cases | Authority |
|---|---|---|---|
| Executive Council | exec-council-brief, exec-multi-agent, exec-strategic-tasks | 1,3,4,5,17 | AZ_FINAL |
| Intelligence Operations | intel-youtube-digest, intel-research-rag, intel-news-digest, intel-market-research | 2,6,8,16,24,30 | HIGH |
| Operations Command | ops-self-heal, ops-dashboard, ops-morning-brief, ops-task-sync | 3,7,9,11,15 | STANDARD |
| Technology Infrastructure | tech-project-state, tech-n8n-proxy, tech-auto-build, tech-knowledge-base | 10,13,14,18,19,25 | STANDARD |
| Financial Operations | fin-earnings-tracker, fin-market-research, fin-portfolio-crm | 8,17,23,24 | STANDARD |

### Subsystem Integration

| Subsystem | OpenClaw Role | Bridge Method |
|---|---|---|
| REPO DEPOT | Real-time repo health → dashboard, project-state skills | `_check_repo_depot()` |
| Memory Doctrine | 3-layer memory feeds knowledge-base skill, health in self-heal | `_check_memory_health()` |
| Matrix Monitor | Agent performance metrics → dashboard, morning brief | HTTP API polling |
| NCC | Command routing through OpenClaw sessions | `_route_ncc_command()` |
| NCL / Second Brain | Semantic search via knowledge-base skill, ingest via chat | `_ncl_ingest()` |
| QForge | Build pipeline integration with auto-build skill | QForge executor API |
| QUSAR | Query optimization data → dashboard | QUSAR orchestrator |
| Conductor | Workflow orchestration via n8n-proxy skill | Conductor integration |
| Flywheel | 14 agents, 9 roles status → operations dashboard | status.json polling |

### Inner Council Integration
47+ persona agents can be spawned as OpenClaw sessions for multi-agent
analysis. Use case #1 (Multi-Agent Team) maps directly:

- **Financial Analysis**: Warren Buffett + Jamie Dimon + Ryan Cohen sessions
- **Tech Strategy**: Elon Musk + Jensen Huang + Sam Altman sessions
- **Content/Media**: Joe Rogan + Lex Fridman + Andrew Huberman sessions
- **Investment**: All financial personas for portfolio review

Spawning: `POST /api/sessions` with persona system prompt loaded from
`inner_council/[persona].py`.

### Portfolio Integration
6 portfolio agents provide data to Financial Ops skills:

| Agent | OpenClaw Feed |
|---|---|
| portfolio_autodiscover | New companies → fin-portfolio-crm auto-create |
| portfolio_autotier | Tier assignments → CRM priority scoring |
| portfolio_intel | Analysis data → fin-market-research context |
| portfolio_maintainer | Health checks → fin-portfolio-crm alerts |
| portfolio_selfheal | Recovery actions → ops-self-heal escalation |
| parallel_portfolio_intel | Parallel analysis → fin-earnings-tracker batch |

### Cross-Department Workflows

**Workflow 1: Morning Intelligence Pipeline**
```
6:00 AM → ops-morning-brief aggregates overnight data
  → exec-council-brief adds strategic layer
  → intel-news-digest provides top stories
  → fin-earnings-tracker adds market data
  → Unified brief delivered to CEO via OpenClaw chat
```

**Workflow 2: Self-Healing Cascade**
```
ops-self-heal detects failure
  → Attempts auto-remediation (3 retries)
  → If unresolved → GASKET alert
  → GASKET → OPTIMUS escalation
  → OPTIMUS → AZ Prime decision
  → AZ → CEO notification (if critical)
  → All logged to Memory Doctrine persistent layer
```

**Workflow 3: Research-to-Action Pipeline**
```
intel-news-digest detects emerging trend
  → intel-market-research performs 30-day deep dive
  → Inner Council analysis (relevant persona agents)
  → fin-market-research validates opportunity
  → exec-strategic-tasks generates action items
  → ops-task-sync pushes to Todoist
  → CEO reviews on phone
```

### Deployment Architecture
```
OpenClaw Gateway (port 18789)
  ├── GASKET Bridge (14 skills) ← existing, GASKET-specific
  ├── System Bridge (18 skills) ← NEW, department-wide
  │     ├── Executive Council (3 skills)
  │     ├── Intelligence Ops (4 skills)
  │     ├── Operations Command (4 skills)
  │     ├── Technology Infra (4 skills)
  │     └── Financial Ops (3 skills)
  └── Direct Skills (ClawHub installs)
        ├── youtube-full, reddit-readonly, bird
        ├── knowledge-base, memsearch
        ├── tech-news-digest, last-30-days
        ├── todoist, gmail-oauth, ical
        └── SuperCall / ClawdTalk (voice)
```

### Security Boundaries
- Executive Council skills: AZ_FINAL authority required
- Department skills: Department authority level enforced
- Cross-department routing: Authority check before forwarding
- Inner Council sessions: Isolated per persona, no cross-contamination
- Portfolio data: Read-only from OpenClaw, write requires agent authority
- All actions logged to Memory Doctrine persistent layer

### Implementation Files
| File | Purpose |
|---|---|
| `agents/openclaw_system_bridge.py` | System-wide department routing bridge |
| `agents/gasket_openclaw_bridge.py` | GASKET-specific bridge (14 skills) |
| `agents/openclaw_integration.py` | OpenClaw installation discovery + AutoGen agent |
| `OPENCLAW_INTEGRATION_MAP.md` | Master mapping document (all 30 use cases × departments) |
| `skills/executive-council/*` | 3 Executive Council skill definitions |
| `skills/intelligence-ops/*` | 4 Intelligence Ops skill definitions |
| `skills/operations-command/*` | 4 Operations Command skill definitions |
| `skills/technology-infra/*` | 4 Technology Infrastructure skill definitions |
| `skills/financial-ops/*` | 3 Financial Operations skill definitions |
| `skills/gasket/*` | 14 GASKET-specific skill definitions |
| `doctrine/OPENCLAW_DOCTRINE.md` | This file (v5.0) |
