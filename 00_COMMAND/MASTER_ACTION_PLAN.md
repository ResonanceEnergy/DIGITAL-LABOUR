# BIT RAGE LABOUR — MASTER ACTION PLAN
## 5-Domain Parallel Audit | Generated: 2026-03-16
## Status: $0 REAL REVENUE → Target: $5K/mo in 30 days

---

## SYSTEM STATUS (Live Audit)

| Metric | Value | Verdict |
|--------|-------|---------|
| Real Clients | 0 (1 internal only) | RED |
| Revenue | $60 Stripe TEST MODE (fake) | RED |
| Emails Sent | 74 / 77 prospects | YELLOW |
| Conversions | 0 | RED |
| Autobidder Bids | 0 | RED |
| Fiverr Orders | 0 | RED |
| Upwork Contracts | 0 | RED |
| NERVE Cycles | 22, GREEN | GREEN |
| Task Queue | 86 tasks queued | YELLOW |
| C-Suite | Built, not running | RED |
| KPI Database | Schema broken | RED |

**Bottom line**: Infrastructure is 85% built but 0% earning. Every piece exists — nothing is connected to real money.

---

## THE 5 DOMAINS

| # | Domain | Subagent | Files Audited | Tasks | Critical |
|---|--------|----------|---------------|-------|----------|
| 1 | Revenue & Sales | Revenue Agent | 22 files | 12 | 3 |
| 2 | Platform & Freelance | Platform Agent | 18 files | 15 | 4 |
| 3 | Ops & Automation | Ops Agent | 20 files | 32 | 10 |
| 4 | Content & Marketing | Content Agent | 25 files | 19 | 5 |
| 5 | C-Suite & Intelligence | Intel Agent | 20 files | 20 | 3 |

**Total: 98 tasks identified. 25 CRITICAL.**

---

# UNIFIED CRITICAL PATH (Do THIS WEEK)

These 15 tasks unblock ALL revenue. Everything else is optimization.

## DAY 1 — FOUNDATION

### 1. Fix KPI Logger Schema
- **Domain**: C-Suite
- **Action**: Delete corrupt `data/kpi.db`, run `kpi/logger.py` to recreate with proper `events` table
- **Why**: Every executive, every metric, every report depends on KPI working
- **Time**: 30 min

### 2. Start C-Suite Scheduler Daemon
- **Domain**: C-Suite
- **Action**: Launch `c_suite/scheduler.py --daemon --interval 30`
- **Why**: Board meetings, standups, cash checks all need the scheduler running
- **Time**: 30 min

### 3. Add .env Validation on Startup
- **Domain**: Ops
- **Action**: Add `check_env_keys()` to `launch.py` — validate MATRIX_AUTH_TOKEN, SMTP_HOST, STRIPE keys, LLM keys exist before any daemon starts
- **Why**: Daemons silently fail on missing config. Loud failures save hours of debugging
- **Time**: 1 hr

### 4. Complete self_check.py Stub Functions
- **Domain**: Ops
- **Action**: Implement `_check_pipeline()`, `_check_outreach()`, `_check_csuite()`, `_check_financials()`, `heal_issues()` in `automation/self_check.py`
- **Why**: NERVE Phase 2 (self-healing) calls these — currently they're empty stubs
- **Time**: 2 hrs

## DAY 2 — PLATFORM ACTIVATION

### 5. Create Platform Accounts (Upwork/Fiverr/Freelancer)
- **Domain**: Platform
- **Action**: Register seller accounts on all 3 platforms. Add credentials to `.env`
- **Why**: Can't bid, can't sell, can't earn without accounts
- **Time**: 2 hrs (manual)

### 6. Publish 4 Fiverr Gigs (Quick Start)
- **Domain**: Platform + Content
- **Action**: Create 4 gigs from `listings/fiverr_upwork_ready.md`:
  1. AI Lead Research + Cold Email Outreach ($12/$80/$400)
  2. Support Ticket Triage + AI Responses ($10/$50/$200)
  3. Content Repurposer — Blog to Social ($10/$75/$200)
  4. Invoice & Contract Data Extraction ($5/$40/$150)
