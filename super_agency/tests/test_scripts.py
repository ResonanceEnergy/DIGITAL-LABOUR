import os
import sys
import subprocess
from pathlib import Path

# path hack
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root)
sys.path.append(os.path.join(root, "agents"))

import agents.orchestrator as orchestrator
import agents.council as council
from agents import common


def test_orchestrator_main(tmp_path, monkeypatch):
    """Test that orchestrator.main() shells out to sentry and brief scripts."""
    import os

    # Create the departmental directory the orchestrator expects to chdir into
    dept_dir = tmp_path / "departments" / "operations_command" / "system_monitoring"
    dept_dir.mkdir(parents=True)

    # Point the orchestrator's ROOT to our tmp tree
    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)

    # Capture subprocess calls instead of actually running scripts
    calls = []
    original_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and len(cmd) > 1:
            script = str(cmd[-1])
            if script.endswith((".py",)):
                calls.append(script)
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="", stderr="")
        return original_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)

    orchestrator.main()

    # Verify both scripts were invoked
    assert any(
        "repo_sentry" in c for c in calls), f"repo_sentry not called: {calls}"
    assert any(
        "daily_brief" in c for c in calls), f"daily_brief not called: {calls}"


def test_council_propose_function(tmp_path, monkeypatch):
    # use tmp decisions dir
    monkeypatch.setattr(common, "CONFIG", {"decisions_dir": str(tmp_path)})
    monkeypatch.setattr(council, "DECISIONS_DIR", Path(str(tmp_path)))

    # call evaluate + save_decision directly; ensure portfolio contains the repo
    monkeypatch.setattr(council, "PORTFOLIO", {
                        "repositories": [{"name": "ANY"}]})
    proposal = {"repo": "ANY", "action": "foo",
        "autonomy": "L1", "risk": "MEDIUM", "id": "123"}
    decision = council.evaluate(proposal)
    assert decision["approved"]
    council.save_decision(proposal, decision)
    files = list(tmp_path.glob("decision_*.json"))
    assert files
