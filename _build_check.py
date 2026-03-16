"""Build verification — import-test all agents and core modules."""
import importlib
import os
import sys
import time

start = time.time()
agents_dir = "agents"
agent_ok = 0
agent_fail = []

for d in sorted(os.listdir(agents_dir)):
    runner = os.path.join(agents_dir, d, "runner.py")
    if os.path.isfile(runner):
        mod = f"agents.{d}.runner"
        try:
            importlib.import_module(mod)
            agent_ok += 1
        except Exception as e:
            agent_fail.append((d, str(e)[:80]))

print(f"Agents: {agent_ok}/{agent_ok + len(agent_fail)} OK")
for name, err in agent_fail:
    print(f"  FAIL: {name} -- {err}")

# Core modules
core_mods = [
    "utils.dl_agent", "utils.llm_client",
    "dispatcher.router", "dispatcher.queue",
    "api.intake", "api.monitor", "api.payments",
    "api.rapidapi",
    "billing.tracker", "billing.payments",
    "c_suite.axiom", "c_suite.vectis", "c_suite.ledgr", "c_suite.boardroom",
    "dashboard.health",
    "automation.nerve", "automation.orchestrator",
    "automation.outreach", "automation.prospect_engine",
    "automation.revenue_daemon", "automation.self_check",
]
core_ok = 0
core_fail = []
for m in core_mods:
    try:
        importlib.import_module(m)
        core_ok += 1
    except Exception as e:
        core_fail.append((m, str(e)[:80]))

print(f"Core:   {core_ok}/{core_ok + len(core_fail)} OK")
for name, err in core_fail:
    print(f"  FAIL: {name} -- {err}")

# API routes
try:
    from api.rapidapi import rapid_app
    print(f"API:    {len(rapid_app.routes)} routes")
except Exception as e:
    print(f"API:    FAIL -- {e}")

elapsed = time.time() - start
total_fail = len(agent_fail) + len(core_fail)
status = "PASS" if total_fail == 0 else f"FAIL ({total_fail} errors)"
print(f"\nBUILD ALL: {status}  ({elapsed:.1f}s)")
