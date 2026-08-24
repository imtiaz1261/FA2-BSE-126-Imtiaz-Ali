"""
ai/guardrails/input_guard.py — Input Guardrail
================================================
Screens every user message BEFORE sending it to the LLM.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GuardResult:
    safe: bool
    reason: str = ""
    check: str = ""
    metadata: dict = field(default_factory=dict)


_INJECTION_PATTERNS = [
    r"ignore\s+(all|previous|above|prior|every)(\s+\w+)?\s*(instructions?|prompts?|rules?|constraints?)",
    r"disregard\s+(your\s+)?(all\s+|previous\s+|the\s+)?(instructions?|prompts?|guidelines?|rules?|training)",
    r"forget\s+(everything|all|previous)(\s+\w+)?\s*(instructions?|you|above)",
    r"you\s+are\s+now\s+(?:a|an|the)\s+\w",
    r"new\s+(instructions?|rules?|persona|role|objective)\s*[:.]",
    r"system\s*prompt\s*[:=]",
    r"<\s*/?system\s*>",
    r"\[INST\]|\[\/INST\]",
    r"###\s*(instruction|system|human|assistant)\s*:",
    r"override\s+(your\s+)?(instructions?|guidelines?|rules?|training)",
    r"from\s+now\s+on\s+(you|ignore|forget|act)",
    r"bypass\s+(your\s+)?(safety|guidelines?|instructions?|restrictions?)",
]

_JAILBREAK_PATTERNS = [
    r"\bdan\b.{0,20}(mode|prompt|jailbreak)",
    r"developer\s+mode",
    r"\bjailbreak\b",
    r"do\s+anything\s+now",
    r"pretend\s+(you\s+are|to\s+be)\s+(not|no\s+longer)\s+an?\s+ai",
    r"act\s+as\s+if\s+you\s+(have\s+no|don.t\s+have|without)\s+(restrictions?|limits?|guidelines?)",
    r"unrestricted\s+ai",
    r"evil\s+(mode|version|ai|bot)",
    r"uncensored\s+(mode|version|response)",
]

_SYSTEM_EXTRACTION_PATTERNS = [
    r"(print|show|reveal|display|output|repeat|tell\s+me)\s+(your|the)\s+(system\s+prompt|instructions|rules|guidelines|context)",
    r"what\s+(are\s+your|is\s+your)\s+(system\s+prompt|instructions|initial\s+prompt|guidelines)",
    r"(show|tell|print|output)\s+me\s+(the\s+|your\s+)?(system|initial|original)\s+prompt",
    r"show\s+me\s+your\s+(system\s+prompt|instructions|guidelines|rules|context|training)",
    r"what\s+(does\s+your|are\s+your|is\s+your)\s+(system|initial)\s+(prompt|instruction)",
    r"(ignore|skip|bypass)\s+your\s+(system\s+prompt|instructions|guidelines)",
    r"translate\s+your\s+(system\s+prompt|instructions)\s+(to|into)",
]

_HARMFUL_PATTERNS = [
    r"how\s+to\s+(make|build|create|synthesize)\s+(bomb|weapon|explosive|poison|drug|meth|fentanyl)",
    r"kill\s+(yourself|myself)|suicide\s+method|how\s+to\s+die",
    r"child\s+(porn|pornography|sexual|nude)|csam",
    r"hack\s+(into|someone|their)|ransomware\s+code",
]

_PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"\b\d{16}\b", "credit_card"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone"),
]


def _matches_any(text: str, patterns: list[str]) -> str | None:
    tl = text.lower()
    for p in patterns:
        if re.search(p, tl, re.IGNORECASE | re.DOTALL):
            return p
    return None


def check_input(message: str, max_length: int = 32_000) -> GuardResult:
    """Run all input checks. Returns GuardResult(safe=True) if message passes."""
    if len(message) > max_length:
        logger.warning("input_guard_length", chars=len(message))
        return GuardResult(safe=False, check="length",
                           reason=f"Message exceeds {max_length:,} characters.")

    hit = _matches_any(message, _INJECTION_PATTERNS)
    if hit:
        logger.warning("input_guard_injection", pattern=hit[:60])
        return GuardResult(safe=False, check="prompt_injection",
                           reason="Your message contains prompt injection instructions. Please rephrase.")

    hit = _matches_any(message, _JAILBREAK_PATTERNS)
    if hit:
        logger.warning("input_guard_jailbreak", pattern=hit[:60])
        return GuardResult(safe=False, check="jailbreak",
                           reason="Your message contains jailbreak patterns and cannot be processed.")

    hit = _matches_any(message, _SYSTEM_EXTRACTION_PATTERNS)
    if hit:
        logger.warning("input_guard_extraction", pattern=hit[:60])
        return GuardResult(safe=False, check="system_extraction",
                           reason="Requests to reveal system instructions are not permitted.")

    hit = _matches_any(message, _HARMFUL_PATTERNS)
    if hit:
        logger.warning("input_guard_harmful", pattern=hit[:60])
        return GuardResult(safe=False, check="harmful_content",
                           reason="Your message violates our usage policy and cannot be processed.")

    pii_found = [pii_type for pattern, pii_type in _PII_PATTERNS if re.search(pattern, message)]
    if pii_found:
        logger.info("input_guard_pii_detected", types=pii_found)

    return GuardResult(safe=True, metadata={"pii_detected": pii_found} if pii_found else {})
