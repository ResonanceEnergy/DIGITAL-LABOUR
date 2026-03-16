# SKILL: intel-youtube-digest
## YouTube Intelligence Division Daily Digest

Automated daily digest from YouTube Intelligence Division agents —
Joe Rogan, Lex Fridman, Tom Bilyeu, Jordan Peterson.

### Triggers
- Cron: Daily at 8:00 AM
- Manual: "youtube digest", "what's new on youtube"

### What It Does
1. Each YouTube Intelligence agent monitors its assigned channel
2. Fetches latest videos from past 24-48 hours via youtube-full skill
3. Gets transcripts and generates 2-3 bullet summaries per video
4. Cross-references against 90-day catalog to avoid duplicates
5. Delivers structured digest to intelligence-operations topic

### Channels Monitored
| Agent | Channel | Focus |
|---|---|---|
| Joe Rogan | @joerogan | Cultural intelligence, guest insights |
| Lex Fridman | @lexfridman | AI research, technology trends |
| Tom Bilyeu | @TomBilyeu | Business strategy, mindset |
| Jordan Peterson | @JordanBPeterson | Psychology, philosophy |

### Output Format
```
YOUTUBE INTELLIGENCE DIGEST — [date]

@lexfridman — "Interview with [Guest]"
• Key insight about AI safety and alignment approaches
• Discussion of novel compute paradigm
• Relevant to: QUSAR system, AI research portfolio
Link: https://youtube.com/watch?v=...

@joerogan — "[Episode Title]"
• Cultural trend discussion about [topic]
• Notable guest perspective on [subject]
Link: https://youtube.com/watch?v=...

[No new videos from @TomBilyeu, @JordanBPeterson]
```

### Data Pipeline
1. youtube-full skill fetches channel/latest (free, 0 credits)
2. Only new videos trigger transcript fetch (1 credit each)
3. Transcripts auto-ingested into NCL Second Brain
4. Semantic search enabled via memsearch integration

### Dependencies
- youtube-full skill (clawhub install youtube-full)
- NCL Second Brain (ncl_second_brain/engine/)
- departments/intelligence_operations/youtube_intelligence/ agents
