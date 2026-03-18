"""DEPRECATED — Use bitrage.py checks or bitrage_monitor.py --command instead.

Original: Portfolio Sample Generator — run each of our 20 agents with demo data
to produce portfolio samples that prove capabilities to potential clients.

Generates one showcase piece per agent, saves to output/portfolio/.

Usage:
    python -m scripts.gen_portfolio                   # All 20 agents
    python -m scripts.gen_portfolio --agent seo_content # Single agent
    python -m scripts.gen_portfolio --provider anthropic # Use specific LLM
    python -m scripts.gen_portfolio --list              # List available agents
"""

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from dotenv import load_dotenv
load_dotenv(PROJECT / ".env")

PORTFOLIO_DIR = PROJECT / "output" / "portfolio"
PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)

# ── Demo inputs for each agent ──────────────────────────────────────────────
# Each entry: (module_path, function_kwargs)
AGENT_DEMOS = {
    "ad_copy": {
        "import": "agents.ad_copy.runner",
        "kwargs": {
            "product": "AI-powered email automation platform that writes, sends, and tracks email campaigns",
            "platform": "google_search",
            "audience": "small business owners",
            "goal": "conversions",
        },
    },
    "seo_content": {
        "import": "agents.seo_content.runner",
        "kwargs": {
            "topic": "How AI Virtual Assistants Are Replacing Traditional Admin Work in 2026",
            "business": "Bit Rage Labour — AI-powered business services",
            "content_type": "blog",
            "tone": "professional",
        },
    },
    "data_entry": {
        "import": "agents.data_entry.runner",
        "kwargs": {
            "raw_data": "John Smith, CEO, Acme Corp, john@acme.com, +1-555-0100, New York\nJane Doe, CTO, Beta Inc, jane@beta.io, +44-20-7946-0958, London\nBob Wilson, Marketing Director, Gamma Ltd, bob@gamma.co, +61-2-8765-4321, Sydney",
            "output_format": "json",
            "task_type": "clean",
        },
    },
    "resume_writer": {
        "import": "agents.resume_writer.runner",
        "kwargs": {
            "career_data": "5 years as a digital marketing manager at a SaaS company. Led teams of 8. Grew organic traffic 340%. Managed $200K/month ad spend. Launched 3 product lines. Python, SQL, Google Analytics, HubSpot certified.",
            "target_role": "Head of Growth",
            "target_industry": "B2B SaaS",
            "style": "combination",
        },
    },
    "lead_gen": {
        "import": "agents.lead_gen.runner",
        "kwargs": {
            "industry": "E-commerce",
            "icp": "Online retailers doing $1M-$10M annual revenue who need help with email marketing and customer retention",
            "geo": "United States",
            "count": 10,
        },
    },
    "email_marketing": {
        "import": "agents.email_marketing.runner",
        "kwargs": {
            "brief": "Launch email sequence for a new AI writing tool. Target: content marketers and agency owners. Goal: free trial signups. Tool name: WriteBot AI. Key features: writes blog posts in 5 minutes, SEO optimized, 50+ templates.",
        },
    },
    "social_media": {
        "import": "agents.social_media.runner",
        "kwargs": {
            "brief": "Create a week of social media content for a B2B AI automation agency. Target platforms: LinkedIn, Twitter/X. Tone: professional but approachable. Key messages: AI saves 20+ hours/week, white-glove service, real ROI.",
        },
    },
    "content_repurpose": {
        "import": "agents.content_repurpose.runner",
        "kwargs": {
            "content": "A 2000-word blog post about how small businesses can use AI to automate their operations, covering email automation, data entry, customer support, and lead generation.",
            "formats": "linkedin,twitter,email,summary",
        },
    },
    "web_scraper": {
        "import": "agents.web_scraper.runner",
        "kwargs": {
            "brief": "Extract contact information for 10 digital marketing agencies in London from Google search results. Fields needed: company name, website, phone, email, services offered.",
        },
    },
    "crm_ops": {
        "import": "agents.crm_ops.runner",
        "kwargs": {
            "brief": "Clean and deduplicate a CRM contact list. Standardize phone numbers to E.164 format. Merge duplicate entries. Flag incomplete records. Add lead scoring based on job title and company size.",
        },
    },
    "bookkeeping": {
        "import": "agents.bookkeeping.runner",
        "kwargs": {
            "brief": "Categorize these transactions: $150 Adobe Creative Cloud (Software), $2400 Google Ads (Marketing), $89 Namecheap domain renewal (Web Hosting), $500 Contractor payment to Jane (Labor), $45 Zoom subscription (Software), $1200 Office rent (Rent).",
        },
    },
    "proposal_writer": {
        "import": "agents.proposal_writer.runner",
        "kwargs": {
            "brief": "Write a proposal for a web scraping and data entry project. Client needs 5000 product listings scraped from competitor websites, cleaned, and formatted into CSV. Budget range: $500-$1000. Timeline: 2 weeks.",
        },
    },
    "product_desc": {
        "import": "agents.product_desc.runner",
        "kwargs": {
            "product": "EcoBlend Pro — Portable Smart Blender with AI nutrition tracking, 6 titanium blades, 1200W motor, BPA-free Tritan jug, built-in scale, connects to health app via Bluetooth",
            "platform": "amazon",
        },
    },
    "market_research": {
        "import": "agents.market_research.runner",
        "kwargs": {
            "topic": "AI Virtual Assistant market for small businesses in 2026",
            "scope": "Market size, growth rate, key players, trends, and opportunities for a new entrant offering AI-powered business services",
        },
    },
    "business_plan": {
        "import": "agents.business_plan.runner",
        "kwargs": {
            "brief": "Create a business plan for an AI-powered freelancing agency that deploys 20 specialized AI agents to handle data entry, content writing, lead generation, and customer support for SMB clients. Revenue model: per-task pricing + monthly retainers.",
        },
    },
    "press_release": {
        "import": "agents.press_release.runner",
        "kwargs": {
            "brief": "Bit Rage Labour launches industry-first 24-agent AI workforce. The platform offers 20 specialized AI agents covering everything from SEO content to bookkeeping, available 24/7 at a fraction of traditional costs. Based in the UK.",
        },
    },
    "tech_docs": {
        "import": "agents.tech_docs.runner",
        "kwargs": {
            "brief": "Write API documentation for a REST endpoint: POST /api/v1/agents/run. Accepts JSON body with fields: agent (string, one of 20 agent types), input (object, agent-specific), provider (string, default 'openai'). Returns JSON with output, qa_result, and metadata.",
        },
    },
    "doc_extract": {
        "import": "agents.doc_extract.runner",
        "kwargs": {
            "brief": "Extract key data from this invoice text: Invoice #INV-2026-0042, From: Acme Solutions Ltd, To: Beta Corp, Date: 2026-03-15, Due: 2026-04-15, Items: Consulting (40hrs x $150 = $6000), Software License ($1200), Total: $7200, Tax: $1440, Grand Total: $8640",
        },
    },
    "support": {
        "import": "agents.support.runner",
        "kwargs": {
            "brief": "Customer complaint: 'I purchased your Premium plan 3 days ago but I still can't access the advanced analytics dashboard. I've tried logging out and back in, clearing cache, and using a different browser. My account email is sarah@example.com. This is urgent as I need to prepare a report by Friday.'",
        },
    },
    "sales_ops": {
        "import": "agents.sales_ops.runner",
        "kwargs": {
            "brief": "Write a cold outreach email sequence (3 emails) targeting marketing directors at e-commerce companies doing $5M-$50M revenue. Offer: AI-powered email marketing automation that increases open rates by 40% and saves 15 hours per week.",
        },
    },
}


