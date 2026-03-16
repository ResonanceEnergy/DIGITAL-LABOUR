import json
import sys
import os
from pathlib import Path

# ensure project root is importable
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)

import pytest
import agents.system_file_analyzer as sfa


# ---------------------------------------------------------------------------
# analyze_file
# ---------------------------------------------------------------------------

def _write_test_file(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_analyze_file_clean(tmp_path):
    """A well-formed file should produce no issues."""
    src = '''\
"""Module docstring."""


def helper() -> None:
    """Helper docstring."""
    pass
'''
    p = _write_test_file(tmp_path, "clean.py", src)
    result = sfa.analyze_file(p)
    assert result["issues"] == [], result["issues"]


def test_analyze_file_missing_module_docstring(tmp_path):
    src = "x = 1\n"
    p = _write_test_file(tmp_path, "nodoc.py", src)
    result = sfa.analyze_file(p)
    assert any("module-level docstring" in i for i in result["issues"])


def test_analyze_file_missing_function_docstring(tmp_path):
    src = '''\
"""Module doc."""


def my_func():
    pass
'''
    p = _write_test_file(tmp_path, "nodocfunc.py", src)
    result = sfa.analyze_file(p)
    assert any("my_func" in i and "docstring" in i for i in result["issues"])


def test_analyze_file_bare_except(tmp_path):
    src = '''\
"""Module doc."""

try:
    x = 1
except:
    pass
'''
    p = _write_test_file(tmp_path, "bare.py", src)
    result = sfa.analyze_file(p)
    assert any("bare" in i for i in result["issues"])


def test_analyze_file_todo_comment(tmp_path):
    src = '''\
"""Module doc."""

# TODO: fix this later
x = 1
'''
    p = _write_test_file(tmp_path, "todo.py", src)
    result = sfa.analyze_file(p)
    assert any("TODO" in i for i in result["issues"])


def test_analyze_file_exceeds_max_lines(tmp_path):
    lines = ["# line\n"] * 10
    src = '"""mod doc."""\n' + "".join(lines)
    p = _write_test_file(tmp_path, "big.py", src)
    result = sfa.analyze_file(p, max_lines=5)
    assert any("exceeds" in i for i in result["issues"])


def test_analyze_file_syntax_error(tmp_path):
    src = "def broken(:\n"
    p = _write_test_file(tmp_path, "syntax.py", src)
    result = sfa.analyze_file(p)
    assert any("Syntax error" in i for i in result["issues"])


def test_analyze_file_missing_return_annotation(tmp_path):
    src = '''\
"""Module doc."""


def no_annotation():
    """Has docstring."""
    return 42
'''
    p = _write_test_file(tmp_path, "noanno.py", src)
    result = sfa.analyze_file(p)
    assert any("return-type annotation" in i for i in result["issues"])


# ---------------------------------------------------------------------------
# analyze_directory
# ---------------------------------------------------------------------------

def test_analyze_directory_finds_py_files(tmp_path):
    _write_test_file(tmp_path, "a.py", '"""doc."""\n')
    _write_test_file(tmp_path, "b.py", '"""doc."""\n')
    _write_test_file(tmp_path, "README.md", "# readme\n")
    results = sfa.analyze_directory(tmp_path)
    paths = [r["path"] for r in results]
    assert any("a.py" in p for p in paths)
    assert any("b.py" in p for p in paths)
    assert not any("README.md" in p for p in paths)


def test_analyze_directory_excludes_dirs(tmp_path):
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    _write_test_file(cache, "cached.py", "x=1\n")
    _write_test_file(tmp_path, "real.py", '"""doc."""\n')
    results = sfa.analyze_directory(tmp_path)
    paths = [r["path"] for r in results]
    assert not any("__pycache__" in p for p in paths)
    assert any("real.py" in p for p in paths)


# ---------------------------------------------------------------------------
# generate_recommendations
# ---------------------------------------------------------------------------

def test_generate_recommendations_no_issues():
    recs = sfa.generate_recommendations(
        [{"path": "x.py", "issues": [], "line_count": 10}])
    assert recs == ["No issues detected — system files look healthy."]


def test_generate_recommendations_ordered_by_frequency():
    # docstring issues appear more often → should come first
    reports = [
        {"path": "a.py", "issues": [
            "Missing module-level docstring.", "bare 'except' clause"], "line_count": 5},
        {"path": "b.py", "issues": [
            "Missing module-level docstring."], "line_count": 5},
    ]
    recs = sfa.generate_recommendations(reports)
    # docstring recommendation should rank higher than bare-except
    docstring_idx = next(i for i, r in enumerate(recs)
                         if "docstring" in r.lower())
    bare_idx = next(i for i, r in enumerate(recs) if "bare" in r.lower())
    assert docstring_idx < bare_idx


# ---------------------------------------------------------------------------
# run (integration)
# ---------------------------------------------------------------------------

def test_run_produces_report(tmp_path, monkeypatch):
    monkeypatch.setattr(sfa, "_DEFAULT_MAX_LINES", 500)

    # create a minimal python file to analyse
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    _write_test_file(src_dir, "sample.py", '"""doc."""\nx = 1\n')

    out_dir = tmp_path / "reports"
    report = sfa.run(root=src_dir, output_dir=out_dir, max_lines=500)

    assert report["files_analyzed"] >= 1
    assert "recommendations" in report

    # verify persisted JSON
    json_files = list(out_dir.glob("system_file_analysis_*.json"))
    assert len(json_files) == 1
    loaded = json.loads(json_files[0].read_text())
    assert loaded["files_analyzed"] == report["files_analyzed"]
