"""Auto-Register — Automated platform onboarding for all income channels.

Walks through every income platform in priority order:
  1. Generates all content (profiles, gig listings, bot templates, bid copy)
  2. Opens registration URL in browser
  3. Waits for confirmation (or auto-advances in batch mode)
  4. Updates income tracker status
  5. Logs completion with timestamp

Modes:
  --prepare     Generate all content files without opening browsers
  --run         Guided walk-through (opens browser, waits for confirmation)
  --run --yes   Batch mode (no prompts, marks researched + opens all URLs)
  --status      Show registration progress dashboard
  --reset       Reset all statuses to not_started

Usage:
    python -m income.auto_register --prepare        # Generate all content first
    python -m income.auto_register --run             # Guided platform-by-platform
    python -m income.auto_register --run --only fiverr,freelancer  # Specific platforms
    python -m income.auto_register --run --yes       # Batch open all, mark researched
    python -m income.auto_register --status          # Progress dashboard
"""

import json
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from income.tracker import (
    STATUSES,
    _load_tracker,
    _save_tracker,
    update_status,
)
from income.register import REGISTRATIONS
from income.freelance_listings import (
    FIVERR_GIGS,
    FREELANCER_PROFILE,
    UPWORK_PROFILE,
    save_listings,
)
from income.platform_bots import (
    CHATBASE_TEMPLATES,
    BOTPRESS_TEMPLATES,
    save_templates,
)

PREP_DIR = PROJECT_ROOT / "output" / "registration_prep"
LOG_FILE = PROJECT_ROOT / "data" / "registration_log.json"


# ── Content Preparation ────────────────────────────────────────

