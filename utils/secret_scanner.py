"""Secret scanner — Phase 6 Security.

Scans text for leaked credentials, API keys, tokens, and PII.
Used by the QA pipeline (QA-012: no_pii_in_output) and as a
standalone CLI tool for auditing content before delivery.

Usage:
    from utils.secret_scanner import scan_text, mask_secrets
    findings = scan_text(text)
    safe_text = mask_secrets(text)

    # Nightly log scan (prod)
    python utils/secret_scanner.py --scan-logs
"""
import logging
import re
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger("utils.secret_scanner")


class Finding(NamedTuple):
    type: str
    pattern_name: str
    position: int
    length: int
    masked_sample: str


# ── Pattern definitions ──────────────────────────────────────────────────────

_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    # (type, pattern_name, compiled_regex)
    ("api_key", "openai_key",      re.compile(r"sk-[A-Za-z0-9]{32,}", re.ASCII)),
    ("api_key", "anthropic_key",   re.compile(r"sk-ant-[A-Za-z0-9\-_]{32,}", re.ASCII)),
    ("api_key", "google_api_key",  re.compile(r"AIza[0-9A-Za-z\-_]{35}", re.ASCII)),
    ("api_key", "stripe_secret",   re.compile(r"sk_(?:live|test)_[0-9a-zA-Z]{24,}", re.ASCII)),
    ("api_key", "stripe_public",   re.compile(r"pk_(?:live|test)_[0-9a-zA-Z]{24,}", re.ASCII)),
    ("api_key", "generic_bearer",  re.compile(r"Bearer\s+[A-Za-z0-9\-_\.]{20,}", re.ASCII)),
    ("api_key", "github_pat",      re.compile(r"ghp_[A-Za-z0-9]{36}", re.ASCII)),
    ("api_key", "github_oauth",    re.compile(r"gho_[A-Za-z0-9]{36}", re.ASCII)),
    ("credential", "password_kv",  re.compile(r'(?i)(?:password|passwd|secret|api_?key|token)\s*[=:]\s*["\']?[^\s"\']{8,}["\']?')),
    ("credential", "aws_access",   re.compile(r"AKIA[0-9A-Z]{16}", re.ASCII)),
    ("credential", "private_key",  re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
    ("pii", "email_address",       re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")),
    ("pii", "us_phone",            re.compile(r"(?:\+1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}")),
    ("pii", "credit_card",         re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b")),
    ("pii", "ssn",                 re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
]


def scan_text(text: str) -> list[Finding]:
    """Scan text for secrets, credentials, and PII.

    Args:
        text: Raw text to scan.

    Returns:
        List of Finding namedtuples with type, pattern_name, position, length, masked_sample.
    """
    findings: list[Finding] = []
    for secret_type, pattern_name, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group()
            # Mask: keep first 4 and last 2 chars, replace middle with ***
            if len(raw) > 10:
                masked = raw[:4] + "***" + raw[-2:]
            else:
                masked = raw[:2] + "***"
            findings.append(Finding(
                type=secret_type,
                pattern_name=pattern_name,
                position=match.start(),
                length=len(raw),
                masked_sample=masked,
            ))
    if findings:
        logger.critical("[SECRET_LEAK_DETECTED] %d secret(s) found: %s",
                        len(findings), ", ".join(f.pattern_name for f in findings))
    return findings


def mask_secrets(text: str) -> str:
    """Return a copy of text with all detected secrets masked as [REDACTED]."""
    # Collect all match spans sorted by position descending (to preserve offsets)
    spans: list[tuple[int, int]] = []
    for _, _, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end()))

    # Sort descending so we can splice without offset drift
    spans.sort(key=lambda s: s[0], reverse=True)

    # Deduplicate overlapping spans
    deduped: list[tuple[int, int]] = []
    for start, end in spans:
        if deduped and start < deduped[-1][1]:
            continue  # overlaps with previous span
        deduped.append((start, end))

    result = list(text)
    for start, end in deduped:
        result[start:end] = list("[REDACTED]")

    return "".join(result)


def has_secrets(text: str) -> bool:
    """Quick check — returns True if any secret/PII pattern is found."""
    return any(pat.search(text) for _, _, pat in _PATTERNS)


def scan_log_files(log_dir: Path | None = None) -> dict:
    """Nightly scan of JSONL log files for leaked secrets.

    Returns dict with total_findings and per-file breakdown.
    """
    if log_dir is None:
        log_dir = Path(__file__).resolve().parent.parent / "kpi" / "logs"
    if not log_dir.exists():
        return {"scanned": 0, "total_findings": 0, "files": {}}

    total = 0
    file_results: dict[str, list[dict]] = {}
    scanned = 0

    for log_file in sorted(log_dir.glob("*.jsonl")):
        scanned += 1
        text = log_file.read_text(encoding="utf-8", errors="replace")
        findings = scan_text(text)
        if findings:
            file_results[log_file.name] = [f._asdict() for f in findings]
            total += len(findings)

    result = {"scanned": scanned, "total_findings": total, "files": file_results}
    if total > 0:
        logger.critical("[SECRET_LEAK_DETECTED] Nightly scan: %d leak(s) in %d file(s)",
                        total, len(file_results))
    else:
        logger.info("[SECRET_SCAN] Nightly scan clean: %d files checked", scanned)
    return result


if __name__ == "__main__":
    import json
    import sys

    if "--scan-logs" in sys.argv:
        report = scan_log_files()
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["total_findings"] == 0 else 1)

    if len(sys.argv) > 1 and sys.argv[1] != "--scan-logs":
        sample = " ".join(sys.argv[1:])
    else:
        sample = "Contact me at user@example.com, key=sk-abc123XYZabc123XYZabc123XYZabc123"

    results = scan_text(sample)
    if results:
        print(json.dumps([r._asdict() for r in results], indent=2))
    else:
        print("No secrets detected.")
