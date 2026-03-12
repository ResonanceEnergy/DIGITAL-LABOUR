"""Fiverr Full Deployment Config -- 20 gig listings for all agents.

Usage:
    python -m campaign.fiverr_deploy              # Print all 20 gigs
    python -m campaign.fiverr_deploy --agent seo   # Show one gig
    python -m campaign.fiverr_deploy --save        # Save to JSON
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "output" / "fiverr_deploy"

# ---------------------------------------------------------------
#  20 FIVERR GIGS -- One per agent
# ---------------------------------------------------------------

FIVERR_GIGS = [
    # -- 1. Sales Outreach (sales_ops) --
    {
        "agent": "sales_ops",
        "title": "I will generate AI-powered sales outreach sequences with real company signals",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["ai sales agent", "sales outreach", "lead generation",
                 "cold email", "ai agent", "sales automation", "b2b outreach"],
        "description": (
            "AI-Powered Sales Outreach Agent\n\n"
            "I generate hyper-personalized sales outreach sequences for ANY company "
            "using real-time signals -- not templates.\n\n"
            "What You Get:\n"
            "- Deep company research -- funding, hiring, product launches, tech stack\n"
            "- Signal detection -- real triggers that matter to your prospect\n"
            "- 3-email outreach sequence -- personalized to their specific situation\n"
            "- QA-verified output -- every email passes through quality gates\n"
            "- CRM-ready export -- JSON + CSV format\n\n"
            "How It Works:\n"
            "1. You give me a company name + target role\n"
            "2. My AI agent pipeline researches the company in real-time\n"
            "3. A writer agent crafts personalized emails referencing real signals\n"
            "4. A QA agent validates tone, accuracy, and structure\n"
            "5. You get a ready-to-send sequence in under 60 seconds\n\n"
            "This isn't ChatGPT in a wrapper. It's a multi-agent pipeline with "
            "research, writing, and QA stages.\n\n"
            "Average delivery: Under 60 seconds per lead."
        ),
        "packages": {
            "Basic ($5)": "1 company -- full research + 3-email sequence + JSON export",
            "Standard ($20)": "5 companies -- batch processing + CSV export + priority",
            "Premium ($75)": "25 companies -- full batch + follow-up sequences + support",
        },
        "faq": [
            ("What do you need from me?", "Just the company name and target role."),
            ("How fast is delivery?", "Basic in under 5 min. Standard 15 min. Premium 1 hour."),
            ("Do you use templates?", "No. Every email is generated fresh using real-time research."),
        ],
    },
    # -- 2. Support (support) --
    {
        "agent": "support",
        "title": "I will build an AI support ticket resolver that drafts responses instantly",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["ai support agent", "customer support", "ticket resolution",
                 "helpdesk automation", "ai agent", "support bot", "ticket triage"],
        "description": (
            "AI Support Ticket Resolution Agent\n\n"
            "Get instant draft responses for support tickets -- triaged, "
            "severity-scored, and ready to send.\n\n"
            "What You Get:\n"
            "- Auto-triage -- categorizes tickets by type and urgency\n"
            "- Severity scoring -- 1-5 scale with escalation flagging\n"
            "- Draft response -- ready-to-send reply with confidence score\n"
            "- Policy compliance -- checks against your guidelines\n"
            "- Structured output -- JSON format for helpdesk integration\n\n"
            "Works with Zendesk, Freshdesk, Intercom, or plain email.\n\n"
            "Average resolution: 9.6 seconds per ticket."
        ),
        "packages": {
            "Basic ($5)": "10 tickets resolved -- triage + draft response + JSON",
            "Standard ($15)": "50 tickets -- batch processing + analytics report",
            "Premium ($40)": "200 tickets -- full resolution + escalation routing",
        },
        "faq": [
            ("What format do you need?", "Plain text, email, or JSON. Any format works."),
            ("Can this integrate with my helpdesk?", "Yes -- via API or webhook."),
            ("How accurate?", "80%+ QA pass rate. Every response has a confidence score."),
        ],
    },
    # -- 3. Content Repurposing (content_repurpose) --
    {
        "agent": "content_repurpose",
        "title": "I will repurpose your blog post into 5 social media formats using AI",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["content repurposing", "ai content", "social media",
                 "blog to social", "content automation", "ai writer"],
        "description": (
            "AI Content Repurposing Agent\n\n"
            "One blog post -> LinkedIn, Twitter/X, email newsletter, Instagram "
            "caption, and TikTok script. All optimized for each platform.\n\n"
            "What You Get:\n"
            "- LinkedIn post -- professional tone, hashtags, engagement hooks\n"
            "- Twitter/X thread -- under 280 chars per tweet, thread format\n"
            "- Email newsletter -- subject line + body, ready to send\n"
            "- Instagram caption -- emoji-rich, hashtag-optimized\n"
            "- TikTok/Reels script -- spoken format with hooks and CTAs\n\n"
            "One piece of content -> 5 platforms -> 5x the reach.\n\n"
            "Built with multi-agent AI pipelines. Not a ChatGPT prompt."
        ),
        "packages": {
            "Basic ($5)": "1 blog post -> 5 platform formats + editable text",
            "Standard ($20)": "5 posts -> 25 pieces total + content calendar",
            "Premium ($50)": "15 posts -> 75 pieces + monthly content strategy",
        },
        "faq": [
            ("What content can I submit?", "Blog posts, articles, press releases, case studies."),
            ("Can I choose platforms?", "Yes. Default is all 5, pick specific ones."),
            ("Do you handle images?", "Text content only. You add your own images."),
        ],
    },
    # -- 4. Document Extraction (doc_extract) --
    {
        "agent": "doc_extract",
        "title": "I will extract structured data from documents using AI",
        "category": "Programming & Tech > AI Services > AI Agents",
        "tags": ["document extraction", "ai ocr", "invoice processing",
                 "contract analysis", "data extraction", "document automation"],
        "description": (
            "AI Document Data Extraction Agent\n\n"
            "Send me invoices, contracts, or resumes and get clean, "
            "structured JSON data back.\n\n"
            "What You Get:\n"
            "- Entity extraction -- names, dates, amounts, addresses\n"
            "- Document classification -- auto-detects document type\n"
            "- Structured JSON output -- ready for database import\n"
            "- Confidence scores -- reliability rating on every field\n"
            "- QA verification -- accuracy checked before delivery\n\n"
            "Supported: invoices, contracts, resumes/CVs, receipts, POs.\n\n"
            "No more manual data entry. No more copy-paste."
        ),
        "packages": {
            "Basic ($5)": "5 documents extracted -- JSON + confidence scores",
            "Standard ($15)": "25 documents -- batch + CSV export + summary",
            "Premium ($40)": "100 documents -- full batch + custom field mapping",
        },
        "faq": [
            ("What languages?", "English primarily. Other languages on request."),
            ("Can I send PDFs?", "Send text content. For PDF-to-text I recommend OCR tools."),
            ("How accurate?", "85%+ accuracy with confidence scores on every field."),
        ],
    },
    # -- 5. Lead Generation (lead_gen) --
    {
        "agent": "lead_gen",
        "title": "I will build AI-researched B2B lead lists scored to your ICP",
        "category": "Sales & Marketing > Lead Generation",
        "tags": ["lead generation", "b2b leads", "prospect list",
                 "lead research", "sales leads", "icp targeting"],
        "description": (
            "AI B2B Lead Generation Agent\n\n"
            "I build targeted B2B lead lists using an AI research agent that "
            "identifies, scores, and qualifies prospects based on your ideal "
            "customer profile.\n\n"
            "What You Get:\n"
            "- Company name, website, industry, size, location\n"
            "- Decision-maker contacts (name, title, email pattern)\n"
            "- Lead score (1-100) based on ICP fit\n"
            "- Buying signals and pain point analysis\n"
            "- Recommended approach angle per lead\n"
            "- CSV + JSON export, CRM-ready\n\n"
            "Not scraped junk. Each lead is individually researched and scored."
        ),
        "packages": {
            "Basic ($10)": "10 qualified leads -- researched + scored + CSV",
            "Standard ($30)": "30 leads -- full research + approach angles",
            "Premium ($75)": "100 leads -- deep research + pain points + signals",
        },
        "faq": [
            ("What do you need?", "Your ICP: industry, company size, role, geography."),
            ("How are leads scored?", "AI scores fit (1-100) against your ICP criteria."),
            ("What CRMs?", "CSV/JSON works with Salesforce, HubSpot, Zoho, Pipedrive, etc."),
        ],
    },
    # -- 6. Email Marketing (email_marketing) --
    {
        "agent": "email_marketing",
        "title": "I will write AI email marketing sequences with A/B subject lines",
        "category": "Sales & Marketing > Email Marketing",
        "tags": ["email marketing", "email sequence", "drip campaign",
                 "newsletter", "mailchimp", "email copywriting"],
        "description": (
            "AI Email Marketing Sequences\n\n"
            "I write complete email marketing sequences -- welcome series, "
            "nurture campaigns, re-engagement, promotional, and cart abandonment.\n\n"
            "What You Get:\n"
            "- 5-7 email sequence (subject lines + body copy)\n"
            "- A/B variations for subject lines\n"
            "- Send timing recommendations\n"
            "- Segmentation suggestions\n"
            "- Merge tag placeholders (Mailchimp, Klaviyo, etc.)\n"
            "- Spam trigger check + readability score\n\n"
            "Frameworks: AIDA, PAS, BAB -- proven converters."
        ),
        "packages": {
            "Basic ($10)": "3-email sequence + 1 A/B variation",
            "Standard ($25)": "5-email sequence + 2 A/B variations + timing",
            "Premium ($60)": "7-email sequence + 3 A/B + segmentation strategy",
        },
        "faq": [
            ("What platforms?", "Works with Mailchimp, Klaviyo, ConvertKit, etc."),
            ("What types?", "Welcome, nurture, re-engagement, promo, cart abandonment."),
            ("Do you send the emails?", "I provide the copy. You load into your ESP."),
        ],
    },
    # -- 7. SEO Content (seo_content) --
    {
        "agent": "seo_content",
        "title": "I will write SEO blog posts optimized for Google rankings using AI",
        "category": "Writing & Translation > Articles & Blog Posts",
        "tags": ["seo article", "blog writing", "seo content",
                 "content writing", "keyword article", "blog post"],
        "description": (
            "AI SEO Blog Posts & Articles\n\n"
            "I produce SEO-optimized blog posts using a 3-stage AI pipeline: "
            "Keyword Research -> Content Writing -> QA Verification.\n\n"
            "What You Get:\n"
            "- Primary + secondary keyword targeting\n"
            "- SEO title tag (60 chars max) + meta description (155 chars max)\n"
            "- H1/H2/H3 heading structure\n"
            "- 1,500-3,000 word articles (your choice)\n"
            "- Internal linking suggestions\n"
            "- Markdown + HTML export\n"
            "- Readability score (Flesch-Kincaid)\n\n"
            "No fluff. No keyword stuffing. Natural content that ranks AND converts."
        ),
        "packages": {
            "Basic ($10)": "1 article (1,500 words) + SEO meta + Markdown",
            "Standard ($30)": "3 articles (2,000 words each) + keywords + HTML",
            "Premium ($80)": "10 articles (2,000 words) + content strategy",
        },
        "faq": [
            ("Do you do keyword research?", "Yes -- primary + secondary keywords included."),
            ("What word count?", "1,500-3,000. You choose in order notes."),
            ("What niche?", "Any niche. AI adapts to your industry and audience."),
        ],
    },
    # -- 8. Social Media (social_media) --
    {
        "agent": "social_media",
        "title": "I will create AI-optimized social media posts for any platform",
        "category": "Sales & Marketing > Social Media Marketing",
        "tags": ["social media posts", "linkedin posts", "instagram captions",
                 "social media content", "content calendar", "social media manager"],
        "description": (
            "AI Social Media Content Agent\n\n"
            "I generate platform-optimized social media content that "
            "respects character limits, hashtag best practices, and engagement patterns.\n\n"
            "What You Get Per Post:\n"
            "- Platform-specific copy (LinkedIn, Twitter/X, Instagram, Facebook, TikTok)\n"
            "- Hashtag recommendations (broad + niche mix)\n"
            "- Posting time suggestions\n"
            "- CTA options\n"
            "- Image/visual direction notes\n"
            "- Content calendar format\n\n"
            "Consistent brand voice across all platforms. QA verified."
        ),
        "packages": {
            "Basic ($5)": "10 posts for 2 platforms + hashtags",
            "Standard ($20)": "30 posts for 3 platforms + calendar",
            "Premium ($50)": "60 posts for 5 platforms + brand guide",
        },
        "faq": [
            ("Which platforms?", "LinkedIn, Twitter/X, Instagram, Facebook, TikTok."),
            ("Do you post them?", "I provide the copy. You post or schedule."),
            ("Can you match my brand voice?", "Yes -- send me 3-5 examples of your style."),
        ],
    },
    # -- 9. Data Entry (data_entry) --
    {
        "agent": "data_entry",
        "title": "I will do AI-powered data entry, cleaning, and formatting fast",
        "category": "Data > Data Entry",
        "tags": ["data entry", "data cleaning", "data processing",
                 "excel data entry", "spreadsheet", "csv processing"],
        "description": (
            "AI Data Entry & Cleaning Agent\n\n"
            "I process and clean raw data -- messy spreadsheets, unstructured "
            "text, PDFs -- and deliver clean, structured output.\n\n"
            "What You Get:\n"
            "- Data standardization (dates, names, addresses, currencies)\n"
            "- Duplicate detection and removal\n"
            "- Missing value handling (flagged or imputed)\n"
            "- Format conversion (CSV, JSON, Excel)\n"
            "- Validation report with error counts\n\n"
            "Handles: contact lists, product catalogs, survey data, "
            "spreadsheet cleanup, form submissions, and any tabular data."
        ),
        "packages": {
            "Basic ($5)": "200 rows -- cleaned + formatted + validated",
            "Standard ($15)": "1,000 rows -- dedup + standardize + export",
            "Premium ($40)": "5,000 rows -- full processing + validation report",
        },
        "faq": [
            ("What formats?", "CSV, Excel, JSON, plain text, or paste directly."),
            ("How fast?", "Basic same day. Standard 24h. Premium 48h."),
            ("Can you do recurring?", "Yes -- ask about monthly retainer packages."),
        ],
    },
    # -- 10. Web Scraping (web_scraper) --
    {
        "agent": "web_scraper",
        "title": "I will scrape and extract structured data from any website using AI",
        "category": "Programming & Tech > Data Mining & Scraping",
        "tags": ["web scraping", "data scraping", "data mining",
                 "web data extraction", "web crawler", "price scraping"],
        "description": (
            "AI Web Scraping Agent\n\n"
            "I extract structured data from web pages -- product listings, "
            "contact info, directories, job boards, real estate listings.\n\n"
            "What You Get:\n"
            "- Structured data in JSON + CSV\n"
            "- Custom field mapping (name, price, URL, etc.)\n"
            "- Data quality scoring\n"
            "- Duplicate removal\n"
            "- QA validation report\n\n"
            "Send me the page content or URL and tell me what data you need."
        ),
        "packages": {
            "Basic ($5)": "10 pages -- extracted + JSON + CSV",
            "Standard ($20)": "50 pages -- custom fields + dedup + report",
            "Premium ($50)": "200 pages -- full extraction + quality scoring",
        },
        "faq": [
            ("What sites?", "Any public website. I extract from provided content."),
            ("Is it legal?", "I scrape publicly available data only. No login bypass."),
            ("Recurring?", "Ask about automation for scheduled scraping."),
        ],
    },
    # -- 11. CRM Management (crm_ops) --
    {
        "agent": "crm_ops",
        "title": "I will clean and organize your CRM data using AI",
        "category": "Sales & Marketing > CRM",
        "tags": ["crm cleanup", "salesforce admin", "hubspot",
                 "crm data", "contact cleanup", "data deduplication"],
        "description": (
            "AI CRM Data Management Agent\n\n"
            "I clean, deduplicate, and organize your CRM data -- contacts, "
            "deals, pipeline stages, and company records.\n\n"
            "What You Get:\n"
            "- Duplicate detection and merge recommendations\n"
            "- Contact standardization (names, emails, phones, titles)\n"
            "- Missing field identification\n"
            "- Lead scoring suggestions\n"
            "- Pipeline stage validation\n"
            "- Import-ready CSV/JSON export\n\n"
            "Works with: Salesforce, HubSpot, Zoho, Pipedrive, or spreadsheets."
        ),
        "packages": {
            "Basic ($10)": "250 records -- dedup + standardize + export",
            "Standard ($25)": "1,000 records -- full cleanup + lead scoring",
            "Premium ($60)": "5,000 records -- deep clean + merge + validation",
        },
        "faq": [
            ("Which CRMs?", "Salesforce, HubSpot, Zoho, Pipedrive, or any CSV export."),
            ("Do you need login access?", "No -- export your data as CSV, I process it."),
            ("Can you import back?", "I provide import-ready files for your CRM."),
        ],
    },
    # -- 12. Bookkeeping (bookkeeping) --
    {
        "agent": "bookkeeping",
        "title": "I will categorize expenses and reconcile bank statements using AI",
        "category": "Finance > Accounting & Bookkeeping",
        "tags": ["bookkeeping", "expense categorization", "bank reconciliation",
                 "quickbooks", "xero", "accounting data entry"],
        "description": (
            "AI Bookkeeping Agent\n\n"
            "I categorize expenses, reconcile bank statements, and organize "
            "financial records using an AI agent trained on standard chart of accounts.\n\n"
            "What You Get:\n"
            "- Expense categorization (mapped to your chart of accounts)\n"
            "- Transaction matching and reconciliation\n"
            "- Missing receipt flagging\n"
            "- Monthly summary with totals by category\n"
            "- QBO/Xero-compatible export format\n\n"
            "Disclaimer: Data processing assistance only. "
            "All output should be reviewed by your accountant."
        ),
        "packages": {
            "Basic ($10)": "100 transactions -- categorized + summary",
            "Standard ($25)": "500 transactions -- reconciled + QBO export",
            "Premium ($60)": "2,000 transactions -- full reconciliation + report",
        },
        "faq": [
            ("What format?", "Bank CSV, credit card export, PayPal/Stripe export."),
            ("Is this tax advice?", "No -- data processing only. Review with your CPA."),
            ("Monthly service?", "Yes -- ask about monthly retainer pricing."),
        ],
    },
    # -- 13. Proposal Writing (proposal_writer) --
    {
        "agent": "proposal_writer",
        "title": "I will write professional project proposals using AI",
        "category": "Writing & Translation > Business Writing",
        "tags": ["proposal writing", "bid writing", "rfp response",
                 "business proposal", "project proposal", "grant writing"],
        "description": (
            "AI Proposal Writer Agent\n\n"
            "I write compelling project proposals and bid responses that "
            "win more projects.\n\n"
            "What You Get:\n"
            "- Executive summary with hook\n"
            "- Problem statement and proposed solution\n"
            "- Scope of work with deliverables table\n"
            "- Timeline with milestones\n"
            "- Pricing breakdown (tiered options)\n"
            "- Social proof section\n"
            "- Markdown export, ready to format\n\n"
            "Types: Project proposals, RFP responses, service agreements, "
            "grant applications, partnership proposals."
        ),
        "packages": {
            "Basic ($10)": "1 proposal (3-5 pages) -- structured + Markdown",
            "Standard ($30)": "3 proposals -- full scope + pricing tiers",
            "Premium ($70)": "7 proposals -- executive quality + case studies",
        },
        "faq": [
            ("What do you need?", "Project brief, your services, and target client info."),
            ("What format?", "Markdown + optional Word/PDF conversion."),
            ("RFP responses?", "Yes -- send the RFP and I'll tailor the proposal."),
        ],
    },
    # -- 14. Product Descriptions (product_desc) --
    {
        "agent": "product_desc",
        "title": "I will write converting product descriptions for Amazon Shopify Etsy",
        "category": "Writing & Translation > Product Descriptions",
        "tags": ["product descriptions", "amazon listing", "shopify product",
                 "etsy listing", "product copy", "e-commerce copy"],
        "description": (
            "AI Product Description Writer\n\n"
            "I write converting product descriptions optimized for your selling "
            "platform -- Amazon, Shopify, Etsy, eBay, or WooCommerce.\n\n"
            "What You Get:\n"
            "- Platform-optimized product title\n"
            "- Feature bullet points (Amazon ALL CAPS format)\n"
            "- Long-form description with benefits-first copy\n"
            "- SEO meta title + description\n"
            "- A/B headline variations\n"
            "- Keyword integration\n\n"
            "Character limits enforced per platform. No prohibited claims."
        ),
        "packages": {
            "Basic ($5)": "5 product descriptions -- title + bullets + description",
            "Standard ($15)": "20 products -- full optimization + SEO meta",
            "Premium ($40)": "75 products -- bulk processing + A/B variations",
        },
        "faq": [
            ("Which platforms?", "Amazon, Shopify, Etsy, eBay, WooCommerce."),
            ("Do you need product images?", "No -- just product details and specifications."),
            ("Do you do SEO keywords?", "Yes -- included or I use your target keywords."),
        ],
    },
    # -- 15. Resume Writing (resume_writer) --
    {
        "agent": "resume_writer",
        "title": "I will write an ATS-optimized resume that beats applicant tracking systems",
        "category": "Writing & Translation > Resume Writing",
        "tags": ["resume writing", "cv writing", "ats resume",
                 "professional resume", "cover letter", "career services"],
        "description": (
            "AI Resume Writer Agent\n\n"
            "I write ATS-optimized resumes that pass applicant tracking systems "
            "and impress recruiters.\n\n"
            "What You Get:\n"
            "- ATS-friendly format and layout\n"
            "- CAR format bullets (Challenge-Action-Result)\n"
            "- 70%+ bullets with quantified achievements\n"
            "- 8-12 targeted ATS keywords for your role\n"
            "- Strong action verbs throughout\n"
            "- QA verified for ATS compliance\n\n"
            "Levels: Entry-level, Mid-career, Senior, Executive.\n"
            "Styles: Chronological, Functional, Combination, Modern."
        ),
        "packages": {
            "Basic ($10)": "1 resume -- ATS-optimized + keyword targeted",
            "Standard ($25)": "Resume + cover letter + LinkedIn summary",
            "Premium ($50)": "Resume + cover letter + LinkedIn + 3 role variations",
        },
        "faq": [
            ("What do you need?", "Your current resume or career details + target role."),
            ("What format?", "Markdown + optional Word/PDF conversion."),
            ("Entry-level OK?", "Yes -- I focus on potential, skills, and projects."),
        ],
    },
    # -- 16. Ad Copy (ad_copy) --
    {
        "agent": "ad_copy",
        "title": "I will write high converting ad copy for Google Facebook LinkedIn ads",
        "category": "Sales & Marketing > Social Media Advertising",
        "tags": ["ad copy", "google ads", "facebook ads",
                 "ppc copy", "linkedin ads", "ad copywriting"],
        "description": (
            "AI Ad Copy Writer Agent\n\n"
            "I write high-converting ad copy for every major platform -- "
            "Google, Facebook, Instagram, LinkedIn, TikTok, Twitter, YouTube, Pinterest.\n\n"
            "What You Get:\n"
            "- Headlines + descriptions within character limits\n"
            "- A/B variations (benefit-led + pain-point)\n"
            "- Sitelink copy (Google)\n"
            "- Targeting suggestions (keywords + audiences)\n"
            "- Platform policy compliance check\n\n"
            "Character limits enforced: Google 30/90, Facebook 40/125, "
            "LinkedIn 70/150, Twitter 70/280, TikTok 100/100."
        ),
        "packages": {
            "Basic ($10)": "1 campaign -- headlines + descriptions + 2 A/B variants",
            "Standard ($25)": "3 campaigns -- multi-platform + targeting suggestions",
            "Premium ($60)": "8 campaigns -- full creative suite + negatives + audiences",
        },
        "faq": [
            ("Which platforms?", "Google, Facebook, Instagram, LinkedIn, TikTok, Twitter, YouTube, Pinterest."),
            ("Do you manage ads?", "I write the copy. You manage the campaigns."),
            ("What about landing pages?", "Ad copy only. Ask about landing page copy add-on."),
        ],
    },
    # -- 17. Market Research (market_research) --
    {
        "agent": "market_research",
        "title": "I will create an AI market research report with competitive analysis",
        "category": "Business > Market Research",
        "tags": ["market research", "competitive analysis", "swot analysis",
                 "market sizing", "industry analysis", "business analysis"],
        "description": (
            "AI Market Research Reports\n\n"
            "I produce comprehensive market research reports -- market sizing "
            "(TAM/SAM/SOM), competitive landscape, customer segmentation, "
            "trend analysis, and SWOT.\n\n"
            "What You Get:\n"
            "- Market overview (size, growth rate, key drivers)\n"
            "- Competitive landscape (leaders, gaps, emerging players)\n"
            "- Customer analysis (segments, pain points, willingness to pay)\n"
            "- Trend analysis with impact ratings\n"
            "- SWOT analysis (3+ per quadrant)\n"
            "- Actionable recommendations with priority\n\n"
            "Disclaimer: Based on publicly available data and AI analysis."
        ),
        "packages": {
            "Basic ($15)": "Quick overview (3-5 pages) -- market + competitors",
            "Standard ($40)": "Standard report (8-12 pages) -- full analysis + SWOT",
            "Premium ($100)": "Deep dive (15-25 pages) -- comprehensive + recommendations",
        },
        "faq": [
            ("What industries?", "Any industry. Tell me your market and I'll research it."),
            ("Is this primary research?", "No -- secondary research using public data + AI analysis."),
            ("How current?", "Based on latest available public information."),
        ],
    },
    # -- 18. Business Plan (business_plan) --
    {
        "agent": "business_plan",
        "title": "I will write an investor-ready business plan with financial projections",
        "category": "Business > Business Plans",
        "tags": ["business plan", "startup plan", "financial projections",
                 "investor pitch", "fundraising", "lean canvas"],
        "description": (
            "AI Business Plan Writer Agent\n\n"
            "I write investor-ready business plans with financial projections, "
            "market analysis, go-to-market strategy, and risk assessment.\n\n"
            "What You Get:\n"
            "- Executive summary\n"
            "- Company description (mission, vision, values, stage)\n"
            "- Problem/solution with unique value proposition\n"
            "- Market analysis (TAM/SAM/SOM)\n"
            "- Business model with unit economics (LTV, CAC)\n"
            "- Go-to-market strategy (phased)\n"
            "- 3-year financial projections (revenue, expenses, net)\n"
            "- Funding requirements with use-of-funds breakdown\n"
            "- Risk assessment with mitigation strategies\n\n"
            "Types: Startup, expansion, investor pitch, loan application, lean canvas."
        ),
        "packages": {
            "Basic ($20)": "Lean canvas -- 3-5 pages -- key sections",
            "Standard ($50)": "Full plan -- 15-20 pages -- financials included",
            "Premium ($120)": "Investor-ready -- 25-35 pages -- pitch-grade quality",
        },
        "faq": [
            ("What do you need?", "Your business idea, industry, stage, and funding goals."),
            ("Are financials real?", "Estimates for planning. Review with your accountant."),
            ("Pitch deck too?", "Business plan only. Ask about pitch deck content add-on."),
        ],
    },
    # -- 19. Press Release (press_release) --
    {
        "agent": "press_release",
        "title": "I will write an AP-style press release ready for distribution",
        "category": "Writing & Translation > Press Releases",
        "tags": ["press release", "pr writing", "media release",
                 "press release writer", "public relations", "news release"],
        "description": (
            "AI Press Release Writer Agent\n\n"
            "I write AP-style press releases ready for PR Newswire, "
            "Business Wire, or direct media outreach.\n\n"
            "What You Get:\n"
            "- AP-style headline + subheadline\n"
            "- Proper dateline (CITY, State -- Date)\n"
            "- Lead paragraph (WHO, WHAT, WHEN, WHERE, WHY)\n"
            "- Inverted pyramid body structure\n"
            "- 2 spokesperson quotes (properly attributed)\n"
            "- Company boilerplate (50-100 words)\n"
            "- Distribution notes (wire, tags, target outlets)\n"
            "- SEO meta for web distribution\n\n"
            "Types: Product launch, partnership, funding, expansion, "
            "hire, event, milestone, award."
        ),
        "packages": {
            "Basic ($10)": "1 press release -- AP style + distribution notes",
            "Standard ($25)": "3 releases -- wire-ready + SEO meta",
            "Premium ($60)": "7 releases -- full PR campaign + target outlets",
        },
        "faq": [
            ("What format?", "AP style -- ready for wire distribution or direct pitch."),
            ("Do you distribute?", "I write the release. You handle distribution."),
            ("Quotes?", "I draft quotes. You approve or provide your own."),
        ],
    },
    # -- 20. Tech Docs (tech_docs) --
    {
        "agent": "tech_docs",
        "title": "I will write technical documentation API docs READMEs and user guides",
        "category": "Programming & Tech > Other",
        "tags": ["technical documentation", "api documentation", "readme",
                 "user guide", "software documentation", "developer docs"],
        "description": (
            "AI Technical Documentation Writer Agent\n\n"
            "I write clear, structured technical documentation -- API references, "
            "user guides, READMEs, tutorials, runbooks, and SDK guides.\n\n"
            "What You Get:\n"
            "- Audience-appropriate content (devs, DevOps, end-users)\n"
            "- Runnable code examples (not pseudo-code)\n"
            "- API endpoint docs (method, path, params, request/response)\n"
            "- Prerequisites and setup instructions\n"
            "- Troubleshooting section (3+ common issues)\n"
            "- Configuration reference (env vars, config files)\n"
            "- Full Markdown export\n\n"
            "Types: API reference, user guide, README, how-to, tutorial, "
            "architecture, changelog, runbook, SDK guide."
        ),
        "packages": {
            "Basic ($10)": "1 document -- structured + Markdown + code examples",
            "Standard ($30)": "3 documents or full API reference",
            "Premium ($75)": "Full documentation suite -- 5+ docs + glossary",
        },
        "faq": [
            ("What do you need?", "Your codebase, API specs, or product description."),
            ("What languages?", "Python, JavaScript, TypeScript, Go, Java, C#, etc."),
            ("Do you test the code?", "Code examples are syntax-verified. You test runtime."),
        ],
    },
]


# ---------------------------------------------------------------
#  OUTPUT FUNCTIONS
# ---------------------------------------------------------------

def print_gigs():
    """Print all 20 Fiverr gig listings."""
    print(f"\n{'='*70}")
    print("  FIVERR -- 20 GIG LISTINGS")
    print(f"{'='*70}")
    for i, gig in enumerate(FIVERR_GIGS, 1):
        print(f"\n{'_'*70}")
        print(f"  GIG {i}: {gig['title']}")
        print(f"  Agent: {gig['agent']} | Category: {gig['category']}")
        print(f"  Tags: {', '.join(gig['tags'])}")
        print(f"{'_'*70}")
        print(f"\n{gig['description']}")
        print(f"\n  PACKAGES:")
        for pkg, desc in gig["packages"].items():
            print(f"    {pkg}: {desc}")
        print(f"\n  FAQ:")
        for q, a in gig["faq"]:
            print(f"    Q: {q}")
            print(f"    A: {a}")
    print(f"\n{'='*70}\n")


def print_agent(agent_key: str):
    """Print one gig by agent name."""
    gig = next((g for g in FIVERR_GIGS if agent_key in g["agent"]), None)
    if not gig:
        print(f"Unknown agent: {agent_key}")
        print(f"Available: {', '.join(g['agent'] for g in FIVERR_GIGS)}")
        return
    print(f"\n  [{gig['agent'].upper()}] {gig['title']}")
    print(f"  Category: {gig['category']}")
    print(f"\n{gig['description']}")
    print(f"\n  PACKAGES:")
    for pkg, desc in gig["packages"].items():
        print(f"    {pkg}: {desc}")


def save_all():
    """Save all gig listings to JSON."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "fiverr_gigs_all.json"
    path.write_text(json.dumps(FIVERR_GIGS, indent=2), encoding="utf-8")
    print(f"  [SAVED] {path}")
    for i, gig in enumerate(FIVERR_GIGS, 1):
        p = OUTPUT_DIR / f"fiverr_gig_{i}_{gig['agent']}.json"
        p.write_text(json.dumps(gig, indent=2), encoding="utf-8")
        print(f"  [SAVED] {p.name}")
    print(f"\n  All files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fiverr 20-Gig Deployment")
    parser.add_argument("--agent", default="", help="Show one agent's gig")
    parser.add_argument("--save", action="store_true", help="Save to JSON")
    args = parser.parse_args()

    if args.agent:
        print_agent(args.agent)
    elif args.save:
        save_all()
    else:
        print_gigs()
