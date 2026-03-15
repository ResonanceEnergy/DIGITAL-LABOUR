"""Support Resolver Agent — Ticket Triage + Draft Response Pipeline.

Usage:
    python runner.py --ticket "I can't log into my account and I've tried resetting my password 3 times"
    python runner.py --ticket-file ticket.txt --kb-file knowledge_base.md
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env")

sys.path.insert(0, str(PROJECT_ROOT))
from utils.super_agent import make_bridge
llm_call = make_bridge("support", default_temperature=0.4)


# ── Models ──────────────────────────────────────────────────────────────────

class NextAction(BaseModel):
    action: str
    details: str = ""


class Escalation(BaseModel):
    required: bool = False
    reason: str = ""
    team: str = ""


class Citation(BaseModel):
    source: str = ""
    link_or_id: str = ""
    quote: str = ""


class SupportOutput(BaseModel):
    category: str
    severity: str
    sentiment: str
    summary: str
    draft_reply: str
    next_actions: list[NextAction] = []
    escalation: Escalation = Escalation()
    confidence: float = 0.0
    citations: list[Citation] = []


class QAResult(BaseModel):
    status: str = Field(pattern=r"^(PASS|FAIL)$")
    issues: list[str] = []
    revision_notes: str = ""


# ── Prompt Loading ──────────────────────────────────────────────────────────

AGENT_DIR = Path(__file__).parent

def load_prompt(name: str) -> str:
    path = AGENT_DIR / f"{name}_prompt.md"
    if not path.exists():
        path = AGENT_DIR.parent / "qa" / f"{name}_prompt.md"
    return path.read_text(encoding="utf-8")


# ── LLM ─────────────────────────────────────────────────────────────────────

def call_llm(system_prompt: str, user_message: str, provider: str | None = None) -> str:
    return llm_call(system_prompt, user_message, provider=provider, temperature=0.4, json_mode=True)


# ── Agent Functions ─────────────────────────────────────────────────────────

def resolver_agent(ticket: str, kb: str = "", policies: str = "", provider: str | None = None) -> SupportOutput:
    """Classify ticket and draft response."""
    prompt = load_prompt("resolver")
    user_msg = f"TICKET:\n{ticket}"
    if kb:
        user_msg += f"\n\nKNOWLEDGE BASE:\n{kb}"
    if policies:
        user_msg += f"\n\nPOLICIES:\n{policies}"
    raw = call_llm(prompt, user_msg, provider)
    return SupportOutput.model_validate_json(raw)


def qa_agent(ticket: str, output: SupportOutput, provider: str | None = None) -> QAResult:
    """QA check on support output."""
    prompt = load_prompt("qa")
    user_msg = json.dumps({
        "original_ticket": ticket,
        "agent_output": output.model_dump(),
    }, indent=2)
    raw = call_llm(prompt, user_msg, provider)
    return QAResult.model_validate_json(raw)


# ── Pipeline ────────────────────────────────────────────────────────────────

def run_pipeline(
    ticket: str,
    kb: str = "",
    policies: str = "",
    max_retries: int = 1,
    provider: str | None = None,
) -> SupportOutput | None:
    """Run Support pipeline: Resolve → QA (with retry)."""
    start = time.time()

    print(f"[RESOLVE] Processing ticket ({len(ticket)} chars)...")
    output = resolver_agent(ticket, kb, policies, provider)

    for attempt in range(1 + max_retries):
        print(f"[QA] Verifying (attempt {attempt + 1})...")
        qa = qa_agent(ticket, output, provider)

        if qa.status == "PASS":
            elapsed = round(time.time() - start, 1)
            print(f"[PASS] Resolution ready in {elapsed}s")
            return output
        else:
            print(f"[FAIL] Issues: {qa.issues}")
            if attempt < max_retries:
                print("[RETRY] Re-resolving with QA feedback...")
                revision_context = f"{ticket}\n\nPREVIOUS ATTEMPT ISSUES: {qa.revision_notes}"
                output = resolver_agent(revision_context, kb, policies, provider)

    print("[FAILED] Could not pass QA. Flagged for human review.")
    return output


# ── Output ──────────────────────────────────────────────────────────────────

def save_output(output: SupportOutput, output_dir: Path | None = None) -> Path:
    output_dir = output_dir or PROJECT_ROOT / "output" / "support"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"ticket_{uuid4().hex[:8]}.json"
    path = output_dir / filename
    path.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    print(f"[SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Support Resolver Agent")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticket", help="Ticket text (inline)")
    group.add_argument("--ticket-file", help="Path to ticket text file")
    parser.add_argument("--kb-file", help="Path to knowledge base file")
    parser.add_argument("--policy-file", help="Path to policy file")
    parser.add_argument("--provider", default=None, choices=["openai", "anthropic", "gemini", "grok"], help="LLM provider")
    args = parser.parse_args()

    ticket = args.ticket
    if args.ticket_file:
        ticket = Path(args.ticket_file).read_text(encoding="utf-8")

    kb = Path(args.kb_file).read_text(encoding="utf-8") if args.kb_file else ""
    policies = Path(args.policy_file).read_text(encoding="utf-8") if args.policy_file else ""

    result = run_pipeline(ticket, kb, policies, provider=args.provider)
    if result:
        save_output(result)
        if result.escalation.required:
            print(f"\n⚠️  ESCALATION REQUIRED → {result.escalation.team}: {result.escalation.reason}")
        else:
            print("\n✅ Resolution ready to send.")


if __name__ == "__main__":
    main()
