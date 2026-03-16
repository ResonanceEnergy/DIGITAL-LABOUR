"""Press Release Writer Agent — AP-style press releases for distribution.

2-step pipeline:
    1. Writer Agent — produces AP-style press release with quotes, boilerplate
    2. QA Agent — validates AP compliance, completeness, distribution readiness

Handles: product launches, partnerships, funding, executive hires, events,
         milestones, awards, expansion, crisis response.

Usage:
    python -m agents.press_release.runner --text "Company X launches..." --type product_launch
    python -m agents.press_release.runner --file announcement.txt --type funding --tone authoritative
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
call_llm = make_bridge("press_release")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "press_releases"


class Quote(BaseModel):
    speaker: str = ""
    quote: str = ""
    context: str = ""


class MediaContact(BaseModel):
    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""


class DistributionNotes(BaseModel):
    suggested_wire: str = ""
    suggested_tags: list[str] = Field(default_factory=list)
    embargo: str = ""
    target_outlets: list[str] = Field(default_factory=list)


class SEOMeta(BaseModel):
    meta_title: str = ""
    meta_description: str = ""
    keywords: list[str] = Field(default_factory=list)


class WriterOutput(BaseModel):
    headline: str = ""
    subheadline: str = ""
    dateline: str = ""
    lead_paragraph: str = ""
    body_paragraphs: list[str] = Field(default_factory=list)
    quotes: list[Quote] = Field(default_factory=list)
    call_to_action: str = ""
    boilerplate: str = ""
    media_contact: MediaContact = Field(default_factory=MediaContact)
    distribution_notes: DistributionNotes = Field(
        default_factory=DistributionNotes)
    seo_meta: SEOMeta = Field(default_factory=SEOMeta)


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class PressReleaseOutput(BaseModel):
    release: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(announcement: str, company_name: str = "",
                 release_type: str = "product_launch",
                 tone: str = "professional", revision_notes: str = "",
                 provider: str = "openai") -> WriterOutput:
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Release Type: {release_type}\nCompany: {company_name or 'Extract from announcement'}\n"
        f"Tone: {tone}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nAnnouncement:\n{announcement}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return WriterOutput(**json.loads(raw))


def qa_agent(release: WriterOutput, provider: str = "openai") -> QAResult:
    system = _load_prompt("qa_prompt")
    user_msg = f"Press release to validate:\n{json.dumps(release.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


def run_pipeline(announcement: str, company_name: str = "",
                 release_type: str = "product_launch",
                 tone: str = "professional", provider: str = "openai",
                 max_retries: int = 2) -> PressReleaseOutput:
    print(f"\n[PRESS RELEASE] Starting pipeline — {release_type}")

    print("\n  [1/2] Drafting press release...")
    release = writer_agent(announcement, company_name, release_type, tone,
                           provider=provider)
    print(f"  → {release.headline}")
    print(f"  → {len(release.quotes)} quotes, "
          f"{len(release.body_paragraphs)} body paragraphs")

    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(release, provider)
        print(f"  → {qa.status} (score: {qa.score})")
        if qa.status == "PASS":
            break
        if attempt <= max_retries and qa.revision_notes:
            print("  → Revising release...")
            release = writer_agent(announcement, company_name, release_type,
                                   tone, qa.revision_notes, provider)

    return PressReleaseOutput(
        release=release, qa=qa,
        meta={"release_type": release_type, "provider": provider,
              "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def save_output(output: PressReleaseOutput) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"pr_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Press Release Writer Agent")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--company", default="")
    parser.add_argument("--type", default="product_launch",
                        choices=["product_launch", "partnership", "funding",
                                 "expansion", "award", "executive_hire",
                                 "event", "milestone", "crisis_response"],
                        dest="release_type")
    parser.add_argument("--tone", default="professional",
                        choices=["professional", "exciting", "authoritative",
                                 "empathetic"])
    parser.add_argument("--provider", default="openai")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file"); sys.exit(1)

    result = run_pipeline(data, args.company, args.release_type, args.tone,
                          args.provider)
    save_output(result)
