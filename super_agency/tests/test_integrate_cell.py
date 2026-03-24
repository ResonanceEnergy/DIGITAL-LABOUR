import os
import json
import subprocess
import sys
from pathlib import Path

import pytest

# path hack for importing agents
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root)
sys.path.append(os.path.join(root, "agents"))

import agents.integrate_cell as integrate_cell


def write_cfg(root_path, repos_base=None, reports_dir=None):
    cfg = {
        "repos_base": repos_base or "./repos",
        "reports_dir": reports_dir or "./reports",
        "decisions_dir": "./decisions",
        "daily_brief_hour_local": 8,
        "timezone_hint": "local",
        "require_consent_for": ["external_api_calls"],
        "autonomy_defaults": {"default": "L1"},
        "org": "TestOrg"
    }
    cfg_path = root_path / "config"
    cfg_path.mkdir(exist_ok=True)
    (cfg_path / "settings.json").write_text(json.dumps(cfg), encoding='utf-8')


def setup_cell_repo(work_root, name, mandate=None, agents=None, readme=None):
    repo = work_root / "repos" / name
    repo.mkdir(parents=True)
    # initialize git so script sees repository
    subprocess.run(["git", "init"], cwd=repo, check=True)
    # create files
    if mandate is not None:
        ncl = repo / ".ncl"
        ncl.mkdir(exist_ok=True)
        (ncl / "mandate.yaml").write_text(mandate, encoding='utf-8')
    if agents is not None:
        ncl = repo / ".ncl"
        ncl.mkdir(exist_ok=True)
        (ncl / "agents.json").write_text(json.dumps(agents), encoding='utf-8')
    if readme is not None:
        (repo / "README.md").write_text(readme, encoding='utf-8')
    # make commit so .git exists
    subprocess.run(["git", "add", "--all"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True)
    return repo


def test_integrate_basic(tmp_path, monkeypatch):
    # configure a temporary workspace
    monkeypatch.setenv('DL_ROOT', str(tmp_path))
    os.chdir(tmp_path)
    write_cfg(tmp_path, repos_base=str(tmp_path/'repos'),
              reports_dir=str(tmp_path/'reports'))

    # prepare repo content
    mandatetext = "tier: HIGH\nowner: Alice\nmission: Do things"
    agents_spec = {"roles": {"worker": {"quota": 2}}}
    readme = "# Title\nSome description.\n## Details\nInfo"
    setup_cell_repo(tmp_path, "TESTREPO", mandate=mandatetext,
                    agents=agents_spec, readme=readme)

    # run script
    script = Path(root) / "agents" / "integrate_cell.py"
    cp = subprocess.run([sys.executable, str(script),
                        "--repo", "TESTREPO"], capture_output=True, text=True)
    assert cp.returncode == 0
    out = json.loads(cp.stdout)
    # verify outputs exist
    assert Path(out['report_json']).exists()
    assert Path(out['report_md']).exists()
    md = Path(out['report_md']).read_text()
    assert "Tier" in md
    assert "worker" in md
    assert "Title" in md

    # check sensitivity.json updated
    sens = json.loads((tmp_path/'config'/'sensitivity.json').read_text())
    assert 'neural_data' in sens.get('classes', [])


def test_integrate_ncl_updates_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv('DL_ROOT', str(tmp_path))
    os.chdir(tmp_path)
    write_cfg(tmp_path, repos_base=str(tmp_path/'repos'),
              reports_dir=str(tmp_path/'reports'))
    # create docs manifest
    docs = tmp_path / 'docs'
    docs.mkdir()
    manifest = docs / 'NCL_Digital_Twin_Manifest_v1.md'
    manifest.write_text("# Manifest\n", encoding='utf-8')

    setup_cell_repo(tmp_path, "NCL", mandate="", agents={}, readme="# Hi")
    script = Path(root) / "agents" / "integrate_cell.py"
    cp = subprocess.run([sys.executable, str(script),
                        "--repo", "NCL"], capture_output=True, text=True)
    assert cp.returncode == 0
    content = manifest.read_text()
    assert "Integration status" in content


def test_wrapper_script(tmp_path, monkeypatch):
    # ensure the bash wrapper works equivalently to invoking the python module
    import platform
    if platform.system().lower().startswith("win"):
        # wrapper script is bash-only; ensure CI runner has bash or stub implementation
        # pytest.skip("wrapper script is bash-only; skipping on Windows")
        pass
    monkeypatch.setenv('DL_ROOT', str(tmp_path))
    os.chdir(tmp_path)
    write_cfg(tmp_path, repos_base=str(tmp_path/'repos'),
              reports_dir=str(tmp_path/'reports'))

    mandatetext = "tier: LOW\nowner: Bob\nmission: Test"
    setup_cell_repo(tmp_path, "WRAPTEST", mandate=mandatetext,
                    agents={}, readme=None)

    sh = Path(root) / "bin" / "integrate-cell.sh"
    # make sure executable
    try:
        sh.chmod(0o755)
    except Exception:
        pass

    if platform.system().lower().startswith("win"):
        # on windows, just run the python script directly rather than a shell wrapper
        cp = subprocess.run(
            [sys.executable, str(
                 Path(root) /"agents" / "integrate_cell.py"),
             "--repo", "WRAPTEST"],
            capture_output=True, text=True)
    else:
        cp = subprocess.run([str(sh), "--repo", "WRAPTEST"],
                            capture_output=True, text=True)

    assert cp.returncode == 0
    out = json.loads(cp.stdout)
    assert Path(out['report_json']).exists()
    assert 'WRAPTEST' in Path(out['report_md']).read_text()

