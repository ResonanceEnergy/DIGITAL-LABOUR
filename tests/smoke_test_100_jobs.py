"""Smoke Test — 100 Job Posts vs Full Matching/Scoring/Bid Pipeline.

Reads 55 real scraped Upwork jobs + 45 synthetic Freelancer-style jobs
covering all 20 agent capabilities. Tests:
  1. score_project()   — keyword scoring (0-1)
  2. match_project()   — agent matching with confidence
  3. Bid generation    — template bid for every match
  4. Coverage          — all 20 agents must match at least 1 job
  5. Timing            — total pipeline speed

Usage:
    python -m tests.smoke_test_100_jobs
    python -m tests.smoke_test_100_jobs --verbose
    python -m tests.smoke_test_100_jobs --report   # Save JSON report
"""

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from automation.freelancer_jobhunt import score_project, CORE_KEYWORDS, BONUS_KEYWORDS, NEGATIVE_KEYWORDS, MIN_SCORE
from campaign.freelancer_deploy import match_project, FREELANCER_GIGS, BID_TEMPLATES, AUTOBID_RULES

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
#  SYNTHETIC JOBS — 5 per agent type, targeting all 20 agents
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYNTHETIC_JOBS = [
    # ── sales_ops (cold email / outreach) ───────────────────────
    {"title": "Cold Email Specialist for B2B SaaS Lead Outreach",
     "description": "We need someone to build cold email sequences targeting SaaS founders. "
                    "Must research each prospect and personalize the emails. 500 leads.",
     "budget": "$200-500", "skills": ["Cold Email", "Sales", "Lead Generation"], "expected_agent": "sales_ops"},
    {"title": "Personalized Sales Email Sequence Writer",
     "description": "Create 3-email outreach sequences for our B2B sales team. "
                    "Research companies, identify pain points, write prospecting emails.",
     "budget": "$100-300", "skills": ["Sales", "Email", "B2B Marketing"], "expected_agent": "sales_ops"},

    # ── support ─────────────────────────────────────────────────
    {"title": "Zendesk Ticket Triage & Draft Response System",
     "description": "We need help processing our Zendesk support tickets. Categorize by type, "
                    "score severity, and draft customer responses. 200 tickets/week.",
     "budget": "$150-400", "skills": ["Customer Support", "Zendesk", "Help Desk"], "expected_agent": "support"},
    {"title": "AI Help Desk Agent for Customer Ticket Resolution",
     "description": "Set up automated ticket resolution system for our helpdesk. "
                    "Must handle billing, technical, and account inquiries.",
     "budget": "$100-250", "skills": ["Help Desk", "Customer Support", "Automation"], "expected_agent": "support"},

    # ── content_repurpose ───────────────────────────────────────
    {"title": "Repurpose Blog Content into Social Media Posts",
     "description": "Take our 10 blog posts and repurpose content into LinkedIn, Twitter, "
                    "Instagram and newsletter formats. Multi-platform content needed.",
     "budget": "$50-150", "skills": ["Content Writing", "Social Media", "Blog"], "expected_agent": "content_repurpose"},
    {"title": "Content Transformation Specialist — Blog to Social",
     "description": "Transform long-form articles into platform-optimized social content. "
                    "We need blog to social media content repurposing for 20 articles.",
     "budget": "$80-200", "skills": ["Content Repurposing", "Social Media"], "expected_agent": "content_repurpose"},

    # ── doc_extract ─────────────────────────────────────────────
    {"title": "Invoice Processing — Extract Data from 500 PDF Invoices",
     "description": "We have 500 PDF invoices that need to be processed. Extract vendor name, "
                    "date, amounts, line items into structured data. Document extraction project.",
     "budget": "$100-300", "skills": ["Data Extraction", "PDF", "Data Entry"], "expected_agent": "doc_extract"},
    {"title": "Contract Analysis — Extract Key Clauses from Legal Documents",
     "description": "Extract parties, dates, payment terms, and key clauses from 50 contracts. "
                    "Need structured JSON output from document parsing.",
     "budget": "$150-400", "skills": ["Document Processing", "Contract Analysis"], "expected_agent": "doc_extract"},

    # ── lead_gen ────────────────────────────────────────────────
    {"title": "B2B Lead Generation — 200 Qualified Leads for Marketing Agency",
     "description": "Build a qualified lead list of 200 marketing decision-makers. "
                    "Need company info, contacts, lead scoring, and prospect research.",
     "budget": "$150-400", "skills": ["Lead Generation", "B2B", "Research"], "expected_agent": "lead_gen"},
    {"title": "Prospect Research — Sales Lead List Building",
     "description": "Research and compile a list of qualified leads for our sales team. "
                    "Need lead generation with scoring and ICP fit analysis.",
     "budget": "$100-250", "skills": ["Lead Generation", "Sales", "Research"], "expected_agent": "lead_gen"},

    # ── email_marketing ─────────────────────────────────────────
    {"title": "Email Marketing Campaign — Welcome Series for E-commerce",
     "description": "Create a 5-email welcome sequence and nurture drip campaign for our Shopify store. "
                    "Need Mailchimp-compatible sequences with A/B subject lines.",
     "budget": "$100-300", "skills": ["Email Marketing", "Mailchimp", "Copywriting"], "expected_agent": "email_marketing"},
    {"title": "Drip Campaign Writer for SaaS Onboarding",
     "description": "Write a 7-email drip campaign for SaaS user onboarding. "
                    "Need email sequence with engagement triggers and nurture flow.",
     "budget": "$150-400", "skills": ["Email Marketing", "SaaS", "Email Campaign"], "expected_agent": "email_marketing"},

    # ── seo_content ─────────────────────────────────────────────
    {"title": "SEO Blog Writer — 10 Articles for Fitness Website",
     "description": "Write 10 SEO-optimized blog posts targeting specific keywords for a fitness blog. "
                    "Need keyword research, H2/H3 structure, meta descriptions.",
     "budget": "$200-500", "skills": ["SEO", "Blog Writing", "Content Writing"], "expected_agent": "seo_content"},
    {"title": "Keyword-Optimized Article Writing for Tech Blog",
     "description": "Need 5 SEO content articles for a technology blog. Each 2000 words with "
                    "primary keyword targeting and SEO article structure.",
     "budget": "$150-350", "skills": ["SEO", "Article Writing", "Content"], "expected_agent": "seo_content"},

    # ── social_media ────────────────────────────────────────────
    {"title": "Social Media Content Calendar — 30 Days of Posts",
     "description": "Create a month of social media content for LinkedIn and Instagram. "
                    "Need platform-specific social media posts with hashtag recommendations.",
     "budget": "$80-200", "skills": ["Social Media", "Content Creation", "LinkedIn"], "expected_agent": "social_media"},
    {"title": "Instagram Captions and LinkedIn Posts for Consulting Firm",
     "description": "Write 60 social media content pieces — instagram captions and linkedin posts "
                    "for a management consulting firm. Content calendar format.",
     "budget": "$100-250", "skills": ["Social Media Marketing", "LinkedIn", "Instagram"], "expected_agent": "social_media"},

    # ── data_entry ──────────────────────────────────────────────
    {"title": "Data Entry — Clean and Organize 5000 Row Spreadsheet",
     "description": "We have a messy Excel spreadsheet with 5000 rows of contact data. "
                    "Need data cleaning, standardization, and data processing to CSV.",
     "budget": "$50-150", "skills": ["Data Entry", "Excel", "Data Processing"], "expected_agent": "data_entry"},
    {"title": "Data Cleaning Project — Customer Database Formatting",
     "description": "Clean and standardize a CSV customer database. Fix dates, names, addresses. "
                    "Spreadsheet data entry and processing. Remove duplicates.",
     "budget": "$40-100", "skills": ["Data Entry", "Data Cleaning", "CSV"], "expected_agent": "data_entry"},

    # ── web_scraper ─────────────────────────────────────────────
    {"title": "Web Scraping — Extract Product Data from E-commerce Sites",
     "description": "Scrape product listings from 5 e-commerce websites. Extract name, price, "
                    "description, images. Web scraping with structured data mining output.",
     "budget": "$100-300", "skills": ["Web Scraping", "Python", "Data Mining"], "expected_agent": "web_scraper"},
    {"title": "Data Scraping Service — Real Estate Listings",
     "description": "Scrape website real estate listings data extraction from 3 property sites. "
                    "Extract price, address, bedrooms, square footage to CSV.",
     "budget": "$80-200", "skills": ["Data Scraping", "Web Scraping", "Data Extraction"], "expected_agent": "web_scraper"},

    # ── crm_ops ─────────────────────────────────────────────────
    {"title": "CRM Data Cleanup — Salesforce Contact Deduplication",
     "description": "Clean up our Salesforce CRM database. Deduplicate contacts, standardize "
                    "data, merge duplicates. 3000 records need crm cleanup.",
     "budget": "$100-250", "skills": ["CRM", "Salesforce", "Data Cleaning"], "expected_agent": "crm_ops"},
    {"title": "HubSpot CRM Migration and Data Cleanup",
     "description": "Migrate and clean CRM data from spreadsheets to HubSpot. "
                    "Need contact cleanup, deduplication, and CRM data standardization.",
     "budget": "$150-400", "skills": ["HubSpot", "CRM", "Data Migration"], "expected_agent": "crm_ops"},

    # ── bookkeeping ─────────────────────────────────────────────
    {"title": "Bookkeeping — Monthly Expense Categorization for Small Business",
     "description": "Categorize 6 months of expenses for a small business. "
                    "Bank reconciliation, expense categorization, QuickBooks export.",
     "budget": "$100-300", "skills": ["Bookkeeping", "QuickBooks", "Accounting"], "expected_agent": "bookkeeping"},
    {"title": "Bank Reconciliation and Financial Records Organization",
     "description": "Reconcile bank statements, categorize transactions, and organize "
                    "financial records for tax prep. Xero-compatible bookkeeping output.",
     "budget": "$80-200", "skills": ["Bookkeeping", "Xero", "Bank Reconciliation"], "expected_agent": "bookkeeping"},

    # ── proposal_writer ─────────────────────────────────────────
    {"title": "Business Proposal Writer — RFP Response for IT Services",
     "description": "Write a compelling project proposal and RFP response for our IT consulting firm. "
                    "Need executive summary, scope, timeline, pricing. Proposal writing.",
     "budget": "$100-300", "skills": ["Proposal Writing", "Business Writing", "RFP"], "expected_agent": "proposal_writer"},
    {"title": "Grant Writing — Non-Profit Funding Application",
     "description": "Write a grant writing application for a non-profit education program. "
                    "Need proposal with budget justification and impact measures.",
     "budget": "$150-400", "skills": ["Grant Writing", "Proposal Writing"], "expected_agent": "proposal_writer"},

    # ── product_desc ────────────────────────────────────────────
    {"title": "Amazon Product Listing Writer — 50 Kitchen Gadgets",
     "description": "Write Amazon listing product descriptions for 50 kitchen products. "
                    "Need titles, bullet points, A+ content. Product copy for e-commerce.",
     "budget": "$100-250", "skills": ["Product Descriptions", "Amazon", "Copywriting"], "expected_agent": "product_desc"},
    {"title": "Shopify Product Description Writer — Fashion Store",
     "description": "Write Shopify product descriptions for 30 fashion items. "
                    "SEO-optimized product copy with benefits-first writing.",
     "budget": "$80-200", "skills": ["Product Descriptions", "Shopify", "SEO"], "expected_agent": "product_desc"},

    # ── resume_writer ───────────────────────────────────────────
    {"title": "Professional Resume Writer — Executive Level CV",
     "description": "Write an ATS-optimized executive resume and cover letter. "
                    "Need resume writing with keyword targeting for VP of Marketing role.",
     "budget": "$80-200", "skills": ["Resume Writing", "CV Writing", "Career"], "expected_agent": "resume_writer"},
    {"title": "ATS Resume and LinkedIn Profile Optimization",
     "description": "Rewrite my resume for ATS compliance. Need resume with quantified "
                    "achievements, cover letter, and LinkedIn profile summary.",
     "budget": "$50-150", "skills": ["Resume", "LinkedIn", "Career Counseling"], "expected_agent": "resume_writer"},

    # ── ad_copy ─────────────────────────────────────────────────
    {"title": "Google Ads Copy Writer — 10 Campaigns for E-commerce",
     "description": "Write Google Ads copy for 10 PPC campaigns. Need headlines, descriptions, "
                    "sitelinks, and ad copywriting with A/B variations.",
     "budget": "$100-300", "skills": ["Google Ads", "PPC", "Ad Copy", "Copywriting"], "expected_agent": "ad_copy"},
    {"title": "Facebook Ads Copy + LinkedIn Ads for B2B SaaS",
     "description": "Write Facebook ads and LinkedIn ads copy for a B2B SaaS company. "
                    "Need ad copywriting with platform-specific character limits.",
     "budget": "$80-200", "skills": ["Facebook Ads", "LinkedIn Ads", "Ad Copy"], "expected_agent": "ad_copy"},

    # ── market_research ─────────────────────────────────────────
    {"title": "Market Research Report — Competitive Analysis for Fintech",
     "description": "Need a comprehensive market research report with competitive analysis, "
                    "SWOT analysis, and market sizing for a fintech startup.",
     "budget": "$200-500", "skills": ["Market Research", "Competitive Analysis", "SWOT"], "expected_agent": "market_research"},
    {"title": "Industry Analysis — Healthcare Tech Market Report",
     "description": "Write a market research industry analysis report covering healthcare technology. "
                    "Need market sizing, competitor landscape, and feasibility study.",
     "budget": "$150-400", "skills": ["Market Research", "Industry Analysis"], "expected_agent": "market_research"},

    # ── business_plan ───────────────────────────────────────────
    {"title": "Startup Business Plan with Financial Projections",
     "description": "Write an investor-ready business plan for a food delivery startup. "
                    "Need financial projections, market analysis, and lean canvas.",
     "budget": "$200-500", "skills": ["Business Plans", "Financial Projections", "Startup"], "expected_agent": "business_plan"},
    {"title": "Business Plan Writer — Fundraising Pitch Document",
     "description": "Create a business plan for seed fundraising round. Need business model, "
                    "TAM/SAM/SOM, investor pitch content, and startup plan.",
     "budget": "$250-600", "skills": ["Business Plans", "Fundraising", "Startup"], "expected_agent": "business_plan"},

    # ── press_release ───────────────────────────────────────────
    {"title": "Press Release Writer — Product Launch Announcement",
     "description": "Write an AP-style press release for our new product launch. "
                    "Need PR Newswire-ready format with media release distribution notes.",
     "budget": "$50-150", "skills": ["Press Release", "PR", "Copywriting"], "expected_agent": "press_release"},
    {"title": "News Release for Partnership Announcement",
     "description": "Write a press release announcing our new strategic partnership. "
                    "AP-style with spokesperson quotes. News release for media distribution.",
     "budget": "$50-150", "skills": ["Press Release", "Public Relations"], "expected_agent": "press_release"},

    # ── tech_docs ───────────────────────────────────────────────
    {"title": "API Documentation Writer — REST API Reference",
     "description": "Write comprehensive API documentation for our REST API. 20 endpoints. "
                    "Need developer docs with code examples, error codes. Technical writing.",
     "budget": "$150-400", "skills": ["Technical Writing", "API Documentation", "Python"], "expected_agent": "tech_docs"},
    {"title": "Software Documentation — User Guide and README",
     "description": "Write a user guide and README for our open-source Python tool. "
                    "Need technical documentation with setup instructions and tutorials.",
     "budget": "$100-250", "skills": ["Technical Writing", "Software Documentation", "Markdown"], "expected_agent": "tech_docs"},

    # ── Extra mixed / tricky jobs to push to 100 ────────────────
    {"title": "Virtual Assistant — Email Management and Data Entry",
     "description": "Looking for a VA to manage email inbox, do data entry, and organize spreadsheets. "
                    "Must be proficient with Excel and email automation.",
     "budget": "$10-20/hr", "skills": ["Data Entry", "Email", "Virtual Assistant"], "expected_agent": "data_entry"},
    {"title": "Content Strategy — Blog + Social + Email Automation",
     "description": "Need a full content strategy: SEO blog posts, social media content, "
                    "and email marketing drip campaigns. Multi-channel content.",
     "budget": "$500-1500", "skills": ["Content Writing", "SEO", "Email Marketing", "Social Media"], "expected_agent": "seo_content"},
    {"title": "Comprehensive Market Research and Lead List",
     "description": "Combine market research with lead generation. Need competitive analysis, "
                    "SWOT, and then a qualified lead list of 100 companies.",
     "budget": "$300-700", "skills": ["Market Research", "Lead Generation"], "expected_agent": "market_research"},
    {"title": "Full Professional Package — Resume, Cover Letter, LinkedIn",
     "description": "I need a complete career package: ATS resume, customized cover letter, "
                    "and optimized LinkedIn profile summary. Resume writing expert needed.",
     "budget": "$100-250", "skills": ["Resume Writing", "Cover Letter", "LinkedIn"], "expected_agent": "resume_writer"},
    {"title": "E-commerce Setup — Product Descriptions + Ad Copy",
     "description": "Write product descriptions for 20 Shopify products and create Google Ads "
                    "ad copy campaigns. Need product copy and PPC copy in one package.",
     "budget": "$200-500", "skills": ["Product Descriptions", "Google Ads", "Copywriting"], "expected_agent": "product_desc"},
]

