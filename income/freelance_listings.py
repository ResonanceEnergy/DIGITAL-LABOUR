"""Freelance Platform Listings — Ready-to-post gig descriptions for Fiverr + Freelancer.

Generates professional listing copy for each of the 4 agent capabilities.
Covers title, description, tags, pricing tiers, and FAQ for each platform.

Usage:
    python -m income.freelance_listings                # Print all listings
    python -m income.freelance_listings --fiverr       # Fiverr gigs only
    python -m income.freelance_listings --freelancer   # Freelancer.com listings only
    python -m income.freelance_listings --save         # Save to files
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "output" / "freelance_listings"


# ── Fiverr Gig Definitions ─────────────────────────────────────

FIVERR_GIGS = [
    {
        "title": "I will generate AI-powered sales outreach sequences with real company signals",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["ai sales agent", "sales outreach", "lead generation", "cold email", "ai agent", "sales automation", "b2b outreach"],
        "description": """## AI-Powered Sales Outreach Agent

I'll generate hyper-personalized sales outreach sequences for ANY company using real-time signals — not templates.

### What You Get:
- **Deep company research** — funding, hiring, product launches, tech stack
- **Signal detection** — real triggers that matter to your prospect
- **3-email outreach sequence** — personalized to their specific situation
- **QA-verified output** — every email passes through quality gates
- **CRM-ready export** — JSON + CSV format

### How It Works:
1. You give me a company name + target role
2. My AI agent pipeline researches the company in real-time
3. A writer agent crafts personalized emails referencing real signals
4. A QA agent validates tone, accuracy, and structure
5. You get a ready-to-send sequence in under 60 seconds

### Why This Is Different:
This isn't ChatGPT in a wrapper. It's a **multi-agent pipeline** with research, writing, and QA stages. Every output references real company data, not generic filler.

**Average delivery: Under 60 seconds per lead.**

Built by Resonance Energy (Canada) — production AI systems, not prototypes.""",
        "packages": {
            "Basic ($5)": "1 company — full research + 3-email sequence + JSON export",
            "Standard ($20)": "5 companies — batch processing + CSV export + priority delivery",
            "Premium ($75)": "25 companies — full batch + follow-up sequences + dedicated support",
        },
        "faq": [
            ("What do you need from me?", "Just the company name and target role (e.g., 'Stripe, Head of Growth'). I handle everything else."),
            ("How fast is delivery?", "Basic orders delivered in under 5 minutes. Standard in 15 minutes. Premium within 1 hour."),
            ("Can I choose the email tone?", "Yes — professional, casual, or aggressive. Just mention in your order notes."),
            ("Do you use templates?", "No. Every email is generated fresh using real-time company research and AI signal detection."),
            ("What about email verification?", "I provide email pattern predictions. For verified emails, add the verification add-on."),
        ],
    },
    {
        "title": "I will build an AI support ticket resolver that drafts responses instantly",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["ai support agent", "customer support", "ticket resolution", "helpdesk automation", "ai agent", "support bot", "ticket triage"],
        "description": """## AI Support Ticket Resolution Agent

Get instant draft responses for support tickets — triaged, severity-scored, and ready to send.

### What You Get:
- **Auto-triage** — categorizes tickets by type and urgency
- **Severity scoring** — 1-5 scale with escalation flagging
- **Draft response** — ready-to-send reply with confidence score
- **Policy compliance** — checks against your guidelines
- **Structured output** — JSON format for helpdesk integration

### How It Works:
1. You send a support ticket (text, email, or JSON)
2. AI classifies the issue type and severity
3. A response agent drafts a reply based on the context
4. QA agent validates tone and accuracy
5. You get a structured response in under 10 seconds

### Use Cases:
- SaaS companies drowning in tickets
- E-commerce customer service teams
- Agencies managing multiple client support queues
- Anyone who needs faster ticket response times

**Average resolution: 9.6 seconds per ticket.**""",
        "packages": {
            "Basic ($5)": "10 tickets resolved — triage + draft response + JSON export",
            "Standard ($15)": "50 tickets — batch processing + analytics report",
            "Premium ($40)": "200 tickets — full resolution + escalation routing + weekly report",
        },
        "faq": [
            ("What format do you need tickets in?", "Plain text, email format, or JSON. Any format works."),
            ("Can this integrate with my helpdesk?", "Yes — via API or webhook. I'll provide integration docs."),
            ("How accurate are the responses?", "80%+ QA pass rate. Every response includes a confidence score."),
        ],
    },
    {
        "title": "I will repurpose your blog post into 5 social media formats using AI",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["content repurposing", "ai content", "social media", "blog to social", "content automation", "ai writer", "content marketing"],
        "description": """## AI Content Repurposing Agent

