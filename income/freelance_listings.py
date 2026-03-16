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
    # ── Gig 5: Lead Generation ──
    {
        "title": "I will find qualified B2B leads with AI-powered research and scoring",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["lead generation", "b2b leads", "ai lead gen", "prospect research", "lead scoring", "sales leads", "lead list"],
        "description": """## AI Lead Generation Agent

Get a scored list of qualified B2B leads — researched, enriched, and ready for outreach.

### What You Get:
- **ICP-matched leads** -- filtered by industry, size, geo, and role
- **Lead scoring** -- 1-100 score based on fit + buying signals
- **Company enrichment** -- tech stack, funding, headcount, recent news
- **Contact predictions** -- email patterns + LinkedIn URLs
- **Export-ready** -- JSON, CSV, or CRM-import format

### How It Works:
1. Define your Ideal Customer Profile (industry, size, role, region)
2. AI scans databases and web sources for matching companies
3. Each lead is scored and enriched with real signals
4. QA verification filters out low-quality matches
5. Delivered as a scored, ranked list

**50+ qualified leads per batch. Delivered in minutes.**""",
        "packages": {
            "Basic ($5)": "10 qualified leads -- scored + enriched + CSV export",
            "Standard ($20)": "50 leads -- full enrichment + priority scoring + CRM format",
            "Premium ($75)": "200 leads -- deep research + custom scoring + dedicated batch",
        },
        "faq": [
            ("What info do you need?", "Industry, company size range, target role, and geography."),
            ("How do you score leads?", "Combination of ICP fit, buying signals, company growth indicators."),
            ("Can you find emails?", "Email pattern predictions + LinkedIn URLs. Not verified emails."),
        ],
    },
    # ── Gig 6: Email Marketing ──
    {
        "title": "I will create a complete AI-generated email marketing sequence",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["email marketing", "email sequence", "drip campaign", "email automation", "ai copywriting", "newsletter", "email funnel"],
        "description": """## AI Email Marketing Sequence Builder

Complete email sequences -- welcome, nurture, re-engagement, or launch campaigns. AI-written, QA-verified.

### What You Get:
- **5-10 email sequence** -- subject lines + body copy + CTAs
- **Segmentation strategy** -- who gets what, when
- **A/B variants** -- 2 subject line options per email
- **Platform-ready** -- Mailchimp, ConvertKit, or plain HTML
- **Performance predictions** -- expected open/click rates

### Campaign Types:
- Welcome/onboarding sequences
- Nurture drips (education-first selling)
- Product launch announcements
- Re-engagement (win-back) campaigns
- Cart abandonment sequences

**Professional email campaigns in under 5 minutes.**""",
        "packages": {
            "Basic ($5)": "3-email sequence -- subject + body + CTAs",
            "Standard ($20)": "7-email sequence + A/B variants + segmentation notes",
            "Premium ($60)": "Full funnel (10 emails) + strategy doc + platform setup guide",
        },
        "faq": [
            ("What info do I provide?", "Your business, target audience, goal, and preferred tone."),
            ("Which platforms do you support?", "Any platform. I provide copy you paste in."),
            ("Do you handle design?", "Text/HTML copy only. You handle design in your platform."),
        ],
    },
    # ── Gig 7: SEO Content ──
    {
        "title": "I will write SEO-optimized blog posts and articles using AI research",
        "category": "Writing & Translation > Content Writing > SEO Writing",
        "tags": ["seo writing", "blog post", "ai content", "seo article", "content marketing", "keyword optimization", "long form content"],
        "description": """## AI SEO Content Writer

Long-form, keyword-optimized blog posts and articles -- researched, written, and QA-checked by AI agents.

### What You Get:
- **Keyword research** -- primary + secondary + LSI keywords
- **SEO-optimized article** -- title, meta description, H2/H3 structure
- **Internal linking suggestions** -- boost your existing content
- **Readability score** -- Flesch-Kincaid optimized
- **QA-verified** -- no fluff, no AI artifacts, no plagiarism signals

### Content Types:
- Blog posts (1500-3000 words)
- Pillar pages (3000-5000 words)
- How-to guides
- Listicles
- Comparison articles

**Rank-ready content. Not AI slop.**""",
        "packages": {
            "Basic ($5)": "1 blog post (1500 words) -- keyword optimized + meta description",
            "Standard ($20)": "3 articles + keyword research report + internal linking map",
            "Premium ($60)": "10 articles + content calendar + pillar page strategy",
        },
        "faq": [
            ("Do you do keyword research?", "Yes. Primary, secondary, and LSI keywords included."),
            ("What about images?", "Text content only. I suggest image placements and alt text."),
            ("Can I request specific topics?", "Absolutely. Give me the topic, audience, and target keyword."),
        ],
    },
    # ── Gig 8: Social Media ──
    {
        "title": "I will create a month of AI-generated social media content for any platform",
        "category": "Digital Marketing > Social Media Marketing > Social Media Content",
        "tags": ["social media content", "social media posts", "linkedin posts", "twitter content", "instagram captions", "ai social media", "content calendar"],
        "description": """## AI Social Media Content Generator

30 days of platform-optimized social media posts -- scheduled, hashtagged, and ready to post.

### What You Get:
- **30 unique posts** per platform -- no repeats
- **Platform optimization** -- length, hashtags, format per network
- **Content mix** -- educational, promotional, engagement, storytelling
- **Hashtag research** -- relevant, trending, niche-specific
- **Content calendar** -- date + time suggestions for optimal reach

### Platforms Covered:
- LinkedIn (professional, thought leadership)
- Twitter/X (threads, single tweets, engagement hooks)
- Instagram (captions, carousel outlines, Reels scripts)
- Facebook (community posts, event promos)
- TikTok (scripts with hooks and CTAs)

**A full month of content in under 10 minutes.**""",
        "packages": {
            "Basic ($5)": "1 week (7 posts) for 1 platform -- captions + hashtags",
            "Standard ($20)": "30 posts for 2 platforms + content calendar",
            "Premium ($50)": "30 posts for 5 platforms + strategy + engagement templates",
        },
        "faq": [
            ("Which platforms?", "LinkedIn, Twitter/X, Instagram, Facebook, TikTok."),
            ("Do you create images?", "Text/captions only. Image suggestions included."),
            ("Can I pick the content mix?", "Yes. Default is 40% educational, 30% promotional, 30% engagement."),
        ],
    },
    # ── Gig 9: Data Entry ──
    {
        "title": "I will process and clean your messy data using AI -- spreadsheets, CSVs, databases",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["data entry", "data cleaning", "data processing", "spreadsheet", "csv processing", "data formatting", "ai data entry"],
        "description": """## AI Data Entry & Cleaning Agent

Messy spreadsheets, inconsistent formats, duplicate records -- fixed and standardized by AI in minutes.

### What You Get:
- **Data cleaning** -- fix typos, standardize formats, remove duplicates
- **Data transformation** -- convert between formats (CSV, JSON, Excel)
- **Field extraction** -- pull specific data from unstructured text
- **Validation** -- flag impossible values, missing fields, outliers
- **Quality report** -- summary of changes made + confidence scores

### Common Tasks:
- Clean and deduplicate contact lists
- Standardize address/phone/email formats
- Categorize products or transactions
- Merge data from multiple sources
- Convert between file formats

**Hours of manual work done in minutes.**""",
        "packages": {
            "Basic ($5)": "Up to 500 rows -- clean + deduplicate + export",
            "Standard ($15)": "Up to 5,000 rows -- full cleaning + transformation + report",
            "Premium ($40)": "Up to 50,000 rows -- batch processing + custom rules + validation",
        },
        "faq": [
            ("What formats do you accept?", "CSV, JSON, Excel (.xlsx), plain text, TSV."),
            ("How do you handle duplicates?", "Fuzzy matching on key fields. You choose merge strategy."),
            ("Can you handle large files?", "Up to 50K rows per batch. Larger files split automatically."),
        ],
    },
    # ── Gig 10: Web Scraper ──
    {
        "title": "I will scrape and structure web data using AI -- contacts, products, listings",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["web scraping", "data scraping", "lead scraping", "contact extraction", "price scraping", "ai scraper", "data collection"],
        "description": """## AI Web Scraping Agent

Extract structured data from any website -- contacts, products, reviews, listings. Cleaned, formatted, and delivered.

### What You Get:
- **Structured extraction** -- contacts, products, prices, reviews
- **Multi-page support** -- handles pagination and listing pages
- **Data cleaning** -- normalized formats, removed duplicates
- **Multiple export formats** -- JSON, CSV, Excel
- **Extraction schema** -- reusable template for repeat jobs

### Common Scraping Targets:
- Business directories (contacts + emails)
- E-commerce sites (products + prices)
- Job boards (listings + requirements)
- Review sites (ratings + text)
- Real estate listings (prices + details)

**Clean data from any website. No coding required.**""",
        "packages": {
            "Basic ($5)": "1 source -- up to 100 records extracted + CSV",
            "Standard ($20)": "3 sources -- up to 1,000 records + deduplication",
            "Premium ($50)": "10 sources -- up to 10,000 records + custom schema",
        },
        "faq": [
            ("Is this legal?", "I scrape publicly available data only. No login-walled content."),
            ("What if the site changes?", "Schemas are adaptable. I include update instructions."),
            ("Can you schedule recurring scrapes?", "I provide the schema. You can automate with our API."),
        ],
    },
    # ── Gig 11: CRM Operations ──
    {
        "title": "I will clean, enrich and optimize your CRM data using AI",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["crm data", "crm cleanup", "salesforce cleanup", "hubspot data", "crm optimization", "contact enrichment", "data hygiene"],
        "description": """## AI CRM Operations Agent

Clean, deduplicate, enrich, and score your CRM contacts -- HubSpot, Salesforce, or spreadsheet-based.

### What You Get:
- **Deduplication** -- merge duplicate contacts intelligently
- **Data enrichment** -- add missing company info, titles, LinkedIn
- **Lead scoring** -- rank contacts by engagement potential
- **Segmentation** -- auto-tag by industry, size, stage
- **Health report** -- CRM data quality score + recommendations

### Supported CRMs:
- HubSpot (CSV export/import)
- Salesforce (CSV export/import)
- Pipedrive, Zoho, or any spreadsheet-based CRM

**Turn your messy CRM into a sales machine.**""",
        "packages": {
            "Basic ($5)": "Up to 500 contacts -- deduplicate + clean + export",
            "Standard ($20)": "Up to 5,000 contacts -- full enrichment + scoring + segmentation",
            "Premium ($50)": "Up to 25,000 contacts -- deep clean + custom scoring + strategy",
        },
        "faq": [
            ("Which CRMs?", "Any that exports to CSV. HubSpot and Salesforce preferred."),
            ("Do you access my CRM directly?", "No. You export CSV, I process, you re-import."),
            ("How accurate is enrichment?", "Company data 85%+. Individual enrichment varies."),
        ],
    },
    # ── Gig 12: Bookkeeping ──
    {
        "title": "I will categorize and reconcile your financial transactions using AI",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["bookkeeping", "expense categorization", "financial data", "transaction sorting", "ai bookkeeping", "accounting automation", "reconciliation"],
        "description": """## AI Bookkeeping Agent

Categorize expenses, reconcile transactions, and generate financial summaries -- formatted for your accountant.

### What You Get:
- **Auto-categorization** -- income, expenses, transfers classified
- **Tax category mapping** -- aligned with standard tax categories
- **Reconciliation** -- match bank statements to invoices
- **Summary reports** -- monthly P&L, expense breakdown
- **Export-ready** -- QuickBooks, Xero, or CSV format

### Common Tasks:
- Categorize bank statement transactions
- Match invoices to payments
- Generate expense reports
- Prepare data for tax filing
- Monthly financial summaries

**Your bookkeeping done in minutes, not hours.**""",
        "packages": {
            "Basic ($5)": "Up to 100 transactions -- categorized + summary",
            "Standard ($20)": "Up to 500 transactions -- full categorization + P&L report",
            "Premium ($50)": "Up to 2,000 transactions -- reconciliation + tax prep + export",
        },
        "faq": [
            ("What format?", "CSV bank statements, spreadsheets, or plain text transaction lists."),
            ("Do you do actual accounting?", "Data processing only. I categorize and summarize -- your CPA does the rest."),
            ("Which accounting software?", "QuickBooks, Xero, Wave, or plain CSV export."),
        ],
    },
    # ── Gig 13: Proposal Writer ──
    {
        "title": "I will write professional business proposals and project bids using AI",
        "category": "Writing & Translation > Business & Marketing Copy > Business Plans & Proposals",
        "tags": ["business proposal", "project proposal", "proposal writing", "bid writing", "rfp response", "ai proposal", "grant proposal"],
        "description": """## AI Proposal Writer Agent

Professional proposals that win -- project bids, RFP responses, grant applications, partnership proposals.

### What You Get:
- **Executive summary** -- compelling overview of your offering
- **Scope of work** -- detailed deliverables, timeline, milestones
- **Budget breakdown** -- itemized pricing with justification
- **Team/capability section** -- why you're the right choice
- **QA-verified** -- grammar, formatting, persuasion checked

### Proposal Types:
- Project proposals (freelance/agency bids)
- RFP/RFQ responses
- Grant applications
- Partnership proposals
- Internal project pitches

**Win more deals with proposals that close.**""",
        "packages": {
            "Basic ($5)": "1 proposal (2-3 pages) -- executive summary + scope + pricing",
            "Standard ($20)": "1 detailed proposal (5-8 pages) + budget table + timeline",
            "Premium ($60)": "3 proposals + customization per recipient + follow-up email",
        },
        "faq": [
            ("What do you need?", "The project brief, your company info, and your pricing."),
            ("Can you respond to RFPs?", "Yes. Send the RFP document and I'll draft a tailored response."),
            ("What industries?", "Any industry. AI adapts to your sector's language and norms."),
        ],
    },
    # ── Gig 14: Product Descriptions ──
    {
        "title": "I will write compelling product descriptions for any e-commerce platform",
        "category": "Writing & Translation > Business & Marketing Copy > Product Descriptions",
        "tags": ["product descriptions", "ecommerce copy", "amazon listing", "shopify copy", "product copywriting", "ai product writer", "listing optimization"],
        "description": """## AI Product Description Writer

Conversion-optimized product descriptions for Amazon, Shopify, Etsy, eBay, or any e-commerce platform.

### What You Get:
- **Platform-optimized copy** -- formatted for your marketplace
- **SEO keywords** -- naturally woven into descriptions
- **Benefit-focused** -- features translated into customer value
- **Bullet points** -- scannable highlights for quick reading
- **A/B variants** -- 2 versions to test which converts better

### Platforms:
- Amazon (title, bullets, A+ content)
- Shopify (product page copy)
- Etsy (listing description + tags)
- eBay (item description)
- General e-commerce / DTC

**Descriptions that sell, not just describe.**""",
        "packages": {
            "Basic ($5)": "5 product descriptions -- title + description + bullets",
            "Standard ($20)": "20 products -- SEO-optimized + A/B variants",
            "Premium ($50)": "50 products -- full catalog copy + keyword research",
        },
        "faq": [
            ("What do I provide?", "Product name, key features, target audience. Photos optional."),
            ("Which platforms?", "Amazon, Shopify, Etsy, eBay, or custom."),
            ("Do you do A+ / Enhanced content?", "Yes, for Amazon A+ and Shopify rich text."),
        ],
    },
    # ── Gig 15: Resume Writer ──
    {
        "title": "I will write or rewrite your resume and cover letter using AI optimization",
        "category": "Writing & Translation > Resume Writing",
        "tags": ["resume writing", "cv writing", "cover letter", "resume optimization", "ats resume", "ai resume", "job application"],
        "description": """## AI Resume & Cover Letter Writer

ATS-optimized resumes and tailored cover letters -- designed to get past screening and impress hiring managers.

### What You Get:
- **ATS-optimized resume** -- formatted to pass applicant tracking systems
- **Keyword optimization** -- matched to your target role/industry
- **Achievement-focused** -- quantified accomplishments, not just duties
- **Cover letter** -- personalized to company and role
- **Multiple formats** -- PDF-ready text, JSON, and plain text

### Resume Styles:
- Modern (clean, minimal, tech-friendly)
- Executive (senior leadership focus)
- Creative (design/marketing roles)
- Academic (research/education focus)

**Stand out from 300+ applicants per job posting.**""",
        "packages": {
            "Basic ($5)": "Resume rewrite -- ATS-optimized + keyword targeted",
            "Standard ($20)": "Resume + cover letter + LinkedIn summary",
            "Premium ($50)": "Resume + cover letter + LinkedIn + 3 role-specific variants",
        },
        "faq": [
            ("What do I provide?", "Your current resume or experience details + target role."),
            ("Is it ATS-friendly?", "Yes. Optimized formatting and keywords for ATS systems."),
            ("Can I target multiple roles?", "Premium package includes 3 role-specific variants."),
        ],
    },
    # ── Gig 16: Ad Copy ──
    {
        "title": "I will write high-converting ad copy for Google, Meta, and LinkedIn ads",
        "category": "Digital Marketing > Search Engine Marketing (SEM) > PPC Campaign Management",
        "tags": ["ad copy", "google ads", "facebook ads", "linkedin ads", "ppc copy", "ai ad writer", "ad copywriting"],
        "description": """## AI Ad Copy Writer

High-converting ad copy for Google Search, Meta (Facebook/Instagram), LinkedIn, and display ads.

### What You Get:
- **Platform-specific copy** -- character limits and format rules enforced
- **Multiple variants** -- 3-5 ad versions per campaign for A/B testing
- **Headline + description** -- hooks + value props + CTAs
- **Keyword alignment** -- copy matches your target keywords
- **QA-verified** -- no policy violations, no clickbait

### Ad Types:
- Google Search Ads (responsive search ads, headlines + descriptions)
- Meta Ads (primary text + headline + description)
- LinkedIn Ads (sponsored content + message ads)
- Display Ads (banner copy, responsive display)
- YouTube pre-roll scripts

**Ads that convert. Not ads that burn budget.**""",
        "packages": {
            "Basic ($5)": "1 campaign -- 5 ad variants for 1 platform",
            "Standard ($20)": "3 campaigns -- 15 variants across 2 platforms",
            "Premium ($50)": "10 campaigns -- 50 variants across all platforms + strategy notes",
        },
        "faq": [
            ("Which platforms?", "Google, Meta (Facebook/IG), LinkedIn, YouTube, Display."),
            ("Do you run the ads?", "I write copy. You handle platform setup and budget."),
            ("Can you match my brand voice?", "Yes. Send brand guidelines and I'll match tone."),
        ],
    },
    # ── Gig 17: Market Research ──
    {
        "title": "I will conduct AI-powered market research and competitive analysis",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["market research", "competitive analysis", "industry analysis", "market sizing", "ai research", "business intelligence", "market report"],
        "description": """## AI Market Research Agent

Comprehensive market research reports -- competitor analysis, market sizing, trend identification, and strategic recommendations.

### What You Get:
- **Market overview** -- size, growth rate, key players
- **Competitor analysis** -- top 5-10 competitors mapped
- **SWOT analysis** -- strengths, weaknesses, opportunities, threats
- **Trend identification** -- emerging patterns and disruptions
- **Strategic recommendations** -- actionable next steps

### Report Types:
- Market overview (industry landscape)
- Competitive analysis (head-to-head comparison)
- Market entry assessment (new market feasibility)
- Trend analysis (emerging opportunities)
- Customer analysis (segment profiling)

**Research that took weeks, delivered in minutes.**""",
        "packages": {
            "Basic ($5)": "Market snapshot -- overview + top 5 competitors + trends",
            "Standard ($25)": "Full market report -- sizing + SWOT + competitor deep-dive",
            "Premium ($75)": "Strategic report -- full analysis + recommendations + presentation",
        },
        "faq": [
            ("What industries?", "Any industry. AI adapts research to your sector."),
            ("How deep is the analysis?", "Based on publicly available data + AI synthesis."),
            ("Do you include data sources?", "Yes. All claims include source references."),
        ],
    },
    # ── Gig 18: Business Plan ──
    {
        "title": "I will write a professional business plan with financials using AI",
        "category": "Writing & Translation > Business & Marketing Copy > Business Plans & Proposals",
        "tags": ["business plan", "startup plan", "financial projections", "investor pitch", "ai business plan", "business strategy", "funding proposal"],
        "description": """## AI Business Plan Writer

Investor-ready business plans with financial projections, market analysis, and strategic roadmaps.

### What You Get:
- **Executive summary** -- elevator pitch in writing
- **Market analysis** -- TAM/SAM/SOM, competitor landscape
- **Business model** -- revenue streams, pricing strategy
- **Financial projections** -- 3-year P&L, cash flow, break-even
- **Go-to-market strategy** -- launch plan + customer acquisition
- **Team section** -- organizational structure + key hires

### Plan Types:
- Startup business plan (seed/Series A)
- Small business plan (SBA/bank loan ready)
- Growth plan (expansion/scaling strategy)
- Internal strategic plan (operational roadmap)

**The plan investors actually want to read.**""",
        "packages": {
            "Basic ($10)": "Lean plan -- executive summary + model + 1-year financials",
            "Standard ($30)": "Full plan (15-20 pages) -- market analysis + 3-year financials",
            "Premium ($75)": "Investor-ready plan + pitch deck outline + financial model spreadsheet",
        },
        "faq": [
            ("What do I provide?", "Business idea, target market, revenue model, and funding goal."),
            ("Are financials realistic?", "AI generates projections based on industry benchmarks."),
            ("Can I use this for investors?", "Yes. Formatted for investor/bank submission."),
        ],
    },
    # ── Gig 19: Press Release ──
    {
        "title": "I will write a professional press release for your announcement",
        "category": "Writing & Translation > Business & Marketing Copy > Press Releases",
        "tags": ["press release", "media release", "pr writing", "news release", "product launch", "ai press release", "media announcement"],
        "description": """## AI Press Release Writer

AP-style press releases for product launches, partnerships, funding, events, and company news.

### What You Get:
- **AP-style format** -- standard press release structure
- **Compelling headline** -- newsworthy angle that grabs attention
- **Boilerplate** -- company description paragraph
- **Quote sections** -- spokesperson quotes ready for attribution
- **Distribution-ready** -- formatted for PR Newswire, Business Wire, etc.

### Release Types:
- Product/service launch
- Partnership/collaboration announcement
- Funding/investment news
- Event announcement
- Company milestone
- Executive hire/promotion

**Newsworthy press releases in under 5 minutes.**""",
        "packages": {
            "Basic ($5)": "1 press release -- 400-600 words + boilerplate",
            "Standard ($15)": "1 press release + media pitch email + distribution guide",
            "Premium ($40)": "3 press releases + media list suggestions + pitch emails",
        },
        "faq": [
            ("What format?", "Standard AP-style press release. Distribution-ready."),
            ("Do you distribute?", "I write the release. You handle distribution (I suggest platforms)."),
            ("Can you write for my industry?", "Yes. AI adapts tone and terminology to any sector."),
        ],
    },
    # ── Gig 20: Technical Documentation ──
    {
        "title": "I will write technical documentation, API docs, and user guides using AI",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["technical writing", "api documentation", "user guide", "developer docs", "ai tech docs", "software documentation", "readme"],
        "description": """## AI Technical Documentation Agent

API references, user guides, README files, SDK docs, and developer onboarding materials -- clear, accurate, professional.

### What You Get:
- **API documentation** -- endpoints, parameters, examples, error codes
- **User guides** -- step-by-step instructions with screenshots placeholders
- **README files** -- installation, quickstart, configuration
- **SDK integration guides** -- code samples in multiple languages
- **Changelog/release notes** -- versioned update summaries

### Documentation Types:
- REST API reference
- SDK/library documentation
- User/admin guides
- Installation/deployment docs
- Architecture overviews
- Release notes / changelogs

**Documentation your developers will actually read.**""",
        "packages": {
            "Basic ($5)": "1 document (up to 2000 words) -- formatted + code samples",
            "Standard ($20)": "3 documents -- API ref + quickstart + README",
            "Premium ($60)": "Full documentation suite -- API + guides + architecture + changelog",
        },
        "faq": [
            ("What do you need?", "Source code, API specs (OpenAPI/Swagger), or raw notes."),
            ("What languages for code samples?", "Python, JavaScript, curl, and any requested language."),
            ("Do you maintain docs?", "I generate docs. You maintain. Premium includes update process."),
        ],
    },
]


