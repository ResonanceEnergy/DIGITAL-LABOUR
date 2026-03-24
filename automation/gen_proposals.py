"""Generate ready-to-submit Upwork proposals from scraped job data.

Usage:
    python -m automation.gen_proposals          # Generate from top matches
    python -m automation.gen_proposals --all    # Show all matches
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from campaign.upwork_deploy import UPWORK_SERVICES

# ── Match Rules ─────────────────────────────────────────────────

UPWORK_MATCH_RULES = [
    {"agent": "sales_ops", "match_any": ["cold email", "lead outreach", "sales email", "email sequence", "prospecting", "b2b outreach", "sdr", "cold outreach", "sales automation", "personalized email"], "exclude": ["developer", "react", "node.js"]},
    {"agent": "support", "match_any": ["customer support", "help desk", "ticket", "zendesk", "intercom", "freshdesk", "helpdesk", "support agent", "customer service", "ticket triage"], "exclude": ["developer", "react", "ios"]},
    {"agent": "content_repurpose", "match_any": ["repurpose", "content transformation", "blog to social", "content recycling", "multi-platform content", "content adaptation"], "exclude": ["video editing", "animation"]},
    {"agent": "doc_extract", "match_any": ["data extraction", "document processing", "pdf extraction", "invoice processing", "ocr", "contract extraction", "document automation"], "exclude": ["developer", "full stack"]},
    {"agent": "lead_gen", "match_any": ["lead generation", "lead list", "prospect list", "lead research", "b2b leads", "qualified leads", "sales leads", "lead scraping"], "exclude": ["developer", "react"]},
    {"agent": "email_marketing", "match_any": ["email marketing", "email campaign", "drip campaign", "email sequence", "newsletter", "mailchimp", "email copywriting", "welcome series"], "exclude": ["developer"]},
    {"agent": "seo_content", "match_any": ["seo", "blog writing", "article writing", "content writing", "blog post", "seo content", "keyword", "content strategy"], "exclude": ["web developer", "react"]},
    {"agent": "social_media", "match_any": ["social media", "instagram", "linkedin post", "content calendar", "social content", "social media manager", "captions"], "exclude": ["developer", "ads manager"]},
    {"agent": "data_entry", "match_any": ["data entry", "spreadsheet", "data cleaning", "excel", "csv", "data processing", "data formatting", "virtual assistant"], "exclude": ["developer", "python developer"]},
    {"agent": "web_scraper", "match_any": ["web scraping", "data scraping", "scraping", "web crawler", "data mining", "extract data from website", "scrape website"], "exclude": ["developer wanted"]},
    {"agent": "crm_ops", "match_any": ["crm", "salesforce", "hubspot", "crm cleanup", "crm migration", "crm admin", "contact management", "crm data"], "exclude": ["developer"]},
    {"agent": "bookkeeping", "match_any": ["bookkeeping", "accounting", "expense", "quickbooks", "xero", "bank reconciliation", "financial records", "categorization"], "exclude": ["developer", "software"]},
    {"agent": "proposal_writer", "match_any": ["proposal writing", "rfp", "grant writing", "business proposal", "bid writing", "project proposal"], "exclude": ["developer"]},
    {"agent": "product_desc", "match_any": ["product description", "amazon listing", "shopify listing", "product copy", "ecommerce copy", "listing optimization"], "exclude": ["developer"]},
    {"agent": "resume_writer", "match_any": ["resume", "cv writing", "cover letter", "linkedin profile", "ats", "career"], "exclude": ["developer", "recruiter tool"]},
    {"agent": "ad_copy", "match_any": ["ad copy", "google ads", "facebook ads", "ppc", "ad copywriting", "linkedin ads", "advertising copy"], "exclude": ["developer", "media buyer"]},
    {"agent": "market_research", "match_any": ["market research", "competitive analysis", "industry analysis", "market report", "swot", "market sizing"], "exclude": ["developer"]},
    {"agent": "business_plan", "match_any": ["business plan", "financial projections", "startup plan", "investor pitch", "fundraising", "pitch deck"], "exclude": ["developer"]},
    {"agent": "press_release", "match_any": ["press release", "media release", "news release", "pr writing", "public relations"], "exclude": ["developer"]},
    {"agent": "tech_docs", "match_any": ["technical documentation", "api documentation", "user guide", "readme", "software documentation", "technical writing"], "exclude": ["developer wanted"]},
]


def match_job(title: str, desc: str):
    """Match a job to our best service."""
    text = (title + " " + desc).lower()
    matches = []
    for rule in UPWORK_MATCH_RULES:
        any_hits = sum(1 for kw in rule["match_any"] if kw in text)
        excluded = any(kw in text for kw in rule.get("exclude", []))
        if any_hits > 0 and not excluded:
            conf = min(any_hits / (len(rule["match_any"]) * 0.3), 1.0)
            matches.append((rule["agent"], conf))
    matches.sort(key=lambda x: -x[1])
    return matches[0] if matches else None


def load_jobs():
    """Load scraped Upwork jobs."""
    job_file = PROJECT / "data" / "upwork_jobs" / "job_log.jsonl"
    jobs = []
    if job_file.exists():
        with open(job_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    jobs.append(json.loads(line))
    return jobs


def generate_proposal(agent: str, job_title: str) -> str:
    """Generate a tailored proposal for a matched job."""
    service_map = {s["agent"]: s for s in UPWORK_SERVICES}
    svc = service_map.get(agent, {})
    svc_title = svc.get("title", agent.replace("_", " ").title())
    hourly = svc.get("hourly_rate", "$25/hr")
    fixed = svc.get("fixed_price", "$50")

    proposal = f"""Hi there,

