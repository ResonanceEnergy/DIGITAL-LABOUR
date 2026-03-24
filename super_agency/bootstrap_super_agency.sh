#!/usr/bin/env bash
set -euo pipefail

# ========= CONFIGURABLES =========
ORG="${ORG:-ResonanceEnergy}"
REPO="${REPO:-ResonanceEnergy_SuperAgency}"
PRIVACY="${PRIVACY:-public}"     # public | private
RUN_DAILY="${RUN_DAILY:-0}"      # 1 to run first daily cycle after push
# Where to construct the repo locally:
WORK_ROOT="${WORK_ROOT:-$PWD}"
SUPER_DIR="$WORK_ROOT/$REPO"

# ========= SANITY CHECKS =========
command -v gh >/dev/null || { echo "ERROR: gh (GitHub CLI) not found"; exit 1; }
command -v git >/dev/null || { echo "ERROR: git not found"; exit 1; }

# ========= CREATE SKELETON =========
mkdir -p "$SUPER_DIR"/{agents,bin,config,decisions,reports,templates,docs}

# --- NORTH STAR ---
cat > "$SUPER_DIR/NORTH_STAR.md" << 'EOF'
# NORTH STAR — Resonance Energy (2026)

**Mission**  
Build an ethical, local‑first intelligence company‑of‑companies that can autonomously design, ship, and operate digital and physical businesses — privately, reliably, and compounding in value — with human‑aligned governance and full provenance.

**Principles**
1. Local‑first (cloud optional, never mandatory)
2. Consent & Control (explicit receipts, revocable; emergency stop)
3. Provenance‑first (signed, auditable actions & artifacts)
4. Unit Economics (compound value; avoid vanity work)
5. Resilience (offline‑capable; graceful degradation; incident‑ready)
6. Ethical Rails (no keylogging; no hot mics; metadata‑first intake)
7. Council Governance (arena evaluation, risk checks)
8. Do Less, Go Deeper (quality > quantity)

**Autonomy Levels**
- L0 observe
- L1 propose (default)
- L2 act with limits & receipts
- L3 high‑autonomy (council‑gated, time‑boxed, revocable)
EOF