# ── Freelancer.com Listing Definitions ──────────────────────────

FREELANCER_PROFILE = {
    "agency_name": "Digital Labour — AI Agent Agency",
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

I run Digital Labour — we build production AI agent pipelines (not ChatGPT wrappers).

Your project is exactly what our team does daily. We have 4 specialized agents already in production:
- Sales outreach (real-time research + personalized emails)
- Support resolution (triage + draft responses in <10s)
- Content repurposing (blog → 5 social formats)
- Document extraction (invoices/contracts → JSON)

We use GPT-4o, Claude, Gemini, and Grok with automatic failover. Every output passes through QA verification.

I can start immediately and deliver a working prototype within 48 hours.

Let's discuss your specific requirements.

— Digital Labour (Resonance Energy, Canada)""",
        "chatbot_build": """Hi,

We specialize in building AI-powered chatbots and agent systems — not simple rule-based bots, but multi-agent pipelines with real AI reasoning.

Our existing production bots handle:
- Customer support (auto-triage, severity scoring, draft responses)
- Sales qualification (company research + personalized outreach)
- Content generation (multi-platform format optimization)

Tech: Python, FastAPI, OpenAI/Claude/Gemini APIs, webhook delivery, API-first architecture.

I can deliver a working MVP within 3-5 days with full documentation.

— Digital Labour""",
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

— Digital Labour""",
    },
}


