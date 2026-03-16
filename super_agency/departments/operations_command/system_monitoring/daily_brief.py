#!/usr/bin/env python3
from pathlib import Path
import json, datetime, sys
sys.path.append(
    str(Path(__file__).resolve().parent.parent.parent.parent / "agents"))
from common import CONFIG, ROOT, get_portfolio, Log, ensure_dir

REPOS_BASE = Path(CONFIG["repos_base"])
if not REPOS_BASE.is_absolute():
    REPOS_BASE = (ROOT / REPOS_BASE).resolve()
BRIEFS_DIR = Path(CONFIG["reports_dir"]) / "daily"
if not BRIEFS_DIR.is_absolute():
    BRIEFS_DIR = (ROOT / BRIEFS_DIR).resolve()
ensure_dir(BRIEFS_DIR)

HEAL_LOG = ROOT / "logs" / "selfheal.ndjson"
ALERTS_LOG = ROOT / "logs" / "alerts.ndjson"


def _append_weekly_error_summary(lines: list, today_str: str):
    """Aggregate last 7 days of alerts into a summary section."""
    if not ALERTS_LOG.exists():
        return

    cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    severity_counts = {}
    component_counts = {}
    recent_alerts = []

    try:
        for raw_line in ALERTS_LOG.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            ts = entry.get("ts", entry.get("timestamp", ""))
            if ts[:10] < cutoff:
                continue  # older than 7 days
            sev = entry.get("severity", "UNKNOWN")
            comp = entry.get("component", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            component_counts[comp] = component_counts.get(comp, 0) + 1
            recent_alerts.append(entry)
    except OSError:
        return

    if not recent_alerts:
        return

    total = len(recent_alerts)
    lines.append("## ⚠️ Weekly Error Summary (7-day)")
    lines.append("")
    lines.append(f"Total alerts: **{total}**")
    lines.append("")

    # By severity
    if severity_counts:
        parts = [f"{sev}: {cnt}" for sev, cnt in sorted(
            severity_counts.items(), key=lambda x: -x[1])]
        lines.append("- **By severity:** " + ", ".join(parts))

    # By component
    if component_counts:
        top = sorted(component_counts.items(), key=lambda x: -x[1])[:5]
        parts = [f"{comp}: {cnt}" for comp, cnt in top]
        lines.append("- **Top components:** " + ", ".join(parts))

    # Last 3 critical alerts
    crits = [a for a in recent_alerts if a.get("severity") == "CRITICAL"]
    if crits:
        lines.append("")
        lines.append("**Recent CRITICAL alerts:**")
        for a in crits[-3:]:
            msg = a.get("message", a.get("msg", "?"))
            ts = a.get("ts", a.get("timestamp", "?"))
            lines.append(f"  - [{ts[:16]}] {msg}")

    lines.append("")


def collect_repo_summary(repo_name: str):
    repo_root = REPOS_BASE / repo_name
    reports_dir = repo_root / "reports"
    today = datetime.date.today().isoformat()

    summary = {"repo": repo_name, "today": today, "commits": 0, "delta": None}
    jpath = reports_dir / f"delta_plan_{today}.json"
    if jpath.exists():
        try:
            summary["delta"] = json.loads(jpath.read_text(encoding='utf-8'))
        except Exception:
            pass
    if summary["delta"]:
        code = summary["delta"]["summary"].get("code",0)
        tests = summary["delta"]["summary"].get("tests",0)
        docs = summary["delta"]["summary"].get("docs",0)
        summary["commits"] = code + tests + docs
    return summary

def build_portfolio_brief():
    today = datetime.date.today().isoformat()
    lines = [f"# Daily Ops Brief — {today}", ""]

    # --- Second Brain Intelligence (queued yesterday) ---
    queued_dir = BRIEFS_DIR / "queued" / today
    if queued_dir.exists():
        sb_items = sorted(queued_dir.glob("secondbrain_*.json"))
        if sb_items:
            lines.append("## 🧠 Intelligence Digest")
            lines.append("")
            for qf in sb_items:
                try:
                    item = json.loads(qf.read_text(encoding="utf-8"))
                    vid = item.get("video_id", "?")
                    abstract = item.get("abstract", "")
                    insights = item.get("key_insights", [])
                    actions = item.get("action_items", [])
                    confidence = item.get("confidence", "?")
                    lines.append(f"### {vid}")
                    if abstract:
                        lines.append(f"> {abstract}")
                    if insights:
                        lines.append("- **Key insights:** " + \
                                     "; ".join(insights[:3]))
                    if actions:
                        lines.append("- **Action items:** " + \
                                     "; ".join(actions[:3]))
                    lines.append(f"- Confidence: {confidence}")
                    lines.append("")
                except Exception:
                    pass
            lines.append("")

    # --- Weekly Error Summary (last 7 days of alerts) ---
    _append_weekly_error_summary(lines, today)

    # --- Research Projects Summary ---
    try:
        from research_manager import get_all_project_statuses, generate_research_report
        statuses = get_all_project_statuses(today)
        active = [s for s in statuses if s["status"]
            in ("active", "in-progress")]
        if active:
            lines.append("## 📊 Research Projects")
            lines.append("")
            for s in active:
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡",
                    "low": "⚪"}.get(s["priority"], "⚪")
                pbar = f"{
                    s['progress_pct']} % ({
                    s['milestones_done']} /{
                    s['milestones_total']}) "
                changes = s["summary"]["total_changes"]
                lines.append(
                    f"- {icon} **{s['project_name']}** — {pbar} progress, {changes} changes today")
            lines.append("")
        # Also generate standalone research report
        generate_research_report(today)
    except Exception:
        pass  # research_manager not available yet — skip gracefully

    # --- Per-Repo Details ---
    focus = []
    for r in get_portfolio().get("repositories", []):
        name = r["name"]
        s = collect_repo_summary(name)
        if s["delta"]:
            d = s["delta"]
            lines.append(f"## {name}")
            lines.append(
                f"- Changes — code: {d['summary'].get('code',0)}, tests: {d['summary'].get('tests',0)}, docs: {d['summary'].get('docs',0)}, ncl: {d['summary'].get('ncl',0)}")
            if d.get("next_actions"):
                for a in d["next_actions"]:
                    lines.append(f"  - Next: {a}")
            lines.append("")
            if d['summary'].get('ncl',0) or d['summary'].get('code',0) > 5:
                focus.append(name)
    if focus:
        lines.insert(2, f"**Focus:** {', '.join(focus)}\n")
    brief_text = "\n".join(lines)
    out = BRIEFS_DIR / f"brief_{today}.md"
    out.write_text(brief_text, encoding='utf-8')
    Log.info(f"Wrote {out}")
    return brief_text


