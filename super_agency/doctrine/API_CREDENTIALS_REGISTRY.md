# API CREDENTIALS REGISTRY
## Digital-Labour Master Credential Reference
### Version 1.0 — 2026-02-28

> **SECURITY NOTE**: This document catalogs available API providers and their purposes.
> Actual keys are stored ONLY at `~/\.digitallabour/credentials.json` (chmod 600, NOT git-tracked).
> OpenClaw runtime keys are in `~/.openclaw/openclaw.json` env section (chmod 600).

---

## Active Providers

### AI Model Providers (OpenClaw Gateway)

| Provider | Env Variable | Purpose | Status | Config Location |
|----------|-------------|---------|--------|----------------|
| Anthropic | `ANTHROPIC_API_KEY` | Claude Opus/Sonnet/Haiku models | **ACTIVE** | `~/.openclaw/openclaw.json` env section |
| OpenAI | `OPENAI_API_KEY` | GPT, DALL-E, Whisper models | **ACTIVE** | `~/.openclaw/openclaw.json` env section |
| Google Gemini | `GEMINI_API_KEY` | Gemini AI models | **ACTIVE** | `~/.openclaw/openclaw.json` env section |
| xAI | `XAI_API_KEY` | Grok AI models (primary) | **ACTIVE** | `~/.openclaw/openclaw.json` env section |
| xAI (backup) | `XAI_API_KEY_2` | Grok AI models (secondary) | **STORED** | `~/\.digitallabour/credentials.json` only |

### Messaging Platform Tokens

| Provider | Env Variable | Purpose | Status | Config Location |
|----------|-------------|---------|--------|----------------|
| Telegram | `TELEGRAM_BOT_TOKEN` | @agentgasketbot — GASKET agent | **ACTIVE** | `~/.openclaw/openclaw.json` channels.telegram |
| Discord | `DISCORD_BOT_TOKEN` | Digital-Labour Discord bot | **STORED** | `~/\.digitallabour/credentials.json` only |

### Data/API Services

| Provider | Env Variable | Purpose | Status | Config Location |
|----------|-------------|---------|--------|----------------|
| YouTube API (primary) | `YOUTUBE_API_KEY` | SecondBrain ingest pipeline | **STORED** | `~/\.digitallabour/credentials.json` |
| YouTube API (backup) | `YOUTUBE_API_KEY_2` | Backup YouTube API key | **STORED** | `~/\.digitallabour/credentials.json` |

---

## File Locations

| File | Purpose | Permissions | Git-Tracked |
|------|---------|-------------|-------------|
| `~/\.digitallabour/credentials.json` | Master credentials vault (ALL keys) | 600 | **NO** |
| `~/.openclaw/openclaw.json` | OpenClaw gateway config (AI + Telegram keys) | 600 | **NO** |
| `~/.openclaw/agents/gasket/agent/auth-profiles.json` | GASKET agent auth profiles | 600 | **NO** |
| `~/.openclaw/agents/main/agent/auth-profiles.json` | Main agent auth profiles | 600 | **NO** |

---

## Runtime Architecture

```
┌──────────────────────────────────────────────────────┐
│  OpenClaw Gateway (launchd: ai.openclaw.gateway)     │
│  ├─ Reads: ~/.openclaw/openclaw.json                 │
│  ├─ env.ANTHROPIC_API_KEY → Claude API               │
│  ├─ env.OPENAI_API_KEY → OpenAI API                  │
│  ├─ env.GEMINI_API_KEY → Google Gemini API           │
│  ├─ env.XAI_API_KEY → xAI Grok API                  │
│  └─ channels.telegram.botToken → Telegram Bot API    │
├──────────────────────────────────────────────────────┤
│  GASKET Agent (bound to Telegram channel)             │
│  ├─ Default model: anthropic/claude-opus-4-6         │
│  └─ Workspace: ~/repos/Digital-Labour                  │
├──────────────────────────────────────────────────────┤
│  Watchdog (launchd: com.digitallabour.watchdog)        │
│  └─ Uses TELEGRAM_BOT_TOKEN for alert delivery       │
└──────────────────────────────────────────────────────┘
```

---

## Telegram Configuration

- **Bot**: @agentgasketbot (AGENT GASKET)
- **Bot ID**: 8766824944
- **Owner Telegram ID**: 8253467085
- **DM Policy**: pairing (one-time code approval)
- **Group Policy**: allowlist
- **Pairing**: Approved for owner

---

## Key Rotation Protocol

1. Generate new key at provider dashboard
2. Update `~/\.digitallabour/credentials.json` with new value
3. If AI provider: update `~/.openclaw/openclaw.json` env section
4. Restart gateway: `openclaw gateway stop && openclaw gateway start`
5. Verify: `openclaw models status --agent gasket`
6. Update this document's version number

---

## Created
- **Date**: 2026-02-28
- **By**: GASKET Integration Session
- **Commit Context**: Post auth-fix, all providers verified operational
