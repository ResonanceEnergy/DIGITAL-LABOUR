#!/usr/bin/env python3
from __future__ import annotations
"""
Second Brain Pipeline — Python-native cross-platform controller.

Replaces the Makefile-based pipeline with importable functions
that work on Windows and can be called from the orchestrator / API.

Stages:
  1. ingest  — fetch transcript via youtube-transcript-api
  2. enrich  — LLM enrichment (Ollama, graceful fallback)
  3. catalog — index into NCL knowledge graph
  4. brief   — queue for tomorrow's daily ops brief
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge" / "secondbrain"
PYTHON = sys.executable  # use the same interpreter


def _video_id(url: str) -> str:
    """Extract video ID from a YouTube URL."""
    m = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})', url)
    if not m:
        raise ValueError(f"Cannot extract video ID from: {url}")
    return m.group(1)


def _base_dir(vid: str) -> Path:
    now = datetime.now()
    return KNOWLEDGE_DIR / str(now.year) / f"{now.month:02d}" / vid


def _run(label: str, args: list, cwd: Path = ROOT) -> dict:
    """Run a subprocess and return a result dict."""
    cp = subprocess.run(
        args, cwd=str(cwd),
        capture_output=True, text=True, timeout=120
    )
    ok = cp.returncode == 0
    return {
        "stage": label,
        "ok": ok,
        "returncode": cp.returncode,
        "stdout": cp.stdout[-500:] if cp.stdout else "",
        "stderr": cp.stderr[-500:] if cp.stderr else "",
    }


# ── Public API ───────────────────────────────────────────────────────────

def ingest(url: str) -> dict:
    """Stage 1: Fetch transcript."""
    vid = _video_id(url)
    out = _base_dir(vid)
    out.mkdir(parents=True, exist_ok=True)
    result = _run("ingest", [
        PYTHON, str(ROOT / "tools" / "youtubedrop" / "fetch.py"),
        url, "--out", str(out),
    ])
    result["video_id"] = vid
    result["base_dir"] = str(out)
    result["has_transcript"] = (out / "raw.txt").exists()
    return result


def enrich(
    url: str,
    vid: str | None = None,
    base_dir: str | None = None,
) -> dict[str, Any]:
    """Stage 2: LLM enrichment (Ollama optional)."""
    if vid is None:
        vid = _video_id(url)
    bd = Path(base_dir) if base_dir else _base_dir(vid)
    result = _run("enrich", [
        PYTHON, str(ROOT / "tools" / "enrich.py"),
        str(bd), vid, url,
    ])
    result["video_id"] = vid
    result["has_enrichment"] = (bd / "enrich.json").exists()
    return result


def catalog(base_dir: str) -> dict:
    """Stage 3: Index into NCL knowledge graph."""
    enrich_json = Path(base_dir) / "enrich.json"
    if not enrich_json.exists():
        return {
            "stage": "catalog",
            "ok": False,
            "error": "enrich.json not found",
        }
    result = _run("catalog", [
        PYTHON, "-m", "agents.ncl_catalog", str(enrich_json),
    ])
    return result


def queue_brief(base_dir: str) -> dict:
    """Stage 4: Queue for ops brief."""
    enrich_json = Path(base_dir) / "enrich.json"
    if not enrich_json.exists():
        return {
            "stage": "brief",
            "ok": False,
            "error": "enrich.json not found",
        }
    result = _run("brief", [
        PYTHON, str(ROOT / "tools" / "queue_brief.py"), str(enrich_json),
    ])
    return result


def run_full_pipeline(url: str) -> dict[str, Any]:
    """Run all 4 stages sequentially. Returns summary."""
    results: dict[str, Any] = {}

    r = ingest(url)
    results["ingest"] = r
    if not r["ok"] or not r.get("has_transcript"):
        results["stopped_at"] = "ingest"
        return results

    vid = r["video_id"]
    bd = r["base_dir"]

    r = enrich(url, vid=vid, base_dir=bd)
    results["enrich"] = r
    # enrich can fail gracefully — continue even if enrichment is fallback

    r = catalog(bd)
    results["catalog"] = r

    r = queue_brief(bd)
    results["brief"] = r

    results["stopped_at"] = None
    results["video_id"] = vid
    results["base_dir"] = bd
    return results


def list_ingested() -> list[dict[str, Any]]:
    """List all ingested videos with metadata."""
    entries: list[dict[str, Any]] = []
    if not KNOWLEDGE_DIR.exists():
        return entries
    for year_dir in sorted(KNOWLEDGE_DIR.iterdir()):
        if not year_dir.is_dir():
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            for vid_dir in sorted(month_dir.iterdir()):
                if not vid_dir.is_dir():
                    continue
                entry = {
                    "video_id": vid_dir.name,
                    "path": str(vid_dir),
                    "year": year_dir.name,
                    "month": month_dir.name,
                    "has_transcript": (vid_dir / "raw.txt").exists(),
                    "has_enrichment": (vid_dir / "enrich.json").exists(),
                }
                # Read enrichment confidence if available
                ej = vid_dir / "enrich.json"
                if ej.exists():
                    try:
                        data = json.loads(ej.read_text(encoding="utf-8"))
                        entry["confidence"] = data.get("confidence", "unknown")
                        entry["abstract"] = data.get("abstract_120w", "")[:200]
                    except (json.JSONDecodeError, OSError):
                        pass
                entries.append(entry)
    return entries


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Second Brain Pipeline")
    sub = p.add_subparsers(dest="cmd")

    ingest_p = sub.add_parser("ingest")
    ingest_p.add_argument("url")

    full_p = sub.add_parser("full")
    full_p.add_argument("url")

    sub.add_parser("list")

    args = p.parse_args()

    if args.cmd == "ingest":
        print(json.dumps(ingest(args.url), indent=2))
    elif args.cmd == "full":
        print(json.dumps(run_full_pipeline(args.url), indent=2))
    elif args.cmd == "list":
        print(json.dumps(list_ingested(), indent=2))
    else:
        p.print_help()