# ── Output Functions ────────────────────────────────────────────

UPWORK_PROFILE = {
    "title": "AI Automation Expert | Python Developer | GPT-4o, Claude & Gemini Integration",
    "headline": "I Build AI Agents That Replace Manual Work — Sales, Support, Content & Data Pipelines",
    "hourly_rate": "$45/hr",
    "overview": """I build AI agent systems that automate real business tasks — not chatbot demos.

My agents are live in production right now, processing thousands of tasks daily with built-in quality checks.

**Results I Deliver:**
- 50+ personalized sales emails/hour (with real company research, not templates)
- 200+ support tickets triaged/hour with draft responses
- 1 blog post → 5 platform-ready formats in under 60 seconds
- Invoices, contracts, resumes → structured data with 95%+ accuracy

**What Clients Hire Me For:**
→ Custom AI agent builds (sales outreach, lead gen, support, content)
→ Workflow automation — connect AI to your existing tools via APIs
→ Data extraction & processing pipelines (PDF, web, CSV)
→ Multi-LLM systems with failover (GPT-4o → Claude → Gemini)
→ AI-powered email marketing, SEO content, social media calendars

**Tech Stack:**
Python, FastAPI, OpenAI API, Anthropic Claude, Google Gemini, LangChain, Docker, REST APIs, Webhooks, Stripe, PostgreSQL

**Why Clients Choose Me:**
✓ Production-tested — my AI agency (Digital Labour) runs 20 specialized agents serving real clients
✓ Multi-LLM failover — if one provider goes down, another takes over instantly
✓ Every output passes automated QA before delivery — no garbage results
✓ API-first — your agents ship with REST endpoints, webhooks, and monitoring
✓ Fast turnaround — most projects delivered in 1-3 days, not weeks

**How I Work:**
1. You describe the manual process you want automated
2. I scope the agent pipeline and provide a fixed quote
3. I build, test, and deploy — you get API access + documentation
4. Optional: monthly retainer for ongoing optimization

100% Job Success Score target. Based in Canada.""",
    "skills": [
        "Artificial Intelligence", "Python", "OpenAI API", "ChatGPT",
        "Machine Learning", "Automation", "FastAPI", "API Development",
        "Web Scraping", "Data Extraction", "Natural Language Processing",
        "Chatbot Development", "LangChain", "Data Processing", "AI Chatbot",
    ],
    "portfolio_items": [
        {
            "title": "AI Sales Outreach Pipeline",
            "description": "Multi-agent system: research agent -> writer agent -> QA agent. Processes 50+ leads/hour with personalized 3-email sequences using real company signals.",
        },
        {
            "title": "AI Support Ticket Resolver",
            "description": "Automated triage + severity scoring + draft responses. Handles 200+ tickets/hour with <10s response time per ticket.",
        },
        {
            "title": "Content Repurposing Engine",
            "description": "One blog post -> 5 platform-optimized formats (LinkedIn, Twitter/X, email, Instagram, TikTok) with tone matching and character limits.",
        },
        {
            "title": "Document Extraction Agent",
            "description": "Invoice, contract, and resume parser -> structured JSON with entity extraction and confidence scoring.",
        },
        {
            "title": "AI Lead Generation System",
            "description": "ICP-matched B2B lead finder with scoring, enrichment, and CRM-ready export. 50+ qualified leads per batch.",
        },
        {
            "title": "Email Marketing Automation",
            "description": "AI-generated 5-10 email sequences -- welcome, nurture, re-engagement, launch campaigns with A/B variants.",
        },
        {
            "title": "SEO Content Pipeline",
            "description": "Keyword-researched, long-form articles with H2/H3 structure, meta descriptions, and internal linking suggestions.",
        },
        {
            "title": "Social Media Content Engine",
            "description": "30-day content calendars for 5 platforms -- LinkedIn, Twitter/X, Instagram, Facebook, TikTok with hashtag research.",
        },
        {
            "title": "AI Data Entry & Cleaning",
            "description": "Batch data processing -- deduplication, format standardization, validation for up to 50K rows.",
        },
        {
            "title": "Web Scraping Agent",
            "description": "Structured data extraction from any website -- contacts, products, listings with multi-page support.",
        },
        {
            "title": "CRM Data Operations",
            "description": "CRM cleanup, enrichment, lead scoring, and segmentation for HubSpot, Salesforce, or spreadsheet CRMs.",
        },
        {
            "title": "AI Bookkeeping Assistant",
            "description": "Transaction categorization, reconciliation, and financial summaries -- QuickBooks/Xero/CSV export ready.",
        },
        {
            "title": "Proposal Writer Agent",
            "description": "Professional business proposals, RFP responses, and grant applications with budget breakdowns and timelines.",
        },
        {
            "title": "Product Description Writer",
            "description": "Conversion-optimized product copy for Amazon, Shopify, Etsy, eBay with SEO keywords and A/B variants.",
        },
        {
            "title": "Resume & Cover Letter Writer",
            "description": "ATS-optimized resumes, targeted cover letters, and LinkedIn summaries for any industry and level.",
        },
        {
            "title": "Ad Copy Generator",
            "description": "High-converting ad copy for Google, Meta, LinkedIn, YouTube -- multiple variants per campaign for A/B testing.",
        },
        {
            "title": "Market Research Agent",
            "description": "Competitor analysis, market sizing, SWOT, trend identification with actionable strategic recommendations.",
        },
        {
            "title": "Business Plan Writer",
            "description": "Investor-ready business plans with 3-year financials, market analysis, go-to-market strategy.",
        },
        {
            "title": "Press Release Writer",
            "description": "AP-style press releases for product launches, partnerships, funding -- distribution-ready format.",
        },
        {
            "title": "Technical Documentation Agent",
            "description": "API references, user guides, README files, SDK docs with code samples in multiple languages.",
        },
    ],
    "specialized_profiles": [
        {
            "category": "AI & Machine Learning",
            "title": "AI Agent Developer -- Production Multi-Agent Systems",
            "skills": ["Python", "OpenAI API", "FastAPI", "NLP", "Chatbot Development"],
        },
        {
            "category": "Sales & Marketing Automation",
            "title": "AI Sales Automation Specialist -- Outreach & Lead Generation",
            "skills": ["Sales Automation", "Lead Generation", "Cold Email", "CRM Integration"],
        },
        {
            "category": "Content & SEO",
            "title": "AI Content Writer -- SEO, Social Media, Email Marketing",
            "skills": ["SEO Writing", "Content Marketing", "Social Media", "Email Marketing"],
        },
        {
            "category": "Data Processing & Analysis",
            "title": "AI Data Processing -- Extraction, Cleaning, Scraping",
            "skills": ["Data Entry", "Web Scraping", "Data Cleaning", "Document Processing"],
        },
        {
            "category": "Business Writing",
            "title": "AI Business Writer -- Proposals, Plans, Press Releases",
            "skills": ["Business Plan Writing", "Proposal Writing", "Press Release Writing", "Technical Writing"],
        },
    ],
    "service_catalog": [
        {
            "agent": "sales_ops",
            "service_title": "AI Sales Outreach Sequences",
            "description": "Personalized 3-email outreach sequences using real-time company research and signal detection.",
            "fixed_price": "$25-500",
            "delivery": "Same day",
        },
        {
            "agent": "support",
            "service_title": "AI Support Ticket Resolution",
            "description": "Automated ticket triage, severity scoring, and draft response generation.",
            "fixed_price": "$20-200",
            "delivery": "Same day",
        },
        {
            "agent": "content_repurpose",
            "service_title": "Content Repurposing (Blog to Social)",
            "description": "Transform one content piece into 5 platform-optimized versions.",
            "fixed_price": "$15-250",
            "delivery": "Same day",
        },
        {
            "agent": "doc_extract",
            "service_title": "Document Data Extraction",
            "description": "Extract structured data from invoices, contracts, resumes into JSON/CSV.",
            "fixed_price": "$15-200",
            "delivery": "Same day",
        },
        {
            "agent": "lead_gen",
            "service_title": "B2B Lead Generation & Scoring",
            "description": "ICP-matched lead lists with scoring, enrichment, and CRM-ready export.",
            "fixed_price": "$25-500",
            "delivery": "1-2 days",
        },
        {
            "agent": "email_marketing",
            "service_title": "Email Marketing Sequence Builder",
            "description": "Complete email campaigns -- welcome, nurture, launch, re-engagement.",
            "fixed_price": "$20-300",
            "delivery": "Same day",
        },
        {
            "agent": "seo_content",
            "service_title": "SEO Blog Posts & Articles",
            "description": "Keyword-optimized long-form content with meta descriptions and internal linking.",
            "fixed_price": "$15-300",
            "delivery": "Same day",
        },
        {
            "agent": "social_media",
            "service_title": "Social Media Content Calendar",
            "description": "30 days of platform-optimized posts for LinkedIn, Twitter/X, Instagram, Facebook, TikTok.",
            "fixed_price": "$20-250",
            "delivery": "Same day",
        },
        {
            "agent": "data_entry",
            "service_title": "Data Entry & Cleaning",
            "description": "Batch data processing -- cleaning, deduplication, format standardization.",
            "fixed_price": "$10-200",
            "delivery": "Same day",
        },
        {
            "agent": "web_scraper",
            "service_title": "Web Data Extraction",
            "description": "Structured data scraping from websites -- contacts, products, listings.",
            "fixed_price": "$15-250",
            "delivery": "1-2 days",
        },
        {
            "agent": "crm_ops",
            "service_title": "CRM Data Optimization",
            "description": "CRM cleanup, enrichment, lead scoring, and segmentation.",
            "fixed_price": "$20-250",
            "delivery": "1-2 days",
        },
        {
            "agent": "bookkeeping",
            "service_title": "Transaction Categorization & Reconciliation",
            "description": "Expense categorization, reconciliation, and financial summaries.",
            "fixed_price": "$15-250",
            "delivery": "Same day",
        },
        {
            "agent": "proposal_writer",
            "service_title": "Business Proposal & RFP Writing",
            "description": "Professional proposals with scope, budget, timeline, and team sections.",
            "fixed_price": "$25-300",
            "delivery": "1-2 days",
        },
        {
            "agent": "product_desc",
            "service_title": "E-commerce Product Descriptions",
            "description": "Conversion-optimized product copy for Amazon, Shopify, Etsy, eBay.",
            "fixed_price": "$10-250",
            "delivery": "Same day",
        },
        {
            "agent": "resume_writer",
            "service_title": "Resume & Cover Letter Writing",
            "description": "ATS-optimized resumes, cover letters, and LinkedIn profiles.",
            "fixed_price": "$15-250",
            "delivery": "Same day",
        },
        {
            "agent": "ad_copy",
            "service_title": "Ad Copy for Google, Meta & LinkedIn",
            "description": "High-converting ad variants for PPC, social ads, and display campaigns.",
            "fixed_price": "$15-250",
            "delivery": "Same day",
        },
        {
            "agent": "market_research",
            "service_title": "Market Research & Competitive Analysis",
            "description": "Market sizing, competitor mapping, SWOT analysis, trend reports.",
            "fixed_price": "$25-500",
            "delivery": "1-3 days",
        },
        {
            "agent": "business_plan",
            "service_title": "Business Plan with Financials",
            "description": "Investor-ready business plans with 3-year projections and go-to-market strategy.",
            "fixed_price": "$50-500",
            "delivery": "2-5 days",
        },
        {
            "agent": "press_release",
            "service_title": "Press Release Writing",
            "description": "AP-style press releases for launches, partnerships, funding announcements.",
            "fixed_price": "$15-200",
            "delivery": "Same day",
        },
        {
            "agent": "tech_docs",
            "service_title": "Technical Documentation & API Docs",
            "description": "API references, user guides, README files, SDK docs with code samples.",
            "fixed_price": "$25-300",
            "delivery": "1-3 days",
        },
    ],
}


