"""Bookkeeping Agent — Categorize, reconcile, and organize financial data.

2-step pipeline:
    1. Accountant Agent — categorizes transactions, reconciles, assesses tax
    2. QA Agent — validates math accuracy, completeness, and accounting standards

Handles: invoices, receipts, bank statements, expense reports, tax prep,
         budget vs actual analysis, chart of accounts mapping.

Usage:
    python -m agents.bookkeeping.runner --file bank_statement.csv --task categorize
    python -m agents.bookkeeping.runner --file expenses.txt --task expense_report
    python -m agents.bookkeeping.runner --text "..." --task invoice_process
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
call_llm = make_bridge("bookkeeping")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "bookkeeping"


# ── Pydantic Models ────────────────────────────────────────────

class Transaction(BaseModel):
    date: str = ""
    description: str = ""
    amount: float = 0.0
    category: str = ""
    account: str = ""
    vendor: str = ""
    payment_method: str = ""
    tax_deductible: bool = False
    tax_category: str = ""
    receipt_reference: str = ""
    notes: str = ""


class FinancialSummary(BaseModel):
    total_income: float = 0.0
    total_expenses: float = 0.0
    net_income: float = 0.0
    by_category: dict = Field(default_factory=dict)
    by_account: dict = Field(default_factory=dict)


class Reconciliation(BaseModel):
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    unreconciled_items: list = Field(default_factory=list)
    discrepancies: list = Field(default_factory=list)


class TaxRelevant(BaseModel):
    deductible_expenses: float = 0.0
    non_deductible: float = 0.0
    tax_categories: dict = Field(default_factory=dict)
    notes: str = ""


class AccountantOutput(BaseModel):
    task_type: str = ""
    period: str = ""
    currency: str = "USD"
    transactions: list[Transaction] = Field(default_factory=list)
    summary: FinancialSummary = Field(default_factory=FinancialSummary)
    reconciliation: Reconciliation = Field(default_factory=Reconciliation)
    tax_relevant: TaxRelevant = Field(default_factory=TaxRelevant)
    action_items: list[str] = Field(default_factory=list)


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class BookkeepingOutput(BaseModel):
    accounting: AccountantOutput = Field(default_factory=AccountantOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def accountant_agent(
    financial_data: str,
    task_type: str = "categorize",
    chart_of_accounts: str = "",
    currency: str = "USD",
    rules: str = "",
    provider: str = "openai",
) -> AccountantOutput:
    """Step 1: Process financial data."""
    system = _load_prompt("accountant_prompt")
    user_msg = (
        f"Task Type: {task_type}\n"
        f"Currency: {currency}\n"
        f"Chart of Accounts: {chart_of_accounts or 'Use standard chart'}\n"
        f"Rules: {rules or 'Standard bookkeeping rules'}\n\n"
        f"Financial Data:\n{financial_data}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return AccountantOutput(**json.loads(raw))


def qa_agent(accounting: AccountantOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate financial processing accuracy."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Financial output to validate:\n{json.dumps(accounting.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    financial_data: str,
    task_type: str = "categorize",
    chart_of_accounts: str = "",
    currency: str = "USD",
    provider: str = "openai",
    max_retries: int = 2,
) -> BookkeepingOutput:
    """Run the full bookkeeping pipeline: Accountant → QA."""
    print(f"\n[BOOKKEEPING] Starting pipeline — {task_type}")
    print(f"  Currency: {currency} | Provider: {provider}")

    # Step 1: Process
    print("\n  [1/2] Processing financial data...")
    accounting = accountant_agent(financial_data, task_type,
                                   chart_of_accounts, currency, "", provider)
    print(f"  → {len(accounting.transactions)} transactions processed")
    print(f"  → Net income: {currency} {accounting.summary.net_income:,.2f}")

    # Step 2: QA (with retries)
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(accounting, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print(f"  → Reprocessing with revision notes...")
            accounting = accountant_agent(
                financial_data, task_type, chart_of_accounts, currency,
                f"QA REVISION:\n{qa.revision_notes}", provider)

    output = BookkeepingOutput(
        accounting=accounting,
        qa=qa,
        meta={
            "task_type": task_type,
            "currency": currency,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: BookkeepingOutput) -> Path:
    """Save pipeline output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"books_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Bookkeeping Agent")
    parser.add_argument("--text", default="", help="Financial data as text")
    parser.add_argument("--file", default="", help="File containing financial data")
    parser.add_argument("--task", default="categorize",
                        choices=["categorize", "reconcile", "expense_report",
                                 "invoice_process", "bank_statement", "tax_prep",
                                 "budget_vs_actual"])
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file")
        sys.exit(1)

    result = run_pipeline(
        financial_data=data,
        task_type=args.task,
        currency=args.currency,
        provider=args.provider,
    )
    save_output(result)