- **Why**: Fiverr has buyers searching NOW. Fastest path to first sale
- **Time**: 3 hrs (manual)

### 7. Publish Upwork Profile + First 10 Bids
- **Domain**: Platform
- **Action**: Create profile using copy from `campaign/upwork_deploy.py`, apply to 10 matching jobs
- **Why**: Upwork has higher-value contracts ($500-4000/project)
- **Time**: 4 hrs (manual)

## DAY 3 — OUTREACH ACTIVATION

### 8. Build X/Twitter Daily Posting Automation
- **Domain**: Content
- **Action**: Create `automation/x_poster.py` — uses X API + X_BEARER_TOKEN from .env, posts 1 tweet/day from `campaign/SOCIAL_CONTENT.md` (30 pre-written tweets ready)
- **Why**: Zero organic visibility currently. Daily posting compounds fast
- **Time**: 4 hrs

### 9. Fix Email Response Tracking + Follow-Up Loop
- **Domain**: Revenue
- **Action**: Create `automation/email_tracker.py` + `automation/followup_scheduler.py`. 74 emails sent with zero follow-up tracking
- **Why**: 74 emails in the void. Need to know who replied and auto-follow-up
- **Time**: 2 hrs

### 10. Post LinkedIn Content (Days 1-7)
- **Domain**: Content
- **Action**: Copy posts 1-7 from `campaign/SOCIAL_CONTENT.md` into LinkedIn, 1 post/day. Or build `automation/linkedin_poster.py`
- **Why**: Pre-written content sitting unused. LinkedIn reaches decision-makers
- **Time**: 2 hrs

## DAY 4-5 — AUTOMATION ENGINE

### 11. Activate Job Polling Daemons
- **Domain**: Platform
- **Action**: Schedule `automation/upwork_jobhunt.py` + `automation/freelancer_jobhunt.py` every 2 hours. Verify `data/upwork_jobs/job_log.jsonl` populates
- **Why**: Can't bid on jobs we don't know exist
- **Time**: 2 hrs

### 12. Activate Autobidder Daemon
- **Domain**: Platform + Revenue
- **Action**: Start `automation/autobidder.py` with $50/day budget. Test with `--dry-run` first, then live
- **Why**: Manual bidding doesn't scale. Autobidder = 24/7 sales machine
- **Time**: 1 hr

### 13. Score & Prioritize Prospect List
- **Domain**: Revenue
- **Action**: Create `automation/lead_scorer.py` — score 77 prospects by ICP fit (0-50) + buying signals (0-30) + timing (0-20). Add `lead_score` column to `prospects.csv`
- **Why**: Stop spraying 77 prospects equally. Focus on top 15 "hot" ones
- **Time**: 2 hrs

### 14. Switch Stripe to LIVE Mode
- **Domain**: Revenue
- **Action**: Replace `sk_test_` with `sk_live_` in `.env`. Run `billing/payment_links.py` to regenerate live links. Test checkout flow
- **Why**: $60 in test charges = $0 real income. Can't collect real money until live
- **Time**: 30 min

### 15. Implement Email-to-Task Router
- **Domain**: Ops
- **Action**: Add `route_email_to_agent()` to `automation/inbox_reader.py` — classify inbound emails → if lead/demo request → create task in dispatcher
- **Why**: When outreach generates replies, they need to become actionable tasks automatically
- **Time**: 2 hrs

---

# DOMAIN 1: REVENUE & SALES (12 Tasks)

## Phase 1: Quick Wins (Days 1-14) → $500

