"""SEO Content Agent — Keyword research, article writing, and on-page optimization.

3-step pipeline:
    1. Keyword Agent — identifies target keywords, search intent, content gaps
    2. Writer Agent — produces optimized article with meta, schema, internal links
    3. QA Agent — validates SEO best practices, readability, factual accuracy

Usage:
    python -m agents.seo_content.runner --topic "AI sales automation" --type blog
    python -m agents.seo_content.runner --topic "cold email best practices" --tone conversational
    python -m agents.seo_content.runner --topic "document extraction AI" --type pillar_page
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.dl_agent import make_bridge  # noqa: E402
call_llm = make_bridge("seo_content")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "seo_content"


# ── Pydantic Models ────────────────────────────────────────────

class RelatedKeyword(BaseModel):
    keyword: str = ""
    intent: str = ""
    priority: str = ""


class KeywordResearch(BaseModel):
    primary_keyword: str = ""
    search_intent: str = ""
    estimated_difficulty: str = ""
    related_keywords: list[RelatedKeyword] = Field(default_factory=list)
    long_tail_keywords: list[str] = Field(default_factory=list)
    lsi_keywords: list[str] = Field(default_factory=list)
    content_gaps: list[str] = Field(default_factory=list)
    recommended_title: str = ""
    recommended_headings: list[str] = Field(default_factory=list)
    word_count_target: int = 1500


class InternalLink(BaseModel):
    anchor: str = ""
    suggested_url: str = ""


class ArticleOutput(BaseModel):
    title: str = ""
    meta_description: str = ""
    slug: str = ""
    content_html: str = ""
    content_markdown: str = ""
    word_count: int = 0
    reading_time_minutes: int = 0
    primary_keyword_density: float = 0.0
    internal_links_suggested: list[InternalLink] = Field(default_factory=list)
    schema_markup: dict = Field(default_factory=dict)
    featured_image_suggestion: str = ""
    excerpt: str = ""


class SEOScoreBreakdown(BaseModel):
    on_page_seo: int = 0
    readability: int = 0
    content_quality: int = 0
    technical_seo: int = 0


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""
    seo_score_breakdown: SEOScoreBreakdown = Field(default_factory=SEOScoreBreakdown)


class SEOContentOutput(BaseModel):
    keywords: KeywordResearch = Field(default_factory=KeywordResearch)
    article: ArticleOutput = Field(default_factory=ArticleOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def keyword_agent(
    topic: str,
    business: str = "BIT RAGE SYSTEMS — AI automation agency",
    audience: str = "",
    content_type: str = "blog",
    provider: str = "openai",
) -> KeywordResearch:
    """Step 1: Research keywords and content structure."""
    system = _load_prompt("keyword_prompt")
    user_msg = (
        f"Topic: {topic}\n"
        f"Business: {business}\n"
        f"Audience: {audience or 'Business decision-makers looking for AI automation'}\n"
        f"Content Type: {content_type}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return KeywordResearch(**json.loads(raw))


def writer_agent(
    keywords: KeywordResearch,
    business: str = "BIT RAGE SYSTEMS — AI automation agency",
    tone: str = "professional",
    content_type: str = "blog",
    context: str = "",
    provider: str = "openai",
) -> ArticleOutput:
    """Step 2: Write the optimized article."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Keyword Research:\n{json.dumps(keywords.model_dump(), indent=2)}\n\n"
        f"Business: {business}\n"
        f"Tone: {tone}\n"
        f"Content Type: {content_type}\n"
        f"Additional Context: {context}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True, temperature=0.7)
    return ArticleOutput(**json.loads(raw))


def qa_agent(
    keywords: KeywordResearch,
    article: ArticleOutput,
    content_type: str = "blog",
    provider: str = "openai",
) -> QAResult:
    """Step 3: Validate SEO quality and content accuracy."""
    system = _load_prompt("qa_prompt")
    user_msg = (
        f"Content Type: {content_type}\n\n"
        f"Keyword Research:\n{json.dumps(keywords.model_dump(), indent=2)}\n\n"
        f"Article:\n{json.dumps(article.model_dump(), indent=2)}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    topic: str,
    business: str = "BIT RAGE SYSTEMS — AI automation agency",
    audience: str = "",
    tone: str = "professional",
    content_type: str = "blog",
    provider: str = "openai",
    max_retries: int = 2,
) -> SEOContentOutput:
    """Run the full SEO content pipeline: Keywords → Write → QA."""
    print(f"\n[SEO_CONTENT] Starting pipeline — {topic}")
    print(f"  Type: {content_type} | Tone: {tone} | Provider: {provider}")

    # Step 1: Keyword research
    print("\n  [1/3] Keyword research...")
    keywords = keyword_agent(topic, business, audience, content_type, provider)
    print(f"  → Primary: '{keywords.primary_keyword}' ({keywords.estimated_difficulty})")
    print(f"  → {len(keywords.related_keywords)} related, {len(keywords.long_tail_keywords)} long-tail")

    # Step 2: Write article
    print("\n  [2/3] Writing article...")
    article = writer_agent(keywords, business, tone, content_type, "", provider)
    print(f"  → '{article.title}' ({article.word_count} words, {article.reading_time_minutes} min)")

    # Step 3: QA (with retries)
    for attempt in range(1, max_retries + 2):
        print(f"\n  [3/3] SEO QA (attempt {attempt})...")
        qa = qa_agent(keywords, article, content_type, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print(f"  → Rewriting with revisions...")
            article = writer_agent(keywords, business, tone, content_type,
                                   qa.revision_notes, provider)

    output = SEOContentOutput(
        keywords=keywords,
        article=article,
        qa=qa,
        meta={
            "topic": topic,
            "content_type": content_type,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: SEOContentOutput) -> Path:
    """Save pipeline output — JSON + standalone markdown article."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Full JSON output
    json_path = OUTPUT_DIR / f"seo_{ts}_{run_id}.json"
    json_path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                         encoding="utf-8")

    # Standalone markdown article for direct publishing
    if output.article.content_markdown:
        md_path = OUTPUT_DIR / f"{output.article.slug or 'article'}_{run_id}.md"
        front_matter = (
            f"---\n"
            f"title: \"{output.article.title}\"\n"
            f"description: \"{output.article.meta_description}\"\n"
            f"slug: {output.article.slug}\n"
            f"date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
            f"reading_time: {output.article.reading_time_minutes} min\n"
            f"---\n\n"
        )
        md_path.write_text(front_matter + output.article.content_markdown,
                           encoding="utf-8")
        print(f"  [SAVED] {md_path}")

    print(f"  [SAVED] {json_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SEO Content Agent")
    parser.add_argument("--topic", required=True, help="Article topic")
    parser.add_argument("--type", default="blog", dest="content_type",
                        choices=["blog", "landing_page", "pillar_page", "product_description"])
    parser.add_argument("--tone", default="professional",
                        choices=["professional", "conversational", "technical", "beginner-friendly"])
    parser.add_argument("--audience", default="", help="Target reader audience")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    args = parser.parse_args()

    result = run_pipeline(
        topic=args.topic,
        audience=args.audience,
        tone=args.tone,
        content_type=args.content_type,
        provider=args.provider,
    )
    save_output(result)