One blog post → LinkedIn, Twitter/X, email newsletter, Instagram caption, and TikTok script. All optimized for each platform.

### What You Get:
- **LinkedIn post** — professional tone, hashtags, engagement hooks
- **Twitter/X thread** — under 280 chars per tweet, thread format
- **Email newsletter** — subject line + body, ready to send
- **Instagram caption** — emoji-rich, hashtag-optimized
- **TikTok/Reels script** — spoken format with hooks and CTAs

### How It Works:
1. You give me a blog post, article, or content piece
2. AI analyzes tone, key points, and audience
3. Platform-specific agents generate optimized versions
4. QA validates length, format, and platform rules
5. You get 5 ready-to-post pieces in under 60 seconds

**One piece of content → 5 platforms → 5x the reach.**

Built with multi-agent AI pipelines. Not a ChatGPT prompt.""",
        "packages": {
            "Basic ($5)": "1 blog post → 5 platform formats + editable text",
            "Standard ($20)": "5 posts → 25 pieces total + content calendar template",
            "Premium ($50)": "15 posts → 75 pieces + monthly content strategy",
        },
        "faq": [
            ("What content can I submit?", "Blog posts, articles, press releases, case studies — any written content."),
            ("Can I choose which platforms?", "Yes. Default is all 5, but you can pick specific ones."),
            ("Do you handle images?", "Text content only. I provide copy — you add your own images."),
        ],
    },
    {
        "title": "I will extract structured data from documents using AI — invoices, contracts, resumes",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["document extraction", "ai ocr", "invoice processing", "contract analysis", "data extraction", "ai agent", "document automation"],
        "description": """## AI Document Data Extraction Agent

Send me invoices, contracts, or resumes and get clean, structured JSON data back.

### What You Get:
- **Entity extraction** — names, dates, amounts, addresses
- **Document classification** — auto-detects document type
- **Structured JSON output** — ready for database import
- **Confidence scores** — reliability rating on every field
- **QA verification** — accuracy checked before delivery

### Supported Documents:
- Invoices (line items, totals, tax, vendor info)
- Contracts (parties, dates, clauses, obligations)
- Resumes/CVs (experience, skills, education, contact info)
- Receipts, purchase orders, statements

### How It Works:
1. You send document text (paste, upload, or API)
2. AI classifies the document type
3. Extraction agent pulls structured data
4. QA agent validates accuracy
5. You get clean JSON in under 10 seconds

**No more manual data entry. No more copy-paste.**""",
        "packages": {
            "Basic ($5)": "5 documents extracted — JSON output + confidence scores",
            "Standard ($15)": "25 documents — batch + CSV export + summary report",
            "Premium ($40)": "100 documents — full batch + custom field mapping + API access",
        },
        "faq": [
            ("What languages do you support?", "English primarily. Other languages on request."),
            ("Can I send PDFs?", "Send the text content. For PDF-to-text, I can recommend OCR tools."),
            ("How accurate is extraction?", "85%+ accuracy with confidence scores on every field."),
        ],
    },
]


# ── Freelancer.com Listing Definitions ──────────────────────────

FREELANCER_PROFILE = {
    "agency_name": "Bit Rage Labour — AI Agent Agency",
    "tagline": "Production AI agents for sales, support, content & document automation",
    "hourly_rate": "$75-200/hr",
    "about": """We build and deploy production AI agent pipelines — not ChatGPT wrappers.

Our 4 specialized AI agents handle:
• Sales Outreach — real-time company research + personalized 3-email sequences
• Support Resolution — ticket triage, severity scoring, draft responses in <10s
• Content Repurposing — blog → 5 platform formats (LinkedIn, Twitter, Email, Instagram, TikTok)
• Document Extraction — invoices, contracts, resumes → structured JSON

Tech stack: Python, FastAPI, GPT-4o, Claude, Gemini, Grok. Multi-agent pipelines with QA verification.

Based in Canada. Built by Resonance Energy.""",
    "skills": [
        "Artificial Intelligence", "Machine Learning", "Python",
        "FastAPI", "Natural Language Processing", "Chatbot Development",
        "Data Extraction", "Automation", "API Development",
        "Sales Automation", "Customer Support", "Content Writing",
    ],
    "bid_templates": {
        "ai_agent_build": """Hi,

I run Bit Rage Labour — we build production AI agent pipelines (not ChatGPT wrappers).

Your project is exactly what our team does daily. We have 4 specialized agents already in production:
- Sales outreach (real-time research + personalized emails)
- Support resolution (triage + draft responses in <10s)
- Content repurposing (blog → 5 social formats)
- Document extraction (invoices/contracts → JSON)

