"""Ad Copy Writer Agent — PPC and social media ad copy for any platform.

2-step pipeline:
    1. Writer Agent — generates platform-compliant ad copy with variations
    2. QA Agent — validates character limits, policy compliance, and quality

Handles: Google Search/Display, Facebook, Instagram, LinkedIn, Twitter,
         TikTok, YouTube, Pinterest, multi-platform campaigns.

Usage:
    python -m agents.ad_copy.runner --text "AI sales automation tool" --platform google_search
    python -m agents.ad_copy.runner --file product.txt --platform facebook --goal leads
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm  # noqa: E402

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "ad_copy"


class Sitelink(BaseModel):
    text: str = ""
    url: str = ""


class Ad(BaseModel):
    ad_name: str = ""
    headlines: list[str] = Field(default_factory=list)
    descriptions: list[str] = Field(default_factory=list)
    display_url: str = ""
    final_url: str = ""
    sitelinks: list[Sitelink] = Field(default_factory=list)
    callout_extensions: list[str] = Field(default_factory=list)


class Variation(BaseModel):
    variant_name: str = ""
    headlines: list[str] = Field(default_factory=list)
    descriptions: list[str] = Field(default_factory=list)


class TargetingSuggestions(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    audiences: list[str] = Field(default_factory=list)
    demographics: str = ""


class WriterOutput(BaseModel):
    platform: str = ""
    goal: str = ""
    ads: list[Ad] = Field(default_factory=list)
    variations: list[Variation] = Field(default_factory=list)
    platform_limits: dict = Field(default_factory=dict)
    targeting_suggestions: TargetingSuggestions = Field(
        default_factory=TargetingSuggestions)
    copy_rationale: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class AdCopyOutput(BaseModel):
    ads: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(product: str, platform: str = "google_search",
                 audience: str = "", goal: str = "conversions",
                 revision_notes: str = "",
                 provider: str = "openai") -> WriterOutput:
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Platform: {platform}\nGoal: {goal}\n"
        f"Audience: {audience or 'Not specified'}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nProduct/Service:\n{product}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return WriterOutput(**json.loads(raw))


def qa_agent(ads: WriterOutput, provider: str = "openai") -> QAResult:
    system = _load_prompt("qa_prompt")
    user_msg = f"Ad copy to validate:\n{json.dumps(ads.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


def run_pipeline(product: str, platform: str = "google_search",
                 audience: str = "", goal: str = "conversions",
                 provider: str = "openai",
                 max_retries: int = 2) -> AdCopyOutput:
    print(f"\n[AD COPY] Starting pipeline — {platform} / {goal}")

    print("\n  [1/2] Writing ad copy...")
    ads = writer_agent(product, platform, audience, goal, provider=provider)
    print(f"  → {len(ads.ads)} ads + {len(ads.variations)} variations")

    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(ads, provider)
        print(f"  → {qa.status} (score: {qa.score})")
        if qa.status == "PASS":
            break
        if attempt <= max_retries and qa.revision_notes:
            print("  → Rewriting...")
            ads = writer_agent(product, platform, audience, goal,
                               qa.revision_notes, provider)

    return AdCopyOutput(
        ads=ads, qa=qa,
        meta={"platform": platform, "goal": goal, "provider": provider,
              "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def save_output(output: AdCopyOutput) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"ads_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ad Copy Writer Agent")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--platform", default="google_search",
                        choices=["google_search", "google_display", "facebook",
                                 "instagram", "linkedin", "tiktok", "twitter",
                                 "youtube", "pinterest", "multi"])
    parser.add_argument("--audience", default="")
    parser.add_argument("--goal", default="conversions",
                        choices=["awareness", "traffic", "conversions",
                                 "leads", "app_installs", "engagement"])
    parser.add_argument("--provider", default="openai")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file"); sys.exit(1)

    result = run_pipeline(data, args.platform, args.audience, args.goal,
                          args.provider)
    save_output(result)
