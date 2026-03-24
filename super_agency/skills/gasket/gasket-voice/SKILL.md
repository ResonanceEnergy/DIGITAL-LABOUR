# gasket-voice

## Phone & Voice Interface (ClawdTalk + SuperCall)

**Type**: on-demand
**Trigger**: incoming phone call or scheduled outbound
**Model**: Claude / GPT-4o (realtime)

## Description

Turns any phone into a gateway to GASKET and Digital-Labour. Two modes: (1) inbound personal assistant via ClawdTalk — call your agent for calendar, tasks, web search; (2) outbound AI calls via SuperCall — automated guest confirmation, appointment reminders, follow-ups.

## Inbound: ClawdTalk (Personal Assistant)

- **Skill**: [ClawdTalk](https://github.com/team-telnyx/clawdtalk-client)
- **Provider**: Telnyx (SIP telephony)
- **Usage**: Call your dedicated number → speak with GASKET
- **Capabilities**: calendar queries, Jira updates, web search, system status, reminders
- **Hands-free**: driving, walking, cooking — full agent access via voice
- **SMS**: future support for text-based interaction via same number

## Outbound: SuperCall (AI Phone Calls)

- **Skill**: `supercall` from ClawHub (xonder)
- **Provider**: Twilio + OpenAI Realtime API + ngrok
- **Key feature**: sandboxed AI persona — NO access to gateway agent, files, or tools
- **Use cases**:
  - Event guest confirmation (attendance, dietary needs, plus-ones)
  - Appointment reminders
  - Customer follow-ups
  - Survey calls
- **Transcripts**: logged to `~/clawd/supercall-logs/`
- **Safety**: AI persona is completely isolated from main agent context

## Security Model

```
┌─────────────────────────────────────────┐
│  Gateway Agent (GASKET)                 │
│  • Full tool access                     │
│  • Memory, files, skills                │
│  • Initiates SuperCall                  │
├─────────────────────────────────────────┤
│  SuperCall Persona (SANDBOXED)          │
│  • Voice-only interaction               │
│  • Script/persona from gateway          │
│  • NO file access                       │
│  • NO tool access                       │
│  • NO memory access                     │
│  • Prompt injection safe                │
└─────────────────────────────────────────┘
```

## Integration with GASKET

```python
async def handle_voice_query(self, transcript: str):
    """Process inbound voice query from ClawdTalk."""
    # Route to appropriate handler
    if 'calendar' in transcript.lower():
        return await self._query_calendar(transcript)
    elif 'status' in transcript.lower():
        return await self.get_system_status()
    elif 'search' in transcript.lower():
        return await self._web_search(transcript)
    else:
        return await self._general_query(transcript)

async def schedule_outbound_call(self, contact: dict, script: str):
    """Schedule an outbound SuperCall with sandboxed persona."""
    persona = self._build_persona(script)
    result = await self._supercall_execute(contact['phone'], persona)
    await self._log_transcript(contact, result)
```

## Requirements

- Telnyx account (ClawdTalk inbound)
- Twilio account + OpenAI Realtime API key (SuperCall outbound)
- ngrok for local webhook tunnel
- macOS or Linux (always-on recommended)

## Digital-Labour Specific

- Inbound: CEO can call GASKET for status updates while mobile
- Outbound: automated client follow-ups, event coordination
- All transcripts stored in memory doctrine for searchability