We use GPT-4o, Claude, Gemini, and Grok with automatic failover. Every output passes through QA verification.

I can start immediately and deliver a working prototype within 48 hours.

Let's discuss your specific requirements.

— Bit Rage Labour (Resonance Energy, Canada)""",
        "chatbot_build": """Hi,

We specialize in building AI-powered chatbots and agent systems — not simple rule-based bots, but multi-agent pipelines with real AI reasoning.

Our existing production bots handle:
- Customer support (auto-triage, severity scoring, draft responses)
- Sales qualification (company research + personalized outreach)
- Content generation (multi-platform format optimization)

Tech: Python, FastAPI, OpenAI/Claude/Gemini APIs, webhook delivery, API-first architecture.

I can deliver a working MVP within 3-5 days with full documentation.

— Bit Rage Labour""",
        "data_extraction": """Hi,

We have a production document extraction agent that handles invoices, contracts, resumes, and custom document types.

The agent provides:
- Automatic document classification
- Entity extraction (names, dates, amounts, etc.)
- Structured JSON/CSV output
- Confidence scores on every field
- QA verification before delivery

Currently processing documents in under 10 seconds with 85%+ accuracy.

Happy to adapt it to your specific format requirements.

— Bit Rage Labour""",
    },
}


# ── Output Functions ────────────────────────────────────────────

UPWORK_PROFILE = {
    "title": "AI Agent Developer | Multi-Agent Pipelines | GPT-4o, Claude, Gemini",
    "headline": "Production AI Agent Systems — Sales, Support, Content & Data Extraction Automation",
    "hourly_rate": "$85-200/hr",
    "overview": """I build production AI agent pipelines that actually work in business — not ChatGPT wrappers or prompt-only demos.

**What I Build:**
• Sales Outreach Agents — real-time company research → personalized 3-email sequences → QA verification → delivery in <60s
• Support Resolution Agents — ticket triage, severity scoring, draft responses, policy compliance checks
• Content Repurposing Agents — blog post → LinkedIn, Twitter/X, email newsletter, Instagram, TikTok scripts
• Document Extraction Agents — invoices, contracts, resumes → structured JSON/CSV with confidence scores

**My Tech Stack:**
Python | FastAPI | OpenAI GPT-4o | Anthropic Claude | Google Gemini | xAI Grok | Multi-agent orchestration | QA verification pipelines | Webhook delivery | Stripe billing integration | Docker

**What Makes Me Different:**
→ I run a live AI agent agency (Bit Rage Labour) — these agents are in production RIGHT NOW serving paying clients
→ Multi-LLM architecture with automatic failover (if OpenAI is down, Claude takes over instantly)
→ Every output passes through automated QA before delivery
→ Full API-first architecture — your agents ship with REST endpoints, not just scripts

**Engagement Models:**
• Hourly ($85-200/hr) — for custom agent builds
• Fixed price — for well-scoped projects
• Retainer ($750-2,500/mo) — ongoing agent management + optimization