# --- PORTFOLIO (JSON embedded in YAML header for simplicity) ---
ts="$(date -Iseconds)"
cat > "$SUPER_DIR/portfolio.yaml" << 'EOF'
# ResonanceEnergy Portfolio Registry
{
  "north_star": "./NORTH_STAR.md",
  "generated": "TS_PLACEHOLDER",
  "org": "ResonanceEnergy",
  "policies": {
    "autonomy_default": "L1",
    "cloud_usage": "opt-in with redaction & consent",
    "incident_escalation": "Notify Nathan then AZ (digital COO)"
  },
  "repositories": [
    {"name":"NATEBJONES","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"NCL","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"TESLACALLS2026","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"future-predictor-council","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"AAC","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"ADVENTUREHEROAUTO","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"Crimson-Compass","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"YOUTUBEDROP","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"CIVIL-FORGE-TECHNOLOGIES-","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"GEET-PLASMA-PROJECT","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"TESLA-TECH","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"ELECTRIC-UNIVERSE","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"VORTEX-HUNTER","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"MircoHydro","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"electric-ice","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"SUPERSTONK-TRADER","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"HUMAN-HEALTH","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"Adventure-Hero-Chronicles-Of-Glory","visibility":"private","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"QDFG1","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"NCC-Doctrine","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"NCC","visibility":"public","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"resonance-uy-py","visibility":"private","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"},
    {"name":"perpetual-flow-cube","visibility":"private","tier":"TBD","autonomy_level":"L1","risk_tier":"TBD"}
  ]
}
EOF
# inject timestamp
sed -i"" -e "s/TS_PLACEHOLDER/$ts/" "$SUPER_DIR/portfolio.yaml"

# mirror JSON for agents
tail -n +2 "$SUPER_DIR/portfolio.yaml" > "$SUPER_DIR/portfolio.json"

# --- CONFIG ---
cat > "$SUPER_DIR/config/settings.json" << 'EOF'
{
  "repos_base": "./repos",
  "reports_dir": "./reports",
  "decisions_dir": "./decisions",
  "daily_brief_hour_local": 8,
  "timezone_hint": "local",
  "require_consent_for": [
    "external_api_calls",
    "financial_actions",
    "data_sharing_outside_device"
  ],
  "autonomy_defaults": { "default": "L1" }
}
EOF

# --- AGENTS: common.py ---
cat > "$SUPER_DIR/agents/common.py" << 'EOF'
#!/usr/bin/env python3
import os, json, datetime, subprocess, re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG = json.loads((ROOT/"config"/"settings.json").read_text(encoding="utf-8"))
PORTFOLIO = json.loads((ROOT/"portfolio.json").read_text(encoding="utf-8"))

SENSITIVE_ACTIONS = set(CONFIG.get("require_consent_for", []))

class Log:
    @staticmethod
    def info(msg: str):
        print(f"[INFO] {msg}")
    @staticmethod
    def warn(msg: str):
        print(f"[WARN] {msg}")
    @staticmethod
    def error(msg: str):
        print(f"[ERROR] {msg}")

def is_git_repo(path: Path) -> bool:
    return (path/".git").exists()

def run_git(path: Path, args: List[str]) -> Tuple[int, str, str]:
    try:
        cp = subprocess.run(["git", "-C", str(path)] + args, capture_output=True, text=True, check=False)
        return cp.returncode, cp.stdout.strip(), cp.stderr.strip()
    except FileNotFoundError:
        return 127, "", "git not found"

def get_head_commit(path: Path) -> Optional[str]:
    rc, out, err = run_git(path, ["rev-parse", "HEAD"])
    return out if rc == 0 else None

def list_changed_files(path: Path, since_commit: Optional[str]) -> List[Tuple[str,str]]:
    if since_commit:
        rc, out, err = run_git(path, ["diff", "--name-status", f"{since_commit}..HEAD"])
    else:
        rc, out, err = run_git(path, ["show", "--name-status", "-m", "-1", "HEAD"])
    if rc != 0:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split('\t')
        if len(parts) >= 2:
            status, fn = parts[0], parts[-1]
            rows.append((status, fn))
    return rows

def categorize_file(fn: str) -> str:
    fnl = fn.lower()
    if fnl.startswith(".ncl/") or "/.ncl/" in fnl:
        return "ncl"
    if any(seg in fnl for seg in ["/tests/", "/test/", "_test.", ".spec."]):
        return "tests"
    if any(fnl.endswith(ext) for ext in [".md", ".rst", ".txt"]):
        return "docs"
    return "code"

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat()

def load_mandate(repo_root: Path) -> Dict[str, Any]:
    mpath = repo_root/".ncl"/"mandate.yaml"
    jpath = repo_root/".ncl"/"mandate.json"
    if jpath.exists():
        return json.loads(jpath.read_text(encoding="utf-8"))
    data: Dict[str, Any] = {}
    if not mpath.exists():
        return data
    import io
    key = None
    for raw in io.StringIO(mpath.read_text(encoding="utf-8")):
        line = raw.rstrip('\n')
        if not line or line.strip().startswith('#'):
            continue
        if re.match(r"^[A-Za-z0-9_]+:\s*$", line):
            key = line.split(":")[0].strip()
            data[key] = None
        elif ":" in line and not line.lstrip().startswith("-"):
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"')
        elif line.lstrip().startswith("- ") and key:
            if data.get(key) is None or not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(line.strip()[2:])
    return data

def require_consent_for(action_class: str) -> bool:
    return action_class in SENSITIVE_ACTIONS
EOF

# --- AGENTS: repo_sentry.py ---
cat > "$SUPER_DIR/agents/repo_sentry.py" << 'EOF'
#!/usr/bin/env python3
from pathlib import Path
import json, datetime
from common import CONFIG, PORTFOLIO, Log, is_git_repo, get_head_commit, list_changed_files, categorize_file, ensure_dir, now_iso, load_mandate

REPOS_BASE = Path(CONFIG["repos_base"])

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

    if plan["summary"]["tests"] < max(1, int(0.1*max(1, plan["summary"]["code"]))):
        plan["next_actions"].append("Increase test coverage for modified code.")
    if plan["summary"]["ncl"] > 0:
        plan["next_actions"].append("Review .ncl changes with Gatekeeper before autonomy lift.")
    if plan["summary"]["docs"] < 1 and plan["summary"]["code"] > 0:
        plan["next_actions"].append("Update documentation for notable code changes.")

    json_path = reports_dir / f"delta_plan_{datetime.date.today().isoformat()}.json"
    json_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    md = [f"# Delta Plan — {repo_name}", "", f"**Time:** {plan['timestamp']}", f"**HEAD:** {head}", f"**Since:** {last}", ""]
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
    (reports_dir / f"delta_plan_{datetime.date.today().isoformat()}.md").write_text("\n".join(md), encoding='utf-8')

    if head:
        last_file.write_text(head, encoding='utf-8')

if __name__ == '__main__':
    for repo in PORTFOLIO.get("repositories", []):
        process_repo(repo["name"])
    Log.info("Repo Sentry run complete.")
EOF

# --- AGENTS: daily_brief.py ---
cat > "$SUPER_DIR/agents/daily_brief.py" << 'EOF'
#!/usr/bin/env python3
from pathlib import Path
import json, datetime
from common import CONFIG, PORTFOLIO, Log, ensure_dir

REPOS_BASE = Path(CONFIG["repos_base"])
BRIEFS_DIR = Path(CONFIG["reports_dir"]) / "daily"
ensure_dir(BRIEFS_DIR)

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
    focus = []
    for r in PORTFOLIO.get("repositories", []):
        name = r["name"]
        s = collect_repo_summary(name)
        if s["delta"]:
            d = s["delta"]
            lines.append(f"## {name}")
            lines.append(f"- Changes — code: {d['summary'].get('code',0)}, tests: {d['summary'].get('tests',0)}, docs: {d['summary'].get('docs',0)}, ncl: {d['summary'].get('ncl',0)}")
            if d.get("next_actions"):
                for a in d["next_actions"]:
                    lines.append(f"  - Next: {a}")
            lines.append("")
            if d['summary'].get('ncl',0) or d['summary'].get('code',0) > 5:
                focus.append(name)
    if focus:
        lines.insert(2, f"**Focus:** {', '.join(focus)}\n")
    out = BRIEFS_DIR / f"brief_{today}.md"
    out.write_text("\n".join(lines), encoding='utf-8')
    Log.info(f"Wrote {out}")

if __name__ == '__main__':
    build_portfolio_brief()
EOF

# --- AGENTS: council.py ---
cat > "$SUPER_DIR/agents/council.py" << 'EOF'
#!/usr/bin/env python3
from pathlib import Path
import json, argparse, datetime, uuid
from common import CONFIG, PORTFOLIO, Log, ensure_dir, require_consent_for

DECISIONS_DIR = Path(CONFIG["decisions_dir"])
ensure_dir(DECISIONS_DIR)

VALID_AUTONOMY = ["L0","L1","L2","L3"]
VALID_RISK = ["LOW","MEDIUM","HIGH"]

def load_repo(repo_name: str):
    for r in PORTFOLIO.get("repositories", []):
        if r["name"] == repo_name:
            return r
    return None

def has_valid_consent(repo_root: Path, action_class: str) -> bool:
    consents_dir = repo_root/".ncl"/"consents"
    if not consents_dir.exists():
        return False
    for f in consents_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            if data.get("action_class") == action_class and data.get("ttl_valid", True):
                return True
        except Exception:
            pass
    return False

def evaluate(proposal: dict) -> dict:
    decision = {
        "id": proposal.get("id", str(uuid.uuid4())),
        "approved": False,
        "requires_human": False,
        "reason": [],
        "timestamp": datetime.datetime.now().astimezone().isoformat(),
    }
    repo = load_repo(proposal["repo"])
    if not repo:
        decision["reason"].append("Unknown repo")
        return decision

    autonomy = proposal.get("autonomy", "L1")
    risk = proposal.get("risk", "MEDIUM")
    if autonomy not in VALID_AUTONOMY:
        decision["reason"].append("Invalid autonomy level")
        return decision
    if risk not in VALID_RISK:
        decision["reason"].append("Invalid risk tier")
        return decision

    action_class = proposal.get("action", "")
    repo_root = Path(CONFIG["repos_base"]) / repo["name"]
    if require_consent_for(action_class):
        if not has_valid_consent(repo_root, action_class):
            decision["reason"].append("Missing valid consent receipt for sensitive action")
            decision["requires_human"] = True
            return decision

    if autonomy == "L3":
        decision["reason"].append("L3 always requires human + council gate")
        decision["requires_human"] = True
        return decision

    if risk == "HIGH":
        decision["reason"].append("HIGH risk requires human review")
        decision["requires_human"] = True
        return decision

    decision["approved"] = True
    decision["reason"].append("Policy pass: consent satisfied and within autonomy/risk thresholds")
    return decision

def save_decision(proposal: dict, decision: dict):
    rid = proposal.get("repo")
    pid = decision["id"]
    out = DECISIONS_DIR / f"decision_{rid}_{pid}.json"
    out.write_text(json.dumps({"proposal": proposal, "decision": decision}, indent=2), encoding='utf-8')
    Log.info(f"Decision written: {out}")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['propose'])
    ap.add_argument('--repo', required=True)
    ap.add_argument('--action', required=True)
    ap.add_argument('--description', required=True)
    ap.add_argument('--risk', default='MEDIUM', choices=VALID_RISK)
    ap.add_argument('--autonomy', default='L1', choices=VALID_AUTONOMY)
    ap.add_argument('--id', default=None)
    args = ap.parse_args()

    proposal = {
        "id": args.id or str(uuid.uuid4()),
        "repo": args.repo,
        "action": args.action,
        "description": args.description,
        "risk": args.risk,
        "autonomy": args.autonomy
    }
    decision = evaluate(proposal)
    save_decision(proposal, decision)
    print(json.dumps(decision, indent=2))