def queue_for_brief(enrich_file: Path) -> bool:
    """Queue enriched content for tomorrow's ops brief"""
    try:
        if not enrich_file.exists():
            Log.error(f"Enrichment file not found: {enrich_file}")
            return False

        enrich_data = json.loads(enrich_file.read_text(encoding='utf-8'))

        # Create a queued item file for tomorrow's brief
        tomorrow = (datetime.date.today() + \
                    datetime.timedelta(days=1)).isoformat()
        queued_dir = BRIEFS_DIR / "queued" / tomorrow
        ensure_dir(queued_dir)

        video_id = enrich_data["video_id"]
        queue_file = queued_dir / f"secondbrain_{video_id}.json"

        queue_item = {
            "type": "second_brain_ingestion",
            "video_id": video_id,
            "source_url": enrich_data.get("source_url"),
            "abstract": enrich_data.get("abstract_120w", "")[:200] + "...",
            "confidence": enrich_data.get("confidence", "unknown"),
            "action_items": enrich_data.get("action_items", []),
            # Top 3 insights
            "key_insights": enrich_data.get("key_insights", [])[:3],
            "doctrine_principles": enrich_data.get("doctrine_map", {}).get("principles", []),
            "queued_at": datetime.datetime.now().isoformat(),
            "enrich_file": str(enrich_file)
        }

        queue_file.write_text(json.dumps(
            queue_item, indent=2), encoding='utf-8')
        Log.info(f"Queued {video_id} for {tomorrow} ops brief")
        return True

    except Exception as e:
        Log.error(f"Failed to queue for brief: {e}")
        return False

if __name__ == '__main__':
    build_portfolio_brief()