Based in Canada. Built by Resonance Energy.""",
    "skills": [
        "Artificial Intelligence", "Machine Learning", "Python", "FastAPI",
        "OpenAI API", "Claude API", "LangChain", "Natural Language Processing",
        "Chatbot Development", "Data Extraction", "Automation", "API Development",
        "Web Scraping", "Sales Automation", "Customer Support Automation",
    ],
    "portfolio_items": [
        {
            "title": "AI Sales Outreach Pipeline",
            "description": "Multi-agent system: research agent → writer agent → QA agent. Processes 50+ leads/hour with personalized 3-email sequences using real company signals.",
            "url": "https://bit-rage-labour.com",
        },
        {
            "title": "AI Support Ticket Resolver",
            "description": "Automated triage + severity scoring + draft responses. Handles 200+ tickets/hour with <10s response time per ticket.",
            "url": "https://bit-rage-labour.com",
        },
        {
            "title": "Content Repurposing Engine",
            "description": "One blog post → 5 platform-optimized formats (LinkedIn, Twitter/X, email, Instagram, TikTok) with tone matching and character limits.",
            "url": "https://bit-rage-labour.com",
        },
        {
            "title": "Document Extraction Agent",
            "description": "Invoice, contract, and resume parser → structured JSON with entity extraction and confidence scoring.",
            "url": "https://bit-rage-labour.com",
        },
    ],
    "specialized_profiles": [
        {
            "category": "AI & Machine Learning",
            "title": "AI Agent Developer — Production Multi-Agent Systems",
            "skills": ["Python", "OpenAI API", "FastAPI", "NLP", "Chatbot Development"],
        },
        {
            "category": "Sales & Marketing Automation",
            "title": "AI Sales Automation Specialist — Outreach & Lead Generation",
            "skills": ["Sales Automation", "Lead Generation", "Cold Email", "CRM Integration"],
        },
    ],
}




def print_fiverr_gigs():
    """Print all Fiverr gig listings."""
    print(f"\n{'='*70}")
    print("  FIVERR GIG LISTINGS — Ready to Post")
    print(f"{'='*70}")

    for i, gig in enumerate(FIVERR_GIGS, 1):
        print(f"\n{'─'*70}")
        print(f"  GIG {i}: {gig['title']}")
        print(f"  Category: {gig['category']}")
        print(f"  Tags: {', '.join(gig['tags'])}")
        print(f"{'─'*70}")
        print(f"\n{gig['description']}")
        print(f"\n  PACKAGES:")
        for pkg, desc in gig["packages"].items():
            print(f"    {pkg}: {desc}")
        print(f"\n  FAQ:")
        for q, a in gig["faq"]:
            print(f"    Q: {q}")
            print(f"    A: {a}")
    print(f"\n{'='*70}\n")


def print_freelancer_profile():
    """Print Freelancer.com profile and bid templates."""
    p = FREELANCER_PROFILE
    print(f"\n{'='*70}")
    print("  FREELANCER.COM PROFILE — Ready to Create")
    print(f"{'='*70}")
    print(f"\n  Agency: {p['agency_name']}")
    print(f"  Tagline: {p['tagline']}")
    print(f"  Rate: {p['hourly_rate']}")
    print(f"\n  About:\n{p['about']}")
    print(f"\n  Skills: {', '.join(p['skills'])}")
    print(f"\n{'─'*70}")
    print("  BID TEMPLATES:")
    for name, template in p["bid_templates"].items():
        print(f"\n  [{name.upper()}]")
        print(template)
    print(f"\n{'='*70}\n")


def print_upwork_profile():
    """Print Upwork profile content."""
    p = UPWORK_PROFILE
    print(f"\n{'='*70}")
    print("  UPWORK PROFILE — Ready to Create")
    print(f"{'='*70}")
    print(f"\n  Title: {p['title']}")
    print(f"  Headline: {p['headline']}")
    print(f"  Rate: {p['hourly_rate']}")
    print(f"\n  Overview:\n{p['overview']}")
    print(f"\n  Skills: {', '.join(p['skills'])}")
    print(f"\n{'─'*70}")
    print("  PORTFOLIO ITEMS:")
    for item in p["portfolio_items"]:
        print(f"\n  [{item['title']}]")
        print(f"  {item['description']}")
        print(f"  URL: {item['url']}")
    print(f"\n{'─'*70}")
    print("  SPECIALIZED PROFILES:")
    for sp in p["specialized_profiles"]:
        print(f"\n  Category: {sp['category']}")
        print(f"  Title: {sp['title']}")
        print(f"  Skills: {', '.join(sp['skills'])}")
    print(f"\n{'='*70}\n")


def save_listings():
    """Save all listing content to files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save Fiverr gigs
    for i, gig in enumerate(FIVERR_GIGS, 1):
        slug = gig["title"][:50].replace(" ", "_").lower()
        filepath = OUTPUT_DIR / f"fiverr_gig_{i}_{slug}.json"
        filepath.write_text(json.dumps(gig, indent=2), encoding="utf-8")
        print(f"  [SAVED] {filepath.name}")

    # Save Freelancer profile
    filepath = OUTPUT_DIR / "freelancer_profile.json"
    filepath.write_text(json.dumps(FREELANCER_PROFILE, indent=2), encoding="utf-8")
    print(f"  [SAVED] {filepath.name}")

    # Save Upwork profile
    filepath = OUTPUT_DIR / "upwork_profile.json"
    filepath.write_text(json.dumps(UPWORK_PROFILE, indent=2), encoding="utf-8")
    print(f"  [SAVED] {filepath.name}")

    print(f"\n  Listings saved to: {OUTPUT_DIR}")


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Freelance Platform Listings")
    parser.add_argument("--fiverr", action="store_true", help="Show Fiverr gigs")
    parser.add_argument("--freelancer", action="store_true", help="Show Freelancer.com profile")
    parser.add_argument("--upwork", action="store_true", help="Show Upwork profile")
    parser.add_argument("--save", action="store_true", help="Save listings to files")
    args = parser.parse_args()

    if args.fiverr:
        print_fiverr_gigs()
    elif args.freelancer:
        print_freelancer_profile()
    elif args.upwork:
        print_upwork_profile()
    elif args.save:
        save_listings()
    else:
        print_fiverr_gigs()
        print_freelancer_profile()
        print_upwork_profile()
