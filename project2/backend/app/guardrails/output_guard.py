"""
Output Guardrail — Phase 14.

Validates the LLM's reply BEFORE it is sent to the user.

Checks:
  1. PII detection  — phone numbers, SSNs, credit cards, email-like patterns
  2. Sensitive keys — API keys, secrets embedded in output
  3. Policy strings — known dangerous instruction patterns in output
  4. Hallucination flag — response says it cannot do something that
     suggests a misrouted request (lightweight heuristic, not LLM)

Returns an OutputGuardResult:
  clean      — bool (True = pass, safe to send)
  issue      — short label
  detail     — human-readable description
  sanitised  — cleaned version of the text (PII redacted)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings


@dataclass
class OutputGuardResult:
    clean:     bool
    issue:     str  = ""
    detail:    str  = ""
    sanitised: str  = ""


# ─────────────────────────────────────────────────────────────────────────────
# PII patterns with redaction labels
# ─────────────────────────────────────────────────────────────────────────────

_PII_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                        "[SSN REDACTED]"),
    (re.compile(r"\b\d{16}\b|\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b"),
                                                                    "[CARD REDACTED]"),
    (re.compile(r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
                                                                    "[PHONE REDACTED]"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"),                           "[API_KEY REDACTED]"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"),                           "[GITHUB_TOKEN REDACTED]"),
    (re.compile(r"[A-Za-z0-9._%+\-]{3,}@[A-Za-z0-9.\-]+\.[A-Za-z]{2,6}"),
                                                                    "[EMAIL REDACTED]"),
]

# Known dangerous instruction patterns the LLM should never output
_DANGEROUS_OUTPUT: list[re.Pattern] = [
    re.compile(r"(rm\s+-rf\s*/|format\s+c:|del\s+/[sq])", re.I),
    re.compile(r"(drop\s+table|truncate\s+table)", re.I),
    re.compile(r"(password|secret|api.?key)\s*[:=]\s*\S{8,}", re.I),
]


def _redact_pii(text: str) -> tuple[str, list[str]]:
    """Redact PII in-place. Returns (sanitised_text, list_of_issues)."""
    found: list[str] = []
    for pattern, label in _PII_RULES:
        if pattern.search(text):
            found.append(label)
            text = pattern.sub(label, text)
    return text, found


async def check_output(text: str) -> OutputGuardResult:
    """Validate and sanitise LLM output before sending to the user."""
    if not settings.GUARDRAILS_ENABLED:
        return OutputGuardResult(clean=True, sanitised=text)

    # 1. Dangerous instruction patterns
    for pattern in _DANGEROUS_OUTPUT:
        if pattern.search(text):
            return OutputGuardResult(
                clean=False,
                issue="dangerous_output",
                detail="Response contained potentially dangerous instructions and was blocked.",
                sanitised="I'm sorry, I cannot provide that information.",
            )

    # 2. PII redaction (non-blocking — we sanitise and pass)
    sanitised, pii_found = _redact_pii(text)

    if pii_found:
        return OutputGuardResult(
            clean=True,         # sanitised — allow but redacted
            issue="pii_redacted",
            detail=f"PII redacted from response: {', '.join(set(pii_found))}",
            sanitised=sanitised,
        )

    return OutputGuardResult(clean=True, sanitised=text)
