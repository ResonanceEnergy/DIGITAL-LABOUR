"""Generate copy-paste-ready platform upload files for all 6 freelance platforms.

Outputs one text file per platform in output/platform_copy/ with formatted
listings ready to paste into each platform's UI.

Usage:
    python -m tests.gen_platform_copy
"""

import io
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OUT_DIR = PROJECT_ROOT / "output" / "platform_copy"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def gen_fiverr():
    from income.freelance_listings import FIVERR_GIGS
    lines = []
    lines.append("=" * 80)
    lines.append("FIVERR GIG LISTINGS — BIT RAGE SYSTEMS")
    lines.append(f"Total Gigs: {len(FIVERR_GIGS)}")
    lines.append("=" * 80)

    for i, gig in enumerate(FIVERR_GIGS, 1):
        lines.append(f"\n{'─' * 80}")
        lines.append(f"GIG #{i}")
        lines.append(f"{'─' * 80}")
        lines.append(f"Title: {gig['title']}")
        lines.append(f"Category: {gig['category']}")
        lines.append(f"Tags: {', '.join(gig.get('tags', []))}")
        lines.append(f"\nDescription:\n{gig['description']}")

        if gig.get("packages"):
            lines.append("\nPackages:")
            for pkg_name, pkg_val in gig["packages"].items():
                if isinstance(pkg_val, dict):
                    lines.append(f"  {pkg_name}: ${pkg_val.get('price','N/A')} | {pkg_val.get('delivery','N/A')} | {pkg_val.get('description','')}")
                else:
                    lines.append(f"  {pkg_name}: {pkg_val}")

        if gig.get("faq"):
            lines.append("\nFAQ:")
            for faq in gig["faq"]:
                if isinstance(faq, (list, tuple)) and len(faq) >= 2:
                    lines.append(f"  Q: {faq[0]}")
                    lines.append(f"  A: {faq[1]}")
                elif isinstance(faq, dict):
                    lines.append(f"  Q: {faq.get('q', '')}")
                    lines.append(f"  A: {faq.get('a', '')}")

    path = OUT_DIR / "fiverr_listings.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Fiverr: {len(FIVERR_GIGS)} gigs -> {path.name}")
    return path


def gen_upwork():
    from income.freelance_listings import UPWORK_PROFILE
    lines = []
    lines.append("=" * 80)
    lines.append("UPWORK PROFILE & SERVICE CATALOG — BIT RAGE SYSTEMS")
    lines.append("=" * 80)

    lines.append(f"\nAgency: {UPWORK_PROFILE.get('agency_name', 'BIT RAGE SYSTEMS')}")
    lines.append(f"Tagline: {UPWORK_PROFILE.get('tagline', '')}")
    lines.append(f"Overview:\n{UPWORK_PROFILE.get('overview', '')}")

    lines.append(f"\n{'=' * 80}")
    lines.append(f"SERVICE CATALOG ({len(UPWORK_PROFILE['service_catalog'])} services)")
    lines.append("=" * 80)

    for i, svc in enumerate(UPWORK_PROFILE["service_catalog"], 1):
        lines.append(f"\n{'─' * 80}")
        lines.append(f"SERVICE #{i}: {svc.get('agent', '').upper()}")
        lines.append(f"{'─' * 80}")
        lines.append(f"Title: {svc['service_title']}")
        lines.append(f"Price: ${svc.get('fixed_price', 'N/A')}")
        lines.append(f"Delivery: {svc.get('delivery', 'N/A')}")
        lines.append(f"\n{svc['description']}")

    lines.append(f"\n{'=' * 80}")
    lines.append(f"PORTFOLIO ({len(UPWORK_PROFILE['portfolio_items'])} items)")
    lines.append("=" * 80)

    for i, item in enumerate(UPWORK_PROFILE["portfolio_items"], 1):
        lines.append(f"\n  {i}. {item.get('title', '')}")
        lines.append(f"     Category: {item.get('category', '')}")
        lines.append(f"     {item.get('description', '')[:200]}")

    if UPWORK_PROFILE.get("specialized_profiles"):
        lines.append(f"\n{'=' * 80}")
        lines.append(f"SPECIALIZED PROFILES ({len(UPWORK_PROFILE['specialized_profiles'])})")
        lines.append("=" * 80)
        for sp in UPWORK_PROFILE["specialized_profiles"]:
            lines.append(f"\n  {sp.get('title', '')}")
            lines.append(f"  Rate: ${sp.get('hourly_rate', 'N/A')}/hr")
            lines.append(f"  Skills: {', '.join(sp.get('skills', []))}")

    path = OUT_DIR / "upwork_listings.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Upwork: {len(UPWORK_PROFILE['service_catalog'])} services + {len(UPWORK_PROFILE['portfolio_items'])} portfolio -> {path.name}")
    return path


