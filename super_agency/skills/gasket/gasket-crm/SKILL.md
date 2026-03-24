# gasket-crm

## Personal CRM with Auto-Contact Discovery

**Type**: always-on + cron
**Trigger**: cron (daily 6 AM scan + 7 AM meeting prep)
**Model**: any

## Description

Automatically discovers and tracks professional contacts from email and calendar interactions. Maintains a relationship database with interaction history, last contact dates, and notes. Generates meeting prep briefings before external meetings.

## Daily Pipeline

### 6:00 AM — Contact Discovery Scan
1. Scan last 24 hours of email (sent + received)
2. Scan today's + tomorrow's calendar events
3. Extract contact info (name, email, company, role)
4. New contacts → add to CRM database
5. Existing contacts → update last_contact, increment interaction count

### 7:00 AM — Meeting Prep Briefings
1. Query today's calendar for external meetings
2. For each external attendee:
   - Pull CRM record (first seen, interaction count, notes)
   - Search recent email threads for context
   - Check if any pending action items
3. Deliver briefing via Telegram/Discord

## Database Schema (SQLite)

```sql
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    company TEXT,
    role TEXT,
    first_seen DATE,
    last_contact DATE,
    interaction_count INTEGER DEFAULT 0,
    notes TEXT,
    tags TEXT,  -- comma-separated
    follow_up_date DATE
);

CREATE TABLE interactions (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id),
    timestamp DATETIME,
    type TEXT,  -- email, meeting, call
    summary TEXT,
    sentiment TEXT  -- positive, neutral, needs-attention
);
```

## Natural Language Queries

- "What do I know about [person]?"
- "Who needs follow-up this week?"
- "When did I last talk to [person]?"
- "Who have I met from [company]?"
- "Show contacts I haven't reached out to in 30+ days"

## Integration with GASKET

```python
async def daily_crm_scan(self):
    """Run daily contact discovery and meeting prep."""
    # Scan emails via gog CLI
    new_contacts = await self._scan_emails_for_contacts()
    # Update CRM database
    for contact in new_contacts:
        await self._upsert_contact(contact)
    # Generate meeting prep
    meetings = await self._get_today_meetings()
    for meeting in meetings:
        briefing = await self._generate_meeting_prep(meeting)
        await self._deliver_briefing(briefing)
```

## Skills Required

- `gog` CLI — Gmail + Google Calendar access
- `imessage` — optional, for iMessage contact tracking on macOS

## Super-Agency Specific

- Tracks contacts across all Super-Agency business interactions
- Meeting prep integrates with morning brief
- Follow-up reminders posted to Telegram
- Contact relationship graph for networking insights
