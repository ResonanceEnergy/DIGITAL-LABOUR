"""Upwork Full Deployment Config -- 20 specialized proposals + profile sections.

Usage:
    python -m campaign.upwork_deploy              # Print all 20 services
    python -m campaign.upwork_deploy --agent seo   # Show one service
    python -m campaign.upwork_deploy --save        # Save to JSON
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "output" / "upwork_deploy"

# ---------------------------------------------------------------
#  AGENCY PROFILE
# ---------------------------------------------------------------

AGENCY_PROFILE = {
    "name": "BIT RAGE SYSTEMS",
    "tagline": "AI Agent Agency -- Multi-Agent Pipelines for Any Business Task",
    "title": "AI Agent Developer | Multi-Agent Pipelines | Automation Architect",
    "hourly_rate": {"min": 50, "max": 200, "currency": "CAD"},
    "location": "Canada",
    "overview": (
        "We build AI agent pipelines that replace repetitive labor.\n\n"
        "What we deliver:\n"
        "- Multi-agent architectures (research -> writer -> QA -> export)\n"
        "- Provider-agnostic LLM integration (GPT-4o, Claude, Gemini, Grok)\n"
        "- Structured output (Pydantic models, JSON, CSV, Markdown)\n"
        "- QA verification layers with confidence scoring\n"
        "- Production-ready deployment (API, CLI, webhook)\n\n"
        "20 specialized AI agents. 6 cross-sell bundles. One agency.\n\n"
        "Industries: SaaS, e-commerce, real estate, fintech, healthcare, "
        "professional services, agencies, startups."
    ),
    "skills": [
        "Python", "AI Agents", "OpenAI API", "Claude API", "LLM Pipelines",
        "Automation", "Web Scraping", "CRM Integration", "Data Processing",
        "Email Marketing", "Sales Outreach", "SEO Content", "Technical Writing",
        "Business Planning", "Market Research",
    ],
}

# ---------------------------------------------------------------
#  20 SERVICE LISTINGS
# ---------------------------------------------------------------

UPWORK_SERVICES = [
    {
        "agent": "sales_ops",
        "title": "AI Sales Outreach Sequences with Real Company Signals",
        "category": "Sales & Marketing > Lead Generation",
        "subcategory": "B2B Lead Generation",
        "hourly_rate": "$75-150/hr",
        "fixed_price": "$100-500",
        "description": (
            "I build AI-powered sales outreach pipelines that research prospects "
            "in real-time and generate hyper-personalized email sequences.\n\n"
            "Each outreach sequence includes:\n"
            "- Deep company research (funding, hiring, product launches)\n"
            "- Signal detection (triggers that matter to your prospect)\n"
            "- 3-email personalized sequence\n"
            "- QA-verified output with confidence scores\n"
            "- CRM-ready export (JSON + CSV)\n\n"
            "Not templates. Not ChatGPT prompts. A real multi-agent pipeline "
            "with research, writing, and verification stages."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I specialize in AI-powered sales outreach systems. "
            "Your project caught my attention because {relevance_hook}.\n\n"
            "Here's what I'd deliver:\n"
            "1. Research agent that pulls live company signals\n"
            "2. Writer agent that crafts personalized sequences\n"
            "3. QA agent that validates before sending\n\n"
            "I've built 20 specialized AI agents at BIT RAGE SYSTEMS. "
            "Average delivery under 60 seconds per lead.\n\n"
            "Happy to show a live demo on your prospect list.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Sales Outreach Pipeline",
            "description": "Multi-agent system: research -> personalize -> QA -> export",
        },
    },
    {
        "agent": "support",
        "title": "AI Customer Support Ticket Resolution System",
        "category": "Customer Service > Customer Support",
        "subcategory": "Technical Support",
        "hourly_rate": "$50-125/hr",
        "fixed_price": "$75-400",
        "description": (
            "I build AI agents that auto-triage and draft responses for "
            "support tickets -- Zendesk, Freshdesk, Intercom, or email.\n\n"
            "Capabilities:\n"
            "- Auto-categorize ticket type and urgency\n"
            "- Severity scoring (1-5) with escalation flagging\n"
            "- Draft responses with confidence scores\n"
            "- Policy compliance checking\n\n"
            "Average resolution time: 9.6 seconds per ticket."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I build AI support resolution systems. "
            "{relevance_hook}\n\n"
            "My agent handles: triage, severity scoring, draft responses, "
            "and escalation routing -- all in under 10 seconds per ticket.\n\n"
            "Works with Zendesk, Freshdesk, Intercom, or plain email.\n\n"
            "Happy to run a demo batch on 10 of your tickets.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Support Ticket Resolver",
            "description": "Triage + draft + QA pipeline for helpdesk automation",
        },
    },
    {
        "agent": "content_repurpose",
        "title": "AI Content Repurposing -- Blog to Social Media Pipeline",
        "category": "Sales & Marketing > Content Marketing",
        "subcategory": "Content Strategy",
        "hourly_rate": "$50-100/hr",
        "fixed_price": "$50-300",
        "description": (
            "I repurpose your existing content into 5 platform-optimized formats "
            "using a multi-agent AI pipeline.\n\n"
            "One blog post becomes:\n"
            "- LinkedIn post (professional, hashtags, CTA)\n"
            "- Twitter/X thread (280-char tweets)\n"
            "- Email newsletter (subject + body)\n"
            "- Instagram caption (emoji-rich, hashtag-optimized)\n"
            "- TikTok/Reels script (spoken format, hooks)\n\n"
            "One piece of content -> 5 platforms -> 5x the reach."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I see you need content repurposed across platforms. "
            "{relevance_hook}\n\n"
            "My AI pipeline takes one source piece and produces 5 platform-specific "
            "versions -- each optimized for engagement on its platform.\n\n"
            "I can process your first post as a free sample.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "Content Repurposing Pipeline",
            "description": "Blog -> LinkedIn + Twitter + Email + Instagram + TikTok",
        },
    },
    {
        "agent": "doc_extract",
        "title": "AI Document Data Extraction -- Invoices Contracts Resumes",
        "category": "Data Science & Analytics > Data Processing",
        "subcategory": "Data Extraction",
        "hourly_rate": "$50-125/hr",
        "fixed_price": "$50-400",
        "description": (
            "I extract structured data from documents using AI -- invoices, "
            "contracts, resumes, receipts, purchase orders.\n\n"
            "Outputs:\n"
            "- Clean JSON with named entities\n"
            "- Document classification (auto-detect type)\n"
            "- Confidence scores on every field\n"
            "- Batch processing support\n"
            "- Custom field mapping\n\n"
            "No more manual data entry."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I build AI document extraction pipelines. "
            "{relevance_hook}\n\n"
            "My agent extracts structured JSON data from documents with "
            "confidence scores on every field.\n\n"
            "I'll process 5 of your documents as a sample.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "Document Extraction Agent",
            "description": "Invoices/contracts -> structured JSON with confidence scores",
        },
    },
    {
        "agent": "lead_gen",
        "title": "AI B2B Lead List Builder with ICP Scoring",
        "category": "Sales & Marketing > Lead Generation",
        "subcategory": "B2B Lead Generation",
        "hourly_rate": "$75-150/hr",
        "fixed_price": "$100-500",
        "description": (
            "I build targeted B2B lead lists using AI research agents.\n\n"
            "Each lead includes:\n"
            "- Company intel (name, website, industry, size, location)\n"
            "- Decision-maker contacts\n"
            "- ICP fit score (1-100)\n"
            "- Buying signals and pain points\n"
            "- Recommended approach angle\n"
            "- CRM-ready export (CSV + JSON)\n\n"
            "Not scraped junk. Each lead individually researched and scored."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I build AI-driven lead lists scored against your ideal customer profile. "
            "{relevance_hook}\n\n"
            "Each lead comes with fit score, buying signals, and approach angle "
            "-- not just name and email.\n\n"
            "I'll deliver 5 sample leads for your ICP to prove quality.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Lead Gen System",
            "description": "ICP targeting -> research -> scoring -> CRM export",
        },
    },
    {
        "agent": "email_marketing",
        "title": "AI Email Marketing Sequences -- Drip Campaigns & Nurture",
        "category": "Sales & Marketing > Email Marketing",
        "subcategory": "Email Copywriting",
        "hourly_rate": "$50-100/hr",
        "fixed_price": "$75-300",
        "description": (
            "I write complete email marketing sequences using AI:\n\n"
            "- Welcome series (5-7 emails)\n"
            "- Nurture campaigns\n"
            "- Re-engagement sequences\n"
            "- Cart abandonment\n"
            "- Promotional campaigns\n\n"
            "Each sequence includes subject lines, A/B variations, "
            "send timing, segmentation notes, and ESP merge tags."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I specialize in AI-generated email sequences. "
            "{relevance_hook}\n\n"
            "I'll write a 5-email sequence with A/B subject lines, "
            "timing recommendations, and ready merge tags for your ESP.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "Email Marketing Sequences",
            "description": "AI-written drip campaigns with A/B variations",
        },
    },
    {
        "agent": "seo_content",
        "title": "AI SEO Blog Posts -- Keyword Research to Published Article",
        "category": "Writing > Blog Writing",
        "subcategory": "SEO Writing",
        "hourly_rate": "$50-100/hr",
        "fixed_price": "$50-400",
        "description": (
            "I produce SEO-optimized blog posts using a 3-stage pipeline:\n"
            "Keyword Research -> Content Writing -> QA Verification.\n\n"
            "Each article includes:\n"
            "- Primary + secondary keyword targeting\n"
            "- SEO title (60 chars) + meta description (155 chars)\n"
            "- H1/H2/H3 heading structure\n"
            "- 1,500-3,000 words\n"
            "- Internal linking suggestions\n"
            "- Readability score\n\n"
            "Natural content that ranks AND converts."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I write SEO blog posts using a 3-stage AI pipeline. "
            "{relevance_hook}\n\n"
            "You'll get keyword-targeted articles with proper heading structure, "
            "meta tags, and readability scoring.\n\n"
            "I'll deliver a sample article for your primary keyword.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "SEO Content Pipeline",
            "description": "Keyword research -> 2,000-word articles -> QA verification",
        },
    },
    {
        "agent": "social_media",
        "title": "AI Social Media Content -- Multi-Platform Posts & Calendar",
        "category": "Sales & Marketing > Social Media Marketing",
        "subcategory": "Social Media Content Creation",
        "hourly_rate": "$40-80/hr",
        "fixed_price": "$50-250",
        "description": (
            "I generate platform-optimized social media content:\n\n"
            "- LinkedIn (professional, thought leadership)\n"
            "- Twitter/X (threads, engagement hooks)\n"
            "- Instagram (captions, hashtags)\n"
            "- Facebook (community, engagement)\n"
            "- TikTok (scripts, hooks, CTAs)\n\n"
            "Each post includes hashtag recommendations, posting times, "
            "CTA options, and visual direction notes."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I produce AI-optimized social media content. "
            "{relevance_hook}\n\n"
            "I'll create 10 posts across your platforms as a trial.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "Social Media Content Engine",
            "description": "30-60 posts/month, 5 platforms, consistent brand voice",
        },
    },
    {
        "agent": "data_entry",
        "title": "AI Data Entry & Cleaning -- Fast Accurate Structured",
        "category": "Admin Support > Data Entry",
        "subcategory": "Data Entry",
        "hourly_rate": "$30-60/hr",
        "fixed_price": "$25-200",
        "description": (
            "I process and clean data using AI:\n\n"
            "- Standardization (dates, names, addresses, currencies)\n"
            "- Duplicate detection and removal\n"
            "- Missing value handling\n"
            "- Format conversion (CSV, JSON, Excel)\n"
            "- Validation reports\n\n"
            "Contact lists, product catalogs, survey data, spreadsheets."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I do AI-powered data entry and cleaning. "
            "{relevance_hook}\n\n"
            "Send me a sample and I'll process the first 200 rows free "
            "so you can verify quality.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Data Entry System",
            "description": "5,000+ rows/batch with dedup, standardization, validation",
        },
    },
    {
        "agent": "web_scraper",
        "title": "AI Web Scraping -- Structured Data from Any Website",
        "category": "Data Science & Analytics > Data Mining",
        "subcategory": "Web Scraping",
        "hourly_rate": "$50-125/hr",
        "fixed_price": "$50-400",
        "description": (
            "I extract structured data from web pages using AI:\n\n"
            "- Product listings, directories, job boards\n"
            "- Contact info, real estate listings\n"
            "- Custom field mapping\n"
            "- JSON + CSV export\n"
            "- Data quality scoring\n"
            "- Duplicate removal\n\n"
            "Public data only. No login bypass."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I do AI-powered web data extraction. "
            "{relevance_hook}\n\n"
            "I'll extract a 10-page sample so you can verify the output format.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Web Scraping Pipeline",
            "description": "Pages -> structured JSON + CSV with quality scoring",
        },
    },
    {
        "agent": "crm_ops",
        "title": "AI CRM Data Cleanup -- Dedup Standardize Enrich",
        "category": "Sales & Marketing > CRM",
        "subcategory": "CRM Management",
        "hourly_rate": "$50-100/hr",
        "fixed_price": "$75-400",
        "description": (
            "I clean and organize CRM data using AI:\n\n"
            "- Duplicate detection and merge recommendations\n"
            "- Contact standardization\n"
            "- Missing field identification\n"
            "- Lead scoring suggestions\n"
            "- Pipeline stage validation\n\n"
            "Works with Salesforce, HubSpot, Zoho, Pipedrive, or CSV."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I specialize in AI CRM data cleanup. "
            "{relevance_hook}\n\n"
            "Export a sample of 250 records and I'll show you the dedup "
            "and standardization results.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "CRM Cleanup Agent",
            "description": "5,000 records: dedup + standardize + score + export",
        },
    },
    {
        "agent": "bookkeeping",
        "title": "AI Bookkeeping -- Expense Categorization & Reconciliation",
        "category": "Accounting & Consulting > Bookkeeping",
        "subcategory": "Bookkeeping",
        "hourly_rate": "$40-80/hr",
        "fixed_price": "$50-300",
        "description": (
            "I categorize expenses and reconcile bank statements using AI:\n\n"
            "- Expense categorization (chart of accounts mapping)\n"
            "- Transaction matching\n"
            "- Missing receipt flagging\n"
            "- Monthly summary reports\n"
            "- QBO/Xero-compatible export\n\n"
            "Data processing assistance only. Review with your accountant."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I do AI-assisted bookkeeping data processing. "
            "{relevance_hook}\n\n"
            "I'll process 100 transactions as a sample.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Bookkeeping Pipeline",
            "description": "Bank CSV -> categorized + reconciled + QBO export",
        },
    },
    {
        "agent": "proposal_writer",
        "title": "AI Proposal Writer -- Bids RFPs Project Proposals",
        "category": "Writing > Business Writing",
        "subcategory": "Proposals",
        "hourly_rate": "$50-100/hr",
        "fixed_price": "$50-350",
        "description": (
            "I write compelling project proposals and bid responses:\n\n"
            "- Executive summary\n"
            "- Problem/solution framing\n"
            "- Scope of work with deliverables\n"
            "- Timeline and milestones\n"
            "- Tiered pricing options\n"
            "- Social proof section\n\n"
            "Types: project proposals, RFP responses, service agreements, "
            "grant applications."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I write AI-powered proposals that win projects. "
            "{relevance_hook}\n\n"
            "I'll draft a 3-page proposal as a sample.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Proposal Generator",
            "description": "Brief -> executive-quality proposal with pricing tiers",
        },
    },
    {
        "agent": "product_desc",
        "title": "AI Product Descriptions -- Amazon Shopify Etsy Optimized",
        "category": "Sales & Marketing > Product Marketing",
        "subcategory": "Product Description",
        "hourly_rate": "$40-80/hr",
        "fixed_price": "$25-200",
        "description": (
            "I write converting product descriptions for e-commerce:\n\n"
            "- Platform-optimized titles\n"
            "- Feature bullet points (Amazon format)\n"
            "- Benefits-first descriptions\n"
            "- SEO meta\n"
            "- A/B headline variations\n\n"
            "Platforms: Amazon, Shopify, Etsy, eBay, WooCommerce."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I write AI-optimized product descriptions. "
            "{relevance_hook}\n\n"
            "I'll write 5 sample descriptions for your products.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "Product Description Engine",
            "description": "75 products/batch: titles + bullets + descriptions + SEO",
        },
    },
    {
        "agent": "resume_writer",
        "title": "AI Resume Writing -- ATS Optimized with CAR Format",
        "category": "Writing > Resume Writing",
        "subcategory": "Resume Writing",
        "hourly_rate": "$50-100/hr",
        "fixed_price": "$50-250",
        "description": (
            "I write ATS-optimized resumes that beat tracking systems:\n\n"
            "- ATS-friendly format\n"
            "- CAR format bullets (Challenge-Action-Result)\n"
            "- 70%+ quantified achievements\n"
            "- 8-12 targeted keywords\n"
            "- Strong action verbs\n\n"
            "Levels: entry, mid-career, senior, executive."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I write ATS-optimized resumes. "
            "{relevance_hook}\n\n"
            "I'll review your current resume and show you the improvements "
            "before you commit.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Resume Writer",
            "description": "ATS-optimized resumes with CAR format and keywords",
        },
    },
    {
        "agent": "ad_copy",
        "title": "AI Ad Copy -- Google Facebook LinkedIn Twitter Ads",
        "category": "Sales & Marketing > Social Media Advertising",
        "subcategory": "Social Media Ad Copy",
        "hourly_rate": "$50-100/hr",
        "fixed_price": "$50-300",
        "description": (
            "I write ad copy for all major platforms:\n\n"
            "- Headlines + descriptions within char limits\n"
            "- A/B variations (benefit-led + pain-point)\n"
            "- Sitelink copy (Google)\n"
            "- Targeting suggestions\n"
            "- Policy compliance check\n\n"
            "Platforms: Google, Facebook, Instagram, LinkedIn, TikTok, "
            "Twitter, YouTube, Pinterest."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I write high-converting ad copy using AI. "
            "{relevance_hook}\n\n"
            "I'll write a sample campaign with A/B variations for your product.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Ad Copy Engine",
            "description": "8 platforms: headlines + descriptions + A/B + targeting",
        },
    },
    {
        "agent": "market_research",
        "title": "AI Market Research Reports -- Competitive Analysis & SWOT",
        "category": "Business > Market Research",
        "subcategory": "Market Research",
        "hourly_rate": "$75-150/hr",
        "fixed_price": "$100-500",
        "description": (
            "I produce AI-powered market research reports:\n\n"
            "- Market sizing (TAM/SAM/SOM)\n"
            "- Competitive landscape analysis\n"
            "- Customer segmentation\n"
            "- Trend analysis with impact ratings\n"
            "- SWOT analysis\n"
            "- Actionable recommendations\n\n"
            "Based on publicly available data and AI analysis."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I produce AI market research reports. "
            "{relevance_hook}\n\n"
            "I'll deliver a quick competitive overview as a sample.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Market Research Engine",
            "description": "TAM/SAM/SOM + competitive landscape + SWOT + recommendations",
        },
    },
    {
        "agent": "business_plan",
        "title": "AI Business Plans -- Financial Projections & GTM Strategy",
        "category": "Business > Business Plans",
        "subcategory": "Business Plan Writing",
        "hourly_rate": "$75-150/hr",
        "fixed_price": "$100-600",
        "description": (
            "I write investor-ready business plans:\n\n"
            "- Executive summary\n"
            "- Market analysis (TAM/SAM/SOM)\n"
            "- Business model + unit economics\n"
            "- Go-to-market strategy\n"
            "- 3-year financial projections\n"
            "- Funding requirements\n"
            "- Risk assessment\n\n"
            "Types: startup, expansion, investor pitch, loan application."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I write investor-ready business plans. "
            "{relevance_hook}\n\n"
            "I'll draft the executive summary and financials overview "
            "as a sample.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Business Plan Generator",
            "description": "25-35 page plans with financials, GTM, and risk assessment",
        },
    },
    {
        "agent": "press_release",
        "title": "AI Press Releases -- AP Style Wire-Ready Distribution",
        "category": "Writing > Press Releases",
        "subcategory": "Press Release Writing",
        "hourly_rate": "$50-100/hr",
        "fixed_price": "$50-300",
        "description": (
            "I write AP-style press releases ready for distribution:\n\n"
            "- Headline + subheadline\n"
            "- Proper dateline\n"
            "- Lead paragraph (5 Ws)\n"
            "- Inverted pyramid structure\n"
            "- Spokesperson quotes\n"
            "- Company boilerplate\n"
            "- SEO meta for web distribution\n\n"
            "Types: product launch, funding, partnership, hire, event."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I write AP-style press releases. "
            "{relevance_hook}\n\n"
            "I'll draft the headline, lead, and first quote as a sample.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Press Release Writer",
            "description": "AP-style releases: headline + body + quotes + distribution notes",
        },
    },
    {
        "agent": "tech_docs",
        "title": "AI Technical Documentation -- API Docs READMEs User Guides",
        "category": "IT & Networking > Technical Writing",
        "subcategory": "Technical Documentation",
        "hourly_rate": "$75-150/hr",
        "fixed_price": "$75-500",
        "description": (
            "I write clear technical documentation using AI:\n\n"
            "- API references (endpoints, params, responses)\n"
            "- User guides with step-by-step instructions\n"
            "- READMEs with code examples\n"
            "- Tutorials and how-tos\n"
            "- Runbooks and troubleshooting guides\n"
            "- SDK guides with working code\n\n"
            "Languages: Python, JS/TS, Go, Java, C#."
        ),
        "proposal_template": (
            "Hi {client_name},\n\n"
            "I write AI-powered technical documentation. "
            "{relevance_hook}\n\n"
            "I'll document one endpoint or write one section as a sample.\n\n"
            "Best,\nBIT RAGE SYSTEMS"
        ),
        "portfolio_item": {
            "title": "AI Technical Doc Writer",
            "description": "API refs + user guides + READMEs with working code examples",
        },
    },
]


# ---------------------------------------------------------------
#  SPECIALIZED PROFILES
# ---------------------------------------------------------------

SPECIALIZED_PROFILES = [
    {
        "name": "AI Agent Developer",
        "description": "Build multi-agent AI pipelines for B2B automation",
        "agents": ["sales_ops", "support", "lead_gen", "crm_ops", "web_scraper"],
    },
    {
        "name": "AI Content Writer",
        "description": "SEO content, social media, email marketing, ad copy",
        "agents": ["seo_content", "social_media", "email_marketing",
                   "content_repurpose", "ad_copy"],
    },
    {
        "name": "AI Business Consultant",
        "description": "Market research, business plans, proposals, press releases",
        "agents": ["market_research", "business_plan", "proposal_writer",
                   "press_release"],
    },
    {
        "name": "AI Data Processor",
        "description": "Data entry, document extraction, web scraping, bookkeeping",
        "agents": ["data_entry", "doc_extract", "web_scraper", "bookkeeping"],
    },
]


# ---------------------------------------------------------------
#  OUTPUT FUNCTIONS
# ---------------------------------------------------------------

def print_services():
    """Print all 20 Upwork service listings."""
    print(f"\n{'='*70}")
    print("  UPWORK -- 20 SERVICE LISTINGS")
    print(f"{'='*70}")
    for i, svc in enumerate(UPWORK_SERVICES, 1):
        print(f"\n{'_'*70}")
        print(f"  SERVICE {i}: {svc['title']}")
        print(f"  Agent: {svc['agent']} | Category: {svc['category']}")
        print(f"  Rate: {svc['hourly_rate']} hourly | {svc['fixed_price']} fixed")
        print(f"{'_'*70}")
        print(f"\n{svc['description']}")
        print(f"\n  PORTFOLIO: {svc['portfolio_item']['title']}")
        print(f"    {svc['portfolio_item']['description']}")
    print(f"\n{'='*70}\n")


def print_agent(agent_key: str):
    """Print one service by agent name."""
    svc = next((s for s in UPWORK_SERVICES if agent_key in s["agent"]), None)
    if not svc:
        print(f"Unknown agent: {agent_key}")
        print(f"Available: {', '.join(s['agent'] for s in UPWORK_SERVICES)}")
        return
    print(f"\n  [{svc['agent'].upper()}] {svc['title']}")
    print(f"  Category: {svc['category']}")
    print(f"  Rate: {svc['hourly_rate']} | Fixed: {svc['fixed_price']}")
    print(f"\n{svc['description']}")
    print(f"\n  PROPOSAL TEMPLATE:")
    print(f"  {svc['proposal_template']}")


def save_all():
    """Save all Upwork deployment data to JSON."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    path = OUTPUT_DIR / "upwork_profile.json"
    path.write_text(json.dumps(AGENCY_PROFILE, indent=2), encoding="utf-8")
    print(f"  [SAVED] {path.name}")

    path = OUTPUT_DIR / "upwork_services_all.json"
    path.write_text(json.dumps(UPWORK_SERVICES, indent=2), encoding="utf-8")
    print(f"  [SAVED] {path.name}")

    path = OUTPUT_DIR / "upwork_specialized_profiles.json"
    path.write_text(json.dumps(SPECIALIZED_PROFILES, indent=2), encoding="utf-8")
    print(f"  [SAVED] {path.name}")

    proposals = {s["agent"]: s["proposal_template"] for s in UPWORK_SERVICES}
    path = OUTPUT_DIR / "upwork_proposals.json"
    path.write_text(json.dumps(proposals, indent=2), encoding="utf-8")
    print(f"  [SAVED] {path.name}")

    print(f"\n  All files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Upwork 20-Service Deployment")
    parser.add_argument("--agent", default="", help="Show one agent's service")
    parser.add_argument("--save", action="store_true", help="Save to JSON")
    args = parser.parse_args()

    if args.agent:
        print_agent(args.agent)
    elif args.save:
        save_all()
    else:
        print_services()