| # | Priority | Task | Action | Revenue Impact |
|---|----------|------|--------|----------------|
| R1 | CRITICAL | Post Fiverr Gigs | 4 gigs from `listings/fiverr_upwork_ready.md` | $500-2K/mo |
| R2 | CRITICAL | Upwork Job Applications | Create `automation/upwork_apply.py`, 10 jobs/day | $1-4K/mo |
| R3 | CRITICAL | Fix Email Response Tracking | Create `email_tracker.py` + `followup_scheduler.py` | Convert 20% of 74 sent |
| R4 | HIGH | Score Prospect List | Create `lead_scorer.py`, add scores to CSV | Focus on top 20% |
| R5 | HIGH | Real Autobidder | Replace stub polling in `autobidder.py` | $1-2K/mo |
| R6 | HIGH | Minimal CRM | Create `data/crm.db` + `automation/crm_tracker.py` | Pipeline visibility |
| R7 | HIGH | Response Playbook | Create `campaign/RESPONSE_PLAYBOOK.md` | Faster close rates |

## Phase 2: Scale (Days 15-28) → $2K

| R8 | MEDIUM | LinkedIn DM Outreach | Create `automation/linkedin_dm_bot.py`, 10 DMs/day | $1.6-6K/mo |
| R9 | MEDIUM | Stripe LIVE Mode | Switch .env key, regenerate payment links | Real payments |
| R10 | MEDIUM | LinkedIn Income Tracking | Update `income_tracker.json` | Track all channels |

## Phase 3: Enterprise (Days 29+) → $5K+

| R11 | MEDIUM | Retainer Migration | Create `automation/retainer_pitcher.py` | +$750/mo per client |
| R12 | MEDIUM | Referral Program | Create `automation/referral_tracker.py` | +$500-1K/mo |

---

# DOMAIN 2: PLATFORM & FREELANCE (15 Tasks)

## Phase 1: Platform Setup (Days 1-2)

| # | Priority | Task | Action |
|---|----------|------|--------|
| P1 | CRITICAL | Create Platform Accounts | Register on Upwork/Fiverr/Freelancer, add creds to .env |
| P2 | CRITICAL | Publish Fiverr Gigs | 4-20 gigs from `campaign/fiverr_deploy.py` |
| P3 | CRITICAL | Fiverr Copy Document | Create `campaign/FIVERR_GIGS_FINAL_COPY.md` |
| P4 | CRITICAL | Upwork + Freelancer Listings | Publish 20 services each from deploy scripts |

## Phase 2: Job Polling (Days 3-4)

| P5 | HIGH | .env Platform Credentials | Add tokens, browser settings, budget caps |
| P6 | HIGH | Activate Upwork Job Polling | Schedule `upwork_jobhunt.py` every 2 hrs |
| P7 | HIGH | Activate Freelancer Job Polling | Schedule `freelancer_jobhunt.py` every 2 hrs |
| P8 | HIGH | Activate Autobidder | Start daemon, $50/day budget, 30-min scan interval |

## Phase 3: Delivery (Days 8-14)

| P9 | MEDIUM | Order Router | Create `delivery/order_router.py` — route won contracts to agents |
| P10 | MEDIUM | Upwork Payment Polling | Create `automation/payment_poller.py` |
| P11 | MEDIUM | Fiverr Payment Polling | Create `automation/fiverr_payment_poller.py` |

## Phase 4: Optimization (Week 2+)

| P12 | HIGH | A/B Test Bid Templates | Create bid variants, track win rates |
| P13 | HIGH | Kill Losers / Double Winners | Prune bottom 3 gigs, scale top 3 |
| P14 | MEDIUM | Cross-Sell Bundling | Create `delivery/bundle_routers.py` |
| P15 | LOW | Revenue Dashboard | Platform-specific revenue tracking |

---

# DOMAIN 3: OPS & AUTOMATION (32 Tasks)

## Critical (Days 1-2)