def generate_sample(agent_name: str, provider: str = "openai") -> dict:
    """Generate a single portfolio sample for one agent."""
    if agent_name not in AGENT_DEMOS:
        print(f"  [SKIP] Unknown agent: {agent_name}")
        return {"agent": agent_name, "status": "unknown"}

    demo = AGENT_DEMOS[agent_name]
    print(f"\n  [{agent_name}] Generating portfolio sample...")

    try:
        import importlib
        module = importlib.import_module(demo["import"])
        run_pipeline = module.run_pipeline
        save_output = module.save_output

        kwargs = {**demo["kwargs"], "provider": provider}
        result = run_pipeline(**kwargs)

        # Save to portfolio directory
        output_data = result.model_dump() if hasattr(result, "model_dump") else result
        portfolio_file = PORTFOLIO_DIR / f"{agent_name}_sample.json"
        portfolio_file.write_text(json.dumps(output_data, indent=2, default=str), encoding="utf-8")

        # Also save via agent's own save_output
        save_output(result)

        qa_status = "UNKNOWN"
        if hasattr(result, "qa"):
            qa_status = result.qa.status if hasattr(result.qa, "status") else str(result.qa)
        elif isinstance(output_data, dict) and "qa" in output_data:
            qa_status = output_data["qa"].get("status", "UNKNOWN")

        print(f"  [{agent_name}] QA: {qa_status} — saved to {portfolio_file.name}")
        return {"agent": agent_name, "status": "success", "qa": qa_status, "file": str(portfolio_file)}

    except Exception as e:
        print(f"  [{agent_name}] FAILED: {e}")
        traceback.print_exc()
        return {"agent": agent_name, "status": "error", "error": str(e)}


def generate_all(provider: str = "openai") -> list[dict]:
    """Generate portfolio samples for all 20 agents."""
    print(f"\n{'='*70}")
    print(f"  BIT RAGE LABOUR — Portfolio Generator")
    print(f"  Generating samples across {len(AGENT_DEMOS)} agents")
    print(f"  Provider: {provider}")
    print(f"  Output: {PORTFOLIO_DIR}")
    print(f"{'='*70}")

    results = []
    for agent_name in AGENT_DEMOS:
        result = generate_sample(agent_name, provider=provider)
        results.append(result)

    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "error")
    print(f"\n{'='*70}")
    print(f"  PORTFOLIO GENERATION COMPLETE")
    print(f"  Success: {success}/{len(results)} | Failed: {failed}")

    if failed:
        print(f"\n  Failed agents:")
        for r in results:
            if r["status"] == "error":
                print(f"    - {r['agent']}: {r.get('error', '')[:60]}")

    print(f"{'='*70}")

    # Save manifest
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "results": results,
    }
    manifest_file = PORTFOLIO_DIR / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return results


def list_agents():
    """List all available agents."""
    print(f"\n  Available agents ({len(AGENT_DEMOS)}):")
    for name in sorted(AGENT_DEMOS.keys()):
        print(f"    - {name}")


def main():
    parser = argparse.ArgumentParser(description="Bit Rage Labour — Portfolio Sample Generator")
    parser.add_argument("--agent", type=str, default="", help="Generate for a single agent")
    parser.add_argument("--provider", type=str, default="openai",
                        choices=["openai", "anthropic", "gemini", "grok"],
                        help="LLM provider to use")
    parser.add_argument("--list", action="store_true", help="List available agents")
    args = parser.parse_args()

    if args.list:
        list_agents()
    elif args.agent:
        generate_sample(args.agent, provider=args.provider)
    else:
        generate_all(provider=args.provider)


if __name__ == "__main__":
    main()