def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def prepare_all():
    """Generate every content file needed for registration.

    Creates output/registration_prep/ with ready-to-paste content for each
    platform — profiles, gig listings, bid templates, bot configs.
    """
    PREP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print("  PREPARING REGISTRATION CONTENT")
    print(f"{'='*70}")

    # 1. Fiverr gigs
    fiverr_dir = PREP_DIR / "fiverr"
    fiverr_dir.mkdir(exist_ok=True)
    for i, gig in enumerate(FIVERR_GIGS, 1):
        _save_json(fiverr_dir / f"gig_{i}.json", gig)
        # Also save plain-text version for easy copy-paste
        txt_path = fiverr_dir / f"gig_{i}.txt"
        lines = [
            f"TITLE: {gig['title']}",
            f"CATEGORY: {gig['category']}",
            f"TAGS: {', '.join(gig['tags'])}",
            "",
            "DESCRIPTION:",
            gig["description"],
            "",
            "PACKAGES:",
        ]
        for pkg, desc in gig["packages"].items():
            lines.append(f"  {pkg}: {desc}")
        lines.append("\nFAQ:")
        for q, a in gig["faq"]:
            lines.append(f"  Q: {q}")
            lines.append(f"  A: {a}")
        txt_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [OK] {len(FIVERR_GIGS)} Fiverr gigs → {fiverr_dir}")

    # 2. Freelancer.com profile + bid templates
    freelancer_dir = PREP_DIR / "freelancer"
    freelancer_dir.mkdir(exist_ok=True)
    _save_json(freelancer_dir / "profile.json", FREELANCER_PROFILE)
    profile_txt = [
        f"AGENCY NAME: {FREELANCER_PROFILE['agency_name']}",
        f"TAGLINE: {FREELANCER_PROFILE['tagline']}",
        f"HOURLY RATE: {FREELANCER_PROFILE['hourly_rate']}",
        "",
        "ABOUT:",
        FREELANCER_PROFILE["about"],
        "",
        f"SKILLS: {', '.join(FREELANCER_PROFILE['skills'])}",
    ]
    (freelancer_dir / "profile.txt").write_text("\n".join(profile_txt), encoding="utf-8")
    for name, template in FREELANCER_PROFILE["bid_templates"].items():
        (freelancer_dir / f"bid_{name}.txt").write_text(template.strip(), encoding="utf-8")
    print(f"  [OK] Freelancer profile + {len(FREELANCER_PROFILE['bid_templates'])} bid templates → {freelancer_dir}")

    # 3. Upwork profile
    upwork_dir = PREP_DIR / "upwork"
    upwork_dir.mkdir(exist_ok=True)
    _save_json(upwork_dir / "profile.json", UPWORK_PROFILE)
    upwork_txt = [
        f"TITLE: {UPWORK_PROFILE['title']}",
        f"HEADLINE: {UPWORK_PROFILE['headline']}",
        f"HOURLY RATE: {UPWORK_PROFILE['hourly_rate']}",
        "",
        "OVERVIEW:",
        UPWORK_PROFILE["overview"],
        "",
        f"SKILLS: {', '.join(UPWORK_PROFILE['skills'])}",
        "",
        "PORTFOLIO:",
    ]
    for item in UPWORK_PROFILE.get("portfolio_items", []):
        upwork_txt.append(f"\n  {item['title']}")
        upwork_txt.append(f"  {item['description']}")
    (upwork_dir / "profile.txt").write_text("\n".join(upwork_txt), encoding="utf-8")
    print(f"  [OK] Upwork profile + portfolio → {upwork_dir}")

    # 4. Chatbase bot templates
    chatbase_dir = PREP_DIR / "chatbase"
    chatbase_dir.mkdir(exist_ok=True)
    for i, bot in enumerate(CHATBASE_TEMPLATES, 1):
        _save_json(chatbase_dir / f"bot_{i}_{bot['name'].lower().replace(' ', '_')}.json", bot)
    print(f"  [OK] {len(CHATBASE_TEMPLATES)} Chatbase templates → {chatbase_dir}")

    # 5. Botpress bot templates
    botpress_dir = PREP_DIR / "botpress"
    botpress_dir.mkdir(exist_ok=True)
    for i, bot in enumerate(BOTPRESS_TEMPLATES, 1):
        _save_json(botpress_dir / f"bot_{i}_{bot['name'].lower().replace(' ', '_')}.json", bot)
    print(f"  [OK] {len(BOTPRESS_TEMPLATES)} Botpress templates → {botpress_dir}")

    # 6. Also run the original save functions for output/ canonical copies
    print("\n  Saving canonical copies to output/...")
    save_listings()
    save_templates()

    # 7. Master checklist summary
    summary = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "platforms": {},
    }
    for key, reg in sorted(REGISTRATIONS.items(), key=lambda x: x[1]["priority"]):
        summary["platforms"][key] = {
            "name": reg["name"],
            "priority": reg["priority"],
            "url": reg["url"],
            "time": reg["time"],
            "step_count": len(reg["steps"]),
            "requires": reg.get("requires", []),
        }
    _save_json(PREP_DIR / "master_checklist.json", summary)

    total_files = sum(1 for _ in PREP_DIR.rglob("*") if _.is_file())
    print(f"\n{'='*70}")
    print(f"  DONE — {total_files} files generated in {PREP_DIR}")
    print(f"{'='*70}\n")
    return True


# ── Registration Log ───────────────────────────────────────────

def _load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return {"events": []}


def _append_log(platform: str, action: str, details: str = ""):
    log = _load_log()
    log["events"].append({
        "time": datetime.now(timezone.utc).isoformat(),
        "platform": platform,
        "action": action,
        "details": details,
    })
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(log, indent=2), encoding="utf-8")


# ── Guided Registration ────────────────────────────────────────

def _platform_key_to_tracker_key(reg_key: str) -> str:
    """Map register.py keys to tracker.py keys (they mostly match)."""
    mapping = {
        "stripe_live": "stripe_direct",
    }
    return mapping.get(reg_key, reg_key)