| # | Priority | Task | Action |
|---|----------|------|--------|
| O1 | CRITICAL | Complete `_check_pipeline()` | Implement in `self_check.py` — check stuck tasks |
| O2 | CRITICAL | Complete `_check_outreach()` | Check FAIL leads, prospect queue depth |
| O3 | CRITICAL | Complete `_check_csuite()` | Check BoardRoom health, last standup age |
| O4 | CRITICAL | Complete `_check_financials()` | Check billing.db, query revenue/costs/margin |
| O5 | CRITICAL | Implement `heal_issues()` | Auto-heal simple issues, escalate complex |
| O6 | CRITICAL | .env validation on startup | `launch.py` → validate all required keys |
| O7 | CRITICAL | Audit NERVE Phase 3+ | Verify Phases 3/4/5 are fully implemented |
| O8 | CRITICAL | Audit orchestrator services | Verify all 4 daemons registered correctly |
| O9 | CRITICAL | Email→task router | `inbox_reader.py` → classify + dispatch emails |
| O10 | CRITICAL | Graceful shutdown handlers | SIGTERM/SIGINT on all daemons |

## High (Days 2-3)

| O11 | HIGH | Fix daemon PID cleanup | Remove stale PIDs in `launch.py` |
| O12 | HIGH | Unified state manager | Create `automation/state_manager.py` |
| O13 | HIGH | Consolidate state files | Refactor all state reads through StateManager |
| O14 | HIGH | Watchdog crash detection | Set status to "crashed" when NERVE dies |
| O15 | HIGH | Error recovery circuit breaker | Exponential backoff per NERVE phase |
| O16 | HIGH | Service startup orchestrator | Ordered startup with health checks |
| O17 | HIGH | Unified health endpoint | `GET /status` single source of truth |
| O18 | HIGH | SIGTERM handler for NERVE | Flush logs, save state, clean exit |
| O19 | HIGH | Audit revenue_daemon.py | Verify Stripe polling + income updates |
| O20 | HIGH | Verify Matrix C2 execution | Trace all command paths end-to-end |

## Medium (Week 2)

| O21-O30 | MEDIUM | Structured logging, decision API, metrics export, IMAP retry, task processor, reprocess loop, orchestrator fix, scheduler health, prospect replenishment, daemon runbook |

## Low (Week 3)

| O31 | LOW | WebSocket dashboard updates |
| O32 | LOW | Docker multi-stage build |

---

# DOMAIN 4: CONTENT & MARKETING (19 Tasks)

## Critical (This Week)

| # | Priority | Task | Action |
|---|----------|------|--------|
| C1 | CRITICAL | Publish Fiverr Gigs | 4-20 gigs, copy from `listings/fiverr_upwork_ready.md` |
| C2 | CRITICAL | X/Twitter Daily Posting | Create `automation/x_poster.py`, 1 post/day from SOCIAL_CONTENT.md |
| C3 | CRITICAL | Cold Email Campaign #1 | Create `automation/cold_email_spray.py`, 50 SaaS founders |
| C4 | CRITICAL | LinkedIn Daily Posts | Posts 1-7 from `SOCIAL_CONTENT.md`, 1/day |
| C5 | CRITICAL | Upwork Profile + 10 Bids | Profile from `upwork_deploy.py`, apply to 10 jobs |

## High (Weeks 2-3)

| C6 | HIGH | SEO Blog Post #1 | Run `agents.seo_content.runner`, publish to `site/blog/` |
| C7 | HIGH | Lead Magnet Setup | Create `api/lead_magnet.py` — free demo task + email capture |
| C8 | HIGH | Cold Email Follow-ups | Day 3 + Day 7 follow-ups from `COLD_EMAIL_SEQUENCES.md` |
| C9 | HIGH | Reddit Launch (5 posts) | r/SaaS, r/sales, r/entrepreneur, r/freelance, r/smallbusiness |
| C10 | HIGH | Fiverr Optimization | Promoted Ads $5-10/day, review requests |

## Medium (Weeks 3-4)

