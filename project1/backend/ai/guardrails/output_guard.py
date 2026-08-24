"""
ai/guardrails/output_guard.py — Output Guardrail
==================================================
Validates LLM responses BEFORE returning them to the user.

Checks:
1. Prompt leakage     — response contains system prompt fragments
2. PII in response    — response includes credit cards, SSNs, etc.
3. Harmful content    — dangerous instructions in the response
4. Refusal markers    — model says it can't help (pass through with flag)
5. Empty response     — blank or whitespace-only output

Safe fallback is returned when the response fails any check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from backend.core.logging import get_logger

logger = get_logger(__name__)

SAFE_FALLBACK = (
    "I'm sorry, but I'm unable to provide a response to that request. "
    "Please try rephrasing your question."
)


@dataclass
class OutputGuardResult:
    safe: bool
    content: str           # Either original content or the fallback
    check: str = ""
    reason: str = ""
    metadata: dict = field(default_factory=dict)


_LEAK_PATTERNS = [
    r"you\s+are\s+(a\s+helpful|an?\s+ai)\s+assistant\s+called",
    r"your\s+system\s+prompt\s+(is|says|states)",
    r"<system>|</system>",
    r"\[system\]|\[\/system\]",
    r"###\s*system\s*:",
]

_HARMFUL_OUTPUT_PATTERNS = [
    r"(step\s+\d+.{0,50})?(how\s+to\s+(make|build|synthesize)\s+(bomb|weapon|explosive|meth|fentanyl))",
    r"(here\s+(is|are)\s+the\s+instructions?\s+to.{0,40}(kill|harm|attack))",
    r"(child\s+(porn|sexual|nude))",
]

_PII_RESPONSE_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b", "credit_card"),
]

_REFUSAL_MARKERS = [
    r"i\s+(can.t|cannot|am\s+not\s+able\s+to|am\s+unable\s+to)\s+(help|assist|provide|generate|create)",
    r"i\s+must\s+(decline|refuse)",
    r"(this\s+request\s+(violates|is\s+against)|i\s+won.t\s+help\s+with)",
]


def check_output(content: str) -> OutputGuardResult:
    """
    Validate LLM output before sending to the user.

    Args:
        content: The raw LLM response string.

    Returns:
        OutputGuardResult — safe=True passes original content through,
        safe=False replaces with SAFE_FALLBACK.
    """
    # 1. Empty response
    if not content or not content.strip():
        logger.warning("output_guard_empty_response")
        return OutputGuardResult(
            safe=False,
            content="I wasn't able to generate a response. Please try again.",
            check="empty",
            reason="Empty response from LLM",
        )

    tl = content.lower()

    # 2. Prompt leakage
    for pattern in _LEAK_PATTERNS:
        if re.search(pattern, tl, re.IGNORECASE):
            logger.warning("output_guard_prompt_leak", pattern=pattern[:60])
            return OutputGuardResult(
                safe=False,
                content=SAFE_FALLBACK,
                check="prompt_leak",
                reason="Response may contain system prompt content",
            )

    # 3. Harmful output
    for pattern in _HARMFUL_OUTPUT_PATTERNS:
        if re.search(pattern, tl, re.IGNORECASE | re.DOTALL):
            logger.warning("output_guard_harmful", pattern=pattern[:60])
            return OutputGuardResult(
                safe=False,
                content=SAFE_FALLBACK,
                check="harmful_content",
                reason="Response contains potentially harmful content",
            )

    # 4. PII in response — replace with placeholder
    cleaned = content
    pii_found = []
    for pattern, pii_type in _PII_RESPONSE_PATTERNS:
        if re.search(pattern, cleaned):
            cleaned = re.sub(pattern, f"[{pii_type} REDACTED]", cleaned)
            pii_found.append(pii_type)

    if pii_found:
        logger.warning("output_guard_pii_redacted", types=pii_found)
        return OutputGuardResult(
            safe=True,            # still passes but with redaction
            content=cleaned,
            check="pii_redacted",
            reason=f"PII redacted from response: {pii_found}",
            metadata={"pii_redacted": pii_found},
        )

    # 5. Refusal marker — pass through but flag it
    for pattern in _REFUSAL_MARKERS:
        if re.search(pattern, tl, re.IGNORECASE):
            return OutputGuardResult(
                safe=True,
                content=content,
                check="model_refusal",
                metadata={"model_refused": True},
            )

    return OutputGuardResult(safe=True, content=content)