# ── PeoplePerHour Profile ──────────────────────────────────────

PEOPLEPERHOUR_PROFILE = {
    "agency_name": "Digital Labour",
    "tagline": "AI Agent Agency -- 20 Specialized Agents for Business Automation",
    "hourly_rate": "GBP60-150/hr",
    "about": """We deploy production AI agent pipelines for sales, content, data, and business operations.

20 specialized agents covering: sales outreach, support tickets, content repurposing, document extraction, lead generation, email marketing, SEO content, social media, data entry, web scraping, CRM operations, bookkeeping, proposal writing, product descriptions, resume writing, ad copy, market research, business plans, press releases, and technical documentation.

Multi-LLM architecture (GPT-4o, Claude, Gemini, Grok) with QA verification on every output. Built by Resonance Energy, Canada.""",
    "hourlies": [
        {
            "title": "AI Sales Outreach -- Personalized Email Sequences",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "1 company researched + 3-email personalized outreach sequence + JSON export. Real-time company signals, not templates.",
        },
        {
            "title": "AI Content Repurposing -- Blog to 5 Social Formats",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "Transform 1 blog post into LinkedIn, Twitter/X, email newsletter, Instagram caption, and TikTok script.",
        },
        {
            "title": "AI SEO Blog Post (1500 words)",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "Keyword-optimized blog post with meta description, H2/H3 structure, and internal linking suggestions.",
        },
        {
            "title": "AI Resume Rewrite -- ATS Optimized",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "ATS-optimized resume rewrite with keyword targeting for your specific role and industry.",
        },
        {
            "title": "AI Product Descriptions (5 products)",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "5 conversion-optimized product descriptions for Amazon, Shopify, Etsy, or eBay.",
        },
        {
            "title": "AI Ad Copy -- 5 Variants for Any Platform",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "5 high-converting ad copy variants for Google, Meta, LinkedIn, or YouTube.",
        },
        {
            "title": "AI Data Cleaning -- Up to 500 Rows",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "Clean, deduplicate, and standardize up to 500 rows of data. CSV/JSON export.",
        },
        {
            "title": "AI Document Extraction -- 5 Documents",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "Extract structured data from 5 invoices, contracts, or resumes into JSON.",
        },
        {
            "title": "AI Press Release Writing",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "AP-style press release for product launches, partnerships, or company news.",
        },
        {
            "title": "AI Business Proposal (2-3 pages)",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "Professional business proposal with executive summary, scope, and pricing.",
        },
        # ── 11-20: Remaining agents ────────────────────────────
        {
            "title": "AI Support Ticket Triage & Draft Responses",
            "agent": "support",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "5 support tickets triaged with severity scoring + draft responses + escalation flags. Works with any helpdesk.",
        },
        {
            "title": "AI Lead Generation -- 10 Qualified B2B Leads",
            "agent": "lead_gen",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "10 ICP-matched B2B leads with company size, tech stack, funding signals, and decision-maker contacts.",
        },
        {
            "title": "AI Email Marketing -- 5-Email Sequence",
            "agent": "email_marketing",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "Complete 5-email sequence (welcome, nurture, or launch) with subject lines, preview text, and CTAs.",
        },
        {
            "title": "AI Social Media Calendar -- 7 Days, 5 Platforms",
            "agent": "social_media",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "7-day content calendar for LinkedIn, Twitter/X, Instagram, Facebook, TikTok with hashtag research.",
        },
        {
            "title": "AI Web Scraping -- Extract Data from Any Website",
            "agent": "web_scraper",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "Scrape structured data from up to 5 URLs -- contacts, products, listings. JSON/CSV output.",
        },
        {
            "title": "AI CRM Cleanup & Lead Scoring",
            "agent": "crm_ops",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "Clean, deduplicate, and score up to 200 CRM contacts. Segmentation tags included.",
        },
        {
            "title": "AI Bookkeeping -- Transaction Categorization",
            "agent": "bookkeeping",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "Categorize up to 100 transactions with reconciliation notes. QuickBooks/Xero/CSV export.",
        },
        {
            "title": "AI Market Research Report",
            "agent": "market_research",
            "price": "GBP10",
            "delivery": "2 days",
            "description": "Competitor analysis, market sizing, SWOT, and trend report with actionable recommendations.",
        },
        {
            "title": "AI Business Plan with Financials",
            "agent": "business_plan",
            "price": "GBP15",
            "delivery": "3 days",
            "description": "Investor-ready business plan with executive summary, market analysis, and 3-year financial projections.",
        },
        {
            "title": "AI Technical Documentation & API Docs",
            "agent": "tech_docs",
            "price": "GBP5",
            "delivery": "1 day",
            "description": "API reference, user guide, or README with code samples. Markdown or HTML output.",
        },
    ],
}