def run_guided(only: list = None, batch: bool = False):  # noqa: E501
    """Walk through each platform registration in priority order.

    Args:
        only: If set, only process these platform keys.
        batch: If True, skip prompts — open all URLs and mark researched.
    """
    tracker = _load_tracker()
    ordered = sorted(REGISTRATIONS.items(), key=lambda x: x[1]["priority"])

    if only:
        ordered = [(k, v) for k, v in ordered if k in only]

    # Filter out already-completed (registered or beyond)
    pending = []
    for key, reg in ordered:
        tracker_key = _platform_key_to_tracker_key(key)
        src = tracker["sources"].get(tracker_key, {})
        status = src.get("status", "not_started")
        status_idx = STATUSES.index(status) if status in STATUSES else 0
        # Skip anything already registered or beyond
        if status_idx >= STATUSES.index("registered"):
            continue
        pending.append((key, reg, tracker_key, status))

    if not pending:
        print("\n  All platforms are already registered or beyond. Nothing to do.")
        print("  Run: python -m income.auto_register --status")
        return

    total = len(pending)
    print(f"\n{'='*70}")
    print(f"  AUTOMATED REGISTRATION — {total} platforms pending")
    print(f"{'='*70}")

    if batch:
        print("  Mode: BATCH (opening all URLs, marking researched)")
    else:
        print("  Mode: GUIDED (step-by-step with confirmation)")
    print(f"  Content: output/registration_prep/")
    print(f"{'='*70}")

    completed = 0
    skipped = 0

    for i, (key, reg, tracker_key, current_status) in enumerate(pending, 1):
        print(f"\n{'─'*70}")
        print(f"  [{i}/{total}] #{reg['priority']} {reg['name']}")
        print(f"  URL:  {reg['url']}")
        print(f"  Time: {reg['time']}")
        print(f"  Status: {current_status}")
        if reg.get("requires"):
            print(f"  Requires: {', '.join(reg['requires'])}")
        print(f"{'─'*70}")

        # Show steps
        for step in reg["steps"]:
            print(f"    {step}")

        # Point to prepared content
        content_hints = {
            "fiverr": "  Content: output/registration_prep/fiverr/",
            "freelancer": "  Content: output/registration_prep/freelancer/",
            "upwork": "  Content: output/registration_prep/upwork/",
            "chatbase": "  Content: output/registration_prep/chatbase/",
            "botpress": "  Content: output/registration_prep/botpress/",
        }
        if key in content_hints:
            print(f"\n{content_hints[key]}")

        if batch:
            # Batch mode: open URL and mark researched
            if reg["url"]:
                webbrowser.open(reg["url"])
            update_status(tracker_key, "researched",
                          f"Auto-opened {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}")
            _append_log(key, "researched", "batch mode — URL opened")
            completed += 1
            continue

        # Interactive mode
        print(f"\n  Actions:")
        print(f"    [o] Open URL in browser")
        print(f"    [r] Mark as researched")
        print(f"    [d] Mark as registered (done)")
        print(f"    [s] Skip this platform")
        print(f"    [q] Quit registration")

        while True:
            try:
                choice = input("\n  > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  Exiting.")
                return

            if choice == "o":
                if reg["url"]:
                    webbrowser.open(reg["url"])
                    print(f"  -> Opened {reg['url']}")
                    _append_log(key, "url_opened")
                else:
                    print("  -> No URL for this platform")
            elif choice == "r":
                update_status(tracker_key, "researched",
                              f"Reviewed {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}")
                _append_log(key, "researched", "manual")
                completed += 1
                break
            elif choice == "d":
                update_status(tracker_key, "registered",
                              f"Registered {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}")
                _append_log(key, "registered", "manual confirmation")
                completed += 1
                break
            elif choice == "s":
                _append_log(key, "skipped")
                skipped += 1
                break
            elif choice == "q":
                print(f"\n  Stopped. Completed: {completed}, Skipped: {skipped}")
                return
            else:
                print("  -> Invalid choice. Use: o / r / d / s / q")

    print(f"\n{'='*70}")
    print(f"  REGISTRATION COMPLETE")
    print(f"  Completed: {completed}  Skipped: {skipped}")
    print(f"  Run: python -m income.auto_register --status")
    print(f"{'='*70}\n")


# ── Status Dashboard ───────────────────────────────────────────

