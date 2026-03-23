"""MASTER INCOME SOURCE REGISTRY — Every revenue channel for DIGITAL LABOUR.

Ranked by ROI, speed-to-first-dollar, and integration effort.

Each source has:
  - name:          Platform/channel name
  - category:      CRYPTO_AGENT | PLATFORM_MARKETPLACE | FREELANCE | DIRECT_SALES |
                   API_MARKETPLACE | ENTERPRISE | AFFILIATE | DEFI
  - integration:   API | SMART_CONTRACT | LISTING | EMAIL | SDK | WEBHOOK
  - effort:        1-5 (1=trivial deploy, 5=heavy build)
  - speed_days:    Estimated days to first revenue
  - monthly_upside: Estimated max monthly revenue at scale (USD)
  - roi_score:     Computed (upside / effort)
  - status:        NOT_STARTED | IN_PROGRESS | LIVE
  - how:           Step-by-step integration procedure
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class IncomeSource:
    name: str
    category: str
    integration: str
    effort: int          # 1-5
    speed_days: int      # days to first $
    monthly_upside: int  # USD ceiling
    roi_score: float = 0.0
    status: str = "NOT_STARTED"
    how: List[str] = field(default_factory=list)
    url: str = ""
    notes: str = ""

    def __post_init__(self):
        self.roi_score = round(self.monthly_upside / max(self.effort, 1) / max(self.speed_days, 1), 1)


# ══════════════════════════════════════════════════════════════════════════════
#  TIER 1 — HIGHEST ROI / FASTEST TO REVENUE
# ══════════════════════════════════════════════════════════════════════════════

TIER_1 = [

    # ── 1. Freelance Platforms (sell agent-building as a service) ─────────
    IncomeSource(
        name="Freelancer.com — AI Agent Jobs",
        category="FREELANCE",
        integration="LISTING",
        effort=1,
        speed_days=3,
        monthly_upside=8000,
        url="https://www.freelancer.com/jobs/ai-agents/",
        notes="21 active AI agent jobs right now. Average bids $54-$6280. "
              "List as agency, bid on agent-building contracts.",
        how=[
            "1. Create Freelancer.com agency profile as 'DIGITAL LABOUR — AI Agent Workforce'",
            "2. List all 4 agents as capabilities (Sales Ops, Support, Content, Doc Extract)",
            "3. Bid on AI agent jobs — focus on $200-$2000 range for fast wins",
            "4. Use existing worker agents to DELIVER the work (auto-fulfillment)",
            "5. Scale: auto-monitor new AI agent job postings, auto-bid via API",
        ],
    ),

    IncomeSource(
        name="Fiverr — AI Services + Programming & Tech",
        category="FREELANCE",
        integration="LISTING",
        effort=1,
        speed_days=5,
        monthly_upside=6000,
        url="https://www.fiverr.com/categories/ai-services",
        notes="Fiverr has dedicated 'AI Services' category. "
              "Sell agent outputs as gigs: email copywriting, doc extraction, content repurposing.",
        how=[
            "1. Create Fiverr seller profile as 'BitRageLabour'",
            "2. Create 4 gigs matching each agent's capability:",
            "   - 'AI Sales Email Generator' ($25-100/batch)",
            "   - 'AI Document Data Extraction' ($15-50/doc)",
            "   - 'AI Content Repurposer — Turn 1 piece into 10' ($30-75)",
            "   - 'AI Customer Support Bot Setup' ($100-500)",
            "3. Use DIGITAL LABOUR agents to auto-fulfill orders",
            "4. Scale with Fiverr Pro application for premium pricing",
        ],
    ),

    # ── 2. Direct Stripe Sales (already configured) ──────────────────────
    IncomeSource(
        name="Direct Stripe Sales — bit-rage-labour.com",
        category="DIRECT_SALES",
        integration="WEBHOOK",
        effort=1,
        speed_days=1,
        monthly_upside=5000,
        url="https://bit-rage-labour.com",
        notes="10 Stripe products ALREADY configured (test mode). "
              "Switch to live mode, enable payment links, embed on website. "
              "Products: sales_outreach $2.40/lead, support_ticket $1/ticket, "
              "content_repurpose $3/piece, doc_extract $1.50/doc, "
              "sales_starter $750/mo retainer.",
        how=[
            "1. Switch Stripe to LIVE mode (flip test→live keys in .env)",
            "2. Create Stripe Payment Links for all 10 products",
            "3. Embed payment links on bit-rage-labour.com landing page",
            "4. Add checkout flow: payment → auto-create client → assign agent",
            "5. Enable Stripe Checkout Sessions for subscription products",
        ],
    ),

    # ── 3. RapidAPI — Sell agents as APIs ────────────────────────────────
    IncomeSource(
        name="RapidAPI Hub — Sell Agent APIs",
        category="API_MARKETPLACE",
        integration="API",
        effort=2,
        speed_days=7,
        monthly_upside=4000,
        url="https://rapidapi.com/hub",
        notes="30M+ devs. Sell each agent as a REST API. "
              "MCP support just launched. Metered billing built-in. "
              "Categories: AI Based APIs, Business Software.",
        how=[
            "1. Sign up as RapidAPI Provider at rapidapi.com",
            "2. Wrap each agent as a FastAPI endpoint (already have api/intake.py)",
            "3. Expose 4 APIs: /sales-email, /doc-extract, /content-repurpose, /support-ticket",
            "4. Configure pricing tiers on RapidAPI (free tier + paid)",
            "5. RapidAPI handles billing, auth, rate limiting, docs",
            "6. Optional: add MCP endpoints for AI-to-AI consumption",
        ],
    ),

    # ── 4. Email Outreach (now enriched with 50 real emails) ─────────────
    IncomeSource(
        name="Email Outreach — 50 Enriched Prospects",
        category="DIRECT_SALES",
        integration="EMAIL",
        effort=1,
        speed_days=7,
        monthly_upside=3000,
        url="",
        notes="50 prospects now have real emails (enriched via email_discovery.py). "
              "sent_log.json is empty/reset. Ready for re-blast. "
              "Zoho SMTP configured: sales@bit-rage-labour.com.",
        how=[
            "1. Run: python -m automation.outreach (sends to all 50 enriched prospects)",
            "2. NERVE daemon monitors responses and triggers followups",
            "3. Followup sequence: Day 3, Day 7, Day 14",
            "4. Scale: use prospect_engine.py to generate 200+ more prospects",
            "5. Feed new prospects through email_discovery.py for enrichment",
        ],
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
#  TIER 2 — CRYPTO AGENT ECONOMY (MEDIUM EFFORT, HIGH CEILING)
# ══════════════════════════════════════════════════════════════════════════════

TIER_2 = [

    # ── 5. Virtuals Protocol / ACP ───────────────────────────────────────
    IncomeSource(
        name="Virtuals Protocol — Agent Commerce Protocol (ACP)",
        category="CRYPTO_AGENT",
        integration="SMART_CONTRACT",
        effort=3,
        speed_days=14,
        monthly_upside=15000,
        url="https://app.virtuals.io/",
        notes="$479.79M total aGDP. $3.3M total agent revenue. "
              "2.02M jobs completed. 20,015 AI projects. "
              "Agent-to-agent commerce via smart contracts. "
              "Top agent Ethy AI: $218M aGDP, 1.14M jobs. "
              "$VIRTUAL token. Butler system for human-agent gateway.",
        how=[
            "1. Register at app.virtuals.io — 'Register Your Agent'",
            "2. Deploy agent wrapper that implements ACP interface",
            "3. Define agent capabilities (sales copy, doc extract, content, support)",
            "4. Set pricing per job in USDC via smart contract",
            "5. Agent receives jobs from other agents automatically",
            "6. Revenue accrues in USDC — withdraw to wallet",
            "7. Optional: tokenize agent for capital markets ($VIRTUAL ecosystem)",
        ],
    ),

    # ── 6. Fetch.ai / Agentverse ─────────────────────────────────────────
    IncomeSource(
        name="Fetch.ai Agentverse — 2.7M Agent Ecosystem",
        category="CRYPTO_AGENT",
        integration="SDK",
        effort=3,
        speed_days=14,
        monthly_upside=8000,
        url="https://agentverse.ai/",
        notes="2.7M agents registered. Monetization via subscriptions + premium tags. "
              "ASI:One handles discovery. Supports LangChain, CrewAI, custom agents. "
              "Performance analytics dashboard included.",
        how=[
            "1. Sign up at agentverse.ai",
            "2. Register agents as 'External Agents' (bring your own code)",
            "3. Configure agent identity with verified metadata",
            "4. Set monetization: subscription tiers or pay-per-use",
            "5. ASI:One indexes agent for discovery by 2.7M agent network",
            "6. Respond to requests via Agentverse webhooks",
            "7. Track performance via analytics dashboard",
        ],
    ),

    # ── 7. Olas Network / Mech Marketplace ───────────────────────────────
    IncomeSource(
        name="Olas Network — Mech Marketplace + Dev Rewards",
        category="CRYPTO_AGENT",
        integration="SDK",
        effort=3,
        speed_days=21,
        monthly_upside=10000,
        url="https://olas.network/build",
        notes="62 total Olas builders. $1M grants program. "
              "Up to $100K in grants per agent. OLAS staking rewards. "
              "Register on Mech Marketplace. Pearl AI Agent App Store. "
              "Self-custody wallets via Safe (account abstraction). "
              "Builder earned $1.2M OLAS in one year.",
        how=[
            "1. Install Olas Stack toolchain (stack.olas.network)",
            "2. Wrap DIGITAL LABOUR agents in Olas SDK",
            "3. Register as Sovereign Agent on Mech Marketplace",
            "4. Apply for Accelerator — up to $100K grant",
            "5. Earn OLAS Dev Rewards for registered agent components",
            "6. Optional: deploy to Pearl (AI Agent App Store) for consumer access",
            "7. Stake OLAS for additional staking rewards",
        ],
    ),

    # ── 8. ElizaOS / Eliza Cloud ─────────────────────────────────────────
    IncomeSource(
        name="ElizaOS — Eliza Cloud + Marketplace",
        category="CRYPTO_AGENT",
        integration="SDK",
        effort=3,
        speed_days=14,
        monthly_upside=6000,
        url="https://docs.elizaos.ai/",
        notes="Most popular agentic framework. 90+ plugins. "
              "Eliza Cloud: 2-command deploy. ERC-8004 on-chain discovery. "
              "X402 crypto payments. Marketplace to publish & monetize. "
              "$elizaOS token ecosystem.",
        how=[
            "1. npm install -g @elizaos/cli",
            "2. Wrap DIGITAL LABOUR agents as ElizaOS plugins",
            "3. elizaos login → elizaos deploy --project-name bit-rage-labour",
            "4. Register on Eliza Cloud marketplace for discoverability",
            "5. Enable X402 crypto payments for agent services",
            "6. On-chain agent discovery via ERC-8004",
        ],
    ),

    # ── 9. SingularityNET / ASI Token ────────────────────────────────────
    IncomeSource(
        name="SingularityNET — AI Marketplace + ASI Token",
        category="CRYPTO_AGENT",
        integration="SDK",
        effort=4,
        speed_days=30,
        monthly_upside=5000,
        url="https://singularitynet.io/ecosystem/",
        notes="12 ecosystem projects. ASI (FET) token. "
              "DEEP Funding grants. Dev resources at dev.singularitynet.io. "
              "List AI services on decentralized marketplace.",
        how=[
            "1. Register at dev.singularitynet.io",
            "2. Package agents as SingularityNET services (gRPC interface)",
            "3. Publish to AI Marketplace with pricing in ASI/AGIX",
            "4. Apply for DEEP Funding (deepfunding.ai) for grants",
            "5. Services discovered by ecosystem of 12+ partner projects",
        ],
    ),

    # ── 10. Morpheus Network ─────────────────────────────────────────────
    IncomeSource(
        name="Morpheus — MOR Token + Builder Rewards",
        category="CRYPTO_AGENT",
        integration="SDK",
        effort=3,
        speed_days=21,
        monthly_upside=4000,
        url="https://mor.org/",
        notes="320K+ staked ETH. 14.2K daily MOR emissions. "
              "6,500+ capital providers. $5.5M+ protocol-owned liquidity. "
              "Earn as Builder (build agents → MOR rewards). "
              "Also can earn as Capital/Code/Compute contributor.",
        how=[
            "1. Register as Morpheus Builder at mor.org",
            "2. Build DIGITAL LABOUR as a Morpheus-compatible agent application",
            "3. Earn MOR tokens based on usage of your agents",
            "4. Optional: provide stETH as Capital contributor for additional MOR",
            "5. Optional: contribute code to Morpheus codebase for Code rewards",
        ],
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
#  TIER 3 — PLATFORM/SAAS (MEDIUM EFFORT, STEADY RECURRING)
# ══════════════════════════════════════════════════════════════════════════════

TIER_3 = [

    # ── 11. Chatbase / Botpress White-Label ──────────────────────────────
    IncomeSource(
        name="Chatbase — White-Label AI Agent Reseller",
        category="PLATFORM_MARKETPLACE",
        integration="API",
        effort=2,
        speed_days=7,
        monthly_upside=5000,
        url="https://www.chatbase.co/",
        notes="10,000+ businesses use Chatbase. White-label available. "
              "Sell preconfigured chatbots to clients. "
              "Endorsed by OpenAI. Integrates Stripe, Zendesk, Salesforce, etc.",
        how=[
            "1. Sign up at chatbase.co (free tier available)",
            "2. Build pre-configured agents for common use cases",
            "3. Resell to clients as white-label bots with markup",
            "4. Chatbase handles hosting, training, analytics",
            "5. Charge clients $200-$1000/mo for 'managed AI support'",
        ],
    ),

    IncomeSource(
        name="Botpress — Managed AI Agent Builder",
        category="PLATFORM_MARKETPLACE",
        integration="API",
        effort=2,
        speed_days=7,
        monthly_upside=4000,
        url="https://botpress.com/",
        notes="Botpress Managed plan: build & maintain agents for clients at $995-$1495/mo. "
              "White-label webchat. PAYG starts at $0. "
              "90+ integrations. Can BYOK (bring your own key).",
        how=[
            "1. Sign up at botpress.com (free PAYG tier)",
            "2. Build agent templates for DIGITAL LABOUR use cases",
            "3. Deploy agents on client behalf via Botpress APIs",
            "4. Charge clients for 'Managed AI Agent' service",
            "5. Botpress handles infra; you handle relationship + customization",
        ],
    ),

    # ── 12. Relevance AI — AI Workforce ──────────────────────────────────
    IncomeSource(
        name="Relevance AI — AI Workforce Platform",
        category="PLATFORM_MARKETPLACE",
        integration="API",
        effort=2,
        speed_days=10,
        monthly_upside=5000,
        url="https://relevanceai.com/",
        notes="Used by Canva, Databricks, Autodesk. "
              "Build AI agents + workforces. Marketplace access included. "
              "2000+ integrations. Schedule tasks, calling & meeting agents. "
              "Free tier: 200 actions/mo, unlimited agents.",
        how=[
            "1. Sign up at app.relevanceai.com (free tier)",
            "2. Build DIGITAL LABOUR agents using Relevance AI tools",
            "3. List on Relevance Marketplace for discovery",
            "4. Offer as managed service to clients via Relevance platform",
            "5. Scale to Team plan ($234/mo) for 84K actions/year",
        ],
    ),

    # ── 13. Zapier Agents ────────────────────────────────────────────────
    IncomeSource(
        name="Zapier Agents — Automation + Lead Gen",
        category="PLATFORM_MARKETPLACE",
        integration="API",
        effort=2,
        speed_days=5,
        monthly_upside=3000,
        url="https://zapier.com/agents",
        notes="2.2M+ companies use Zapier. Agent marketplace with templates. "
              "Customer generated 2000+ leads in one month. "
              "Chrome extension. 7000+ app integrations.",
        how=[
            "1. Build DIGITAL LABOUR Zapier Agent templates",
            "2. Publish to Zapier Agent template gallery",
            "3. Use Zapier Agents for own lead gen (auto-prospect, auto-qualify)",
            "4. Connect Zapier to DIGITAL LABOUR API for auto-fulfillment",
            "5. Earn via template usage + consulting on agent setup",
        ],
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
#  TIER 4 — DEFI / CRYPTO YIELD (PASSIVE INCOME)
# ══════════════════════════════════════════════════════════════════════════════

TIER_4 = [

    # ── 14. Wayfinder DeFi Agents ────────────────────────────────────────
    IncomeSource(
        name="Wayfinder — DeFi AI Agent Platform",
        category="DEFI",
        integration="SDK",
        effort=3,
        speed_days=14,
        monthly_upside=5000,
        url="https://wayfinder.ai/",
        notes="DeFi agent on every blockchain. Multi-model (Claude/GPT/Gemini/Grok). "
              "One-click deploy. Self-custody wallets. $PROMPT token. "
              "Strategies: swaps, lending, bridging, perps.",
        how=[
            "1. Sign up at wayfinder.ai",
            "2. Deploy DIGITAL LABOUR as Wayfinder agent",
            "3. Configure DeFi strategies (yield farming, arb)",
            "4. Self-custody wallet earns from strategy execution",
            "5. $PROMPT token rewards for active agents",
        ],
    ),

    # ── 15. XRP Ledger — NFT + Token Agent Economy ──────────────────────
    IncomeSource(
        name="XRP Ledger — Agent NFTs + Token Payments",
        category="CRYPTO_AGENT",
        integration="SMART_CONTRACT",
        effort=4,
        speed_days=30,
        monthly_upside=3000,
        url="https://xrpl.org/docs/concepts/tokens/nfts",
        notes="XRPL supports NFTokenMint, token payments, trust lines. "
              "Low fees (~$0.00001/tx). Fast settlement (3-5s). "
              "Mint agent capabilities as NFTs. Accept XRP payments.",
        how=[
            "1. Set up XRPL wallet (xrpl-py library)",
            "2. Mint agent capability NFTs (one per worker agent type)",
            "3. Create XRP payment channel for agent service fees",
            "4. Build XRPL payment gateway in api/intake.py",
            "5. Accept XRP alongside Stripe for global crypto payments",
        ],
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
#  TIER 5 — ENTERPRISE B2B (SLOWER BUT BIGGEST DEALS)
# ══════════════════════════════════════════════════════════════════════════════

TIER_5 = [

    # ── 16. Upwork / Premium Freelance ───────────────────────────────────
    IncomeSource(
        name="Upwork — AI Agent Services (Premium)",
        category="FREELANCE",
        integration="LISTING",
        effort=2,
        speed_days=14,
        monthly_upside=10000,
        url="https://www.upwork.com/",
        notes="$3.8B marketplace. Premium clients. Expert-verified accounts. "
              "AI automation is top-trending category. "
              "Higher ticket: $50-200/hr for AI agent development.",
        how=[
            "1. Create Upwork Expert profile — 'AI Agent Workforce Builder'",
            "2. Complete profile verification + skills tests",
            "3. Apply for AI/ML specialized categories",
            "4. Bid on enterprise AI agent projects ($5K-$50K)",
            "5. Deliver using DIGITAL LABOUR's agent infrastructure",
        ],
    ),

    # ── 17. Consulting / Retainers ───────────────────────────────────────
    IncomeSource(
        name="Direct Consulting — AI Agent Setup Retainers",
        category="ENTERPRISE",
        integration="EMAIL",
        effort=2,
        speed_days=30,
        monthly_upside=15000,
        url="",
        notes="Sell 'AI Agent Workforce' setup as consulting. "
              "$2K-$10K/client for setup + $500-$2K/mo retainer. "
              "Use existing DIGITAL LABOUR infrastructure to deliver.",
        how=[
            "1. Create consulting offer deck (ai-workforce-setup.pdf)",
            "2. Price: $2K setup fee + $750/mo managed service",
            "3. Use email outreach to pitch to enriched prospects",
            "4. Client gets white-label DIGITAL LABOUR agents",
            "5. Recurring revenue from monthly management retainer",
        ],
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
#  COMBINED REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

ALL_SOURCES = TIER_1 + TIER_2 + TIER_3 + TIER_4 + TIER_5


def get_ranked_sources():
    """Return all sources ranked by ROI score (highest first)."""
    return sorted(ALL_SOURCES, key=lambda s: s.roi_score, reverse=True)


def get_by_category(category: str):
    """Return sources filtered by category."""
    return [s for s in ALL_SOURCES if s.category == category]


def get_actionable_now():
    """Return sources with effort <= 2 and speed_days <= 7 — can start earning THIS WEEK."""
    return [s for s in ALL_SOURCES if s.effort <= 2 and s.speed_days <= 7]


def print_roadmap():
    """Print the full ranked roadmap."""
    ranked = get_ranked_sources()
    print("\n" + "=" * 80)
    print("  DIGITAL LABOUR — MASTER INCOME ROADMAP (Ranked by ROI Score)")
    print("=" * 80)

    for i, src in enumerate(ranked, 1):
        print(f"\n{'─' * 70}")
        print(f"  #{i}  {src.name}")
        print(f"  Category: {src.category} | Integration: {src.integration}")
        print(f"  Effort: {'★' * src.effort}{'☆' * (5 - src.effort)} ({src.effort}/5)")
        print(f"  Speed to $: {src.speed_days} days | Monthly Upside: ${src.monthly_upside:,}")
        print(f"  ROI Score: {src.roi_score} | Status: {src.status}")
        if src.url:
            print(f"  URL: {src.url}")
        print(f"\n  Steps:")
        for step in src.how:
            print(f"    {step}")

    # Summary
    total_upside = sum(s.monthly_upside for s in ALL_SOURCES)
    quick_wins = get_actionable_now()
    quick_upside = sum(s.monthly_upside for s in quick_wins)

    print(f"\n{'=' * 80}")
    print(f"  TOTAL SOURCES: {len(ALL_SOURCES)}")
    print(f"  MAX MONTHLY UPSIDE (all sources): ${total_upside:,}")
    print(f"  QUICK WINS (this week): {len(quick_wins)} sources → ${quick_upside:,}/mo potential")
    print(f"  LIVE: {sum(1 for s in ALL_SOURCES if s.status == 'LIVE')}")
    print(f"  IN PROGRESS: {sum(1 for s in ALL_SOURCES if s.status == 'IN_PROGRESS')}")
    print(f"  NOT STARTED: {sum(1 for s in ALL_SOURCES if s.status == 'NOT_STARTED')}")
    print("=" * 80)


if __name__ == "__main__":
    print_roadmap()
