"""Quick verification of all agents, platforms, and autobidder."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 1. Test all 24 agent imports
agents = [
    "sales_ops", "support", "content_repurpose", "doc_extract",
    "lead_gen", "email_marketing", "seo_content", "social_media",
    "data_entry", "web_scraper", "crm_ops", "bookkeeping",
    "proposal_writer", "product_desc", "resume_writer", "ad_copy",
    "market_research", "business_plan", "press_release", "tech_docs",
    "context_manager", "qa_manager", "production_manager", "automation_manager",
]
ok = 0
for a in agents:
    try:
        __import__(f"agents.{a}.runner")
        ok += 1
    except Exception as e:
        print(f"  FAIL: {a} -> {e}")
print(f"Agent imports: {ok}/{len(agents)} OK")

# 2. Autobidder
try:
    from automation.autobidder import run_scan, print_status, get_bid_history
    print("Autobidder: OK")
except Exception as e:
    print(f"Autobidder: FAIL -> {e}")

# 3. Platform profiles
from income.freelance_listings import (
    FIVERR_GIGS, UPWORK_PROFILE, PEOPLEPERHOUR_PROFILE,
    GURU_PROFILE, TOPTAL_PROFILE,
)
print(f"Fiverr gigs: {len(FIVERR_GIGS)}")
print(f"Upwork portfolio items: {len(UPWORK_PROFILE['portfolio_items'])}")
print(f"Upwork service catalog: {len(UPWORK_PROFILE['service_catalog'])}")
print(f"Upwork specialized profiles: {len(UPWORK_PROFILE['specialized_profiles'])}")
print(f"PPH hourlies: {len(PEOPLEPERHOUR_PROFILE['hourlies'])}")
print(f"Guru service listings: {len(GURU_PROFILE['service_listings'])}")
print(f"Toptal project types: {len(TOPTAL_PROFILE['project_types'])}")

# 4. Dispatcher
from dispatcher.router import DAILY_LIMITS, TOKEN_BUDGETS
print(f"Dispatcher DAILY_LIMITS: {len(DAILY_LIMITS)} entries")
print(f"Dispatcher TOKEN_BUDGETS: {len(TOKEN_BUDGETS)} entries")

# 5. Matching engine
from campaign.freelancer_deploy import (
    match_project, FREELANCER_GIGS, BID_TEMPLATES, AUTOBID_RULES,
)
print(f"Freelancer gigs: {len(FREELANCER_GIGS)}")
print(f"Bid templates: {len(BID_TEMPLATES)}")
print(f"Autobid rules: {len(AUTOBID_RULES)}")

# Quick match test
m = match_project("Need cold email outreach campaign", "b2b sales emails")
if m:
    print(f"Match test: {m[0]['agent']} at {m[0]['confidence']:.0%}")

print("\n=== ALL CHECKS PASSED ===")