| C11 | MEDIUM | LinkedIn DM Outreach | 10-20 prospects/week from `dm_templates.md` |
| C12 | MEDIUM | Press Release | Generate via `agents.press_release`, distribute to PRWeb |
| C13 | MEDIUM | Case Study Blog | First customer results → blog + LinkedIn + Twitter |
| C14 | MEDIUM | Analytics Dashboard | Create `data/lead_tracking.csv` + per-channel tracking |
| C15 | MEDIUM | Product Hunt Launch | Prep assets, schedule launch |

## Low (Month 2)

| C16-C19 | LOW | Upwork/Freelancer listing optimization, email newsletter, YouTube channel, LinkedIn newsletter |

---

# DOMAIN 5: C-SUITE & INTELLIGENCE (20 Tasks)

## Critical (Days 1-3)

| # | Priority | Task | Action |
|---|----------|------|--------|
| I1 | CRITICAL | Fix KPI Logger Schema | Recreate `data/kpi.db` with proper `events` table |
| I2 | CRITICAL | Start Scheduler Daemon | Launch `c_suite/scheduler.py --daemon --interval 30` |
| I3 | CRITICAL | Verify E2E Data Flow | Run AXIOM/VECTIS/LEDGR manually, verify real data |

## High (Week 1-2)

| I4 | HIGH | Build Execution Dispatcher | Create `dispatcher/board_dispatcher.py` — execute board directives |
| I5 | HIGH | AXIOM Market Research | Integrate `agents.market_research` into AXIOM sitrep |
| I6 | HIGH | QA Manager → KPI | `qa_manager` reads KPI data, produces agent health scores |
| I7 | HIGH | Executive Dashboard Fix | Verify `exec_dashboard.py` displays all verdicts |
| I8 | HIGH | Production Manager → VECTIS | VECTIS includes capacity utilization |
| I9 | HIGH | Automation Manager → VECTIS | VECTIS includes platform bidding health |
| I10 | HIGH | Board → Executor Loop | Create `automation/board_executor.py` |
| I11 | HIGH | C-Suite Operations Runbook | Create `docs/C_SUITE_OPERATIONS.md` |

## Medium (Week 2-4)

| I12 | MEDIUM | Context Manager Enrichment | Enrich tasks with client context before agent execution |
| I13 | MEDIUM | Market-Driven Pricing | LEDGR recommends pricing based on market conditions |
| I14 | MEDIUM | KPI Dashboard Webapp | `api/kpi_dashboard.py` + Chart.js frontend |
| I15 | MEDIUM | Auto-Scaling Recommendations | VECTIS recommends agent scaling based on queue depth |
| I16 | MEDIUM | Monthly Strategic Review | Deep-dive board meeting on 1st of each month |
| I17 | MEDIUM | Revenue Attribution | Track which board decisions drove which revenue |
| I18 | MEDIUM | Pricing Automation | LEDGR price changes auto-execute (with safety threshold) |
| I19 | MEDIUM | Baseline KPI Metrics | Define success metrics, capture baseline |
| I20 | MEDIUM | C-Suite Health Check Script | `scripts/csuite_health_check.py` — 1-min diagnostic |

---

# 7-DAY EXECUTION CALENDAR

## Day 1 (Today) — Foundation
- [ ] I1: Fix KPI logger schema
- [ ] I2: Start C-Suite scheduler
- [ ] O6: Add .env validation
- [ ] O1-O5: Complete self_check stubs

## Day 2 — Platform Launch
- [ ] P1: Create platform accounts (manual)
- [ ] P2/C1: Publish 4 Fiverr gigs (manual)
- [ ] P4/C5: Upwork profile + 10 bids (manual)
- [ ] R9: Switch Stripe to LIVE mode

## Day 3 — Outreach Ignition
- [ ] C2: Build X/Twitter poster automation
- [ ] C4: Post LinkedIn content (days 1-3)
- [ ] R3: Fix email response tracking
- [ ] O9: Implement email→task router

