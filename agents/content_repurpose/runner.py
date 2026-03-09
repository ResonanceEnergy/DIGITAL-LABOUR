"""Content Repurposer Agent — transforms source content into multiple formats.

Pipeline: Analyze → Write → QA (with retry)

Usage:
    python -m agents.content_repurpose.runner --text "Your blog post here..."
    python -m agents.content_repurpose.runner --file blog.txt
    python -m agents.content_repurpose.runner --file blog.txt --formats linkedin,twitter
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm

PROMPT_DIR = Path(__file__).resolve().parent


# ── Models ──────────────────────────────────────────────────────────────────

class ContentAnalysis(BaseModel):
    title: str = ""
    core_message: str = ""
    key_points: list[str] = Field(default_factory=list)
    target_audience: str = ""
    tone: str = "professional"
    hooks: list[str] = Field(default_factory=list)
    stats_or_quotes: list[str] = Field(default_factory=list)
    word_count: int = 0


class RepurposedContent(BaseModel):
    linkedin_post: str = ""
    twitter_thread: list[str] = Field(default_factory=list)
    email_newsletter: str = ""
    instagram_caption: str = ""
    summary_blurb: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    checks: dict = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ContentOutput(BaseModel):
    analysis: ContentAnalysis
    content: RepurposedContent
    qa: QAResult
    qa_status: str = "FAIL"
    provider: str = ""
    duration_s: float = 0.0
    timestamp: str = ""


# ── Agents ──────────────────────────────────────────────────────────────────

def analyzer_agent(source_text: str, provider: str | None = None) -> ContentAnalysis:
    """Analyze source content and extract key insights."""
    prompt = (PROMPT_DIR / "analyzer_prompt.md").read_text(encoding="utf-8")
    raw = call_llm(prompt, source_text, provider=provider)
    data = json.loads(raw)
    return ContentAnalysis(**data)


def writer_agent(
    analysis: ContentAnalysis,
    formats: list[str] | None = None,
    provider: str | None = None,
) -> RepurposedContent:
    """Generate repurposed content in requested formats."""
    prompt = (PROMPT_DIR / "writer_prompt.md").read_text(encoding="utf-8")
    fmt_list = formats or ["linkedin_post", "twitter_thread", "email_newsletter", "instagram_caption", "summary_blurb"]
    user_msg = json.dumps({
        "analysis": analysis.model_dump(),
        "requested_formats": fmt_list,
    })
    raw = call_llm(prompt, user_msg, provider=provider)
    data = json.loads(raw)
    return RepurposedContent(**data)


def qa_agent(analysis: ContentAnalysis, content: RepurposedContent, provider: str | None = None) -> QAResult:
    """Verify the repurposed content quality."""
    prompt = (PROMPT_DIR / "qa_prompt.md").read_text(encoding="utf-8")
    user_msg = json.dumps({
        "analysis": analysis.model_dump(),
        "content": content.model_dump(),
    })
    raw = call_llm(prompt, user_msg, provider=provider)
    data = json.loads(raw)
    return QAResult(**data)


# ── Pipeline ────────────────────────────────────────────────────────────────

def run_pipeline(
    source_text: str = "",
    source_url: str = "",
    formats: list[str] | None = None,
    provider: str | None = None,
    max_retries: int = 1,
) -> Optional[ContentOutput]:
    """Run the full content repurposing pipeline."""
    start = time.time()

    if not source_text:
        print("[ERROR] No source text provided.")
        return None

    print(f"[CONTENT] Analyzing source ({len(source_text)} chars)...")
    analysis = analyzer_agent(source_text, provider=provider)
    print(f"  → Title: {analysis.title}")
    print(f"  → {len(analysis.key_points)} key points, tone: {analysis.tone}")

    for attempt in range(1 + max_retries):
        print(f"[CONTENT] Writing repurposed content (attempt {attempt + 1})...")
        content = writer_agent(analysis, formats=formats, provider=provider)

        print("[CONTENT] QA check...")
        qa = qa_agent(analysis, content, provider=provider)
        print(f"  → QA: {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break
        if qa.issues:
            print(f"  → Issues: {', '.join(qa.issues[:3])}")

    elapsed = round(time.time() - start, 2)
    output = ContentOutput(
        analysis=analysis,
        content=content,
        qa=qa,
        qa_status=qa.status,
        provider=provider or "default",
        duration_s=elapsed,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Save output
    save_output(output)
    return output


def save_output(output: ContentOutput):
    """Save the repurposed content to output directory."""
    out_dir = PROJECT_ROOT / "output" / "content_repurpose"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    title_slug = output.analysis.title[:30].replace(" ", "_").lower() if output.analysis.title else "untitled"
    filepath = out_dir / f"{title_slug}_{ts}.json"
    filepath.write_text(json.dumps(output.model_dump(), indent=2), encoding="utf-8")
    print(f"[CONTENT] Saved: {filepath}")


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Content Repurposer Agent")
    parser.add_argument("--text", type=str, default="", help="Source text to repurpose")
    parser.add_argument("--file", type=str, default="", help="Path to source text file")
    parser.add_argument("--formats", type=str, default="", help="Comma-separated formats: linkedin,twitter,email,instagram,summary")
    parser.add_argument("--provider", type=str, default="", help="LLM provider")
    args = parser.parse_args()

    source = args.text
    if args.file:
        source = Path(args.file).read_text(encoding="utf-8")

    if not source:
        print("Provide --text or --file")
        sys.exit(1)

    fmt = args.formats.split(",") if args.formats else None
    result = run_pipeline(source_text=source, formats=fmt, provider=args.provider or None)

    if result:
        print(f"\n{'=' * 50}")
        print(f"Status: {result.qa_status} | Score: {result.qa.score} | Time: {result.duration_s}s")
        if result.content.linkedin_post:
            print(f"\n--- LinkedIn ---\n{result.content.linkedin_post[:200]}...")
        if result.content.twitter_thread:
            print(f"\n--- Twitter Thread ({len(result.content.twitter_thread)} tweets) ---")
            for t in result.content.twitter_thread[:2]:
                print(f"  {t}")