I specialize in exactly this type of work. I run purpose-built AI agents (not generic ChatGPT prompts) designed specifically for {svc_title.lower()}.

Here's what makes my approach different:
- Each task runs through a dedicated AI pipeline built for {agent.replace('_', ' ')} work
- Every output passes automated quality checks before delivery
- Structured output (JSON, CSV, or formatted docs) ready to import into your systems
- Fast turnaround: most tasks completed same-day, many within hours

I've tested this system across SaaS, fintech, eCommerce, and professional services — with 80-100% first-pass quality rates.

Happy to do a small sample task free so you can judge the quality firsthand before committing.

Looking forward to your reply,
Nathan
BIT RAGE SYSTEMS AI

Rate: {hourly} or {fixed} fixed per deliverable"""

    return proposal


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate Upwork proposals from scraped jobs")
    parser.add_argument("--all", action="store_true", help="Show all matches")
    parser.add_argument("--top", type=int, default=5, help="Number of top proposals to generate")
    args = parser.parse_args()

    jobs = load_jobs()
    print(f"\nLoaded {len(jobs)} scraped Upwork jobs")

    # Match all jobs
    matched = []
    for j in jobs:
        title = j.get("title", "")
        desc = j.get("description", j.get("snippet", ""))
        result = match_job(title, desc)
        if result:
            agent, conf = result
            matched.append((conf, agent, title, desc, j))

    matched.sort(key=lambda x: -x[0])
    print(f"Matched: {len(matched)}/{len(jobs)}\n")

    # Generate proposals for top N
    limit = len(matched) if args.all else min(args.top, len(matched))
    proposals = []

    for i, (conf, agent, title, desc, j) in enumerate(matched[:limit], 1):
        budget = j.get("budget", j.get("hourly_range", "?"))
        url = j.get("url", "?")
        proposal_text = generate_proposal(agent, title)

        print("=" * 70)
        print(f"  [{i}] {title[:65]}")
        print(f"      Agent: {agent} | Confidence: {conf:.0%} | Budget: {budget}")
        print(f"      URL: {url[:80]}")
        print("-" * 70)
        print(proposal_text)
        print()

        proposals.append({
            "job_title": title,
            "agent": agent,
            "confidence": conf,
            "budget": budget,
            "url": url,
            "proposal": proposal_text,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    # Save to file
    output_dir = PROJECT / "output"
    output_dir.mkdir(exist_ok=True)

    # Save JSON for machine use
    json_path = output_dir / "upwork_proposals.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(proposals, f, indent=2, ensure_ascii=False)

    # Save TXT for copy-paste
    txt_path = output_dir / "upwork_proposals_ready.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"UPWORK PROPOSALS — READY TO SUBMIT\n")
        f.write(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"Total: {len(proposals)}\n\n")
        for p in proposals:
            f.write("=" * 70 + "\n")
            f.write(f"JOB: {p['job_title']}\n")
            f.write(f"AGENT: {p['agent']} | CONFIDENCE: {p['confidence']:.0%}\n")
            f.write(f"URL: {p['url']}\n")
            f.write("-" * 70 + "\n")
            f.write(p["proposal"] + "\n\n")

    print(f"\nSaved {len(proposals)} proposals:")
    print(f"  JSON: {json_path}")
    print(f"  TXT:  {txt_path}")
    print(f"\nOpen the TXT file and copy-paste into Upwork when applying.")


if __name__ == "__main__":
    main()
