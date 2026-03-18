"""Social Media Agent — Create platform-optimized posts, threads, and calendars.

2-step pipeline:
    1. Strategist Agent — creates platform-native content with posting schedule
    2. QA Agent — validates platform constraints, engagement best practices

Usage:
    python -m agents.social_media.runner --topic "AI automation results" --platforms linkedin,twitter
    python -m agents.social_media.runner --topic "product launch" --platforms linkedin,twitter,instagram
    python -m agents.social_media.runner --topic "case study" --cta leads
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
call_llm = make_bridge("social_media")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "social_media"


# ── Pydantic Models ────────────────────────────────────────────

class SocialPost(BaseModel):
    platform: str = ""
    post_type: str = ""
    content: object = ""  # str or list[str] for threads
    character_count: object = 0  # int or list[int] for threads
    hashtags: list[str] = Field(default_factory=list)
    best_time: str = ""
    image_suggestion: str = ""
    engagement_hook: str = ""
    cta: str = ""


class CalendarEntry(BaseModel):
    day: str = ""
    platform: str = ""
    type: str = ""


class HashtagStrategy(BaseModel):
    branded: list[str] = Field(default_factory=list)
    industry: list[str] = Field(default_factory=list)
    trending: list[str] = Field(default_factory=list)


class SocialMediaPlan(BaseModel):
    campaign_theme: str = ""
    posts: list[SocialPost] = Field(default_factory=list)
    content_calendar: list[CalendarEntry] = Field(default_factory=list)
    hashtag_strategy: HashtagStrategy = Field(default_factory=HashtagStrategy)


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class SocialMediaOutput(BaseModel):
    plan: SocialMediaPlan = Field(default_factory=SocialMediaPlan)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def strategist_agent(
    topic: str,
    brand: str = "Bit Rage Labour — AI automation agency",
    platforms: list[str] = None,
    tone: str = "professional",
    cta_goal: str = "engagement",
    context: str = "",
    provider: str = "openai",
) -> SocialMediaPlan:
    """Step 1: Create platform-optimized social content."""
    if platforms is None:
        platforms = ["linkedin", "twitter"]
    system = _load_prompt("strategist_prompt")
    user_msg = (
        f"Topic: {topic}\n"
        f"Brand: {brand}\n"
        f"Platforms: {', '.join(platforms)}\n"
        f"Tone: {tone}\n"
        f"CTA Goal: {cta_goal}\n"
        f"Additional Context: {context}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True, temperature=0.7)
    return SocialMediaPlan(**json.loads(raw))


def qa_agent(plan: SocialMediaPlan, provider: str = "openai") -> QAResult:
    """Step 2: Validate social content quality."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Social media plan to validate:\n{json.dumps(plan.model_dump(), indent=2, default=str)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    topic: str,
    brand: str = "Bit Rage Labour — AI automation agency",
    platforms: list[str] = None,
    tone: str = "professional",
    cta_goal: str = "engagement",
    provider: str = "openai",
    max_retries: int = 2,
) -> SocialMediaOutput:
    """Run the full social media pipeline: Strategist → QA."""
    if platforms is None:
        platforms = ["linkedin", "twitter"]

    print(f"\n[SOCIAL_MEDIA] Starting pipeline — {topic}")
    print(f"  Platforms: {', '.join(platforms)} | Provider: {provider}")

    # Step 1: Create content
    print("\n  [1/2] Creating social content...")
    plan = strategist_agent(topic, brand, platforms, tone, cta_goal, "", provider)
    print(f"  → {len(plan.posts)} posts created across {len(set(p.platform for p in plan.posts))} platforms")

    # Step 2: QA (with retries)
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(plan, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print(f"  → Recreating with revision notes...")
            plan = strategist_agent(topic, brand, platforms, tone, cta_goal,
                                    qa.revision_notes, provider)

    output = SocialMediaOutput(
        plan=plan,
        qa=qa,
        meta={
            "topic": topic,
            "platforms": platforms,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: SocialMediaOutput) -> Path:
    """Save pipeline output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"social_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Social Media Agent")
    parser.add_argument("--topic", required=True, help="Content topic")
    parser.add_argument("--platforms", default="linkedin,twitter",
                        help="Comma-separated platforms")
    parser.add_argument("--tone", default="professional",
                        choices=["professional", "casual", "bold", "friendly", "authoritative"])
    parser.add_argument("--cta", default="engagement", dest="cta_goal",
                        choices=["engagement", "traffic", "leads", "awareness"])
    parser.add_argument("--provider", default="openai", help="LLM provider")
    args = parser.parse_args()

    result = run_pipeline(
        topic=args.topic,
        platforms=args.platforms.split(","),
        tone=args.tone,
        cta_goal=args.cta_goal,
        provider=args.provider,
    )
    save_output(result)
