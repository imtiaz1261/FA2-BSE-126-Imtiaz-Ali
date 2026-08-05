"""
Core sentiment classification logic — separated from the CLI so it can be
reused, tested, or wrapped in a different interface later.
"""

import sys
from openai import OpenAI
from config import LLM_PROVIDER, GROQ_API_KEY, OPENAI_API_KEY, MODEL_NAME

VALID_LABELS = ("Positive", "Negative", "Neutral")


class ClassificationError(Exception):
    """Raised when a sentiment classification request fails."""


def get_client() -> OpenAI:
    """Build an OpenAI-compatible client pointed at the configured provider."""
    if LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            sys.exit(
                "ERROR: GROQ_API_KEY is missing.\n"
                "Get a free key at https://console.groq.com/keys and add it "
                "to your .env file (GROQ_API_KEY=...)."
            )
        return OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            sys.exit(
                "ERROR: OPENAI_API_KEY is missing.\n"
                "Add it to your .env file, or set LLM_PROVIDER=groq to use "
                "the free Groq API instead."
            )
        return OpenAI(api_key=OPENAI_API_KEY)

    sys.exit(f"ERROR: Unknown LLM_PROVIDER '{LLM_PROVIDER}'. Use 'groq' or 'openai'.")


def classify_review(client: OpenAI, review_text: str) -> str:
    """
    Classify a single review as Positive, Negative, or Neutral using the LLM.

    Uses a constrained system prompt so the model returns exactly one of
    the three labels, with no extra commentary — this keeps the output
    reliable enough to parse and put straight into a table.
    """
    if not review_text or not review_text.strip():
        raise ClassificationError("Review text cannot be empty.")

    system_prompt = (
        "You are a sentiment classification assistant. Classify the "
        "customer review the user gives you as exactly one of these three "
        "words: Positive, Negative, or Neutral. "
        "Respond with ONLY that single word — no punctuation, no "
        "explanation, no extra text."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": review_text},
            ],
            temperature=0,  # deterministic classification, not creative output
        )
        label = response.choices[0].message.content.strip()
    except Exception as e:
        raise ClassificationError(f"Classification request failed: {e}") from e

    return _normalize_label(label)


def _normalize_label(raw_label: str) -> str:
    """
    Map the model's raw output onto one of the three canonical labels.
    Models occasionally add punctuation or slightly different casing
    ("positive.", "NEGATIVE") — this normalizes that instead of failing.
    """
    cleaned = raw_label.strip().strip(".").strip().capitalize()
    if cleaned in VALID_LABELS:
        return cleaned

    lowered = cleaned.lower()
    for label in VALID_LABELS:
        if label.lower() in lowered:
            return label

    # Model returned something unexpected — surface it rather than
    # silently guessing wrong.
    raise ClassificationError(
        f"Unrecognized sentiment label returned by the model: '{raw_label}'"
    )


def classify_reviews(client: OpenAI, reviews: list[str]) -> list[dict]:
    """
    Classify a list of reviews and return structured results, one dict
    per review, suitable for direct use in a table.
    """
    results = []
    for review in reviews:
        try:
            label = classify_review(client, review)
            error = None
        except ClassificationError as e:
            label = "ERROR"
            error = str(e)
        results.append({"review": review, "sentiment": label, "error": error})
    return results