# ── Guru Profile ────────────────────────────────────────────────

GURU_PROFILE = {
    "agency_name": "Digital Labour -- AI Agent Agency",
    "tagline": "20 AI Agents for Sales, Content, Data & Business Automation",
    "hourly_rate": "$75-175/hr",
    "about": """Production AI agent agency with 20 specialized agents covering every major business automation category.

Our agents don't just generate text -- they run multi-step pipelines with research, generation, QA verification, and structured output. Every deliverable passes quality gates before reaching you.

Services: Sales outreach, support resolution, content repurposing, document extraction, lead generation, email marketing, SEO content, social media management, data entry/cleaning, web scraping, CRM operations, bookkeeping, proposal writing, product descriptions, resume/CV writing, ad copy, market research, business plans, press releases, technical documentation.

Tech: Python, FastAPI, GPT-4o, Claude, Gemini, Grok. Multi-LLM with failover.
Location: Canada | Agency: Resonance Energy""",
    "skills": [
        "Artificial Intelligence", "Python", "Machine Learning",
        "Data Extraction", "Content Writing", "Sales Automation",
        "SEO", "Chatbot Development", "API Development",
        "Business Analysis", "Technical Writing", "Ad Copywriting",
    ],
    "service_listings": [
        {
            "agent": "sales_ops",
            "title": "AI Sales Outreach Pipeline",
            "category": "Programming & Development",
            "price": "$25-500",
            "description": "Personalized 3-email sequences with real-time company research. 50+ leads/hour.",
        },
        {
            "agent": "support",
            "title": "AI Support Ticket Resolution",
            "category": "Programming & Development",
            "price": "$20-200",
            "description": "Ticket triage, severity scoring, draft responses in <10s. Any helpdesk.",
        },
        {
            "agent": "content_repurpose",
            "title": "AI Content Repurposing",
            "category": "Writing & Translation",
            "price": "$15-250",
            "description": "Blog -> LinkedIn + Twitter + Email + Instagram + TikTok. 5 formats from 1 piece.",
        },
        {
            "agent": "doc_extract",
            "title": "AI Document Data Extraction",
            "category": "Admin Support",
            "price": "$15-200",
            "description": "Invoices, contracts, resumes -> structured JSON/CSV with confidence scores.",
        },
        {
            "agent": "lead_gen",
            "title": "AI B2B Lead Generation",
            "category": "Sales & Marketing",
            "price": "$25-500",
            "description": "ICP-matched leads with scoring, enrichment, and CRM-ready export.",
        },
        {
            "agent": "email_marketing",
            "title": "AI Email Marketing Sequences",
            "category": "Sales & Marketing",
            "price": "$20-300",
            "description": "Welcome, nurture, launch, re-engagement sequences with A/B subject lines.",
        },
        {
            "agent": "seo_content",
            "title": "AI SEO Content Writing",
            "category": "Writing & Translation",
            "price": "$15-300",
            "description": "Keyword-optimized blog posts, articles, and pillar pages. 1500-5000 words.",
        },
        {
            "agent": "social_media",
            "title": "AI Social Media Content Calendar",
            "category": "Sales & Marketing",
            "price": "$20-250",
            "description": "30-day calendars for 5 platforms with hashtag research and engagement hooks.",
        },
        {
            "agent": "data_entry",
            "title": "AI Data Entry & Cleaning",
            "category": "Admin Support",
            "price": "$10-200",
            "description": "Data cleaning, deduplication, standardization -- up to 50K rows per batch.",
        },
        {
            "agent": "web_scraper",
            "title": "AI Web Scraping & Data Mining",
            "category": "Programming & Development",
            "price": "$15-250",
            "description": "Structured extraction from any website -- contacts, products, pricing, listings.",
        },
        {
            "agent": "crm_ops",
            "title": "AI CRM Data Operations",
            "category": "Admin Support",
            "price": "$20-250",
            "description": "CRM cleanup, enrichment, lead scoring, segmentation for any CRM.",
        },
        {
            "agent": "bookkeeping",
            "title": "AI Bookkeeping & Reconciliation",
            "category": "Finance & Management",
            "price": "$15-250",
            "description": "Transaction categorization, reconciliation, financial summaries. QBO/Xero/CSV.",
        },
        {
            "agent": "proposal_writer",
            "title": "AI Proposal & RFP Writing",
            "category": "Writing & Translation",
            "price": "$25-300",
            "description": "Business proposals, RFP responses, grant applications with timelines and budgets.",
        },
        {
            "agent": "product_desc",
            "title": "AI Product Descriptions",
            "category": "Writing & Translation",
            "price": "$10-250",
            "description": "Conversion-optimized copy for Amazon, Shopify, Etsy, eBay with SEO keywords.",
        },
        {
            "agent": "resume_writer",
            "title": "AI Resume & Cover Letter Writing",
            "category": "Writing & Translation",
            "price": "$15-250",
            "description": "ATS-optimized resumes, cover letters, LinkedIn summaries for any industry.",
        },
        {
            "agent": "ad_copy",
            "title": "AI Ad Copy -- Google, Meta, LinkedIn",
            "category": "Sales & Marketing",
            "price": "$15-250",
            "description": "High-converting ad variants for PPC, social, display. Multiple A/B options.",
        },
        {
            "agent": "market_research",
            "title": "AI Market Research & Competitive Analysis",
            "category": "Business & Management",
            "price": "$25-500",
            "description": "Competitor analysis, market sizing, SWOT, financial projections.",
        },
        {
            "agent": "business_plan",
            "title": "AI Business Plan with Financials",
            "category": "Business & Management",
            "price": "$50-500",
            "description": "Investor-ready plans with 3-year projections, market analysis, GTM strategy.",
        },
        {
            "agent": "press_release",
            "title": "AI Press Release Writing",
            "category": "Writing & Translation",
            "price": "$15-200",
            "description": "AP-style press releases for launches, partnerships, funding. Distribution-ready.",
        },
        {
            "agent": "tech_docs",
            "title": "AI Technical Documentation",
            "category": "Programming & Development",
            "price": "$25-300",
            "description": "API references, user guides, README, SDK docs with code samples.",
        },
    ],
}


