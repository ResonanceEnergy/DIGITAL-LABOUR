"""Smoke Test — Upwork Platform: 100 Job Posts vs Scoring + Matching Pipeline.

Loads real scraped Upwork jobs + synthetic jobs covering all 20 agent
services, then tests:
  1. score_job()          — keyword scoring (0-1)
  2. match_job_to_service — service matching with confidence
  3. generate_proposal()  — proposal generation for every match
  4. Coverage             — all 20 services must match at least 1 job
  5. Timing               — total pipeline speed

Usage:
    python -m tests.smoke_test_upwork
    python -m tests.smoke_test_upwork --verbose
    python -m tests.smoke_test_upwork --report
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from campaign.upwork_deploy import UPWORK_SERVICES, SPECIALIZED_PROFILES

# ── Inline scoring (from automation/upwork_jobhunt.py, avoids playwright import) ──
CORE_KEYWORDS = [
    "ai agent", "chatbot", "automation", "automate", "python",
    "openai", "gpt", "claude", "gemini", "langchain",
    "fastapi", "data extraction", "web scraping", "api",
]
BONUS_KEYWORDS = [
    "nlp", "machine learning", "lead generation", "email automation",
    "content", "seo", "crm", "sales automation", "support", "ticket",
    "workflow", "pipeline", "backend", "scrape", "n8n",
]
NEGATIVE_KEYWORDS = [
    "wordpress", "shopify theme", "php developer", "react native",
    "ios app", "android app", "unity", "unreal engine",
    "video editing", "graphic design", "illustration",
    "solidity", "blockchain", "smart contract",
]


def score_job(title: str, description: str) -> float:
    """Score a job 0-1 based on keyword relevance (mirrors upwork_jobhunt.score_job)."""
    text = f"{title} {description}".lower()
    core_hits = sum(1 for kw in CORE_KEYWORDS if kw in text)
    bonus_hits = sum(1 for kw in BONUS_KEYWORDS if kw in text)
    negs = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    raw = (core_hits * 0.10) + (bonus_hits * 0.04) - (negs * 0.15)
    return round(max(0.0, min(1.0, raw)), 2)


def generate_proposal(title: str, description: str) -> str:
    """Generate a tailored proposal (mirrors upwork_jobhunt.generate_proposal)."""
    text = f"{title} {description}".lower()
    pitch_blocks = []
    if any(kw in text for kw in ["sales", "outreach", "lead", "cold email", "b2b"]):
        pitch_blocks.append("AI sales outreach pipeline — 50+ personalized leads/hour.")
    if any(kw in text for kw in ["support", "ticket", "customer service", "helpdesk"]):
        pitch_blocks.append("AI support ticket resolver — 200+ tickets/hour, <10s response.")
    if any(kw in text for kw in ["content", "blog", "social media", "seo", "writing"]):
        pitch_blocks.append("Content repurposing engine — 1 piece to 5 platform formats.")
    if any(kw in text for kw in ["data extract", "document", "invoice", "pdf", "scraping", "scrape"]):
        pitch_blocks.append("Document extraction agents — structured JSON/CSV, 95%+ accuracy.")
    if any(kw in text for kw in ["chatbot", "chat bot", "conversational", "ai assistant"]):
        pitch_blocks.append("Production chatbots with GPT-4o/Claude, multi-turn memory.")
    if any(kw in text for kw in ["automation", "workflow", "automate", "pipeline"]):
        pitch_blocks.append("End-to-end automation pipelines via REST APIs and webhooks.")
    if any(kw in text for kw in ["python", "fastapi", "api", "backend"]):
        pitch_blocks.append("Senior Python developer — FastAPI, async, cloud deployment.")
    if any(kw in text for kw in ["openai", "gpt", "claude", "gemini", "llm", "langchain"]):
        pitch_blocks.append("Multi-LLM integration — GPT-4o, Claude, Gemini with failover.")
    if not pitch_blocks:
        pitch_blocks.append("Production AI systems with Python, FastAPI, and multi-LLM integration.")
    return f"Hi,\n\n{chr(10).join(pitch_blocks[:3])}\n\n— BIT RAGE SYSTEMS"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UPWORK SERVICE MATCHING ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Build keyword rules from UPWORK_SERVICES (mirrors AUTOBID_RULES logic)
UPWORK_MATCH_RULES = [
    {
        "agent": "sales_ops",
        "match_any": ["cold email", "outreach", "sales email", "b2b email",
                      "email sequence", "sales sequence", "prospecting email",
                      "sales outreach", "lead outreach"],
        "exclude": ["cold calling", "phone", "telemarketing"],
    },
    {
        "agent": "support",
        "match_any": ["customer support", "ticket", "help desk", "helpdesk",
                      "support agent", "ticket resolution", "zendesk", "freshdesk",
                      "intercom", "support ticket"],
        "exclude": ["phone support", "call center"],
    },
    {
        "agent": "content_repurpose",
        "match_any": ["content repurpos", "blog to social", "repurpose content",
                      "content transform", "multi-platform content",
                      "repurpose blog"],
        "exclude": ["video editing", "graphic design"],
    },
    {
        "agent": "doc_extract",
        "match_any": ["document extract", "invoice processing", "contract analysis",
                      "data extraction", "pdf extract", "ocr", "document parsing",
                      "document data"],
        "exclude": ["handwriting", "physical documents"],
    },
    {
        "agent": "lead_gen",
        "match_any": ["lead generation", "lead list", "b2b leads", "prospect list",
                      "lead research", "qualified leads", "sales leads",
                      "prospect research"],
        "exclude": ["telemarketing", "cold calling"],
    },
    {
        "agent": "email_marketing",
        "match_any": ["email marketing", "email campaign", "drip campaign", "newsletter",
                      "email sequence", "welcome email", "nurture", "mailchimp",
                      "klaviyo", "email copywriting"],
        "exclude": ["cold email", "spam", "bulk email"],
    },
    {
        "agent": "seo_content",
        "match_any": ["seo article", "seo blog", "seo content", "blog post",
                      "blog writing", "keyword article", "content writing seo",
                      "article writing", "seo optimized"],
        "exclude": ["link building", "backlinks", "technical seo audit"],
    },
    {
        "agent": "social_media",
        "match_any": ["social media post", "social media content", "instagram caption",
                      "linkedin post", "twitter content", "social media marketing",
                      "content calendar", "social media manager"],
        "exclude": ["social media ads", "paid social", "graphic design"],
    },
    {
        "agent": "data_entry",
        "match_any": ["data entry", "data cleaning", "data processing", "spreadsheet",
                      "excel data", "csv processing", "data formatting",
                      "data migration", "copy paste", "typing"],
        "exclude": ["web development", "programming"],
    },
    {
        "agent": "web_scraper",
        "match_any": ["web scraping", "data scraping", "data mining", "scrape website",
                      "web data", "screen scraping", "web crawler", "price scraping",
                      "extract from website"],
        "exclude": ["hacking", "bypass captcha"],
    },
    {
        "agent": "crm_ops",
        "match_any": ["crm", "salesforce", "hubspot", "zoho crm", "pipedrive",
                      "crm cleanup", "crm data", "crm migration", "contact cleanup"],
        "exclude": ["crm development", "custom crm build"],
    },
    {
        "agent": "bookkeeping",
        "match_any": ["bookkeeping", "expense categoriz", "bank reconcil", "quickbooks",
                      "xero", "accounting data", "financial records", "transaction categor"],
        "exclude": ["tax filing", "audit", "cpa", "tax return"],
    },
    {
        "agent": "proposal_writer",
        "match_any": ["proposal writ", "bid writing", "rfp response", "business proposal",
                      "project proposal", "grant writing", "tender response"],
        "exclude": ["government contract", "legal brief"],
    },
    {
        "agent": "product_desc",
        "match_any": ["product description", "amazon listing", "shopify product",
                      "etsy listing", "ebay description", "product copy",
                      "e-commerce copy", "product listing"],
        "exclude": ["product photography", "product design"],
    },
    {
        "agent": "resume_writer",
        "match_any": ["resume writ", "cv writ", "resume", "curriculum vitae",
                      "cover letter", "linkedin profile", "ats resume"],
        "exclude": ["resume website", "portfolio website"],
    },
    {
        "agent": "ad_copy",
        "match_any": ["ad copy", "google ads", "facebook ads", "ppc copy",
                      "linkedin ads", "ad copywriting", "social media ads",
                      "tiktok ads", "ppc", "paid advertising copy"],
        "exclude": ["ad management", "campaign management", "media buying"],
    },
    {
        "agent": "market_research",
        "match_any": ["market research", "competitive analysis", "swot analysis",
                      "market sizing", "industry analysis", "feasibility study",
                      "market report", "competitor research"],
        "exclude": ["primary research", "survey design", "focus group"],
    },
    {
        "agent": "business_plan",
        "match_any": ["business plan", "startup plan", "financial projection",
                      "investor pitch", "fundraising plan", "lean canvas",
                      "business model", "pitch deck content"],
        "exclude": ["pitch deck design", "financial audit"],
    },
    {
        "agent": "press_release",
        "match_any": ["press release", "pr writing", "media release", "news release",
                      "publicity", "pr newswire", "press announcement"],
        "exclude": ["press kit design", "media buying"],
    },
    {
        "agent": "tech_docs",
        "match_any": ["technical documentation", "api documentation", "readme",
                      "user guide", "software documentation", "developer docs",
                      "technical writing", "sdk documentation", "runbook"],
        "exclude": ["technical support", "bug fixing"],
    },
]


def match_job_to_service(title: str, description: str) -> list[dict]:
    """Match an Upwork job post to services based on keyword rules.

    Returns list of matches sorted by confidence (highest first).
    """
    text = f"{title} {description}".lower()
    matches = []

    for rule in UPWORK_MATCH_RULES:
        if any(ex.lower() in text for ex in rule["exclude"]):
            continue

        any_hits = sum(1 for kw in rule["match_any"] if kw.lower() in text)
        if any_hits == 0:
            continue

        confidence = min(any_hits / max(len(rule["match_any"]) * 0.3, 1), 1.0)
        if confidence >= 0.7:
            svc = next((s for s in UPWORK_SERVICES if s["agent"] == rule["agent"]), None)
            matches.append({
                "agent": rule["agent"],
                "confidence": round(confidence, 2),
                "service_title": svc["title"] if svc else "",
                "proposal_template": svc["proposal_template"] if svc else "",
            })

    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return matches


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LOAD REAL SCRAPED JOBS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_upwork_jobs() -> list[dict]:
    """Load scraped Upwork jobs from JSONL, deduplicate by title."""
    job_log = PROJECT / "data" / "upwork_jobs" / "job_log.jsonl"
    if not job_log.exists():
        print("[WARN] No Upwork job log found — using synthetic only")
        return []
    seen_titles = set()
    jobs = []
    for line in job_log.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        job = json.loads(line)
        key = job.get("title", "").strip().lower()
        if key and key not in seen_titles:
            seen_titles.add(key)
            jobs.append({
                "title": job.get("title", ""),
                "description": job.get("description", ""),
                "budget": job.get("budget", ""),
                "skills": job.get("skills", []),
                "source": "upwork_scraped",
            })
    return jobs


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SYNTHETIC JOBS — targeting all 20 Upwork services
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYNTHETIC_JOBS = [
    # ── sales_ops ───────────────────────────────────────────────
    {"title": "Cold Email Specialist for B2B SaaS Lead Outreach",
     "description": "Build cold email sequences targeting SaaS founders. "
                    "Research each prospect and personalize sales emails. 500 leads.",
     "expected_agent": "sales_ops"},
    {"title": "Personalized Sales Email Sequence Writer",
     "description": "Create 3-email outreach sequences for B2B sales team. "
                    "Sales outreach with prospect research and cold email personalization.",
     "expected_agent": "sales_ops"},

    # ── support ─────────────────────────────────────────────────
    {"title": "Zendesk Ticket Triage & Draft Response System",
     "description": "Process Zendesk support tickets. Categorize by type, score severity, "
                    "draft customer support responses. 200 tickets/week.",
     "expected_agent": "support"},
    {"title": "AI Help Desk Agent for Customer Ticket Resolution",
     "description": "Automated ticket resolution for helpdesk. Handle billing, technical, "
                    "and account support ticket inquiries with severity scoring.",
     "expected_agent": "support"},

    # ── content_repurpose ───────────────────────────────────────
    {"title": "Repurpose Blog Content into Social Media Posts",
     "description": "Take 10 blog posts and repurpose content into LinkedIn, Twitter, "
                    "Instagram formats. Multi-platform content repurposing needed.",
     "expected_agent": "content_repurpose"},
    {"title": "Content Transformation Specialist — Blog to Social",
     "description": "Transform long-form articles into platform-optimized social content. "
                    "Blog to social media content repurposing for 20 articles.",
     "expected_agent": "content_repurpose"},

    # ── doc_extract ─────────────────────────────────────────────
    {"title": "Invoice Processing — Extract Data from 500 PDF Invoices",
     "description": "Extract vendor name, date, amounts, line items from PDF invoices. "
                    "Document extraction and data extraction into structured JSON.",
     "expected_agent": "doc_extract"},
    {"title": "Contract Analysis — Extract Key Clauses",
     "description": "Extract parties, dates, payment terms from 50 contracts. "
                    "Document extraction and contract analysis with document parsing.",
     "expected_agent": "doc_extract"},

    # ── lead_gen ────────────────────────────────────────────────
    {"title": "B2B Lead Generation — 200 Qualified Leads",
     "description": "Build qualified lead list of 200 marketing decision-makers. "
                    "Lead generation with lead research and prospect research scoring.",
     "expected_agent": "lead_gen"},
    {"title": "Prospect Research — Sales Lead List Building",
     "description": "Research and compile qualified leads for sales team. "
                    "Lead generation with prospect list scoring and ICP fit analysis.",
     "expected_agent": "lead_gen"},

    # ── email_marketing ─────────────────────────────────────────
    {"title": "Email Marketing Campaign — Welcome Series for E-commerce",
     "description": "Create 5-email welcome sequence and nurture drip campaign for Shopify. "
                    "Email marketing with Mailchimp-compatible email sequences.",
     "expected_agent": "email_marketing"},
    {"title": "Drip Campaign Writer for SaaS Onboarding",
     "description": "Write 7-email drip campaign for SaaS user onboarding. "
                    "Email marketing sequence with engagement triggers and nurture flow.",
     "expected_agent": "email_marketing"},

    # ── seo_content ─────────────────────────────────────────────
    {"title": "SEO Blog Writer — 10 Articles for Fitness Website",
     "description": "Write 10 SEO blog posts targeting specific keywords for a fitness blog. "
                    "SEO article writing with keyword research, H2/H3 structure.",
     "expected_agent": "seo_content"},
    {"title": "Keyword-Optimized Article Writing for Tech Blog",
     "description": "Need 5 SEO content articles for a technology blog. Each 2000 words with "
                    "keyword article structure and SEO blog optimization.",
     "expected_agent": "seo_content"},

    # ── social_media ────────────────────────────────────────────
    {"title": "Social Media Content Calendar — 30 Days of Posts",
     "description": "Create a month of social media content for LinkedIn and Instagram. "
                    "Social media posts with content calendar and hashtag recommendations.",
     "expected_agent": "social_media"},
    {"title": "Instagram Captions and LinkedIn Posts for Firm",
     "description": "Write 60 social media content pieces — instagram caption and linkedin post "
                    "for consulting firm. Social media marketing with content calendar.",
     "expected_agent": "social_media"},

    # ── data_entry ──────────────────────────────────────────────
    {"title": "Data Entry — Clean and Organize 5000 Row Spreadsheet",
     "description": "Messy Excel spreadsheet with 5000 rows of contact data. "
                    "Data cleaning, data entry, standardization, data processing to CSV.",
     "expected_agent": "data_entry"},
    {"title": "Data Cleaning Project — Customer Database Formatting",
     "description": "Clean and standardize CSV customer database. Fix dates, names, addresses. "
                    "Data entry and data processing. Remove duplicates from spreadsheet.",
     "expected_agent": "data_entry"},

    # ── web_scraper ─────────────────────────────────────────────
    {"title": "Web Scraping — Extract Product Data from E-commerce",
     "description": "Scrape product listings from 5 e-commerce websites. Web scraping with "
                    "data mining. Extract name, price, description to structured data.",
     "expected_agent": "web_scraper"},
    {"title": "Data Scraping Service — Real Estate Listings",
     "description": "Web scraping for real estate listings data extraction from 3 property sites. "
                    "Data scraping with web data extraction to CSV.",
     "expected_agent": "web_scraper"},

    # ── crm_ops ─────────────────────────────────────────────────
    {"title": "CRM Data Cleanup — Salesforce Contact Deduplication",
     "description": "Clean up Salesforce CRM database. Deduplicate contacts, standardize "
                    "CRM data, merge duplicates. 3000 records need CRM cleanup.",
     "expected_agent": "crm_ops"},
    {"title": "HubSpot CRM Migration and Data Cleanup",
     "description": "Migrate and clean CRM data from spreadsheets to HubSpot. "
                    "Contact cleanup, deduplication, CRM data standardization.",
     "expected_agent": "crm_ops"},

    # ── bookkeeping ─────────────────────────────────────────────
    {"title": "Bookkeeping — Monthly Expense Categorization",
     "description": "Categorize 6 months of expenses. Bookkeeping with bank reconciliation, "
                    "expense categorization, QuickBooks export.",
     "expected_agent": "bookkeeping"},
    {"title": "Bank Reconciliation and Financial Records",
     "description": "Reconcile bank statements, categorize transactions with bookkeeping. "
                    "Xero-compatible financial records organization.",
     "expected_agent": "bookkeeping"},

    # ── proposal_writer ─────────────────────────────────────────
    {"title": "Business Proposal Writer — RFP Response for IT",
     "description": "Write compelling project proposal and RFP response for IT consulting. "
                    "Proposal writing with executive summary, scope, pricing.",
     "expected_agent": "proposal_writer"},
    {"title": "Grant Writing — Non-Profit Funding Application",
     "description": "Write a grant writing application for education non-profit. "
                    "Proposal writing with budget justification and impact measures.",
     "expected_agent": "proposal_writer"},

    # ── product_desc ────────────────────────────────────────────
    {"title": "Amazon Product Listing Writer — 50 Kitchen Gadgets",
     "description": "Write Amazon listing product descriptions for 50 kitchen products. "
                    "Product description with titles, bullet points, product copy.",
     "expected_agent": "product_desc"},
    {"title": "Shopify Product Description Writer — Fashion",
     "description": "Write Shopify product descriptions for 30 fashion items. "
                    "SEO-optimized product copy with e-commerce copy and product listing.",
     "expected_agent": "product_desc"},

    # ── resume_writer ───────────────────────────────────────────
    {"title": "Professional Resume Writer — Executive Level CV",
     "description": "Write ATS resume and cover letter for executive. "
                    "Resume writing with keyword targeting for VP of Marketing.",
     "expected_agent": "resume_writer"},
    {"title": "ATS Resume and LinkedIn Profile Optimization",
     "description": "Rewrite resume for ATS compliance. Resume writing with "
                    "cover letter and LinkedIn profile summary.",
     "expected_agent": "resume_writer"},

    # ── ad_copy ─────────────────────────────────────────────────
    {"title": "Google Ads Copy Writer — 10 PPC Campaigns",
     "description": "Write Google Ads copy for 10 PPC campaigns. Ad copywriting with "
                    "headlines, descriptions, sitelinks, and A/B variations.",
     "expected_agent": "ad_copy"},
    {"title": "Facebook Ads Copy + LinkedIn Ads for B2B SaaS",
     "description": "Write Facebook ads and LinkedIn ads copy for B2B SaaS. "
                    "Ad copywriting with platform-specific character limits and PPC.",
     "expected_agent": "ad_copy"},

    # ── market_research ─────────────────────────────────────────
    {"title": "Market Research Report — Competitive Analysis for Fintech",
     "description": "Comprehensive market research report with competitive analysis, "
                    "SWOT analysis, and market sizing for a fintech startup.",
     "expected_agent": "market_research"},
    {"title": "Industry Analysis — Healthcare Tech Market Report",
     "description": "Market research industry analysis covering healthcare technology. "
                    "Market sizing, competitor research, and feasibility study.",
     "expected_agent": "market_research"},

    # ── business_plan ───────────────────────────────────────────
    {"title": "Startup Business Plan with Financial Projections",
     "description": "Investor-ready business plan for food delivery startup. "
                    "Financial projection, business model, lean canvas, startup plan.",
     "expected_agent": "business_plan"},
    {"title": "Business Plan Writer — Fundraising Pitch Document",
     "description": "Business plan for seed fundraising round. Business model, "
                    "investor pitch content, startup plan with financial projection.",
     "expected_agent": "business_plan"},

    # ── press_release ───────────────────────────────────────────
    {"title": "Press Release Writer — Product Launch Announcement",
     "description": "AP-style press release for product launch. "
                    "PR newswire-ready media release with press announcement.",
     "expected_agent": "press_release"},
    {"title": "News Release for Partnership Announcement",
     "description": "Write press release announcing strategic partnership. "
                    "News release with spokesperson quotes for media release.",
     "expected_agent": "press_release"},

    # ── tech_docs ───────────────────────────────────────────────
    {"title": "API Documentation Writer — REST API Reference",
     "description": "Write comprehensive API documentation for REST API. 20 endpoints. "
                    "Technical writing with developer docs and code examples.",
     "expected_agent": "tech_docs"},
    {"title": "Software Documentation — User Guide and README",
     "description": "Write user guide and README for open-source Python tool. "
                    "Technical documentation with software documentation and setup.",
     "expected_agent": "tech_docs"},

    # ── Extra mixed / tricky jobs ───────────────────────────────
    {"title": "Virtual Assistant — Email Management and Data Entry",
     "description": "VA to manage email inbox, do data entry, and organize spreadsheets. "
                    "Must be proficient with Excel and email. Data processing.",
     "expected_agent": "data_entry"},
    {"title": "Content Strategy — Blog + Social + Email Automation",
     "description": "Full content strategy: SEO blog posts, social media content, "
                    "email marketing drip campaigns. SEO content multi-channel.",
     "expected_agent": "seo_content"},
    {"title": "Comprehensive Market Research and Lead List",
     "description": "Combine market research with lead generation. Competitive analysis, "
                    "SWOT, and qualified lead list of 100 companies. Market report.",
     "expected_agent": "market_research"},
    {"title": "Full Professional Package — Resume, Cover Letter",
     "description": "Complete career package: ATS resume, customized cover letter, "
                    "LinkedIn profile. Resume writing expert needed.",
     "expected_agent": "resume_writer"},
    {"title": "E-commerce Setup — Product Descriptions + Ad Copy",
     "description": "Write product descriptions for 20 Shopify products and create "
                    "Google Ads ad copy campaigns. Product copy and ad copywriting.",
     "expected_agent": "product_desc"},
]

NEGATIVE_JOBS = [
    {"title": "Unity 3D Game Developer — Mobile RPG",
     "description": "Build a 3D RPG game in Unity for iOS and Android. C# developer "
                    "with game development and 3D modeling. Unity game dev only.",
     "expected_agent": None},
    {"title": "React Native Mobile App — Fitness Tracker",
     "description": "Build react native iOS app for fitness tracking. Android app "
                    "developer with react native experience.",
     "expected_agent": None},
    {"title": "WordPress Theme Designer — Custom PHP Plugin",
     "description": "Design custom wordpress theme with PHP. WP theme from scratch "
                    "with graphic design and animation. Frontend only.",
     "expected_agent": None},
    {"title": "Solidity Smart Contract Developer — DeFi Protocol",
     "description": "Build blockchain smart contracts in Solidity for DeFi protocol. "
                    "Blockchain developer with Ethereum experience.",
     "expected_agent": None},
    {"title": "Video Editing — YouTube Channel Intro & Outro",
     "description": "Create video editing intros and outros for YouTube channel. "
                    "Motion graphics, animation, and video editing skills.",
     "expected_agent": None},
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SMOKE TEST ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MIN_SCORE = 0.15  # Upwork uses 0.15 default threshold


def run_smoke_test(verbose: bool = False, save_report: bool = False):
    """Run full Upwork smoke test against scoring + matching + proposal pipeline."""
    print("\n" + "=" * 70)
    print("  UPWORK SMOKE TEST — 100 Job Posts vs Full Pipeline")
    print("  score_job() → match_job_to_service() → generate_proposal()")
    print("=" * 70)

    # Build job list
    real_jobs = load_upwork_jobs()
    print(f"\n  [DATA] Loaded {len(real_jobs)} real scraped Upwork jobs (deduplicated)")
    print(f"  [DATA] {len(SYNTHETIC_JOBS)} synthetic jobs covering all 20 services")
    print(f"  [DATA] {len(NEGATIVE_JOBS)} negative control jobs (should NOT match)")

    all_jobs = []
    for j in real_jobs:
        j.setdefault("source", "upwork_scraped")
        all_jobs.append(j)
    for j in SYNTHETIC_JOBS:
        j["source"] = "synthetic"
        all_jobs.append(j)
    for j in NEGATIVE_JOBS:
        j["source"] = "negative_control"
        all_jobs.append(j)

    total = len(all_jobs)
    print(f"  [DATA] Total test jobs: {total}")
    print("-" * 70)

    # Metrics
    results = []
    scores_above_min = 0
    scores_zero = 0
    match_count = 0
    no_match_count = 0
    negative_correct = 0
    negative_wrong = 0
    agent_match_counts = Counter()
    agent_coverage = set()
    score_distribution = {
        "0.00": 0, "0.01-0.10": 0, "0.11-0.25": 0,
        "0.26-0.50": 0, "0.51-0.75": 0, "0.76-1.00": 0,
    }
    confidence_values = []
    expected_hits = 0
    expected_misses = 0
    proposal_generated = 0
    proposal_empty = 0
    timings = []

    for i, job in enumerate(all_jobs, 1):
        title = job.get("title", "")
        desc = job.get("description", "")
        source = job.get("source", "unknown")
        expected_agent = job.get("expected_agent")

        t0 = time.perf_counter()

        # 1. Score
        score = score_job(title, desc)

        # 2. Match to service
        matches = match_job_to_service(title, desc)

        # 3. Generate proposal
        proposal = generate_proposal(title, desc) if matches else ""
        has_proposal = len(proposal) > 50

        elapsed = (time.perf_counter() - t0) * 1000  # ms
        timings.append(elapsed)

        top_agent = matches[0]["agent"] if matches else None
        top_confidence = matches[0]["confidence"] if matches else 0

        # Score distribution
        if score == 0:
            score_distribution["0.00"] += 1
            scores_zero += 1
        elif score <= 0.10:
            score_distribution["0.01-0.10"] += 1
        elif score <= 0.25:
            score_distribution["0.11-0.25"] += 1
        elif score <= 0.50:
            score_distribution["0.26-0.50"] += 1
        elif score <= 0.75:
            score_distribution["0.51-0.75"] += 1
        else:
            score_distribution["0.76-1.00"] += 1

        if score >= MIN_SCORE:
            scores_above_min += 1

        # Match tracking
        if matches:
            match_count += 1
            for m in matches:
                agent_match_counts[m["agent"]] += 1
                agent_coverage.add(m["agent"])
                confidence_values.append(m["confidence"])
            if has_proposal:
                proposal_generated += 1
            else:
                proposal_empty += 1
        else:
            no_match_count += 1

        # Negative control check
        if source == "negative_control":
            if not matches:
                negative_correct += 1
            else:
                negative_wrong += 1

        # Expected agent check
        if expected_agent:
            if top_agent == expected_agent:
                expected_hits += 1
            else:
                expected_misses += 1

        result = {
            "index": i,
            "title": title[:80],
            "source": source,
            "score": score,
            "matches": len(matches),
            "top_agent": top_agent,
            "top_confidence": top_confidence,
            "has_proposal": has_proposal,
            "expected_agent": expected_agent,
            "correct_match": top_agent == expected_agent if expected_agent else None,
            "elapsed_ms": round(elapsed, 2),
        }
        results.append(result)

        if verbose:
            status = "✓" if (not expected_agent or top_agent == expected_agent) else "✗"
            match_str = f"{top_agent}({top_confidence})" if top_agent else "NO MATCH"
            print(f"  [{i:3d}] {status} score={score:.2f} | {match_str:30s} | {title[:55]}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  RESULTS REPORT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    print("\n" + "=" * 70)
    print("  UPWORK SMOKE TEST RESULTS")
    print("=" * 70)

    print(f"\n  Total jobs tested:          {total}")
    print(f"  Real scraped (Upwork):      {len(real_jobs)}")
    print(f"  Synthetic (all 20 agents):  {len(SYNTHETIC_JOBS)}")
    print(f"  Negative controls:          {len(NEGATIVE_JOBS)}")

    # Scoring
    print(f"\n  ── SCORING (score_job) ─────────────────────")
    print(f"  Scores above MIN ({MIN_SCORE}):  {scores_above_min}/{total} ({100*scores_above_min/total:.1f}%)")
    print(f"  Scores = 0 (no keywords):   {scores_zero}/{total} ({100*scores_zero/total:.1f}%)")
    print(f"  Score distribution:")
    for band, count in score_distribution.items():
        bar = "█" * int(count * 40 / max(total, 1))
        print(f"    {band:12s}: {count:3d} {bar}")

    # Matching
    print(f"\n  ── MATCHING (match_job_to_service) ─────────")
    print(f"  Jobs with service match:    {match_count}/{total} ({100*match_count/total:.1f}%)")
    print(f"  Jobs with no match:         {no_match_count}/{total} ({100*no_match_count/total:.1f}%)")
    if confidence_values:
        avg_conf = sum(confidence_values) / len(confidence_values)
        max_conf = max(confidence_values)
        min_conf = min(confidence_values)
        print(f"  Confidence — avg: {avg_conf:.2f}, min: {min_conf:.2f}, max: {max_conf:.2f}")

    # Agent coverage
    all_agents = set(s["agent"] for s in UPWORK_SERVICES)
    missing_agents = all_agents - agent_coverage
    print(f"\n  ── SERVICE COVERAGE ───────────────────────")
    print(f"  Services matched:           {len(agent_coverage)}/20 ({100*len(agent_coverage)/20:.0f}%)")
    if missing_agents:
        print(f"  MISSING (no matches):       {', '.join(sorted(missing_agents))}")
    print(f"\n  Match counts per service:")
    for agent in sorted(all_agents):
        count = agent_match_counts.get(agent, 0)
        bar = "█" * min(count, 40)
        flag = " ← ZERO!" if count == 0 else ""
        print(f"    {agent:22s}: {count:3d} {bar}{flag}")

    # Expected agent accuracy
    synth_total = expected_hits + expected_misses
    if synth_total > 0:
        print(f"\n  ── EXPECTED AGENT ACCURACY ─────────────────")
        print(f"  Correct top match:          {expected_hits}/{synth_total} ({100*expected_hits/synth_total:.1f}%)")
        print(f"  Wrong top match:            {expected_misses}/{synth_total}")
        if expected_misses > 0:
            print(f"  Mismatches:")
            for r in results:
                if r.get("correct_match") is False:
                    print(f"    {r['title'][:60]}")
                    print(f"      expected={r['expected_agent']}, got={r['top_agent']}")

    # Negative controls
    neg_total = negative_correct + negative_wrong
    if neg_total > 0:
        print(f"\n  ── NEGATIVE CONTROLS ──────────────────────")
        print(f"  Correctly rejected:         {negative_correct}/{neg_total} ({100*negative_correct/neg_total:.1f}%)")
        if negative_wrong > 0:
            print(f"  FALSE POSITIVES:            {negative_wrong}")
            for r in results:
                if r["source"] == "negative_control" and r["matches"] > 0:
                    print(f"    {r['title'][:60]} → matched {r['top_agent']}")

    # Proposals
    print(f"\n  ── PROPOSAL GENERATION ────────────────────")
    print(f"  Proposals generated:        {proposal_generated}")
    print(f"  Proposals empty/short:      {proposal_empty}")

    # Specialized profiles
    print(f"\n  ── SPECIALIZED PROFILES ──────────────────")
    for profile in SPECIALIZED_PROFILES:
        covered = sum(1 for a in profile["agents"] if a in agent_coverage)
        total_p = len(profile["agents"])
        print(f"    {profile['name']:30s}: {covered}/{total_p} agents matched")

    # Performance
    avg_time = sum(timings) / len(timings) if timings else 0
    max_time = max(timings) if timings else 0
    total_time = sum(timings)
    print(f"\n  ── PERFORMANCE ───────────────────────────")
    print(f"  Total pipeline time:        {total_time:.1f}ms")
    print(f"  Avg per job:                {avg_time:.2f}ms")
    print(f"  Max per job:                {max_time:.2f}ms")
    if avg_time > 0:
        print(f"  Throughput:                 {1000/avg_time:.0f} jobs/sec")

    # Overall verdict
    print(f"\n  {'='*50}")
    issues = []
    if len(agent_coverage) < 20:
        issues.append(f"Only {len(agent_coverage)}/20 services covered")
    if negative_wrong > 0:
        issues.append(f"{negative_wrong} false positive(s) on negative controls")
    if synth_total > 0 and expected_hits / synth_total < 0.80:
        issues.append(f"Service accuracy below 80% ({100*expected_hits/synth_total:.0f}%)")
    if proposal_empty > 0:
        issues.append(f"{proposal_empty} matched jobs had empty/short proposals")

    if not issues:
        print("  VERDICT: ✓ ALL CHECKS PASSED")
    else:
        print(f"  VERDICT: ✗ {len(issues)} ISSUE(S) FOUND")
        for issue in issues:
            print(f"    • {issue}")
    print("=" * 70 + "\n")

    # Save report
    if save_report:
        report_path = PROJECT / "output" / "smoke_test_upwork_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "platform": "upwork",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_jobs": total,
            "real_jobs": len(real_jobs),
            "synthetic_jobs": len(SYNTHETIC_JOBS),
            "negative_jobs": len(NEGATIVE_JOBS),
            "scores_above_min": scores_above_min,
            "match_rate": round(match_count / total, 3),
            "service_coverage": len(agent_coverage),
            "missing_services": sorted(missing_agents),
            "expected_accuracy": round(expected_hits / synth_total, 3) if synth_total else None,
            "negative_control_pass": negative_correct == neg_total,
            "avg_time_ms": round(avg_time, 2),
            "total_time_ms": round(total_time, 2),
            "score_distribution": score_distribution,
            "service_match_counts": dict(agent_match_counts),
            "results": results,
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  Report saved: {report_path}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upwork smoke test — 100 jobs vs matching pipeline")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each job result")
    parser.add_argument("--report", "-r", action="store_true", help="Save JSON report")
    args = parser.parse_args()
    run_smoke_test(verbose=args.verbose, save_report=args.report)