EOF

# --- AGENTS: orchestrator.py ---
cat > "$SUPER_DIR/agents/orchestrator.py" << 'EOF'
#!/usr/bin/env python3
import subprocess, sys
from common import ROOT, Log

SENTRY = ROOT/"agents"/"repo_sentry.py"
DAILY = ROOT/"agents"/"daily_brief.py"

def main():
    Log.info("Running Repo Sentry across portfolio…")
    cp = subprocess.run([sys.executable, str(SENTRY)])
    if cp.returncode != 0:
        Log.warn("Repo Sentry exited with non-zero code")
    Log.info("Compiling Daily Ops Brief…")
    cp = subprocess.run([sys.executable, str(DAILY)])
    if cp.returncode != 0:
        Log.warn("Daily Brief exited with non-zero code")
    Log.info("Done.")

if __name__ == '__main__':
    main()
EOF

# --- BIN: runners ---
cat > "$SUPER_DIR/bin/run_daily.sh" << 'EOF'
#!/usr/bin/env bash
set -e
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
ROOT="$SCRIPT_DIR/.."
python3 "$ROOT/agents/orchestrator.py"
EOF
chmod +x "$SUPER_DIR/bin/run_daily.sh"

cat > "$SUPER_DIR/bin/propose.sh" << 'EOF'
#!/usr/bin/env bash
# Usage: ./propose.sh <repo> <action> <autonomy> <risk> "Description"
set -e
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
ROOT="$SCRIPT_DIR/.."
python3 "$ROOT/agents/council.py" propose --repo "$1" --action "$2" --autonomy "${3:-L1}" --risk "${4:-MEDIUM}" --description "$5"
EOF
chmod +x "$SUPER_DIR/bin/propose.sh"