## Day 4 — Automation Activation
- [ ] P6: Activate Upwork job polling
- [ ] P7: Activate Freelancer job polling
- [ ] P8: Activate autobidder ($50/day)
- [ ] O10: Add graceful shutdown handlers

## Day 5 — Intelligence
- [ ] R4: Score & prioritize prospects
- [ ] I3: Verify C-Suite E2E data flow
- [ ] I4: Build execution dispatcher
- [ ] C3: Cold email campaign #1 (50 founders)

## Day 6 — Content & Scale
- [ ] C6: Publish SEO blog post #1
- [ ] C9: Reddit launch (5 posts)
- [ ] R6: Build minimal CRM
- [ ] I5: AXIOM market research integration

## Day 7 — Review & Optimize
- [ ] Review all metrics: bids placed, emails sent, posts published, responses received
- [ ] R7: Create response playbook
- [ ] I11: Write C-Suite operations runbook
- [ ] I19: Capture baseline KPI metrics
- [ ] Commit "Week 1 Complete" checkpoint

---

# SUCCESS METRICS (30-Day Targets)

| Metric | Now | Day 7 | Day 14 | Day 30 |
|--------|-----|-------|--------|--------|
| Fiverr Gigs Live | 0 | 4 | 20 | 20 |
| Upwork Bids Sent | 0 | 10 | 70 | 200 |
| Autobidder Bids | 0 | 20 | 100 | 400 |
| Emails Sent | 74 | 124 | 250 | 500 |
| X/Twitter Posts | 0 | 5 | 12 | 30 |
| LinkedIn Posts | 0 | 7 | 14 | 30 |
| Real Clients | 0 | 1-2 | 3-5 | 8-12 |
| Real Revenue | $0 | $50-200 | $500-1.5K | $3-5K |
| NERVE Status | GREEN | GREEN | GREEN | GREEN |
| C-Suite Running | NO | YES | YES | YES |
| KPI Tracking | BROKEN | WORKING | OPTIMIZED | AUTOMATED |
| Board Meetings | 0 | 5 | 14 | 30 |

---

# FILE MANIFEST (New Files to Create)

```
automation/x_poster.py          — X/Twitter daily posting
automation/email_tracker.py     — Track email responses
automation/followup_scheduler.py — Auto follow-up sequences
automation/lead_scorer.py       — Score prospects by ICP fit
automation/crm_tracker.py       — Minimal CRM
automation/cold_email_spray.py  — Batch cold email sender
automation/linkedin_dm_bot.py   — LinkedIn DM automation
automation/retainer_pitcher.py  — Convert buyers to retainers
automation/referral_tracker.py  — Referral program tracking
automation/upwork_apply.py      — Upwork job application bot
automation/state_manager.py     — Unified state management
automation/board_executor.py    — Execute board directives
automation/fiverr_publish.py    — Selenium Fiverr gig publishing
automation/payment_poller.py    — Platform payment monitoring
delivery/order_router.py        — Route won contracts to agents
delivery/bundle_routers.py      — Cross-sell bundle routing
dispatcher/board_dispatcher.py  — Board directive dispatcher
api/lead_magnet.py             — Free demo lead capture
api/kpi_dashboard.py           — KPI web dashboard
billing/price_updater.py       — Automated pricing changes
scripts/csuite_health_check.py — C-Suite diagnostic
campaign/FIVERR_GIGS_FINAL_COPY.md — Copy-paste ready gig text
campaign/RESPONSE_PLAYBOOK.md  — Sales response templates
docs/C_SUITE_OPERATIONS.md    — C-Suite runbook
00_COMMAND/DAEMON_RUNBOOK.md   — Daemon lifecycle runbook
```

---

*Generated by 5 parallel subagents auditing 105+ files across all domains.*
*Next step: Execute Day 1 tasks or tell me which domain to attack first.*