# ── Toptal Profile ──────────────────────────────────────────────

TOPTAL_PROFILE = {
    "agency_name": "Digital Labour (Resonance Energy)",
    "vertical": "AI & Machine Learning",
    "hourly_rate": "$100-250/hr",
    "engagement_types": ["Hourly", "Part-time", "Full-time"],
    "headline": "AI Agent Systems Architect -- Production Multi-Agent Pipelines",
    "bio": """I architect and deploy production AI agent systems for businesses -- multi-agent pipelines with research, generation, QA, and delivery stages.

Currently operating 20 specialized AI agents in production serving paying clients across sales automation, content generation, data processing, and business intelligence.

Key differentiators:
- Multi-LLM architecture (GPT-4o, Claude, Gemini, Grok) with automatic failover
- Every output passes through automated QA verification before delivery
- API-first FastAPI architecture with webhook delivery and Stripe billing
- Sub-60-second delivery on most agent tasks

Technical depth: Python, FastAPI, OpenAI/Anthropic/Google/xAI APIs, Pydantic data models, multi-agent orchestration, Docker, CI/CD. I build systems that run autonomously in production, not demos.

Based in Canada. Founded Resonance Energy -- building the intersection of AI, energy, and autonomous systems.""",
    "skills": [
        "Python", "FastAPI", "OpenAI API", "Anthropic Claude",
        "Multi-Agent Systems", "NLP", "Machine Learning",
        "System Architecture", "API Design", "Docker",
    ],
    "project_types": [
        {"agent": "sales_ops", "title": "AI Sales Outreach Pipeline", "rate": "$150-250/hr",
         "description": "Multi-agent sales research + personalized email sequences at scale."},
        {"agent": "support", "title": "AI Support Resolution System", "rate": "$125-200/hr",
         "description": "Automated ticket triage, severity scoring, and draft response generation."},
        {"agent": "content_repurpose", "title": "Content Repurposing Engine", "rate": "$100-175/hr",
         "description": "Transform one content piece into 5 platform-optimized formats."},
        {"agent": "doc_extract", "title": "Document Extraction Pipeline", "rate": "$125-200/hr",
         "description": "Invoice, contract, resume parsing into structured JSON with confidence scores."},
        {"agent": "lead_gen", "title": "B2B Lead Generation System", "rate": "$150-250/hr",
         "description": "ICP-matched lead research with scoring, enrichment, and CRM integration."},
        {"agent": "email_marketing", "title": "Email Marketing Automation", "rate": "$100-175/hr",
         "description": "AI-generated campaign sequences with A/B variants and performance optimization."},
        {"agent": "seo_content", "title": "SEO Content Pipeline", "rate": "$100-175/hr",
         "description": "Keyword-researched long-form articles with semantic structure and internal linking."},
        {"agent": "social_media", "title": "Social Media Content Engine", "rate": "$100-175/hr",
         "description": "Multi-platform content calendars with engagement optimization and hashtag strategy."},
        {"agent": "data_entry", "title": "Data Processing & Migration", "rate": "$100-150/hr",
         "description": "Large-scale data cleaning, deduplication, format standardization up to 50K rows."},
        {"agent": "web_scraper", "title": "Web Data Extraction System", "rate": "$125-200/hr",
         "description": "Custom scrapers for contacts, products, pricing, or listings from any website."},
        {"agent": "crm_ops", "title": "CRM Data Optimization", "rate": "$125-200/hr",
         "description": "CRM cleanup, enrichment, lead scoring, and advanced segmentation."},
        {"agent": "bookkeeping", "title": "AI Bookkeeping & Financial Processing", "rate": "$100-175/hr",
         "description": "Transaction categorization, reconciliation, and financial summary generation."},
        {"agent": "proposal_writer", "title": "Proposal & RFP Automation", "rate": "$125-200/hr",
         "description": "AI-generated business proposals, RFP responses, and grant applications."},
        {"agent": "product_desc", "title": "E-commerce Product Copy Engine", "rate": "$100-150/hr",
         "description": "Conversion-optimized product descriptions for all major marketplaces."},
        {"agent": "resume_writer", "title": "Resume & Career Document System", "rate": "$100-150/hr",
         "description": "ATS-optimized resumes, cover letters, and LinkedIn profiles at scale."},
        {"agent": "ad_copy", "title": "Ad Copy Generation Engine", "rate": "$125-200/hr",
         "description": "Multi-variant ad copy for Google, Meta, LinkedIn with performance targeting."},
        {"agent": "market_research", "title": "Market Intelligence & Analysis", "rate": "$150-250/hr",
         "description": "Competitor mapping, market sizing, SWOT, trend analysis with strategic recommendations."},
        {"agent": "business_plan", "title": "Business Plan Automation", "rate": "$150-250/hr",
         "description": "Investor-ready plans with financials, market validation, and go-to-market strategy."},
        {"agent": "press_release", "title": "Press Release Pipeline", "rate": "$100-175/hr",
         "description": "AP-style press releases for launches, funding, partnerships. Distribution-ready."},
        {"agent": "tech_docs", "title": "Technical Documentation System", "rate": "$125-200/hr",
         "description": "API references, user guides, SDK docs with code samples in multiple languages."},
    ],
    "note": "Toptal requires screening -- apply at toptal.com/talent/apply. This profile is for post-acceptance use.",
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
