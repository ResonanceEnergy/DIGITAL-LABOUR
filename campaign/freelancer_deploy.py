"""Freelancer.com Full Deployment Config — 20 gig listings + bid templates.

Maps every agent to a Freelancer service listing with:
- Gig title, description, skills, pricing packages, delivery times
- Ready-to-send bid templates per service category
- Agent routing (which runner handles which gig type)
- Keyword matching for autobidding

Usage:
    python -m campaign.freelancer_deploy                 # Print all listings
    python -m campaign.freelancer_deploy --gigs          # Gig listings only
    python -m campaign.freelancer_deploy --bids          # Bid templates only
    python -m campaign.freelancer_deploy --save          # Save to JSON files
    python -m campaign.freelancer_deploy --agent sales   # Show specific agent
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "output" / "freelancer_deploy"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENCY PROFILE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AGENCY_PROFILE = {
    "name": "Digital Labour — AI Agent Agency",
    "tagline": "20 production AI agents. Sales, content, research, docs — delivered in minutes, not days.",
    "hourly_rate_range": "$50-200/hr",
    "fixed_price_range": "$25-2,000",
    "location": "Canada",
    "parent": "Resonance Energy",
    "skills_master": [
        "Artificial Intelligence", "Machine Learning", "Python",
        "OpenAI API", "Natural Language Processing", "Content Writing",
        "Data Entry", "Data Processing", "Web Scraping", "SEO",
        "Email Marketing", "Sales Automation", "CRM", "Bookkeeping",
        "Resume Writing", "Business Plans", "Market Research",
        "Technical Writing", "Copywriting", "Press Releases",
        "Document Processing", "Lead Generation", "Social Media",
        "Ad Copy", "PPC", "Proposal Writing", "API Development",
    ],
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  20 GIG LISTINGS — One per agent
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FREELANCER_GIGS = [
    # ── 1. Sales Outreach ───────────────────────────────────────
    {
        "id": "sales_outreach",
        "agent": "sales_ops",
        "title": "AI-Powered Cold Email & Sales Outreach Sequences",
        "category": "Sales / Lead Generation",
        "skills": ["Cold Email", "Sales", "Lead Generation", "B2B Marketing", "AI"],
        "description": (
            "I build hyper-personalized cold email sequences using an AI agent pipeline "
            "that researches your prospect in real-time — funding rounds, hiring signals, "
            "product launches, tech stack — then crafts a 3-email outreach sequence "
            "referencing those specific signals.\n\n"
            "NOT templates. NOT ChatGPT in a wrapper. A multi-agent pipeline: "
            "Research Agent -> Writer Agent -> QA Agent. Every email passes quality verification "
            "before delivery.\n\n"
            "Deliverables:\n"
            "• Deep company research with real-time signals\n"
            "• 3-email personalized sequence (intro, follow-up, break-up)\n"
            "• CRM-ready export (JSON + CSV)\n"
            "• QA verification on every output\n\n"
            "Average delivery: Under 60 seconds per lead."
        ),
        "packages": {
            "Starter — $25": {"leads": 5, "emails_per": 3, "delivery": "Same day"},
            "Growth — $75": {"leads": 20, "emails_per": 3, "delivery": "24 hours"},
            "Scale — $200": {"leads": 50, "emails_per": 5, "delivery": "48 hours"},
        },
        "keywords": ["cold email", "outreach", "sales email", "lead generation email",
                      "b2b email", "sales sequence", "email campaign", "prospecting"],
    },
    # ── 2. Support Ticket Resolution ────────────────────────────
    {
        "id": "support_ticket",
        "agent": "support",
        "title": "AI Customer Support — Ticket Triage & Draft Responses",
        "category": "Customer Service / Virtual Assistant",
        "skills": ["Customer Support", "Help Desk", "Ticket Resolution", "AI", "Automation"],
        "description": (
            "I process support tickets through an AI agent pipeline that triages, "
            "scores severity (1-5), and drafts ready-to-send responses — all in under 10 seconds.\n\n"
            "Deliverables:\n"
            "• Ticket classification (billing, technical, account, general)\n"
            "• Severity scoring with escalation flags\n"
            "• Draft response with confidence score\n"
            "• Policy compliance check\n"
            "• Structured JSON export for helpdesk integration\n\n"
            "Works with any helpdesk: Zendesk, Freshdesk, Intercom, or plain email."
        ),
        "packages": {
            "Starter — $20": {"tickets": 25, "delivery": "Same day"},
            "Business — $50": {"tickets": 100, "delivery": "24 hours"},
            "Enterprise — $150": {"tickets": 500, "delivery": "48 hours"},
        },
        "keywords": ["customer support", "help desk", "ticket resolution", "support agent",
                      "customer service", "ticket triage", "helpdesk", "zendesk"],
    },
    # ── 3. Content Repurposing ──────────────────────────────────
    {
        "id": "content_repurpose",
        "agent": "content_repurpose",
        "title": "AI Content Repurposing — Blog to 5 Social Media Formats",
        "category": "Content Writing / Social Media",
        "skills": ["Content Writing", "Social Media", "Content Marketing", "Copywriting", "AI"],
        "description": (
            "Send me one blog post or article — I'll transform it into 5 platform-optimized "
            "content pieces using a multi-agent AI pipeline.\n\n"
            "You get:\n"
            "• LinkedIn post — professional tone, hashtags, engagement hooks\n"
            "• Twitter/X thread — under 280 chars/tweet, threaded format\n"
            "• Email newsletter — subject line + body, ready to send\n"
            "• Instagram caption — emoji-rich, hashtag-optimized\n"
            "• TikTok/Reels script — spoken format, hooks, CTAs\n\n"
            "AI analyzes tone, extracts key points, then generates each format "
            "respecting platform-specific rules. QA verified."
        ),
        "packages": {
            "Starter — $15": {"posts": 1, "formats": 5, "delivery": "Same day"},
            "Standard — $50": {"posts": 5, "formats": 5, "delivery": "24 hours"},
            "Bulk — $120": {"posts": 15, "formats": 5, "delivery": "48 hours"},
        },
        "keywords": ["content repurposing", "blog to social", "content marketing",
                      "social media content", "repurpose content", "content creation"],
    },
    # ── 4. Document Extraction ──────────────────────────────────
    {
        "id": "doc_extract",
        "agent": "doc_extract",
        "title": "AI Document Data Extraction — Invoices, Contracts, Resumes to JSON",
        "category": "Data Entry / Data Processing",
        "skills": ["Data Extraction", "Data Entry", "Document Processing", "AI", "Python"],
        "description": (
            "Send invoices, contracts, or resumes — get clean, structured JSON data back.\n\n"
            "Deliverables:\n"
            "• Entity extraction — names, dates, amounts, addresses, line items\n"
            "• Auto document classification (invoice, contract, resume, receipt)\n"
            "• Structured JSON + CSV output, database-ready\n"
            "• Confidence scores on every extracted field\n"
            "• QA verification before delivery\n\n"
            "Handles invoices (line items, tax, totals), contracts (parties, dates, "
            "clauses), resumes (experience, skills, education), and receipts."
        ),
        "packages": {
            "Starter — $15": {"documents": 10, "delivery": "Same day"},
            "Standard — $40": {"documents": 50, "delivery": "24 hours"},
            "Bulk — $100": {"documents": 200, "delivery": "48 hours"},
        },
        "keywords": ["data extraction", "document processing", "invoice processing",
                      "contract analysis", "data entry", "pdf extraction", "ocr"],
    },
    # ── 5. Lead Generation ──────────────────────────────────────
    {
        "id": "lead_gen",
        "agent": "lead_gen",
        "title": "AI B2B Lead Generation — Scored & Qualified Lead Lists",
        "category": "Lead Generation / Research",
        "skills": ["Lead Generation", "B2B", "Market Research", "Sales", "AI"],
        "description": (
            "I build targeted B2B lead lists using an AI research agent that identifies, "
            "scores, and qualifies prospects based on your ideal customer profile.\n\n"
            "Deliverables:\n"
            "• Company name, website, industry, size, location\n"
            "• Decision-maker contacts (name, title, email pattern)\n"
            "• Lead score (1-100) based on ICP fit\n"
            "• Buying signals and pain point analysis\n"
            "• Recommended approach angle per lead\n"
            "• CSV + JSON export, CRM-ready\n\n"
            "Not scraped junk. Each lead is researched and scored against your ICP."
        ),
        "packages": {
            "Starter — $30": {"leads": 25, "delivery": "24 hours"},
            "Growth — $75": {"leads": 75, "delivery": "48 hours"},
            "Scale — $175": {"leads": 200, "delivery": "72 hours"},
        },
        "keywords": ["lead generation", "b2b leads", "prospect list", "lead research",
                      "qualified leads", "lead list", "sales leads", "prospecting"],
    },
    # ── 6. Email Marketing ──────────────────────────────────────
    {
        "id": "email_marketing",
        "agent": "email_marketing",
        "title": "AI Email Marketing Campaigns — Full Sequences with A/B Copy",
        "category": "Email Marketing / Copywriting",
        "skills": ["Email Marketing", "Copywriting", "Marketing Automation", "AI", "Mailchimp"],
        "description": (
            "I build complete email marketing sequences — welcome series, nurture campaigns, "
            "re-engagement, promotional, and cart abandonment — using an AI copywriting agent.\n\n"
            "Deliverables:\n"
            "• 5-7 email sequence (subject lines + body copy)\n"
            "• A/B variations for subject lines\n"
            "• Send timing recommendations\n"
            "• Segmentation suggestions\n"
            "• Merge tag placeholders (works with Mailchimp, Klaviyo, etc.)\n"
            "• QA verified for spam triggers, readability, CTA clarity\n\n"
            "Every email follows proven frameworks: AIDA, PAS, BAB."
        ),
        "packages": {
            "Starter — $25": {"emails": 3, "variations": 1, "delivery": "Same day"},
            "Standard — $60": {"emails": 5, "variations": 2, "delivery": "24 hours"},
            "Premium — $150": {"emails": 7, "variations": 3, "delivery": "48 hours"},
        },
        "keywords": ["email marketing", "email sequence", "email campaign", "drip campaign",
                      "newsletter", "email copywriting", "mailchimp", "klaviyo"],
    },
    # ── 7. SEO Content Writing ──────────────────────────────────
    {
        "id": "seo_content",
        "agent": "seo_content",
        "title": "AI SEO Blog Posts & Articles — Keyword-Optimized, Publish-Ready",
        "category": "SEO / Content Writing",
        "skills": ["SEO", "Content Writing", "Blog Writing", "Keyword Research", "AI"],
        "description": (
            "I produce SEO-optimized blog posts and articles using a 3-stage AI pipeline: "
            "Keyword Research -> Content Writing -> QA Verification.\n\n"
            "Deliverables:\n"
            "• Primary + secondary keyword targeting\n"
            "• SEO title tag (≤60 chars) + meta description (≤155 chars)\n"
            "• H1/H2/H3 heading structure\n"
            "• 1,500-3,000 word articles (your choice)\n"
            "• Internal linking suggestions\n"
            "• Markdown + HTML export\n"
            "• Readability score (Flesch-Kincaid)\n\n"
            "No fluff. No keyword stuffing. Natural, authoritative content "
            "that ranks AND converts."
        ),
        "packages": {
            "Starter — $25": {"articles": 1, "words": "1,500", "delivery": "Same day"},
            "Standard — $75": {"articles": 3, "words": "2,000", "delivery": "48 hours"},
            "Bulk — $200": {"articles": 10, "words": "2,000", "delivery": "5 days"},
        },
        "keywords": ["seo content", "blog writing", "seo article", "content writing",
                      "keyword research", "blog post", "seo copywriting", "article writing"],
    },
    # ── 8. Social Media Content ─────────────────────────────────
    {
        "id": "social_media",
        "agent": "social_media",
        "title": "AI Social Media Content — Posts for LinkedIn, Twitter, Instagram & More",
        "category": "Social Media Marketing / Content",
        "skills": ["Social Media", "Content Creation", "Copywriting", "LinkedIn", "Instagram"],
        "description": (
            "I generate platform-optimized social media content using an AI strategist agent "
            "that understands character limits, hashtag best practices, and engagement patterns.\n\n"
            "Deliverables per post:\n"
            "• Platform-specific copy (LinkedIn, Twitter/X, Instagram, Facebook, TikTok)\n"
            "• Hashtag recommendations (mix of broad + niche)\n"
            "• Posting time suggestions\n"
            "• CTA options\n"
            "• Image/visual direction notes\n"
            "• Content calendar format\n\n"
            "Consistent brand voice across all platforms. QA verified."
        ),
        "packages": {
            "Starter — $20": {"posts": 10, "platforms": 2, "delivery": "Same day"},
            "Standard — $55": {"posts": 30, "platforms": 3, "delivery": "48 hours"},
            "Bulk — $130": {"posts": 60, "platforms": 5, "delivery": "5 days"},
        },
        "keywords": ["social media posts", "social media content", "linkedin posts",
                      "instagram captions", "social media marketing", "content calendar"],
    },
    # ── 9. Data Entry & Processing ──────────────────────────────
    {
        "id": "data_entry",
        "agent": "data_entry",
        "title": "AI Data Entry & Data Cleaning — Structured, Accurate, Fast",
        "category": "Data Entry / Data Processing",
        "skills": ["Data Entry", "Data Processing", "Data Cleaning", "Excel", "CSV"],
        "description": (
            "I process and clean raw data — messy spreadsheets, unstructured text, PDFs — "
            "and deliver clean, structured output using an AI data processing agent.\n\n"
            "Deliverables:\n"
            "• Data standardization (dates, names, addresses, currencies)\n"
            "• Duplicate detection and removal\n"
            "• Missing value handling (flagged or imputed)\n"
            "• Format conversion (CSV, JSON, Excel)\n"
            "• Validation report with error counts\n"
            "• QA verification on accuracy\n\n"
            "Handles: contact lists, product catalogs, survey data, spreadsheet cleanup, "
            "form submissions, and any tabular data."
        ),
        "packages": {
            "Starter — $15": {"rows": 200, "delivery": "Same day"},
            "Standard — $40": {"rows": 1000, "delivery": "24 hours"},
            "Bulk — $100": {"rows": 5000, "delivery": "48 hours"},
        },
        "keywords": ["data entry", "data cleaning", "data processing", "spreadsheet",
                      "excel data entry", "csv processing", "data formatting", "data migration"],
    },
    # ── 10. Web Scraping ────────────────────────────────────────
    {
        "id": "web_scraper",
        "agent": "web_scraper",
        "title": "AI Web Scraping — Structured Data from Any Website",
        "category": "Web Scraping / Data Mining",
        "skills": ["Web Scraping", "Data Mining", "Python", "Data Extraction", "Automation"],
        "description": (
            "I extract structured data from web pages — product listings, contact info, "
            "directories, job boards, real estate listings — using an AI extraction agent.\n\n"
            "Deliverables:\n"
            "• Structured data in JSON + CSV\n"
            "• Field mapping (name, price, URL, email, phone, etc.)\n"
            "• Data quality scoring\n"
            "• Duplicate removal\n"
            "• QA validation report\n\n"
            "Send me the page content or URL and tell me what data you need. "
            "I handle the extraction and deliver clean, structured output.\n\n"
            "Note: I extract data from provided content. For recurring scraping "
            "or live crawling, ask about custom automation."
        ),
        "packages": {
            "Starter — $20": {"pages": 10, "delivery": "Same day"},
            "Standard — $60": {"pages": 50, "delivery": "24 hours"},
            "Bulk — $150": {"pages": 200, "delivery": "48 hours"},
        },
        "keywords": ["web scraping", "data scraping", "data mining", "data extraction",
                      "web data", "screen scraping", "web crawler", "price scraping"],
    },
    # ── 11. CRM Management ──────────────────────────────────────
    {
        "id": "crm_ops",
        "agent": "crm_ops",
        "title": "AI CRM Data Management — Cleanup, Dedup, Enrichment",
        "category": "CRM / Data Management",
        "skills": ["CRM", "Salesforce", "HubSpot", "Data Cleaning", "Data Entry"],
        "description": (
            "I clean, deduplicate, and organize your CRM data using an AI agent that "
            "understands contact records, deal stages, and pipeline management.\n\n"
            "Deliverables:\n"
            "• Duplicate detection and merge recommendations\n"
            "• Contact standardization (names, emails, phones, titles)\n"
            "• Missing field identification\n"
            "• Lead scoring suggestions\n"
            "• Pipeline stage validation\n"
            "• Import-ready CSV/JSON export\n\n"
            "Works with exports from: Salesforce, HubSpot, Zoho, Pipedrive, "
            "or any spreadsheet-based CRM."
        ),
        "packages": {
            "Starter — $25": {"records": 250, "delivery": "Same day"},
            "Standard — $65": {"records": 1000, "delivery": "24 hours"},
            "Bulk — $150": {"records": 5000, "delivery": "48 hours"},
        },
        "keywords": ["crm management", "crm cleanup", "crm data", "salesforce admin",
                      "hubspot", "data deduplication", "crm migration", "contact cleanup"],
    },
    # ── 12. Bookkeeping ─────────────────────────────────────────
    {
        "id": "bookkeeping",
        "agent": "bookkeeping",
        "title": "AI Bookkeeping — Expense Categorization & Bank Reconciliation",
        "category": "Accounting / Bookkeeping",
        "skills": ["Bookkeeping", "QuickBooks", "Accounting", "Data Entry", "Financial Analysis"],
        "description": (
            "I categorize expenses, reconcile bank statements, and organize financial records "
            "using an AI bookkeeping agent trained on standard chart of accounts.\n\n"
            "Deliverables:\n"
            "• Expense categorization (mapped to your chart of accounts)\n"
            "• Transaction matching and reconciliation\n"
            "• Missing receipt flagging\n"
            "• Monthly summary with totals by category\n"
            "• QBO/Xero-compatible export format\n"
            "• QA verification on all categorizations\n\n"
            "Disclaimer: This is data processing assistance, not licensed accounting advice. "
            "All output should be reviewed by your accountant.\n\n"
            "Handles: bank statements, credit card transactions, PayPal/Stripe exports, "
            "receipt data, and general ledger entries."
        ),
        "packages": {
            "Starter — $25": {"transactions": 100, "delivery": "Same day"},
            "Standard — $65": {"transactions": 500, "delivery": "24 hours"},
            "Bulk — $150": {"transactions": 2000, "delivery": "48 hours"},
        },
        "keywords": ["bookkeeping", "expense categorization", "bank reconciliation",
                      "quickbooks", "xero", "accounting data entry", "financial records"],
    },
    # ── 13. Proposal Writing ────────────────────────────────────
    {
        "id": "proposal_writer",
        "agent": "proposal_writer",
        "title": "AI Proposal & Bid Writing — Win More Projects",
        "category": "Business Writing / Proposal",
        "skills": ["Proposal Writing", "Business Writing", "Copywriting", "RFP", "Bid Writing"],
        "description": (
            "I write compelling project proposals and bid responses using an AI writer agent "
            "that structures your value proposition, scope, timeline, and pricing.\n\n"
            "Deliverables:\n"
            "• Executive summary with hook\n"
            "• Problem statement and proposed solution\n"
            "• Scope of work with deliverables table\n"
            "• Timeline with milestones\n"
            "• Pricing breakdown (tiered options)\n"
            "• Social proof section (case studies, testimonials)\n"
            "• Markdown export, ready to format\n\n"
            "Types: Project proposals, RFP responses, service agreements, "
            "grant applications, partnership proposals."
        ),
        "packages": {
            "Starter — $30": {"proposals": 1, "delivery": "Same day"},
            "Standard — $80": {"proposals": 3, "delivery": "48 hours"},
            "Bulk — $175": {"proposals": 7, "delivery": "5 days"},
        },
        "keywords": ["proposal writing", "bid writing", "rfp response", "business proposal",
                      "project proposal", "grant writing", "tender response"],
    },
    # ── 14. Product Descriptions ────────────────────────────────
    {
        "id": "product_desc",
        "agent": "product_desc",
        "title": "AI Product Descriptions — Amazon, Shopify, Etsy, eBay Optimized",
        "category": "Product Descriptions / E-commerce",
        "skills": ["Product Descriptions", "Copywriting", "E-commerce", "SEO", "Amazon"],
        "description": (
            "I write converting product descriptions optimized for your selling platform — "
            "Amazon, Shopify, Etsy, eBay, or WooCommerce — using an AI copywriting agent.\n\n"
            "Deliverables:\n"
            "• Platform-optimized product title\n"
            "• Feature bullet points (Amazon ALL CAPS lead phrase format)\n"
            "• Long-form description with benefits-first copy\n"
            "• SEO meta title + description\n"
            "• A/B headline variations\n"
            "• Keyword integration (your keywords or AI-suggested)\n"
            "• QA verified for platform compliance\n\n"
            "Character limits enforced per platform. No prohibited claims. "
            "Benefits-first, not features-first."
        ),
        "packages": {
            "Starter — $15": {"products": 5, "delivery": "Same day"},
            "Standard — $45": {"products": 20, "delivery": "24 hours"},
            "Bulk — $120": {"products": 75, "delivery": "48 hours"},
        },
        "keywords": ["product description", "amazon listing", "shopify product",
                      "etsy listing", "ebay description", "product copy", "e-commerce copy"],
    },
    # ── 15. Resume Writing ──────────────────────────────────────
    {
        "id": "resume_writer",
        "agent": "resume_writer",
        "title": "AI Resume & CV Writing — ATS-Optimized, Interview-Ready",
        "category": "Resume Writing / Career Services",
        "skills": ["Resume Writing", "CV Writing", "Career Counseling", "HR", "Recruitment"],
        "description": (
            "I write ATS-optimized resumes and CVs using an AI agent trained on "
            "recruiter preferences, applicant tracking systems, and hiring patterns.\n\n"
            "Deliverables:\n"
            "• ATS-friendly resume with keyword optimization\n"
            "• CAR format bullets (Challenge-Action-Result)\n"
            "• 70%+ bullets with quantified achievements\n"
            "• 8-12 targeted ATS keywords for your role\n"
            "• Strong action verbs (no passive voice)\n"
            "• Skills section organized by relevance\n"
            "• QA verified for ATS compliance\n\n"
            "Levels: Entry-level (potential-focused), Mid-career (achievements), "
            "Senior (leadership + P&L), Executive (board-level).\n\n"
            "Styles: Chronological, Functional, Combination, Modern, Executive."
        ),
        "packages": {
            "Starter — $25": {"resumes": 1, "delivery": "Same day"},
            "Standard — $60": {"resumes": 1, "extras": "Cover letter + LinkedIn summary", "delivery": "24 hours"},
            "Premium — $120": {"resumes": 1, "extras": "Cover letter + LinkedIn + 3 role variations", "delivery": "48 hours"},
        },
        "keywords": ["resume writing", "cv writing", "ats resume", "resume writer",
                      "professional resume", "executive resume", "cover letter"],
    },
    # ── 16. Ad Copy (PPC / Social) ──────────────────────────────
    {
        "id": "ad_copy",
        "agent": "ad_copy",
        "title": "AI Ad Copy — Google Ads, Facebook, LinkedIn, TikTok PPC Copy",
        "category": "Advertising / PPC / Copywriting",
        "skills": ["Ad Copy", "Google Ads", "Facebook Ads", "PPC", "Copywriting", "LinkedIn Ads"],
        "description": (
            "I write high-converting ad copy for every major platform — Google Search, "
            "Google Display, Facebook, Instagram, LinkedIn, TikTok, Twitter, YouTube, "
            "Pinterest — using an AI copywriting agent that enforces character limits "
            "and platform policies.\n\n"
            "Deliverables:\n"
            "• Headlines + descriptions within platform character limits\n"
            "• A/B variations (benefit-led + pain-point)\n"
            "• Sitelink copy (Google)\n"
            "• Targeting suggestions (keywords, negatives, audiences)\n"
            "• Platform policy compliance check\n"
            "• QA verified — no policy violations\n\n"
            "Character limits enforced: Google 30/90, Facebook 40/125, "
            "LinkedIn 70/150, Twitter 70/280, TikTok 100/100."
        ),
        "packages": {
            "Starter — $20": {"campaigns": 1, "variations": 2, "delivery": "Same day"},
            "Standard — $55": {"campaigns": 3, "variations": 3, "delivery": "24 hours"},
            "Premium — $140": {"campaigns": 8, "variations": 4, "delivery": "48 hours"},
        },
        "keywords": ["ad copy", "google ads", "facebook ads", "ppc copy", "linkedin ads",
                      "ad copywriting", "social media ads", "tiktok ads", "ppc"],
    },
    # ── 17. Market Research ─────────────────────────────────────
    {
        "id": "market_research",
        "agent": "market_research",
        "title": "AI Market Research Reports — Competitive Analysis & SWOT",
        "category": "Market Research / Business Analysis",
        "skills": ["Market Research", "Competitive Analysis", "Business Analysis", "SWOT", "AI"],
        "description": (
            "I produce comprehensive market research reports using an AI analysis agent — "
            "market sizing (TAM/SAM/SOM), competitive landscape, customer segmentation, "
            "trend analysis, and SWOT.\n\n"
            "Deliverables:\n"
            "• Market overview (size, growth rate, key drivers and barriers)\n"
            "• Competitive landscape (leaders, emerging players, market gaps)\n"
            "• Customer analysis (segments, pain points, willingness to pay)\n"
            "• Trend analysis with impact ratings (HIGH/MEDIUM/LOW)\n"
            "• SWOT analysis (3+ per quadrant, no filler)\n"
            "• Actionable recommendations with priority + timeframe\n"
            "• Methodology and limitations stated\n\n"
            "Report types: Market overview, competitive analysis, industry trends, "
            "customer analysis, SWOT, market sizing, feasibility study.\n\n"
            "Disclaimer: Based on publicly available information and AI analysis. "
            "Not a substitute for primary research."
        ),
        "packages": {
            "Quick — $35": {"depth": "Quick overview", "pages": "3-5", "delivery": "Same day"},
            "Standard — $100": {"depth": "Standard report", "pages": "8-12", "delivery": "48 hours"},
            "Comprehensive — $250": {"depth": "Deep dive", "pages": "15-25", "delivery": "5 days"},
        },
        "keywords": ["market research", "competitive analysis", "swot analysis",
                      "market sizing", "industry analysis", "feasibility study",
                      "market report", "business analysis"],
    },
    # ── 18. Business Plan Writing ───────────────────────────────
    {
        "id": "business_plan",
        "agent": "business_plan",
        "title": "AI Business Plan Writing — Investor-Ready with Financial Projections",
        "category": "Business Plans / Financial Planning",
        "skills": ["Business Plans", "Financial Projections", "Startup", "Fundraising", "Strategy"],
        "description": (
            "I write investor-ready business plans with financial projections, market analysis, "
            "go-to-market strategy, and risk assessment — using an AI planning agent.\n\n"
            "Deliverables:\n"
            "• Executive summary\n"
            "• Company description (mission, vision, values, stage)\n"
            "• Problem/solution with unique value proposition\n"
            "• Market analysis (TAM/SAM/SOM)\n"
            "• Business model with unit economics (LTV, CAC)\n"
            "• Go-to-market strategy (phased)\n"
            "• Operations plan with team + milestones\n"
            "• 3-year financial projections (revenue, expenses, net)\n"
            "• Funding requirements with use-of-funds breakdown\n"
            "• Risk assessment with mitigation strategies\n"
            "• QA verified for financial consistency\n\n"
            "Types: Startup, expansion, investor pitch, loan application, lean canvas.\n\n"
            "Disclaimer: Financial projections are estimates for planning purposes."
        ),
        "packages": {
            "Lean Canvas — $50": {"type": "Lean canvas", "pages": "3-5", "delivery": "Same day"},
            "Standard — $150": {"type": "Full plan", "pages": "15-20", "delivery": "48 hours"},
            "Investor-Ready — $350": {"type": "Pitch-ready + financials", "pages": "25-35", "delivery": "5 days"},
        },
        "keywords": ["business plan", "startup plan", "financial projections",
                      "investor pitch", "fundraising", "business plan writer",
                      "lean canvas", "loan application"],
    },
    # ── 19. Press Release Writing ───────────────────────────────
    {
        "id": "press_release",
        "agent": "press_release",
        "title": "AI Press Release Writing — AP-Style, Distribution-Ready",
        "category": "Press Release / PR",
        "skills": ["Press Release", "PR", "Public Relations", "Copywriting", "AP Style"],
        "description": (
            "I write AP-style press releases ready for PR Newswire, Business Wire, "
            "or direct media outreach — using an AI PR writing agent.\n\n"
            "Deliverables:\n"
            "• AP-style headline + subheadline\n"
            "• Proper dateline (CITY, State — Date)\n"
            "• Lead paragraph (WHO, WHAT, WHEN, WHERE, WHY)\n"
            "• Body with inverted pyramid structure\n"
            "• 2 spokesperson quotes (properly attributed)\n"
            "• Company boilerplate (50-100 words)\n"
            "• Media contact section\n"
            "• Distribution notes (wire service, tags, target outlets)\n"
            "• SEO meta (title ≤60 chars, description ≤155 chars)\n"
            "• QA verified for AP compliance\n\n"
            "Types: Product launch, partnership, funding, expansion, executive hire, "
            "event, milestone, award, crisis response."
        ),
        "packages": {
            "Starter — $25": {"releases": 1, "delivery": "Same day"},
            "Standard — $65": {"releases": 3, "delivery": "48 hours"},
            "Bulk — $150": {"releases": 7, "delivery": "5 days"},
        },
        "keywords": ["press release", "pr writing", "press release writer",
                      "pr newswire", "media release", "news release", "public relations"],
    },
    # ── 20. Technical Documentation ─────────────────────────────
    {
        "id": "tech_docs",
        "agent": "tech_docs",
        "title": "AI Technical Documentation — API Docs, READMEs, User Guides",
        "category": "Technical Writing / Documentation",
        "skills": ["Technical Writing", "API Documentation", "Software Documentation", "Python", "Markdown"],
        "description": (
            "I write clear, structured technical documentation — API references, "
            "user guides, READMEs, tutorials, runbooks, and SDK guides — using an AI "
            "technical writing agent.\n\n"
            "Deliverables:\n"
            "• Audience-appropriate content (developers, DevOps, end-users, stakeholders)\n"
            "• Runnable code examples (not pseudo-code)\n"
            "• API endpoint docs (method, path, params, request/response, errors)\n"
            "• Prerequisites and setup instructions\n"
            "• Troubleshooting section (3+ common issues)\n"
            "• Configuration reference (env vars, config files)\n"
            "• Glossary of domain terms\n"
            "• Full Markdown export\n"
            "• QA verified for accuracy and completeness\n\n"
            "Types: API reference, user guide, README, how-to, tutorial, "
            "architecture docs, changelog, runbook, SDK guide."
        ),
        "packages": {
            "Starter — $30": {"doc_type": "Single doc", "delivery": "Same day"},
            "Standard — $80": {"doc_type": "3 documents or full API ref", "delivery": "48 hours"},
            "Comprehensive — $200": {"doc_type": "Full documentation suite", "delivery": "5 days"},
        },
        "keywords": ["technical writing", "api documentation", "readme", "user guide",
                      "software documentation", "technical documentation", "developer docs"],
    },
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BID TEMPLATES — One per service type
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BID_TEMPLATES = {
    "sales_ops": {
        "subject": "I'll build your personalized sales outreach sequences — AI-powered",
        "body": (
            "Hi,\n\n"
            "I run an AI agent agency that specializes in sales outreach automation. "
            "My pipeline researches each prospect in real-time — funding signals, hiring "
            "activity, product launches — then generates a personalized 3-email sequence.\n\n"
            "This isn't template-based. Every email references real company data.\n\n"
            "What I'd deliver:\n"
            "• Company research with buying signals\n"
            "• 3-email personalized sequence per lead\n"
            "• CRM-ready CSV + JSON export\n"
            "• QA verified output\n\n"
            "I can process {lead_count} leads and deliver within {timeline}.\n\n"
            "Happy to share a sample for one of your target companies.\n\n"
            "— Digital Labour (Resonance Energy, Canada)"
        ),
    },
    "support": {
        "subject": "AI-powered ticket triage + draft responses — under 10 seconds",
        "body": (
            "Hi,\n\n"
            "I build AI support systems that triage tickets, score severity, and "
            "draft responses in under 10 seconds per ticket.\n\n"
            "What you'd get:\n"
            "• Auto-classification (billing, technical, account, general)\n"
            "• Severity scoring (1-5) with escalation flags\n"
            "• Draft response with confidence score\n"
            "• Structured output for helpdesk integration\n\n"
            "Currently handles {ticket_volume}+ tickets per run with 80%+ QA pass rate. "
            "Works with Zendesk, Freshdesk, Intercom exports, or plain text.\n\n"
            "I can start immediately.\n\n"
            "— Digital Labour"
        ),
    },
    "content_repurpose": {
        "subject": "I'll transform your content into 5 platform formats — AI pipeline",
        "body": (
            "Hi,\n\n"
            "I specialize in content repurposing using a multi-agent AI pipeline. "
            "One blog post or article becomes:\n\n"
            "• LinkedIn post (professional, hashtags)\n"
            "• Twitter/X thread (280-char tweets)\n"
            "• Email newsletter (subject + body)\n"
            "• Instagram caption (emoji, hashtags)\n"
            "• TikTok/Reels script (spoken format)\n\n"
            "Each piece is optimized for its platform — character limits, tone, "
            "hashtag strategy. QA verified before delivery.\n\n"
            "I can process {post_count} pieces and deliver in {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "doc_extract": {
        "subject": "AI document extraction — invoices, contracts, resumes -> structured data",
        "body": (
            "Hi,\n\n"
            "I have a production document extraction agent that handles invoices, "
            "contracts, resumes, and custom document types.\n\n"
            "What you'd get:\n"
            "• Entity extraction (names, dates, amounts, line items)\n"
            "• Auto document classification\n"
            "• Structured JSON + CSV output\n"
            "• Confidence scores on every field\n"
            "• QA verification\n\n"
            "Currently processing documents in under 10 seconds with 85%+ accuracy. "
            "Happy to adapt to your specific format requirements.\n\n"
            "— Digital Labour"
        ),
    },
    "lead_gen": {
        "subject": "AI-powered lead research — scored, qualified, CRM-ready",
        "body": (
            "Hi,\n\n"
            "I build targeted B2B lead lists using an AI research agent. Each lead is "
            "individually researched and scored — not scraped from a database.\n\n"
            "What you'd get:\n"
            "• Company + decision-maker details\n"
            "• Lead score (1-100) based on your ICP\n"
            "• Buying signals and pain point analysis\n"
            "• Recommended approach angle\n"
            "• CRM-ready CSV + JSON\n\n"
            "Tell me your ideal customer profile and I'll deliver {lead_count} "
            "qualified leads within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "email_marketing": {
        "subject": "Complete email sequences — welcome, nurture, re-engagement + A/B copy",
        "body": (
            "Hi,\n\n"
            "I write complete email marketing sequences with A/B subject line variations "
            "using an AI copywriting agent.\n\n"
            "What you'd get:\n"
            "• {email_count}-email sequence\n"
            "• A/B subject line variations\n"
            "• Send timing recommendations\n"
            "• Segmentation suggestions\n"
            "• Merge tags for Mailchimp/Klaviyo/etc.\n"
            "• Spam trigger check + readability score\n\n"
            "Frameworks: AIDA, PAS, BAB — proven converters.\n\n"
            "I can deliver the full sequence within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "seo_content": {
        "subject": "SEO blog posts — keyword-optimized, publish-ready, AI-powered",
        "body": (
            "Hi,\n\n"
            "I produce SEO-optimized articles using a 3-stage AI pipeline: "
            "Keyword Research -> Content Writing -> QA Verification.\n\n"
            "What you'd get:\n"
            "• Primary + secondary keyword targeting\n"
            "• SEO title tag + meta description\n"
            "• Proper H1/H2/H3 structure\n"
            "• 1,500-3,000 words (your choice)\n"
            "• Internal linking suggestions\n"
            "• Markdown + HTML export\n\n"
            "No fluff, no keyword stuffing. Natural content that ranks.\n\n"
            "I can deliver {article_count} articles within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "social_media": {
        "subject": "Platform-optimized social content — LinkedIn, Twitter, Instagram + more",
        "body": (
            "Hi,\n\n"
            "I create social media content optimized for each platform using "
            "an AI strategist agent.\n\n"
            "What you'd get per post:\n"
            "• Platform-specific copy\n"
            "• Hashtag recommendations (broad + niche)\n"
            "• Posting time suggestions\n"
            "• CTA options\n"
            "• Visual direction notes\n\n"
            "Consistent brand voice across all platforms. "
            "I can deliver {post_count} posts for {platform_count} platforms "
            "within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "data_entry": {
        "subject": "Fast, accurate data processing — cleaning, formatting, structuring",
        "body": (
            "Hi,\n\n"
            "I process and clean data using an AI data processing agent — messy "
            "spreadsheets, unstructured text, form submissions, whatever you have.\n\n"
            "What you'd get:\n"
            "• Data standardization (dates, names, currencies)\n"
            "• Duplicate detection + removal\n"
            "• Missing value flagging\n"
            "• CSV/JSON/Excel export\n"
            "• Validation report\n\n"
            "I can process {row_count} records within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "web_scraper": {
        "subject": "Structured data extraction from web pages — fast + clean output",
        "body": (
            "Hi,\n\n"
            "I extract structured data from web pages using an AI extraction agent.\n\n"
            "What you'd get:\n"
            "• Clean JSON + CSV output\n"
            "• Custom field mapping\n"
            "• Data quality scoring\n"
            "• Duplicate removal\n"
            "• QA validation report\n\n"
            "Tell me what data you need from the page and I'll deliver "
            "structured output within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "crm_ops": {
        "subject": "CRM data cleanup — dedup, standardize, enrich, export",
        "body": (
            "Hi,\n\n"
            "I clean and organize CRM data using an AI agent — duplicate detection, "
            "contact standardization, missing field identification.\n\n"
            "What you'd get:\n"
            "• Duplicate detection + merge recommendations\n"
            "• Contact standardization (names, emails, phones)\n"
            "• Missing field report\n"
            "• Lead scoring suggestions\n"
            "• Import-ready CSV/JSON\n\n"
            "Works with Salesforce, HubSpot, Zoho, Pipedrive exports, or spreadsheets.\n\n"
            "I can process {record_count} records within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "bookkeeping": {
        "subject": "Expense categorization + bank reconciliation — AI-powered bookkeeping",
        "body": (
            "Hi,\n\n"
            "I process financial records using an AI bookkeeping agent — expense "
            "categorization, transaction matching, and reconciliation.\n\n"
            "What you'd get:\n"
            "• Expenses mapped to your chart of accounts\n"
            "• Transaction matching + reconciliation\n"
            "• Missing receipt flagging\n"
            "• Monthly summary by category\n"
            "• QBO/Xero-compatible export\n\n"
            "Note: This is data processing assistance — all output should be "
            "reviewed by your accountant.\n\n"
            "I can process {transaction_count} transactions within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "proposal_writer": {
        "subject": "Winning proposals — structured, compelling, ready to send",
        "body": (
            "Hi,\n\n"
            "I write project proposals using an AI writer agent that structures "
            "your value proposition for maximum impact.\n\n"
            "What you'd get:\n"
            "• Executive summary with hook\n"
            "• Problem statement + solution\n"
            "• Scope of work + deliverables\n"
            "• Timeline + milestones\n"
            "• Tiered pricing options\n"
            "• Social proof section\n"
            "• Markdown export, ready to format\n\n"
            "I can deliver {proposal_count} proposals within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "product_desc": {
        "subject": "Converting product descriptions — Amazon, Shopify, Etsy optimized",
        "body": (
            "Hi,\n\n"
            "I write product descriptions optimized for your specific platform "
            "using an AI copywriting agent.\n\n"
            "What you'd get:\n"
            "• Platform-specific title + description\n"
            "• Feature bullet points (Amazon ALL CAPS format)\n"
            "• Benefits-first copy\n"
            "• SEO meta title + description\n"
            "• A/B headline variations\n"
            "• Keyword integration\n\n"
            "Character limits enforced. Platform policies checked. "
            "I can deliver {product_count} products within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "resume_writer": {
        "subject": "ATS-optimized resumes — professionally written, keyword-targeted",
        "body": (
            "Hi,\n\n"
            "I write ATS-optimized resumes using an AI agent trained on recruiter "
            "preferences and applicant tracking systems.\n\n"
            "What you'd get:\n"
            "• ATS-friendly format + layout\n"
            "• CAR bullets (Challenge-Action-Result)\n"
            "• 70%+ quantified achievements\n"
            "• 8-12 targeted ATS keywords\n"
            "• Strong action verbs throughout\n"
            "• QA verified for ATS compliance\n\n"
            "Handles: Entry-level to Executive. "
            "Styles: Chronological, Functional, Combination, Modern.\n\n"
            "I can deliver within {timeline}. Happy to discuss your target role.\n\n"
            "— Digital Labour"
        ),
    },
    "ad_copy": {
        "subject": "High-converting ad copy — Google, Facebook, LinkedIn, TikTok",
        "body": (
            "Hi,\n\n"
            "I write ad copy for every major platform using an AI copywriting agent "
            "that enforces character limits and platform policies.\n\n"
            "What you'd get:\n"
            "• Headlines + descriptions within character limits\n"
            "• A/B variations (benefit-led + pain-point)\n"
            "• Sitelink copy (Google)\n"
            "• Targeting suggestions (keywords + audiences)\n"
            "• Policy compliance check\n\n"
            "Platforms: Google Search/Display, Facebook, Instagram, LinkedIn, "
            "TikTok, Twitter, YouTube, Pinterest.\n\n"
            "I can deliver {campaign_count} campaigns within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "market_research": {
        "subject": "Market research report — competitive analysis, SWOT, sizing",
        "body": (
            "Hi,\n\n"
            "I produce market research reports using an AI analysis agent — "
            "market sizing, competitive landscape, customer segmentation, SWOT.\n\n"
            "What you'd get:\n"
            "• Market overview (size, growth, drivers)\n"
            "• Competitive landscape (leaders + gaps)\n"
            "• Customer analysis (segments + pain points)\n"
            "• SWOT analysis (3+ per quadrant)\n"
            "• Actionable recommendations with priority\n"
            "• Methodology and limitations stated\n\n"
            "Based on publicly available data. "
            "I can deliver a {depth} report within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "business_plan": {
        "subject": "Investor-ready business plan — financials, market analysis, GTM strategy",
        "body": (
            "Hi,\n\n"
            "I write business plans with financial projections using an AI planning agent.\n\n"
            "What you'd get:\n"
            "• Executive summary\n"
            "• Market analysis (TAM/SAM/SOM)\n"
            "• Business model with unit economics\n"
            "• Go-to-market strategy (phased)\n"
            "• 3-year financial projections\n"
            "• Risk assessment + mitigation\n"
            "• Use-of-funds breakdown (if fundraising)\n"
            "• QA verified for financial consistency\n\n"
            "Types: Startup, expansion, investor pitch, loan application, lean canvas.\n\n"
            "I can deliver within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "press_release": {
        "subject": "AP-style press release — distribution-ready in 24 hours",
        "body": (
            "Hi,\n\n"
            "I write AP-style press releases ready for wire distribution using "
            "an AI PR writing agent.\n\n"
            "What you'd get:\n"
            "• AP-style headline + subheadline\n"
            "• Proper dateline format\n"
            "• Inverted pyramid structure\n"
            "• 2 spokesperson quotes\n"
            "• Company boilerplate\n"
            "• Distribution notes (wire, tags, target outlets)\n"
            "• SEO meta for web distribution\n\n"
            "Types: Product launch, partnership, funding, expansion, hire, "
            "event, milestone, award.\n\n"
            "I can deliver {release_count} releases within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
    "tech_docs": {
        "subject": "Technical documentation — API docs, READMEs, user guides, runbooks",
        "body": (
            "Hi,\n\n"
            "I write technical documentation using an AI tech writing agent — "
            "API references, READMEs, user guides, tutorials, and runbooks.\n\n"
            "What you'd get:\n"
            "• Audience-appropriate content\n"
            "• Runnable code examples (not pseudo-code)\n"
            "• API endpoint documentation\n"
            "• Prerequisites + setup instructions\n"
            "• Troubleshooting section\n"
            "• Full Markdown export\n\n"
            "Types: API reference, user guide, README, how-to, tutorial, "
            "architecture, changelog, runbook, SDK guide.\n\n"
            "I can deliver within {timeline}.\n\n"
            "— Digital Labour"
        ),
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AUTOBID KEYWORD MATCHING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AUTOBID_RULES = [
    {
        "agent": "sales_ops",
        "match_any": ["cold email", "outreach", "sales email", "b2b email",
                      "email sequence", "sales sequence", "prospecting email"],
        "match_all": [],
        "exclude": ["cold calling", "phone", "telemarketing"],
        "max_bid_usd": 200,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "support",
        "match_any": ["customer support", "ticket", "help desk", "helpdesk",
                      "support agent", "ticket resolution", "zendesk", "freshdesk"],
        "match_all": [],
        "exclude": ["phone support", "call center"],
        "max_bid_usd": 150,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "content_repurpose",
        "match_any": ["content repurpos", "blog to social", "repurpose content",
                      "content transform", "multi-platform content"],
        "match_all": [],
        "exclude": ["video editing", "graphic design"],
        "max_bid_usd": 120,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "doc_extract",
        "match_any": ["document extract", "invoice processing", "contract analysis",
                      "data extraction", "pdf extract", "ocr", "document parsing"],
        "match_all": [],
        "exclude": ["handwriting", "physical documents"],
        "max_bid_usd": 100,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "lead_gen",
        "match_any": ["lead generation", "lead list", "b2b leads", "prospect list",
                      "lead research", "qualified leads", "sales leads"],
        "match_all": [],
        "exclude": ["telemarketing", "cold calling"],
        "max_bid_usd": 175,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "email_marketing",
        "match_any": ["email marketing", "email campaign", "drip campaign", "newsletter",
                      "email sequence", "welcome email", "nurture", "mailchimp", "klaviyo"],
        "match_all": [],
        "exclude": ["cold email", "spam", "bulk email"],
        "max_bid_usd": 150,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "seo_content",
        "match_any": ["seo article", "seo blog", "seo content", "blog post", "blog writing",
                      "keyword article", "content writing seo", "article writing"],
        "match_all": [],
        "exclude": ["link building", "backlinks", "technical seo audit"],
        "max_bid_usd": 200,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "social_media",
        "match_any": ["social media post", "social media content", "instagram caption",
                      "linkedin post", "twitter content", "social media marketing",
                      "content calendar", "social media manager"],
        "match_all": [],
        "exclude": ["social media ads", "paid social", "graphic design"],
        "max_bid_usd": 130,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "data_entry",
        "match_any": ["data entry", "data cleaning", "data processing", "spreadsheet",
                      "excel data", "csv processing", "data formatting", "data migration",
                      "copy paste", "typing"],
        "match_all": [],
        "exclude": ["web development", "programming"],
        "max_bid_usd": 100,
        "confidence_threshold": 0.6,
    },
    {
        "agent": "web_scraper",
        "match_any": ["web scraping", "data scraping", "data mining", "scrape website",
                      "web data", "screen scraping", "web crawler", "price scraping",
                      "extract from website"],
        "match_all": [],
        "exclude": ["hacking", "bypass captcha"],
        "max_bid_usd": 150,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "crm_ops",
        "match_any": ["crm", "salesforce", "hubspot", "zoho crm", "pipedrive",
                      "crm cleanup", "crm data", "crm migration", "contact cleanup"],
        "match_all": [],
        "exclude": ["crm development", "custom crm build"],
        "max_bid_usd": 150,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "bookkeeping",
        "match_any": ["bookkeeping", "expense categoriz", "bank reconcil", "quickbooks",
                      "xero", "accounting data", "financial records", "transaction categor"],
        "match_all": [],
        "exclude": ["tax filing", "audit", "cpa", "tax return"],
        "max_bid_usd": 150,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "proposal_writer",
        "match_any": ["proposal writ", "bid writing", "rfp response", "business proposal",
                      "project proposal", "grant writing", "tender response"],
        "match_all": [],
        "exclude": ["government contract", "legal brief"],
        "max_bid_usd": 175,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "product_desc",
        "match_any": ["product description", "amazon listing", "shopify product",
                      "etsy listing", "ebay description", "product copy", "e-commerce copy",
                      "product listing"],
        "match_all": [],
        "exclude": ["product photography", "product design"],
        "max_bid_usd": 120,
        "confidence_threshold": 0.6,
    },
    {
        "agent": "resume_writer",
        "match_any": ["resume writ", "cv writ", "resume", "curriculum vitae",
                      "cover letter", "linkedin profile", "ats resume"],
        "match_all": [],
        "exclude": ["resume website", "portfolio website"],
        "max_bid_usd": 120,
        "confidence_threshold": 0.6,
    },
    {
        "agent": "ad_copy",
        "match_any": ["ad copy", "google ads", "facebook ads", "ppc copy", "linkedin ads",
                      "ad copywriting", "social media ads", "tiktok ads", "ppc",
                      "paid advertising copy"],
        "match_all": [],
        "exclude": ["ad management", "campaign management", "media buying"],
        "max_bid_usd": 140,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "market_research",
        "match_any": ["market research", "competitive analysis", "swot analysis",
                      "market sizing", "industry analysis", "feasibility study",
                      "market report", "competitor research"],
        "match_all": [],
        "exclude": ["primary research", "survey design", "focus group"],
        "max_bid_usd": 250,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "business_plan",
        "match_any": ["business plan", "startup plan", "financial projection",
                      "investor pitch", "fundraising plan", "lean canvas",
                      "business model", "pitch deck content"],
        "match_all": [],
        "exclude": ["pitch deck design", "financial audit"],
        "max_bid_usd": 350,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "press_release",
        "match_any": ["press release", "pr writing", "media release", "news release",
                      "publicity", "pr newswire", "press announcement"],
        "match_all": [],
        "exclude": ["press kit design", "media buying"],
        "max_bid_usd": 150,
        "confidence_threshold": 0.7,
    },
    {
        "agent": "tech_docs",
        "match_any": ["technical documentation", "api documentation", "readme",
                      "user guide", "software documentation", "developer docs",
                      "technical writing", "sdk documentation", "runbook"],
        "match_all": [],
        "exclude": ["technical support", "bug fixing"],
        "max_bid_usd": 200,
        "confidence_threshold": 0.7,
    },
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CROSS-SELL BUNDLES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BUNDLES = [
    {
        "name": "Full Funnel Package",
        "agents": ["lead_gen", "sales_outreach", "email_marketing", "proposal_writer"],
        "description": "Lead research -> outreach -> nurture -> close. End-to-end.",
        "discount": "15%",
    },
    {
        "name": "Content Engine",
        "agents": ["seo_content", "social_media", "content_repurpose", "ad_copy"],
        "description": "SEO articles -> social posts -> repurposed formats -> paid ads.",
        "discount": "15%",
    },
    {
        "name": "Back Office Automation",
        "agents": ["data_entry", "doc_extract", "bookkeeping", "crm_ops"],
        "description": "Data processing -> extraction -> bookkeeping -> CRM cleanup.",
        "discount": "20%",
    },
    {
        "name": "Startup Launch Kit",
        "agents": ["business_plan", "market_research", "press_release", "product_desc"],
        "description": "Business plan -> market validation -> launch PR -> product listings.",
        "discount": "15%",
    },
    {
        "name": "Career Services Package",
        "agents": ["resume_writer", "proposal_writer"],
        "description": "ATS resume + cover letter + freelance proposal templates.",
        "discount": "10%",
    },
    {
        "name": "Developer Documentation Suite",
        "agents": ["tech_docs", "product_desc"],
        "description": "Full API docs + product descriptions for SaaS launches.",
        "discount": "10%",
    },
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MATCHING ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def match_project(title: str, description: str) -> list[dict]:
    """Match a Freelancer project to agents based on keyword rules.

    Returns list of matches sorted by confidence (highest first).
    """
    text = f"{title} {description}".lower()
    matches = []

    for rule in AUTOBID_RULES:
        # Check exclusions first
        if any(ex.lower() in text for ex in rule["exclude"]):
            continue

        # Count keyword matches
        any_hits = sum(1 for kw in rule["match_any"] if kw.lower() in text)
        if any_hits == 0:
            continue

        # All-match keywords (if any)
        if rule["match_all"]:
            all_hits = all(kw.lower() in text for kw in rule["match_all"])
            if not all_hits:
                continue

        confidence = min(any_hits / max(len(rule["match_any"]) * 0.3, 1), 1.0)
        if confidence >= rule["confidence_threshold"]:
            matches.append({
                "agent": rule["agent"],
                "confidence": round(confidence, 2),
                "max_bid_usd": rule["max_bid_usd"],
                "bid_template": BID_TEMPLATES.get(rule["agent"], {}),
            })

    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return matches


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OUTPUT FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def print_gigs():
    """Print all 20 Freelancer gig listings."""
    print(f"\n{'='*70}")
    print("  FREELANCER.COM — 20 GIG LISTINGS")
    print(f"{'='*70}")

    for i, gig in enumerate(FREELANCER_GIGS, 1):
        print(f"\n{'─'*70}")
        print(f"  GIG {i}: {gig['title']}")
        print(f"  Agent: {gig['agent']} | Category: {gig['category']}")
        print(f"  Skills: {', '.join(gig['skills'])}")
        print(f"{'─'*70}")
        print(f"\n{gig['description']}")
        print(f"\n  PACKAGES:")
        for pkg, details in gig["packages"].items():
            print(f"    {pkg}: {details}")
        print(f"  KEYWORDS: {', '.join(gig['keywords'])}")
    print(f"\n{'='*70}\n")


def print_bids():
    """Print all 20 bid templates."""
    print(f"\n{'='*70}")
    print("  FREELANCER.COM — 20 BID TEMPLATES")
    print(f"{'='*70}")

    for agent_id, template in BID_TEMPLATES.items():
        print(f"\n{'─'*70}")
        print(f"  [{agent_id.upper()}]")
        print(f"  Subject: {template['subject']}")
        print(f"{'─'*70}")
        print(template["body"])
    print(f"\n{'='*70}\n")


def print_bundles():
    """Print cross-sell bundles."""
    print(f"\n{'='*70}")
    print("  CROSS-SELL BUNDLES")
    print(f"{'='*70}")
    for bundle in BUNDLES:
        print(f"\n  {bundle['name']} ({bundle['discount']} discount)")
        print(f"  Agents: {' -> '.join(bundle['agents'])}")
        print(f"  {bundle['description']}")
    print(f"\n{'='*70}\n")


def print_agent_detail(agent_key: str):
    """Print full detail for one agent — gig + bid template."""
    gig = next((g for g in FREELANCER_GIGS if g["agent"] == agent_key), None)
    bid = BID_TEMPLATES.get(agent_key)

    if not gig:
        print(f"Unknown agent: {agent_key}")
        print(f"Available: {', '.join(g['agent'] for g in FREELANCER_GIGS)}")
        return

    print(f"\n{'='*70}")
    print(f"  AGENT: {agent_key}")
    print(f"{'='*70}")
    print(f"\n  Title: {gig['title']}")
    print(f"  Category: {gig['category']}")
    print(f"  Skills: {', '.join(gig['skills'])}")
    print(f"\n{gig['description']}")
    print(f"\n  PACKAGES:")
    for pkg, details in gig["packages"].items():
        print(f"    {pkg}: {details}")
    if bid:
        print(f"\n{'─'*70}")
        print(f"  BID TEMPLATE:")
        print(f"  Subject: {bid['subject']}")
        print(bid["body"])
    print(f"\n{'='*70}\n")


def save_all():
    """Save all listings, templates, and config to JSON files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Gigs
    gigs_path = OUTPUT_DIR / "freelancer_gigs_all.json"
    gigs_path.write_text(json.dumps(FREELANCER_GIGS, indent=2),
                         encoding="utf-8")
    print(f"  [SAVED] {gigs_path.name}")

    # Bid templates
    bids_path = OUTPUT_DIR / "freelancer_bid_templates.json"
    bids_path.write_text(json.dumps(BID_TEMPLATES, indent=2),
                         encoding="utf-8")
    print(f"  [SAVED] {bids_path.name}")

    # Autobid rules
    rules_path = OUTPUT_DIR / "freelancer_autobid_rules.json"
    rules_path.write_text(json.dumps(AUTOBID_RULES, indent=2),
                          encoding="utf-8")
    print(f"  [SAVED] {rules_path.name}")

    # Bundles
    bundles_path = OUTPUT_DIR / "freelancer_bundles.json"
    bundles_path.write_text(json.dumps(BUNDLES, indent=2),
                            encoding="utf-8")
    print(f"  [SAVED] {bundles_path.name}")

    # Agency profile
    profile_path = OUTPUT_DIR / "freelancer_agency_profile.json"
    profile_path.write_text(json.dumps(AGENCY_PROFILE, indent=2),
                            encoding="utf-8")
    print(f"  [SAVED] {profile_path.name}")

    print(f"\n  All files saved to: {OUTPUT_DIR}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Freelancer.com Full Deployment — 20 Gigs + Bid Templates")
    parser.add_argument("--gigs", action="store_true", help="Show gig listings")
    parser.add_argument("--bids", action="store_true", help="Show bid templates")
    parser.add_argument("--bundles", action="store_true", help="Show bundles")
    parser.add_argument("--agent", default="", help="Show detail for one agent")
    parser.add_argument("--match", nargs=2, metavar=("TITLE", "DESC"),
                        help="Match a project to agents")
    parser.add_argument("--save", action="store_true", help="Save all to files")
    args = parser.parse_args()

    if args.gigs:
        print_gigs()
    elif args.bids:
        print_bids()
    elif args.bundles:
        print_bundles()
    elif args.agent:
        print_agent_detail(args.agent)
    elif args.match:
        results = match_project(args.match[0], args.match[1])
        if results:
            print(f"\n  Matched {len(results)} agent(s):")
            for r in results:
                print(f"    {r['agent']} — confidence: {r['confidence']} "
                      f"— max bid: ${r['max_bid_usd']}")
        else:
            print("\n  No agent match found.")
    elif args.save:
        save_all()
    else:
        print_gigs()
        print_bids()
        print_bundles()

