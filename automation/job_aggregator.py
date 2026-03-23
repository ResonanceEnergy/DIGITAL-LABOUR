"""Job Aggregator — unified cross-platform job feed with deduplication and scoring.

Reads scraped job data from all 5 platforms (Freelancer, Upwork, PPH, Guru, Fiverr buyer requests),
normalizes into a common schema, deduplicates cross-posted jobs, scores against our 20 agents,
and produces a ranked opportunity feed.

Usage:
    python -m automation.job_aggregator                    # Aggregate + rank all
    python -m automation.job_aggregator --top 20           # Show top 20 opportunities
    python -m automation.job_aggregator --platform upwork  # Filter by platform
    python -m automation.job_aggregator --agent seo_content # Filter by best-match agent
    python -m automation.job_aggregator --export feed.json  # Export ranked feed
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

# ── Data Sources ────────────────────────────────────────────────────────────
DATA_DIR = PROJECT / "data"
SOURCES = {
    "freelancer": DATA_DIR / "freelancer_jobs" / "project_log.jsonl",
    "upwork":     DATA_DIR / "upwork_jobs" / "job_log.jsonl",
    "pph":        DATA_DIR / "pph_jobs" / "project_log.jsonl",
    "guru":       DATA_DIR / "guru_jobs" / "project_log.jsonl",
    "fiverr_br":  DATA_DIR / "fiverr_orders" / "buyer_requests.jsonl",
}

FEED_DIR = DATA_DIR / "aggregated_feed"
FEED_DIR.mkdir(parents=True, exist_ok=True)
FEED_FILE = FEED_DIR / "ranked_feed.json"

# ── Bid history files (to check what we've already bid on) ──────────────────
BID_LOGS = {
    "freelancer": DATA_DIR / "freelancer_jobs" / "bids_submitted.json",
    "upwork":     DATA_DIR / "upwork_jobs" / "bids_submitted.json",
    "pph":        DATA_DIR / "pph_jobs" / "proposals_sent.json",
    "guru":       DATA_DIR / "guru_jobs" / "bids_submitted.json",
}

# ── Agent Capability Map ────────────────────────────────────────────────────
AGENT_KEYWORDS = {
    "data_entry":       ["data entry", "data processing", "spreadsheet", "csv", "excel", "typing"],
    "web_scraper":      ["web scraping", "scraping", "data mining", "web crawl", "extract data"],
    "email_marketing":  ["email marketing", "email campaign", "newsletter", "drip", "mailchimp"],
    "seo_content":      ["seo", "blog", "article", "keyword research", "content writing", "seo writing"],
    "lead_gen":         ["lead generation", "lead gen", "prospect", "b2b leads", "cold calling"],
    "sales_ops":        ["cold email", "outreach", "sales", "follow-up", "pipeline"],
    "content_repurpose":["content", "repurpose", "social media content", "content creation"],
    "social_media":     ["social media", "linkedin", "instagram", "twitter", "facebook", "tiktok"],
    "product_desc":     ["product description", "amazon", "shopify", "etsy", "ecommerce", "listing"],
    "bookkeeping":      ["bookkeeping", "accounting", "quickbooks", "xero", "expense", "invoice"],
    "resume_writer":    ["resume", "cv", "cover letter", "linkedin profile"],
    "market_research":  ["market research", "competitive analysis", "swot", "industry report"],
    "business_plan":    ["business plan", "financial projection", "pitch deck", "startup plan"],
    "ad_copy":          ["ad copy", "google ads", "facebook ads", "ppc", "advertising"],
    "tech_docs":        ["technical documentation", "api documentation", "user guide", "manual"],
    "press_release":    ["press release", "media release", "pr writing"],
    "proposal_writer":  ["proposal", "bid writing", "rfp", "tender"],
    "crm_ops":          ["crm", "salesforce", "hubspot", "zoho", "customer data"],
    "doc_extract":      ["document extraction", "ocr", "pdf extraction", "invoice processing"],
    "support":          ["customer support", "help desk", "ticket", "support agent", "live chat"],
}


def _parse_budget(budget_str: str) -> float:
    """Extract a numeric budget from various string formats."""
    if not budget_str:
        return 0.0
    nums = re.findall(r"[\d,]+\.?\d*", budget_str.replace(",", ""))
    if nums:
        vals = [float(n) for n in nums]
        return max(vals)  # Take the higher end of ranges
    return 0.0


def _load_jsonl(filepath: Path, max_age_hours: int = 48) -> list[dict]:
    """Load entries from a JSONL file, optionally filtering by age."""
    if not filepath.exists():
        return []
    entries = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    for line in filepath.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            # Check age if timestamp field exists
            ts_field = entry.get("scraped_at") or entry.get("found_at") or entry.get("timestamp")
            if ts_field:
                try:
                    ts = datetime.fromisoformat(ts_field.replace("Z", "+00:00"))
                    if ts < cutoff:
                        continue
                except (ValueError, AttributeError):
                    pass
            entries.append(entry)
        except json.JSONDecodeError:
            continue
    return entries


def _load_all_bids() -> set:
    """Load all previously-bid project IDs across all platforms."""
    all_ids = set()
    for platform, path in BID_LOGS.items():
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for bid in data:
                    pid = str(bid.get("project_id", ""))
                    if pid:
                        all_ids.add(f"{platform}:{pid}")
            except (json.JSONDecodeError, KeyError):
                pass
    return all_ids


def match_agent(title: str, description: str) -> tuple[str, float]:
    """Match a job to the best internal agent and return (agent_name, confidence)."""
    text = f"{title} {description}".lower()
    best_agent = "support"
    best_score = 0.0

    for agent, keywords in AGENT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text)
        score = hits / len(keywords) if keywords else 0
        if score > best_score:
            best_score = score
            best_agent = agent

    return best_agent, round(best_score, 3)


def normalize_entry(entry: dict, platform: str) -> dict:
    """Normalize a platform-specific entry into common schema."""
    title = entry.get("title", "")
    desc = entry.get("description", "") or entry.get("snippet", "")
    budget_str = entry.get("budget", "") or entry.get("budget_range", "")
    url = entry.get("url", "") or entry.get("project_url", "")
    pid = entry.get("project_id", "") or entry.get("job_id", "") or entry.get("id", "")

    agent, agent_conf = match_agent(title, desc)
    score = entry.get("score", 0)

    return {
        "platform": platform,
        "project_id": str(pid),
        "title": title[:200],
        "description": desc[:500],
        "budget_raw": budget_str,
        "budget_usd": _parse_budget(budget_str),
        "url": url,
        "score": score if score else agent_conf,
        "best_agent": agent,
        "agent_confidence": agent_conf,
        "skills": entry.get("skills", []),
        "scraped_at": entry.get("scraped_at") or entry.get("found_at") or "",
    }


def _dedup_key(entry: dict) -> str:
    """Generate deduplication key — normalize title for cross-platform matching."""
    title = re.sub(r"[^a-z0-9 ]", "", entry["title"].lower()).strip()
    # Collapse to first 8 words for fuzzy matching
    words = title.split()[:8]
    return " ".join(words)


def aggregate(max_age_hours: int = 48, platform_filter: str = "", agent_filter: str = "") -> list[dict]:
    """Load, normalize, deduplicate, and rank all jobs across platforms."""
    all_entries = []
    all_bids = _load_all_bids()

    for platform, filepath in SOURCES.items():
        if platform_filter and platform != platform_filter:
            continue
        raw = _load_jsonl(filepath, max_age_hours=max_age_hours)
        for entry in raw:
            normalized = normalize_entry(entry, platform)
            bid_key = f"{platform}:{normalized['project_id']}"
            normalized["already_bid"] = bid_key in all_bids
            all_entries.append(normalized)

    # Dedup cross-posted jobs (keep highest-scoring version)
    seen = {}
    for entry in all_entries:
        key = _dedup_key(entry)
        if key in seen:
            if entry["score"] > seen[key]["score"]:
                seen[key] = entry
        else:
            seen[key] = entry

    deduped = list(seen.values())

    # Filter by agent if requested
    if agent_filter:
        deduped = [e for e in deduped if e["best_agent"] == agent_filter]

    # Rank by composite score: score * 0.6 + agent_confidence * 0.3 + budget_factor * 0.1
    for entry in deduped:
        budget_factor = min(1.0, entry["budget_usd"] / 500.0) if entry["budget_usd"] > 0 else 0.3
        entry["rank_score"] = round(
            entry["score"] * 0.6 + entry["agent_confidence"] * 0.3 + budget_factor * 0.1, 3
        )

    deduped.sort(key=lambda x: x["rank_score"], reverse=True)

    return deduped


def show_feed(entries: list[dict], top_n: int = 30):
    """Pretty-print the ranked feed."""
    print(f"\n{'='*80}")
    print(f"  DIGITAL LABOUR — UNIFIED JOB FEED")
    print(f"  {len(entries)} opportunities across {len(set(e['platform'] for e in entries))} platforms")
    print(f"{'='*80}")

    # Stats
    by_platform = {}
    by_agent = {}
    for e in entries:
        by_platform[e["platform"]] = by_platform.get(e["platform"], 0) + 1
        by_agent[e["best_agent"]] = by_agent.get(e["best_agent"], 0) + 1

    print(f"\n  Platform breakdown:")
    for plat, count in sorted(by_platform.items(), key=lambda x: -x[1]):
        print(f"    {plat:15s} {count:4d}")

    print(f"\n  Top agents by demand:")
    for agent, count in sorted(by_agent.items(), key=lambda x: -x[1])[:10]:
        print(f"    {agent:20s} {count:4d}")

    print(f"\n  {'RANK':>4}  {'SCORE':>5}  {'PLAT':>10}  {'AGENT':>18}  {'BUDGET':>10}  {'TITLE'}")
    print(f"  {'─'*4}  {'─'*5}  {'─'*10}  {'─'*18}  {'─'*10}  {'─'*40}")

    for i, e in enumerate(entries[:top_n], 1):
        bid = " ✓" if e["already_bid"] else ""
        budget = f"${e['budget_usd']:.0f}" if e["budget_usd"] > 0 else e["budget_raw"][:10]
        print(f"  {i:4d}  {e['rank_score']:.3f}  {e['platform']:>10}  {e['best_agent']:>18}  {budget:>10}  {e['title'][:45]}{bid}")


def export_feed(entries: list[dict], filepath: str):
    """Export ranked feed to JSON."""
    output = Path(filepath) if filepath else FEED_FILE
    output.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"\n  Exported {len(entries)} entries to {output}")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DIGITAL LABOUR — Job Aggregator")
    parser.add_argument("--top", type=int, default=30, help="Show top N opportunities")
    parser.add_argument("--platform", type=str, default="", help="Filter by platform")
    parser.add_argument("--agent", type=str, default="", help="Filter by best-match agent")
    parser.add_argument("--hours", type=int, default=48, help="Max age of jobs in hours")
    parser.add_argument("--export", type=str, default="", help="Export to JSON file")
    args = parser.parse_args()

    entries = aggregate(
        max_age_hours=args.hours,
        platform_filter=args.platform,
        agent_filter=args.agent,
    )

    show_feed(entries, top_n=args.top)

    # Always save to default feed file
    export_feed(entries, args.export if args.export else "")


if __name__ == "__main__":
    main()