def gen_pph():
    from income.freelance_listings import PEOPLEPERHOUR_PROFILE
    lines = []
    lines.append("=" * 80)
    lines.append("PEOPLEPERHOUR HOURLIES — BIT RAGE SYSTEMS")
    lines.append(f"Total Hourlies: {len(PEOPLEPERHOUR_PROFILE['hourlies'])}")
    lines.append("=" * 80)

    for i, h in enumerate(PEOPLEPERHOUR_PROFILE["hourlies"], 1):
        lines.append(f"\n{'─' * 80}")
        lines.append(f"HOURLIE #{i}")
        lines.append(f"{'─' * 80}")
        lines.append(f"Title: {h['title']}")
        lines.append(f"Price: {h.get('price', 'N/A')}")
        lines.append(f"Delivery: {h.get('delivery', 'N/A')}")
        lines.append(f"\n{h['description']}")

    path = OUT_DIR / "pph_listings.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  PPH: {len(PEOPLEPERHOUR_PROFILE['hourlies'])} hourlies -> {path.name}")
    return path


def gen_guru():
    from income.freelance_listings import GURU_PROFILE
    lines = []
    lines.append("=" * 80)
    lines.append("GURU SERVICE LISTINGS — BIT RAGE SYSTEMS")
    lines.append(f"Total Listings: {len(GURU_PROFILE['service_listings'])}")
    lines.append("=" * 80)

    for i, s in enumerate(GURU_PROFILE["service_listings"], 1):
        lines.append(f"\n{'─' * 80}")
        lines.append(f"LISTING #{i}: {s.get('agent', '').upper()}")
        lines.append(f"{'─' * 80}")
        lines.append(f"Title: {s['title']}")
        lines.append(f"Category: {s.get('category', '')}")
        lines.append(f"Price: {s.get('price', 'N/A')}")
        lines.append(f"\n{s['description']}")

    path = OUT_DIR / "guru_listings.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Guru: {len(GURU_PROFILE['service_listings'])} listings -> {path.name}")
    return path


def gen_toptal():
    from income.freelance_listings import TOPTAL_PROFILE
    lines = []
    lines.append("=" * 80)
    lines.append("TOPTAL PROJECT TYPES — BIT RAGE SYSTEMS")
    lines.append(f"Total Projects: {len(TOPTAL_PROFILE['project_types'])}")
    lines.append("=" * 80)

    for i, p in enumerate(TOPTAL_PROFILE["project_types"], 1):
        lines.append(f"\n{'─' * 80}")
        lines.append(f"PROJECT #{i}: {p.get('agent', '').upper()}")
        lines.append(f"{'─' * 80}")
        lines.append(f"Title: {p['title']}")
        lines.append(f"Rate: {p.get('rate', 'N/A')}")
        lines.append(f"\n{p['description']}")

    path = OUT_DIR / "toptal_listings.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Toptal: {len(TOPTAL_PROFILE['project_types'])} projects -> {path.name}")
    return path


def gen_freelancer():
    from campaign.freelancer_deploy import FREELANCER_GIGS, BID_TEMPLATES
    lines = []
    lines.append("=" * 80)
    lines.append("FREELANCER GIGS & BID TEMPLATES — BIT RAGE SYSTEMS")
    lines.append(f"Total Gigs: {len(FREELANCER_GIGS)}")
    lines.append("=" * 80)

    for i, gig in enumerate(FREELANCER_GIGS, 1):
        lines.append(f"\n{'─' * 80}")
        lines.append(f"GIG #{i}: {gig.get('agent', '').upper()}")
        lines.append(f"{'─' * 80}")
        lines.append(f"Title: {gig['title']}")
        lines.append(f"Category: {gig.get('category', '')}")
        lines.append(f"Skills: {', '.join(gig.get('skills', []))}")
        lines.append(f"Keywords: {', '.join(gig.get('keywords', []))}")
        lines.append(f"\n{gig['description']}")

        if gig.get("packages"):
            lines.append("\nPackages:")
            for pkg_name, pkg_val in gig["packages"].items():
                if isinstance(pkg_val, dict):
                    lines.append(f"  {pkg_name}: ${pkg_val.get('price','N/A')} | {pkg_val.get('delivery','N/A')} | {pkg_val.get('description','')}")
                else:
                    lines.append(f"  {pkg_name}: {pkg_val}")

    lines.append(f"\n\n{'=' * 80}")
    lines.append("BID TEMPLATES")
    lines.append("=" * 80)

    for agent_key, bid in BID_TEMPLATES.items():
        lines.append(f"\n{'─' * 80}")
        lines.append(f"BID: {agent_key.upper()}")
        lines.append(f"{'─' * 80}")
        lines.append(f"Subject: {bid.get('subject', '')}")
        lines.append(f"\n{bid.get('body', '')}")

    path = OUT_DIR / "freelancer_listings.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Freelancer: {len(FREELANCER_GIGS)} gigs + {len(BID_TEMPLATES)} bids -> {path.name}")
    return path


def main():
    print("=" * 60)
    print("GENERATING PLATFORM UPLOAD COPY")
    print("=" * 60)

    paths = []
    paths.append(gen_fiverr())
    paths.append(gen_upwork())
    paths.append(gen_pph())
    paths.append(gen_guru())
    paths.append(gen_toptal())
    paths.append(gen_freelancer())

    print(f"\n{'=' * 60}")
    print(f"DONE: {len(paths)} platform files generated")
    print(f"Location: {OUT_DIR}")
    for p in paths:
        size = p.stat().st_size
        print(f"  {p.name:30s} {size:>8,} bytes")
    print("=" * 60)


if __name__ == "__main__":
    main()
