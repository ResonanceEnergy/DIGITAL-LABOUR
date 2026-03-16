#!/usr/bin/env python3
from pathlib import Path
import json, datetime, sys
sys.path.append(
    str(Path(__file__).resolve().parent.parent.parent.parent / "agents"))
from common import CONFIG, ROOT, get_portfolio, Log, is_git_repo, get_head_commit, list_changed_files, categorize_file, ensure_dir, now_iso, load_mandate

REPOS_BASE = Path(CONFIG["repos_base"])
if not REPOS_BASE.is_absolute():
    REPOS_BASE = (ROOT / REPOS_BASE).resolve()

def process_repo(repo_name: str):
    repo_root = REPOS_BASE / repo_name
    if not repo_root.exists():
        Log.warn(f"Repo not found locally: {repo_name} ({repo_root})")
        return

    reports_dir = repo_root / "reports"
    ensure_dir(reports_dir)

    state_dir = repo_root / ".ncl" / "state"
    ensure_dir(state_dir)
    last_file = state_dir / "last_commit.txt"
    last = last_file.read_text().strip() if last_file.exists() else None

    head = get_head_commit(repo_root) if is_git_repo(repo_root) else None
    if head is None:
        Log.warn(f"Not a git repo or git missing: {repo_name}")
        changed = []
    else:
        changed = list_changed_files(repo_root, last)

    by_cat = {"ncl": [], "tests": [], "docs": [], "code": []}
    for status, fn in changed:
        by_cat[categorize_file(fn)].append({"status": status, "file": fn})

    mandate = load_mandate(repo_root)

    plan = {
        "repo": repo_name,
        "timestamp": now_iso(),
        "head": head,
        "since": last,
        "summary": {k: len(v) for k,v in by_cat.items()},
        "changes": by_cat,
        "mandate_snapshot": mandate,
        "next_actions": []
    }

    if plan["summary"] ["tests"] <max(
        1, int(0.1 * max(1, plan["summary"] ["code"]))):
        plan["next_actions"].append(
            "Increase test coverage for modified code.")
    if plan["summary"]["ncl"] > 0:
        plan["next_actions"].append(
            "Review .ncl changes with Gatekeeper before autonomy lift.")
    if plan["summary"]["docs"] < 1 and plan["summary"]["code"] > 0:
        plan["next_actions"].append(
            "Update documentation for notable code changes.")

    json_path = reports_dir / \
        f"delta_plan_{datetime.date.today().isoformat()}.json"
    json_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    md = [f"# Delta Plan — {repo_name}", "", f"**Time:** {plan['timestamp']}",
        f"**HEAD:** {head}", f"**Since:** {last}", ""]
    md.append("## Summary")
    for k,v in plan["summary"].items():
        md.append(f"- {k}: {v}")
    md.append("\n## Next Actions")
    if plan["next_actions"]:
        for a in plan["next_actions"]:
            md.append(f"- {a}")
    else:
        md.append("- None")
    md.append("\n## Changed Files")
    for k in ["ncl","tests","docs","code"]:
        if plan["changes"][k]:
            md.append(f"### {k}")
            for item in plan["changes"][k]:
                md.append(f"- {item['status']} {item['file']}")
    (reports_dir / f"delta_plan_{datetime.date.today().isoformat()}.md").write_text(
        "\n".join(md), encoding='utf-8')

    if head:
        last_file.write_text(head, encoding='utf-8')

def check_repo_status(repo_name: str):
    """Check the status of a repository"""
    return process_repo(repo_name)

if __name__ == '__main__':
    for repo in get_portfolio().get("repositories", []):
        process_repo(repo["name"])
    Log.info("Repo Sentry run complete.")
