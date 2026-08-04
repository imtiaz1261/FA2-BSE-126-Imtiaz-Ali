import re
from app.services.token_tracker import count_tokens

_FILLER_PATTERNS = [
    r"\bplease note that\b", r"\bkindly\b", r"\bi would like to\b",
    r"\bcould you please\b", r"\bin order to\b", r"\bas an ai\b",
    r"\bfeel free to\b", r"\bit is important to note that\b",
]


def optimize_prompt(prompt: str) -> dict:
    """
    Trims redundant filler and collapses whitespace/duplicate lines without
    changing the user's actual request. This does NOT summarize or rewrite
    the semantic content — only removes verbosity that costs tokens for free.
    """
    original_tokens = count_tokens(prompt)
    text = prompt

    for pattern in _FILLER_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Collapse repeated whitespace/newlines.
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Drop exact duplicate lines (common with pasted repeated context).
    seen = set()
    lines = []
    for line in text.split("\n"):
        key = line.strip().lower()
        if key and key in seen:
            continue
        seen.add(key)
        lines.append(line)
    text = "\n".join(lines).strip()

    optimized_tokens = count_tokens(text)
    reduction_pct = (
        round((1 - optimized_tokens / original_tokens) * 100, 2)
        if original_tokens else 0.0
    )

    return {
        "optimized_prompt": text,
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "tokens_saved": original_tokens - optimized_tokens,
        "reduction_pct": reduction_pct,
    }
