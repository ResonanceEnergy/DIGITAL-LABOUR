"""Resume / CV Writer Agent — ATS-optimized resumes from raw career data.

2-step pipeline:
    1. Writer Agent — produces structured resume with quantified achievements
    2. QA Agent — validates ATS compliance, quantification, and format

Usage:
    python -m agents.resume_writer.runner --file career.txt --role "Senior Product Manager"
    python -m agents.resume_writer.runner --text "8 years PM..." --role "VP Product" --style executive
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
call_llm = make_bridge("resume_writer")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "resumes"


class Contact(BaseModel):
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    location: str = ""


class Experience(BaseModel):
    company: str = ""
    title: str = ""
    location: str = ""
    dates: str = ""
    bullets: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str = ""
    degree: str = ""
    dates: str = ""
    honors: str = ""


class Skills(BaseModel):
    technical: list[str] = Field(default_factory=list)
    methodologies: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)


class WriterOutput(BaseModel):
    candidate_name: str = ""
    target_role: str = ""
    resume_style: str = ""
    contact: Contact = Field(default_factory=Contact)
    professional_summary: str = ""
    core_competencies: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    ats_keywords: list[str] = Field(default_factory=list)
    formatting_notes: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class ResumeOutput(BaseModel):
    resume: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(career_data: str, target_role: str = "",
                 target_industry: str = "", style: str = "combination",
                 level: str = "mid", revision_notes: str = "",
                 provider: str = "openai") -> WriterOutput:
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Target Role: {target_role}\nIndustry: {target_industry or 'Not specified'}\n"
        f"Style: {style}\nExperience Level: {level}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nCareer Data:\n{career_data}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return WriterOutput(**json.loads(raw))


def qa_agent(resume: WriterOutput, provider: str = "openai") -> QAResult:
    system = _load_prompt("qa_prompt")
    user_msg = f"Resume to validate:\n{json.dumps(resume.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


def run_pipeline(career_data: str, target_role: str = "",
                 target_industry: str = "", style: str = "combination",
                 level: str = "mid", provider: str = "openai",
                 max_retries: int = 2) -> ResumeOutput:
    print(f"\n[RESUME] Starting pipeline — {target_role or 'general'}")
    print("\n  [1/2] Writing resume...")
    resume = writer_agent(career_data, target_role, target_industry, style,
                          level, provider=provider)
    print(f"  → {resume.candidate_name} — {resume.target_role}")
    print(f"  → {len(resume.experience)} positions, {len(resume.core_competencies)} competencies")

    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(resume, provider)
        print(f"  → {qa.status} (score: {qa.score})")
        if qa.status == "PASS":
            break
        if attempt <= max_retries and qa.revision_notes:
            print("  → Rewriting...")
            resume = writer_agent(career_data, target_role, target_industry,
                                  style, level, qa.revision_notes, provider)

    return ResumeOutput(
        resume=resume, qa=qa,
        meta={"target_role": target_role, "style": style, "provider": provider,
              "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def save_output(output: ResumeOutput) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"resume_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Resume Writer Agent")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--role", default="", help="Target role")
    parser.add_argument("--industry", default="")
    parser.add_argument("--style", default="combination",
                        choices=["chronological", "functional", "combination",
                                 "modern", "executive"])
    parser.add_argument("--level", default="mid",
                        choices=["entry", "mid", "senior", "executive"])
    parser.add_argument("--provider", default="openai")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file"); sys.exit(1)

    result = run_pipeline(data, args.role, args.industry, args.style,
                          args.level, args.provider)
    save_output(result)
