"""Product Description Agent — E-commerce product copy for any platform.

2-step pipeline:
    1. Writer Agent — generates platform-optimized product descriptions
    2. QA Agent — validates compliance, keyword integration, and conversion quality

Handles: Amazon, Shopify, Etsy, eBay, WooCommerce, general product copy.

Usage:
    python -m agents.product_desc.runner --text "32oz steel water bottle..." --platform amazon
    python -m agents.product_desc.runner --file specs.txt --platform shopify --tone luxury
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.super_agent import make_bridge  # noqa: E402
call_llm = make_bridge("product_desc")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "product_desc"


# ── Pydantic Models ────────────────────────────────────────────

class SEOMeta(BaseModel):
    meta_title: str = ""
    meta_description: str = ""
    keywords: list[str] = Field(default_factory=list)


class Variation(BaseModel):
    variant: str = ""
    version_a: str = ""
    version_b: str = ""


class WriterOutput(BaseModel):
    product_name: str = ""
    platform: str = ""
    title: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    short_description: str = ""
    long_description: str = ""
    seo_meta: SEOMeta = Field(default_factory=SEOMeta)
    variations: list[Variation] = Field(default_factory=list)
    platform_notes: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class ProductDescOutput(BaseModel):
    description: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(
    product_specs: str,
    platform: str = "amazon",
    audience: str = "",
    tone: str = "professional",
    keywords: str = "",
    revision_notes: str = "",
    provider: str = "openai",
) -> WriterOutput:
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Platform: {platform}\nAudience: {audience or 'General consumers'}\n"
        f"Tone: {tone}\nSEO Keywords: {keywords or 'Auto-detect from specs'}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nProduct Specs:\n{product_specs}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return WriterOutput(**json.loads(raw))


def qa_agent(desc: WriterOutput, provider: str = "openai") -> QAResult:
    system = _load_prompt("qa_prompt")
    user_msg = f"Product description to validate:\n{json.dumps(desc.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    product_specs: str,
    platform: str = "amazon",
    audience: str = "",
    tone: str = "professional",
    keywords: str = "",
    provider: str = "openai",
    max_retries: int = 2,
) -> ProductDescOutput:
    print(f"\n[PRODUCT DESC] Starting pipeline — {platform}")

    print("\n  [1/2] Writing product description...")
    desc = writer_agent(product_specs, platform, audience, tone, keywords,
                        provider=provider)
    print(f"  → \"{desc.title[:60]}...\"")
    print(f"  → {len(desc.bullet_points)} bullet points")

    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(desc, provider)
        print(f"  → {qa.status} (score: {qa.score})")
        if qa.status == "PASS":
            break
        if attempt <= max_retries and qa.revision_notes:
            print("  → Rewriting...")
            desc = writer_agent(product_specs, platform, audience, tone,
                                keywords, qa.revision_notes, provider)

    return ProductDescOutput(
        description=desc, qa=qa,
        meta={"platform": platform, "provider": provider,
              "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def save_output(output: ProductDescOutput) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"product_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Product Description Agent")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--platform", default="amazon",
                        choices=["amazon", "shopify", "etsy", "ebay",
                                 "woocommerce", "general"])
    parser.add_argument("--audience", default="")
    parser.add_argument("--tone", default="professional")
    parser.add_argument("--keywords", default="")
    parser.add_argument("--provider", default="openai")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file"); sys.exit(1)

    result = run_pipeline(data, args.platform, args.audience, args.tone,
                          args.keywords, args.provider)
    save_output(result)