# ── Negative jobs that should NOT match anyone ──────────────────
NEGATIVE_JOBS = [
    {"title": "Unity 3D Game Developer — Mobile RPG",
     "description": "Build a 3D RPG game in Unity for iOS and Android. Need C# developer "
                    "with game development and 3d modeling experience. Unity game dev only.",
     "budget": "$2000-5000", "skills": ["Unity", "Game Development", "C#", "3D Modeling"], "expected_agent": None},
    {"title": "React Native Mobile App — Fitness Tracker",
     "description": "Build a react native iOS app for fitness tracking. Need android app "
                    "developer with react native experience.",
     "budget": "$3000-8000", "skills": ["React Native", "iOS App", "Android App"], "expected_agent": None},
    {"title": "WordPress Theme Designer — Custom PHP Plugin",
     "description": "Design a custom wordpress theme with PHP developer skills. "
                    "Need wp theme from scratch with graphic design and animation.",
     "budget": "$500-1500", "skills": ["WordPress Theme", "PHP Developer", "Graphic Design"], "expected_agent": None},
    {"title": "Solidity Smart Contract Developer — DeFi Protocol",
     "description": "Build blockchain smart contracts in Solidity for a DeFi protocol. "
                    "Need blockchain developer with Solidity and Ethereum experience.",
     "budget": "$5000-15000", "skills": ["Solidity", "Blockchain", "Smart Contracts"], "expected_agent": None},
    {"title": "Video Editing — YouTube Channel Intro & Outro",
     "description": "Create video editing intros and outros for our YouTube channel. "
                    "Need motion graphics, animation, and video editing skills.",
     "budget": "$200-500", "skills": ["Video Editing", "Animation", "Graphic Design"], "expected_agent": None},
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SMOKE TEST ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_smoke_test(verbose: bool = False, save_report: bool = False):
    """Run full 100-job smoke test against scoring + matching + bid pipeline."""
    print("\n" + "=" * 70)
    print("  SMOKE TEST — 100 Job Posts vs Full Pipeline")
    print("  score_project() → match_project() → bid_template")
    print("=" * 70)

    # Build the job list
    real_jobs = load_upwork_jobs()
    print(f"\n  [DATA] Loaded {len(real_jobs)} real scraped Upwork jobs (deduplicated)")
    print(f"  [DATA] {len(SYNTHETIC_JOBS)} synthetic jobs covering all 20 agents")
    print(f"  [DATA] {len(NEGATIVE_JOBS)} negative control jobs (should NOT match)")

    all_jobs = []
    for j in real_jobs:
        j["source"] = "upwork_scraped"
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
    score_distribution = {"0.00": 0, "0.01-0.10": 0, "0.11-0.25": 0, "0.26-0.50": 0, "0.51-0.75": 0, "0.76-1.00": 0}
    confidence_values = []
    expected_hits = 0
    expected_misses = 0
    bid_template_found = 0
    bid_template_missing = 0
    timings = []

    for i, job in enumerate(all_jobs, 1):
        title = job["title"]
        desc = job["description"]
        source = job.get("source", "unknown")
        expected_agent = job.get("expected_agent")

        t0 = time.perf_counter()

        # 1. Score
        score = score_project(title, desc)

        # 2. Match
        matches = match_project(title, desc)

        # 3. Check bid template
        has_bid = False
        top_agent = matches[0]["agent"] if matches else None
        top_confidence = matches[0]["confidence"] if matches else 0
        if top_agent:
            has_bid = top_agent in BID_TEMPLATES

        elapsed = (time.perf_counter() - t0) * 1000  # ms
        timings.append(elapsed)

        # Classify score band
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

        # Count matches
        if matches:
            match_count += 1
            for m in matches:
                agent_match_counts[m["agent"]] += 1
                agent_coverage.add(m["agent"])
                confidence_values.append(m["confidence"])
            if has_bid:
                bid_template_found += 1
            else:
                bid_template_missing += 1
        else:
            no_match_count += 1

        # Negative control check
        if source == "negative_control":
            if not matches:
                negative_correct += 1
            else:
                negative_wrong += 1

        # Expected agent check (synthetic jobs)
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
            "has_bid_template": has_bid,
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
    print("  SMOKE TEST RESULTS")
    print("=" * 70)

    # Summary
    print(f"\n  Total jobs tested:          {total}")
    print(f"  Real scraped (Upwork):      {len(real_jobs)}")
    print(f"  Synthetic (all 20 agents):  {len(SYNTHETIC_JOBS)}")
    print(f"  Negative controls:          {len(NEGATIVE_JOBS)}")

    # Scoring
    print(f"\n  ── SCORING (score_project) ─────────────────")
    print(f"  Scores above MIN ({MIN_SCORE}):  {scores_above_min}/{total} ({100*scores_above_min/total:.1f}%)")
    print(f"  Scores = 0 (no keywords):   {scores_zero}/{total} ({100*scores_zero/total:.1f}%)")
    print(f"  Score distribution:")
    for band, count in score_distribution.items():
        bar = "█" * int(count * 40 / max(total, 1))
        print(f"    {band:12s}: {count:3d} {bar}")

    # Matching
    print(f"\n  ── MATCHING (match_project) ────────────────")
    print(f"  Jobs with agent match:      {match_count}/{total} ({100*match_count/total:.1f}%)")
    print(f"  Jobs with no match:         {no_match_count}/{total} ({100*no_match_count/total:.1f}%)")
    if confidence_values:
        avg_conf = sum(confidence_values) / len(confidence_values)
        max_conf = max(confidence_values)
        min_conf = min(confidence_values)
        print(f"  Confidence — avg: {avg_conf:.2f}, min: {min_conf:.2f}, max: {max_conf:.2f}")

    # Agent coverage
    all_agents = set(g["agent"] for g in FREELANCER_GIGS)
    missing_agents = all_agents - agent_coverage
    print(f"\n  ── AGENT COVERAGE ─────────────────────────")
    print(f"  Agents matched:             {len(agent_coverage)}/20 ({100*len(agent_coverage)/20:.0f}%)")
    if missing_agents:
        print(f"  MISSING (no matches):       {', '.join(sorted(missing_agents))}")
    print(f"\n  Match counts per agent:")
    for agent in sorted(all_agents):
        count = agent_match_counts.get(agent, 0)
        bar = "█" * min(count, 40)
        flag = " ← ZERO!" if count == 0 else ""
        print(f"    {agent:22s}: {count:3d} {bar}{flag}")

    # Expected agent accuracy (synthetic jobs)
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

    # Bid templates
    print(f"\n  ── BID TEMPLATES ─────────────────────────")
    print(f"  Template found for match:   {bid_template_found}")
    print(f"  Template MISSING:           {bid_template_missing}")
    print(f"  Templates available:        {len(BID_TEMPLATES)}/20")

    # Performance
    avg_time = sum(timings) / len(timings) if timings else 0
    max_time = max(timings) if timings else 0
    total_time = sum(timings)
    print(f"\n  ── PERFORMANCE ───────────────────────────")
    print(f"  Total pipeline time:        {total_time:.1f}ms")
    print(f"  Avg per job:                {avg_time:.2f}ms")
    print(f"  Max per job:                {max_time:.2f}ms")
    print(f"  Throughput:                 {1000/avg_time:.0f} jobs/sec" if avg_time > 0 else "")

    # Overall verdict
    print(f"\n  {'='*50}")
    issues = []
    if len(agent_coverage) < 20:
        issues.append(f"Only {len(agent_coverage)}/20 agents covered")
    if negative_wrong > 0:
        issues.append(f"{negative_wrong} false positive(s) on negative controls")
    if synth_total > 0 and expected_hits / synth_total < 0.80:
        issues.append(f"Agent accuracy below 80% ({100*expected_hits/synth_total:.0f}%)")
    if bid_template_missing > 0:
        issues.append(f"{bid_template_missing} matched jobs had no bid template")

    if not issues:
        print("  VERDICT: ✓ ALL CHECKS PASSED")
    else:
        print(f"  VERDICT: ✗ {len(issues)} ISSUE(S) FOUND")
        for issue in issues:
            print(f"    • {issue}")
    print("=" * 70 + "\n")

    # Save report
    if save_report:
        report_path = PROJECT / "output" / "smoke_test_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_jobs": total,
            "real_jobs": len(real_jobs),
            "synthetic_jobs": len(SYNTHETIC_JOBS),
            "negative_jobs": len(NEGATIVE_JOBS),
            "scores_above_min": scores_above_min,
            "match_rate": round(match_count / total, 3),
            "agent_coverage": len(agent_coverage),
            "missing_agents": sorted(missing_agents),
            "expected_accuracy": round(expected_hits / synth_total, 3) if synth_total else None,
            "negative_control_pass": negative_correct == neg_total,
            "avg_time_ms": round(avg_time, 2),
            "total_time_ms": round(total_time, 2),
            "score_distribution": score_distribution,
            "agent_match_counts": dict(agent_match_counts),
            "results": results,
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  Report saved: {report_path}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test 100 jobs against matching pipeline")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each job result")
    parser.add_argument("--report", "-r", action="store_true", help="Save JSON report")
    args = parser.parse_args()
    run_smoke_test(verbose=args.verbose, save_report=args.report)