def show_status():
    """Show combined registration + tracker status."""
    tracker = _load_tracker()
    ordered = sorted(REGISTRATIONS.items(), key=lambda x: x[1]["priority"])

    status_icons = {
        "not_started": "[ ]",
        "researched": "[R]",
        "registered": "[*]",
        "configured": "[C]",
        "active": "[A]",
        "earning": "[$]",
    }

    counts = {s: 0 for s in STATUSES}

    print(f"\n{'='*70}")
    print("  REGISTRATION PROGRESS DASHBOARD")
    print(f"{'='*70}")

    for key, reg in ordered:
        tracker_key = _platform_key_to_tracker_key(key)
        src = tracker["sources"].get(tracker_key, {})
        status = src.get("status", "not_started")
        counts[status] = counts.get(status, 0) + 1
        icon = status_icons.get(status, "[?]")
        notes = src.get("notes", "")[:40]
        print(f"  {icon} #{reg['priority']:>2}  {reg['name']:<42} {notes}")

    # Also show tracker sources NOT in REGISTRATIONS
    extra_keys = set(tracker["sources"].keys()) - {_platform_key_to_tracker_key(k) for k, _ in ordered}
    if extra_keys:
        print(f"\n  {'─'*66}")
        print(f"  OTHER TRACKED SOURCES:")
        for ek in sorted(extra_keys):
            src = tracker["sources"][ek]
            icon = status_icons.get(src["status"], "[?]")
            print(f"  {icon}      {src['name']:<42} {src.get('notes', '')[:40]}")
            counts[src["status"]] = counts.get(src["status"], 0) + 1

    # Summary bar
    done = counts.get("registered", 0) + counts.get("configured", 0) + counts.get("active", 0) + counts.get("earning", 0)
    researched = counts.get("researched", 0)
    not_started = counts.get("not_started", 0)
    total_all = sum(counts.values())

    pct = int((done / max(total_all, 1)) * 100)
    bar_len = 40
    filled = int(bar_len * done / max(total_all, 1))
    bar = "█" * filled + "░" * (bar_len - filled)

    print(f"\n  {bar} {pct}% registered")
    print(f"  Not started: {not_started}  Researched: {researched}  Registered+: {done}")

    # Revenue
    total_rev = tracker.get("total_revenue", 0)
    earning = counts.get("earning", 0)
    print(f"  Revenue: ${total_rev:,.2f}  |  Sources earning: {earning}")

    print(f"\n  Legend: [ ]=Not Started  [R]=Researched  [*]=Registered")
    print(f"          [C]=Configured   [A]=Active      [$]=Earning")
    print(f"{'='*70}\n")

    # Next actions
    next_up = []
    for key, reg in ordered:
        tracker_key = _platform_key_to_tracker_key(key)
        src = tracker["sources"].get(tracker_key, {})
        status = src.get("status", "not_started")
        if status in ("not_started", "researched"):
            next_up.append((key, reg, status))
        if len(next_up) >= 3:
            break

    if next_up:
        print("  NEXT ACTIONS:")
        for key, reg, status in next_up:
            action = "Register" if status == "researched" else "Research"
            print(f"    → {action}: {reg['name']} ({reg['time']}) — {reg['url']}")
        print()


# ── Reset ──────────────────────────────────────────────────────

def reset_all():
    """Reset all registration statuses to not_started."""
    tracker = _load_tracker()
    for key in tracker["sources"]:
        tracker["sources"][key]["status"] = "not_started"
    tracker["updated"] = datetime.now(timezone.utc).isoformat()
    _save_tracker(tracker)
    print("[RESET] All sources set to not_started")


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Automated Platform Registration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python -m income.auto_register --prepare            # Generate all content
  python -m income.auto_register --run                # Guided walk-through
  python -m income.auto_register --run --only fiverr  # Just Fiverr
  python -m income.auto_register --run --yes          # Batch (no prompts)
  python -m income.auto_register --status             # Progress dashboard
""",
    )
    parser.add_argument("--prepare", action="store_true",
                        help="Generate all content files (profiles, gigs, bots)")
    parser.add_argument("--run", action="store_true",
                        help="Start guided registration walk-through")
    parser.add_argument("--yes", action="store_true",
                        help="Batch mode — no prompts, open all URLs, mark researched")
    parser.add_argument("--only", type=str, default="",
                        help="Comma-separated platform keys (e.g. fiverr,freelancer)")
    parser.add_argument("--status", action="store_true",
                        help="Show registration progress dashboard")
    parser.add_argument("--reset", action="store_true",
                        help="Reset all statuses to not_started")

    args = parser.parse_args()

    only_list = [x.strip() for x in args.only.split(",") if x.strip()] if args.only else None

    if args.prepare:
        prepare_all()
    elif args.run:
        if args.prepare or not (PREP_DIR / "master_checklist.json").exists():
            print("  [AUTO] Generating content first...")
            prepare_all()
        run_guided(only=only_list, batch=args.yes)
    elif args.status:
        show_status()
    elif args.reset:
        reset_all()
    else:
        show_status()