# --- TEMPLATE: consent receipt ---
cat > "$SUPER_DIR/templates/consent_receipt.json" << 'EOF'
{
  "action_class": "external_api_calls",
  "scope": "Describe the minimal data and endpoint",
  "limits": { "max_calls": 10, "time_window_hours": 1 },
  "ttl_valid": true,
  "issued_by": "Nathan",
  "issued_at": "TS_PLACEHOLDER"
}
EOF
sed -i"" -e "s/TS_PLACEHOLDER/$ts/" "$SUPER_DIR/templates/consent_receipt.json"

# --- README addendum ---
cat >> "$SUPER_DIR/README.md" << 'EOF'

# Agent Orchestration Pack

## Components
- `agents/repo_sentry.py` — detects repo changes → per‑repo delta plans
- `agents/daily_brief.py` — aggregates → portfolio daily brief
- `agents/council.py` — evaluates proposals (autonomy/risk/consent)
- `agents/orchestrator.py` — runs sentry + brief
- `bin/run_daily.sh` — daily cycle runner
- `bin/propose.sh` — submit a proposal to council

## Config
Edit `config/settings.json` (set `repos_base` to where your 23 repos live locally).

## Run
```bash
./bin/run_daily.sh
```

Propose an action:
```bash
./bin/propose.sh TESLACALLS2026 financial_actions L2 HIGH "Request to place paper trade for strategy X"
```
EOF

# ========= INIT + PUSH =========
cd "$SUPER_DIR"
if [ -d .git ]; then
  git checkout -b feature/agents-orchestration || git switch feature/agents-orchestration
else
  git init
  git checkout -b feature/agents-orchestration
fi

git add .
git commit -m "bootstrap: Bit Rage Systems (NORTH_STAR, portfolio, agents, council & policies)" || true

# create PR on origin/main (idempotent)
if ! git remote get-url origin >/dev/null 2>&1; then
  # try to create the repo under the org if it doesn't exist
  if ! gh repo view "$ORG/$REPO" >/dev/null 2>&1; then
    if [ "$PRIVACY" = "private" ]; then
      gh repo create "$ORG/$REPO" --private --confirm
    else
      gh repo create "$ORG/$REPO" --public --confirm
    fi
  fi
  git remote add origin "git@github.com:$ORG/$REPO.git" || true
fi

git push -u origin feature/agents-orchestration --no-verify || true

# open PR
if gh pr view --repo "$ORG/$REPO" --head feature/agents-orchestration >/dev/null 2>&1; then
  echo "PR already exists"
else
  gh pr create --repo "$ORG/$REPO" --title "bootstrap: Bit Rage Systems (agents + orchestration)" --body "Adds agent orchestration pack, bootstrap script and initial assets." --base main --head feature/agents-orchestration || true
fi

# optional first run
if [ "$RUN_DAILY" = "1" ]; then
  echo "Running first daily cycle..."
  ./bin/run_daily.sh || true
fi

echo "✅ Bit Rage Systems bootstrap saved locally at: $SUPER_DIR"
