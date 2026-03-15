"""Smoke Test — Fiverr Platform: 100 Buyer Search Queries vs Gig Discovery.

Fiverr is seller-side: we publish gigs and buyers find us. This test
simulates 100 buyer search queries and checks if our 20 gigs surface
correctly based on tags, titles, and description keyword matching.

Tests:
  1. Tag matching       — buyer query vs gig tags
  2. Title matching     — buyer query vs gig title keywords
  3. Description match  — buyer query vs gig description keywords
  4. Coverage           — all 20 gigs must be discoverable
  5. Relevance          — correct gig surfaces for expected query
  6. False positives    — unrelated queries should NOT match our gigs
  7. Timing             — total pipeline speed

Usage:
    python -m tests.smoke_test_fiverr
    python -m tests.smoke_test_fiverr --verbose
    python -m tests.smoke_test_fiverr --report
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from campaign.fiverr_deploy import FIVERR_GIGS


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FIVERR GIG DISCOVERY ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def search_gigs(query: str) -> list[dict]:
    """Simulate Fiverr search: match a buyer query against our gigs.

    Scoring:
      - Tag match:         0.25 per matching tag
      - Title word match:  0.15 per matching word
      - Description match: 0.05 per matching keyword
      - Category match:    0.10 bonus

    Returns list of matching gigs sorted by relevance score.
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())
    results = []

    for gig in FIVERR_GIGS:
        score = 0.0

        # Tag matching (highest weight — Fiverr search is tag-driven)
        for tag in gig.get("tags", []):
            if tag.lower() in query_lower:
                score += 0.25
            else:
                # Partial: any word from tag appears in query
                tag_words = set(tag.lower().split())
                overlap = tag_words & query_words
                if overlap:
                    score += 0.10 * len(overlap) / len(tag_words)

        # Title matching
        title_words = set(gig["title"].lower().split())
        # Remove common Fiverr filler words
        filler = {"i", "will", "the", "a", "an", "for", "and", "or", "with", "your", "using", "any"}
        title_keywords = title_words - filler
        title_overlap = query_words & title_keywords
        score += 0.15 * len(title_overlap)

        # Description keyword matching
        desc_lower = gig.get("description", "").lower()
        for word in query_words:
            if len(word) > 3 and word in desc_lower:
                score += 0.05

        # Category matching
        cat_lower = gig.get("category", "").lower()
        for word in query_words:
            if len(word) > 3 and word in cat_lower:
                score += 0.10
                break  # Only one category bonus

        if score >= 0.20:
            results.append({
                "agent": gig["agent"],
                "title": gig["title"],
                "score": round(score, 2),
                "tags": gig.get("tags", []),
                "category": gig.get("category", ""),
                "packages": list(gig.get("packages", {}).keys()),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BUYER SEARCH QUERIES — 5 per gig, targeting all 20 agents
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BUYER_QUERIES = [
    # ── sales_ops ───────────────────────────────────────────────
    {"query": "cold email outreach b2b sales",
     "expected_agent": "sales_ops"},
    {"query": "sales email sequence prospect research",
     "expected_agent": "sales_ops"},
    {"query": "b2b lead outreach personalized cold email",
     "expected_agent": "sales_ops"},

    # ── support ─────────────────────────────────────────────────
    {"query": "customer support ticket automation ai",
     "expected_agent": "support"},
    {"query": "zendesk helpdesk ticket resolution",
     "expected_agent": "support"},
    {"query": "ai customer service agent support ticket",
     "expected_agent": "support"},

    # ── content_repurpose ───────────────────────────────────────
    {"query": "content repurposing blog social media",
     "expected_agent": "content_repurpose"},
    {"query": "repurpose blog post linkedin twitter instagram",
     "expected_agent": "content_repurpose"},
    {"query": "multi-platform content transformation",
     "expected_agent": "content_repurpose"},

    # ── doc_extract ─────────────────────────────────────────────
    {"query": "document extraction invoice processing ai",
     "expected_agent": "doc_extract"},
    {"query": "extract data from documents contracts",
     "expected_agent": "doc_extract"},
    {"query": "ai ocr document automation data extraction",
     "expected_agent": "doc_extract"},

    # ── lead_gen ────────────────────────────────────────────────
    {"query": "b2b lead generation prospect list",
     "expected_agent": "lead_gen"},
    {"query": "lead research sales leads qualified",
     "expected_agent": "lead_gen"},
    {"query": "icp targeting lead generation",
     "expected_agent": "lead_gen"},

    # ── email_marketing ─────────────────────────────────────────
    {"query": "email marketing sequence drip campaign",
     "expected_agent": "email_marketing"},
    {"query": "mailchimp email sequence welcome series",
     "expected_agent": "email_marketing"},
    {"query": "email copywriting newsletter campaign",
     "expected_agent": "email_marketing"},

    # ── seo_content ─────────────────────────────────────────────
    {"query": "seo blog post article writing",
     "expected_agent": "seo_content"},
    {"query": "seo content keyword article optimized",
     "expected_agent": "seo_content"},
    {"query": "blog writing seo article",
     "expected_agent": "seo_content"},

    # ── social_media ────────────────────────────────────────────
    {"query": "social media posts linkedin instagram captions",
     "expected_agent": "social_media"},
    {"query": "social media content calendar manager",
     "expected_agent": "social_media"},
    {"query": "instagram captions linkedin posts content",
     "expected_agent": "social_media"},

    # ── data_entry ──────────────────────────────────────────────
    {"query": "data entry cleaning spreadsheet csv",
     "expected_agent": "data_entry"},
    {"query": "excel data entry processing formatting",
     "expected_agent": "data_entry"},
    {"query": "data cleaning csv processing",
     "expected_agent": "data_entry"},

    # ── web_scraper ─────────────────────────────────────────────
    {"query": "web scraping data extraction website",
     "expected_agent": "web_scraper"},
    {"query": "data scraping web crawler mining",
     "expected_agent": "web_scraper"},
    {"query": "scrape website data mining price",
     "expected_agent": "web_scraper"},

    # ── crm_ops ─────────────────────────────────────────────────
    {"query": "crm cleanup salesforce data deduplication",
     "expected_agent": "crm_ops"},
    {"query": "hubspot crm data contact cleanup",
     "expected_agent": "crm_ops"},
    {"query": "crm data management salesforce admin",
     "expected_agent": "crm_ops"},

    # ── bookkeeping ─────────────────────────────────────────────
    {"query": "bookkeeping expense categorization quickbooks",
     "expected_agent": "bookkeeping"},
    {"query": "bank reconciliation accounting data entry",
     "expected_agent": "bookkeeping"},
    {"query": "xero bookkeeping transaction categorization",
     "expected_agent": "bookkeeping"},

    # ── proposal_writer ─────────────────────────────────────────
    {"query": "proposal writing rfp response business",
     "expected_agent": "proposal_writer"},
    {"query": "business proposal project proposal bid writing",
     "expected_agent": "proposal_writer"},
    {"query": "grant writing proposal writer",
     "expected_agent": "proposal_writer"},

    # ── product_desc ────────────────────────────────────────────
    {"query": "product descriptions amazon shopify listing",
     "expected_agent": "product_desc"},
    {"query": "amazon listing product copy ecommerce",
     "expected_agent": "product_desc"},
    {"query": "shopify product descriptions etsy listing",
     "expected_agent": "product_desc"},

    # ── resume_writer ───────────────────────────────────────────
    {"query": "resume writing ats optimized professional",
     "expected_agent": "resume_writer"},
    {"query": "cv writing cover letter linkedin",
     "expected_agent": "resume_writer"},
    {"query": "ats resume professional resume writer",
     "expected_agent": "resume_writer"},

    # ── ad_copy ─────────────────────────────────────────────────
    {"query": "ad copy google ads facebook ads ppc",
     "expected_agent": "ad_copy"},
    {"query": "linkedin ads ad copywriting social media",
     "expected_agent": "ad_copy"},
    {"query": "google ads ppc copy headlines descriptions",
     "expected_agent": "ad_copy"},

    # ── market_research ─────────────────────────────────────────
    {"query": "market research competitive analysis swot",
     "expected_agent": "market_research"},
    {"query": "market sizing industry analysis report",
     "expected_agent": "market_research"},
    {"query": "competitive analysis business analysis market",
     "expected_agent": "market_research"},

    # ── business_plan ───────────────────────────────────────────
    {"query": "business plan financial projections startup",
     "expected_agent": "business_plan"},
    {"query": "startup plan investor pitch fundraising",
     "expected_agent": "business_plan"},
    {"query": "lean canvas business plan writer",
     "expected_agent": "business_plan"},

    # ── press_release ───────────────────────────────────────────
    {"query": "press release writer ap style pr",
     "expected_agent": "press_release"},
    {"query": "media release news release public relations",
     "expected_agent": "press_release"},
    {"query": "press release writing pr newswire",
     "expected_agent": "press_release"},

    # ── tech_docs ───────────────────────────────────────────────
    {"query": "technical documentation api docs readme",
     "expected_agent": "tech_docs"},
    {"query": "software documentation user guide developer",
     "expected_agent": "tech_docs"},
    {"query": "api documentation technical writing",
     "expected_agent": "tech_docs"},

    # ── Extra mixed / tricky searches ───────────────────────────
    {"query": "ai automation content writing seo",
     "expected_agent": "seo_content"},
    {"query": "email automation drip campaign nurture leads",
     "expected_agent": "email_marketing"},
    {"query": "data extraction document processing invoice pdf",
     "expected_agent": "doc_extract"},
    {"query": "social media linkedin instagram content posts",
     "expected_agent": "social_media"},
    {"query": "web data scraping ecommerce product listings",
     "expected_agent": "web_scraper"},
    {"query": "crm salesforce hubspot data migration cleanup",
     "expected_agent": "crm_ops"},
    {"query": "bookkeeping quickbooks xero expense management",
     "expected_agent": "bookkeeping"},
    {"query": "resume cv ats keyword optimization career",
     "expected_agent": "resume_writer"},
    {"query": "google ads ppc ad campaign copywriting",
     "expected_agent": "ad_copy"},
    {"query": "market report competitive landscape research",
     "expected_agent": "market_research"},
    {"query": "startup business plan financial model investor",
     "expected_agent": "business_plan"},
    {"query": "press release product launch announcement pr",
     "expected_agent": "press_release"},
    {"query": "technical writing sdk guide developer docs",
     "expected_agent": "tech_docs"},
    {"query": "amazon product listing optimization ecommerce copy",
     "expected_agent": "product_desc"},
    {"query": "rfp response grant application proposal",
     "expected_agent": "proposal_writer"},
    {"query": "b2b sales lead list prospect research qualified",
     "expected_agent": "lead_gen"},
    {"query": "cold email b2b outreach sales automation",
     "expected_agent": "sales_ops"},
    {"query": "customer support ai helpdesk ticket agent",
     "expected_agent": "support"},
    {"query": "repurpose content blog to social multi platform",
     "expected_agent": "content_repurpose"},
    {"query": "excel spreadsheet data entry cleaning validation",
     "expected_agent": "data_entry"},
]

# ── Negative queries that should NOT match any of our gigs ──
NEGATIVE_QUERIES = [
    {"query": "unity 3d game developer c# mobile rpg",
     "expected_agent": None},
    {"query": "react native ios android app flutter dart",
     "expected_agent": None},
    {"query": "wordpress theme php plugin development",
     "expected_agent": None},
    {"query": "solidity smart contract blockchain ethereum defi",
     "expected_agent": None},
    {"query": "video editing premiere pro after effects motion",
     "expected_agent": None},
    {"query": "piano teacher music lessons violin singing",
     "expected_agent": None},
    {"query": "architectural 3d rendering autocad revit",
     "expected_agent": None},
    {"query": "voice over narration audiobook recording",
     "expected_agent": None},
    {"query": "translation spanish french german interpreter",
     "expected_agent": None},
    {"query": "photography portrait wedding photoshoot editing",
     "expected_agent": None},
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SMOKE TEST ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_smoke_test(verbose: bool = False, save_report: bool = False):
    """Run full Fiverr smoke test — buyer search queries vs gig discovery."""
    print("\n" + "=" * 70)
    print("  FIVERR SMOKE TEST — Buyer Search Queries vs Gig Discovery")
    print("  search_gigs() → tag match → title match → relevance score")
    print("=" * 70)

    all_queries = []
    for q in BUYER_QUERIES:
        q["source"] = "buyer_query"
        all_queries.append(q)
    for q in NEGATIVE_QUERIES:
        q["source"] = "negative_control"
        all_queries.append(q)

    total = len(all_queries)
    print(f"\n  [DATA] {len(BUYER_QUERIES)} buyer search queries covering all 20 gigs")
    print(f"  [DATA] {len(NEGATIVE_QUERIES)} negative control queries")
    print(f"  [DATA] Total queries: {total}")
    print(f"  [DATA] Gigs available: {len(FIVERR_GIGS)}")
    print("-" * 70)

    # Metrics
    results = []
    match_count = 0
    no_match_count = 0
    negative_correct = 0
    negative_wrong = 0
    gig_match_counts = Counter()
    gig_coverage = set()
    expected_hits = 0
    expected_misses = 0
    relevance_scores = []
    timings = []
    pkg_coverage = Counter()  # Track package tier presence

    for i, query_item in enumerate(all_queries, 1):
        query = query_item["query"]
        source = query_item["source"]
        expected_agent = query_item.get("expected_agent")

        t0 = time.perf_counter()
        gig_results = search_gigs(query)
        elapsed = (time.perf_counter() - t0) * 1000
        timings.append(elapsed)

        top_agent = gig_results[0]["agent"] if gig_results else None
        top_score = gig_results[0]["score"] if gig_results else 0

        if gig_results:
            match_count += 1
            for g in gig_results:
                gig_match_counts[g["agent"]] += 1
                gig_coverage.add(g["agent"])
                relevance_scores.append(g["score"])
                for pkg in g.get("packages", []):
                    pkg_coverage[pkg.split("(")[0].strip()] += 1
        else:
            no_match_count += 1

        if source == "negative_control":
            if not gig_results:
                negative_correct += 1
            else:
                negative_wrong += 1

        if expected_agent:
            if top_agent == expected_agent:
                expected_hits += 1
            else:
                expected_misses += 1

        result = {
            "index": i,
            "query": query[:80],
            "source": source,
            "matches": len(gig_results),
            "top_agent": top_agent,
            "top_score": top_score,
            "expected_agent": expected_agent,
            "correct_match": top_agent == expected_agent if expected_agent else None,
            "elapsed_ms": round(elapsed, 2),
        }
        results.append(result)

        if verbose:
            status = "✓" if (not expected_agent or top_agent == expected_agent) else "✗"
            match_str = f"{top_agent}({top_score})" if top_agent else "NO MATCH"
            print(f"  [{i:3d}] {status} {match_str:35s} | {query[:55]}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  RESULTS REPORT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    print("\n" + "=" * 70)
    print("  FIVERR SMOKE TEST RESULTS")
    print("=" * 70)

    print(f"\n  Total queries tested:       {total}")
    print(f"  Buyer queries:              {len(BUYER_QUERIES)}")
    print(f"  Negative controls:          {len(NEGATIVE_QUERIES)}")
    print(f"  Gigs in catalog:            {len(FIVERR_GIGS)}")

    # Discovery
    print(f"\n  ── GIG DISCOVERY ─────────────────────────")
    print(f"  Queries with gig match:     {match_count}/{total} ({100*match_count/total:.1f}%)")
    print(f"  Queries with no match:      {no_match_count}/{total} ({100*no_match_count/total:.1f}%)")
    if relevance_scores:
        avg_rel = sum(relevance_scores) / len(relevance_scores)
        max_rel = max(relevance_scores)
        min_rel = min(relevance_scores)
        print(f"  Relevance — avg: {avg_rel:.2f}, min: {min_rel:.2f}, max: {max_rel:.2f}")

    # Gig coverage
    all_gig_agents = set(g["agent"] for g in FIVERR_GIGS)
    missing_gigs = all_gig_agents - gig_coverage
    print(f"\n  ── GIG COVERAGE ──────────────────────────")
    print(f"  Gigs discovered:            {len(gig_coverage)}/20 ({100*len(gig_coverage)/20:.0f}%)")
    if missing_gigs:
        print(f"  MISSING (never surfaced):   {', '.join(sorted(missing_gigs))}")
    print(f"\n  Discovery counts per gig:")
    for agent in sorted(all_gig_agents):
        count = gig_match_counts.get(agent, 0)
        bar = "█" * min(count, 40)
        flag = " ← ZERO!" if count == 0 else ""
        print(f"    {agent:22s}: {count:3d} {bar}{flag}")

    # Tag analysis
    print(f"\n  ── TAG ANALYSIS ──────────────────────────")
    total_tags = sum(len(g.get("tags", [])) for g in FIVERR_GIGS)
    unique_tags = set()
    for g in FIVERR_GIGS:
        for tag in g.get("tags", []):
            unique_tags.add(tag.lower())
    print(f"  Total tags across gigs:     {total_tags}")
    print(f"  Unique tags:                {len(unique_tags)}")
    print(f"  Avg tags per gig:           {total_tags/len(FIVERR_GIGS):.1f}")

    # Expected gig accuracy
    query_total = expected_hits + expected_misses
    if query_total > 0:
        print(f"\n  ── EXPECTED GIG ACCURACY ──────────────────")
        print(f"  Correct top gig:            {expected_hits}/{query_total} ({100*expected_hits/query_total:.1f}%)")
        print(f"  Wrong top gig:              {expected_misses}/{query_total}")
        if expected_misses > 0:
            print(f"  Mismatches:")
            for r in results:
                if r.get("correct_match") is False:
                    print(f"    \"{r['query'][:60]}\"")
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
                    print(f"    \"{r['query'][:60]}\" → matched {r['top_agent']}")

    # Package tiers
    print(f"\n  ── PACKAGE TIERS ─────────────────────────")
    for tier in ["Basic", "Standard", "Premium"]:
        count = sum(1 for g in FIVERR_GIGS if any(tier in k for k in g.get("packages", {})))
        print(f"    {tier:10s}: {count}/20 gigs have this tier")

    # Performance
    avg_time = sum(timings) / len(timings) if timings else 0
    max_time = max(timings) if timings else 0
    total_time = sum(timings)
    print(f"\n  ── PERFORMANCE ───────────────────────────")
    print(f"  Total search time:          {total_time:.1f}ms")
    print(f"  Avg per query:              {avg_time:.2f}ms")
    print(f"  Max per query:              {max_time:.2f}ms")
    if avg_time > 0:
        print(f"  Throughput:                 {1000/avg_time:.0f} queries/sec")

    # Overall verdict
    print(f"\n  {'='*50}")
    issues = []
    if len(gig_coverage) < 20:
        issues.append(f"Only {len(gig_coverage)}/20 gigs discoverable")
    if negative_wrong > 0:
        issues.append(f"{negative_wrong} false positive(s) on negative controls")
    if query_total > 0 and expected_hits / query_total < 0.80:
        issues.append(f"Gig accuracy below 80% ({100*expected_hits/query_total:.0f}%)")

    if not issues:
        print("  VERDICT: ✓ ALL CHECKS PASSED")
    else:
        print(f"  VERDICT: ✗ {len(issues)} ISSUE(S) FOUND")
        for issue in issues:
            print(f"    • {issue}")
    print("=" * 70 + "\n")

    # Save report
    if save_report:
        report_path = PROJECT / "output" / "smoke_test_fiverr_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "platform": "fiverr",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_queries": total,
            "buyer_queries": len(BUYER_QUERIES),
            "negative_queries": len(NEGATIVE_QUERIES),
            "gigs_in_catalog": len(FIVERR_GIGS),
            "match_rate": round(match_count / total, 3),
            "gig_coverage": len(gig_coverage),
            "missing_gigs": sorted(missing_gigs),
            "expected_accuracy": round(expected_hits / query_total, 3) if query_total else None,
            "negative_control_pass": negative_correct == neg_total,
            "avg_time_ms": round(avg_time, 2),
            "total_time_ms": round(total_time, 2),
            "gig_match_counts": dict(gig_match_counts),
            "results": results,
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  Report saved: {report_path}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fiverr smoke test — buyer queries vs gig discovery")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each query result")
    parser.add_argument("--report", "-r", action="store_true", help="Save JSON report")
    args = parser.parse_args()
    run_smoke_test(verbose=args.verbose, save_report=args.report)
