# gasket-n8n-proxy

## n8n Workflow Orchestration (Security Proxy Pattern)

**Type**: on-demand + cron
**Trigger**: agent-initiated or scheduled
**Model**: any

## Description

Delegates ALL external API interactions to n8n via webhooks. GASKET never touches third-party credentials directly. Three wins: observability (visual n8n UI for debugging), security (credential isolation — agent can't leak keys), performance (deterministic workflows don't burn LLM tokens on repeat tasks).

## Architecture

```
┌──────────────┐     webhook     ┌──────────────┐     API calls     ┌─────────────┐
│   GASKET     │ ──────────────► │     n8n      │ ────────────────► │  External   │
│  (Agent)     │                 │  (Workflow)  │                   │   APIs      │
│              │ ◄────────────── │              │ ◄──────────────── │             │
│  NO creds    │    response     │  HAS creds   │    data           │  Stripe,    │
│  NO API keys │                 │  Locked flows │                   │  Twilio,    │
└──────────────┘                 └──────────────┘                   │  SendGrid   │
                                                                    └─────────────┘
```

## Workflow Lifecycle

1. **Agent designs** workflow (describes what it needs)
2. **Agent builds** via n8n API (creates nodes, connections)
3. **User adds credentials** manually in n8n UI
4. **User locks workflow** (agent can't modify after locking)
5. **Agent calls** webhook URL to execute

## Key Rules (AGENTS.md)

```markdown
- NEVER store API keys in my environment or skill files
- ALL external API calls go through n8n webhooks
- Credentials are added by humans, not agents
- Locked workflows cannot be modified by agents
- Use n8n's visual UI for debugging complex flows
```

## Docker Stack

```yaml
# openclaw-n8n-stack (github.com/caprihan/openclaw-n8n-stack)
services:
  openclaw:
    image: openclaw/gateway
    ports: ["18789:18789"]
  n8n:
    image: n8nio/n8n
    ports: ["5678:5678"]
    volumes:
      - n8n_data:/home/node/.n8n
```

## Integration with GASKET

```python
async def call_n8n_workflow(self, workflow_name: str, payload: dict):
    """Execute an n8n workflow via webhook."""
    webhook_url = self.n8n_webhooks.get(workflow_name)
    if not webhook_url:
        raise ValueError(f"No webhook registered for {workflow_name}")

    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as resp:
            return await resp.json()

# Example: send email via n8n (agent never sees SendGrid key)
result = await self.call_n8n_workflow('send-email', {
    'to': 'client@example.com',
    'subject': 'Weekly Report',
    'body': report_html
})
```

## n8n Capabilities

- 400+ built-in integrations (Stripe, Twilio, SendGrid, Notion, Airtable, etc.)
- Visual workflow builder for debugging
- Credential vault (encrypted at rest)
- Webhook triggers (sync + async)
- Error handling with retry logic
- Workflow versioning

## Super-Agency Specific

- n8n runs alongside OpenClaw gateway
- All client-facing API interactions proxied through n8n
- GASKET monitors n8n health as part of self-heal checks
- Workflow catalog stored in memory doctrine
