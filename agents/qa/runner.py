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
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_QA_RULES_PATH = PROJECT_ROOT / "config" / "qa_rules.json"
_CLIENT_PROFILES_DIR = PROJECT_ROOT / "config" / "client_profiles"

# QA thresholds from doctrine
PASS_CONFIDENCE = 0.70
RETRY_CONFIDENCE = 0.50


def _load_qa_rules() -> dict:
    if _QA_RULES_PATH.exists():
        try:
            return json.loads(_QA_RULES_PATH.read_text(encoding="utf-8")).get("rules", {})
        except Exception:
            pass
    return {}


def _load_client_profile(client_id: str) -> dict:
    """Load client-specific QA profile, falling back to default."""
    for name in (client_id, "default"):
        path = _CLIENT_PROFILES_DIR / f"{name}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {"min_confidence": PASS_CONFIDENCE, "banned_phrases": []}


QA_RULES: dict = _load_qa_rules()


class QAResult(BaseModel):
    status: str = "FAIL"
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""
    score: int = 0
    confidence: float = 0.0
    applied_rules: list[str] = Field(default_factory=list)
    failed_rule_id: str = ""
    duration_s: float = 0.0


def _pre_check(output_text: str, task_type: str, client_id: str = "") -> Optional[QAResult]:
    """Run deterministic pre-checks before calling the LLM verifier.

    Returns a QAResult immediately if a hard-fail rule triggers, else None.
    """
    profile = _load_client_profile(client_id)
    banned = profile.get("banned_phrases", [])
    applied: list[str] = []

    # QA-001: non-empty
    applied.append("QA-001")
    if not output_text or not output_text.strip():
        return QAResult(
            status="FAIL", issues=["Output is empty"], score=0,
            confidence=0.0, applied_rules=applied, failed_rule_id="QA-001",
        )

    # QA-002: no placeholder text
    applied.append("QA-002")
    import re
    placeholder_re = re.compile(r"\[INSERT\]|\bTODO\b|PLACEHOLDER|<FILL_IN>|<YOUR_[A-Z_]+>", re.IGNORECASE)
    if placeholder_re.search(output_text):
        return QAResult(
            status="FAIL", issues=["Output contains placeholder text"],
            score=0, confidence=0.0, applied_rules=applied, failed_rule_id="QA-002",
        )

    # QA-004: banned phrases
    applied.append("QA-004")
    for phrase in banned:
        if phrase and phrase.lower() in output_text.lower():
            return QAResult(
                status="FAIL", issues=[f"Banned phrase detected: '{phrase}'"],
                score=0, confidence=0.0, applied_rules=applied, failed_rule_id="QA-004",
            )

    # QA-003: minimum length
    applied.append("QA-003")
    if "QA-003" in QA_RULES:
        min_len = QA_RULES["QA-003"].get("params", {}).get(task_type, 0)
        if min_len and len(output_text.strip()) < min_len:
            return QAResult(
                status="FAIL",
                issues=[f"Output too short: {len(output_text.strip())} chars (min {min_len})"],
                score=0, confidence=0.0, applied_rules=applied, failed_rule_id="QA-003",
            )

    return None  # All pre-checks passed


def verify(
    output_text: str,
    task_type: str = "general",
    client_id: str = "",
    custom_prompt: Optional[str] = None,
    provider: Optional[str] = None,
) -> QAResult:
    """Run QA verification on any agent output.

    Args:
        output_text: The agent output to verify (JSON string or text).
        task_type: The type of task for context.
        client_id: Client identifier for profile-based rules.
        custom_prompt: Optional custom QA prompt. Falls back to verifier_prompt.md.
        provider: LLM provider override.

    Returns:
        QAResult with status, issues, confidence, applied_rules, and score.
    """
    start = time.time()

    # Deterministic pre-checks first (no LLM cost)
    pre_result = _pre_check(output_text, task_type, client_id)
    if pre_result is not None:
        pre_result.duration_s = round(time.time() - start, 2)
        return pre_result

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

    # Normalize confidence: LLM returns score 0-100, we store 0.00-1.00
    raw_score = data.get("score", 50)
    confidence = round(raw_score / 100.0, 3) if raw_score > 1 else round(float(raw_score), 3)

    # QA-008: minimum confidence threshold
    profile = _load_client_profile(client_id)
    min_conf = profile.get("min_confidence", PASS_CONFIDENCE)
    llm_status = data.get("status", "FAIL")

    if confidence < RETRY_CONFIDENCE:
        llm_status = "FAIL"
    elif confidence < min_conf:
        llm_status = "FAIL"

    result = QAResult(
        status=llm_status,
        issues=data.get("issues", []),
        revision_notes=data.get("revision_notes", ""),
        score=raw_score,
        confidence=confidence,
        applied_rules=["QA-001", "QA-002", "QA-003", "QA-004", "QA-008"],
        failed_rule_id="QA-008" if llm_status == "FAIL" and not data.get("issues") else "",
        duration_s=round(time.time() - start, 2),
    )
    return result


def run(input_data: dict, provider: Optional[str] = None) -> dict:
    """Pipeline-compatible entry point."""
    output_text = input_data.get("output_text", "")
    task_type = input_data.get("task_type", "general")
    client_id = input_data.get("client_id", "")

    if not output_text:
        return {"status": "FAIL", "issues": ["No output_text provided"], "score": 0, "confidence": 0.0}

    result = verify(output_text, task_type=task_type, client_id=client_id, provider=provider)
    return result.model_dump()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = '{"test": "sample output for QA verification"}'
    r = verify(text)
    print(json.dumps(r.model_dump(), indent=2))
