"""QA Agent — Generic quality verifier for any agent output.

Uses the verifier_prompt.md for sales-specific QA, but also provides
a universal verify() function usable by the pipeline.
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from utils.dl_agent import make_bridge
call_llm = make_bridge("qa", self_reflect=False)

PROMPT_DIR = Path(__file__).parent


class QAResult(BaseModel):
    status: str = "FAIL"
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""
    score: int = 0
    duration_s: float = 0.0


def verify(
    output_text: str,
    task_type: str = "general",
    custom_prompt: Optional[str] = None,
    provider: Optional[str] = None,
) -> QAResult:
    """Run QA verification on any agent output.

    Args:
        output_text: The agent output to verify (JSON string or text).
        task_type: The type of task for context.
        custom_prompt: Optional custom QA prompt. Falls back to verifier_prompt.md.
        provider: LLM provider override.

    Returns:
        QAResult with status, issues, and score.
    """
    start = time.time()

    if custom_prompt:
        system = custom_prompt
    else:
        system = (PROMPT_DIR / "verifier_prompt.md").read_text(encoding="utf-8")

    user_msg = json.dumps({
        "task_type": task_type,
        "output": output_text if len(output_text) < 8000 else output_text[:8000],
    })

    raw = call_llm(system, user_msg, provider=provider)
    data = json.loads(raw)

    result = QAResult(
        status=data.get("status", "FAIL"),
        issues=data.get("issues", []),
        revision_notes=data.get("revision_notes", ""),
        score=data.get("score", 100 if data.get("status") == "PASS" else 50),
        duration_s=round(time.time() - start, 2),
    )
    return result


def run(input_data: dict, provider: Optional[str] = None) -> dict:
    """Pipeline-compatible entry point."""
    output_text = input_data.get("output_text", "")
    task_type = input_data.get("task_type", "general")

    if not output_text:
        return {"status": "FAIL", "issues": ["No output_text provided"], "score": 0}

    result = verify(output_text, task_type=task_type, provider=provider)
    return result.model_dump()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = '{"test": "sample output for QA verification"}'
    r = verify(text)
    print(json.dumps(r.model_dump(), indent=2))
