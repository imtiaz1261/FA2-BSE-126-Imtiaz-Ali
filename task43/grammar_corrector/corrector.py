"""
Core grammar/spelling correction logic — separated from the CLI so it
can be reused, tested, or wrapped in a different interface later.
"""

import sys
import json
import re
from openai import OpenAI
from config import LLM_PROVIDER, GROQ_API_KEY, OPENAI_API_KEY, MODEL_NAME


class CorrectionError(Exception):
    """Raised when a grammar-correction request fails or returns unusable output."""


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


SYSTEM_PROMPT = """You are a professional grammar and spelling correction assistant.

Given a paragraph of text, correct all grammar, spelling, and punctuation
mistakes without changing the meaning, tone, or style more than necessary.

Respond with ONLY a valid JSON object, no markdown code fences, no extra
commentary, in exactly this shape:

{
  "corrected_text": "the fully corrected paragraph",
  "changes": [
    "short description of change 1",
    "short description of change 2"
  ]
}

Keep each entry in "changes" short (under 15 words) — a brief note of
what was fixed, e.g. "Fixed subject-verb agreement in sentence 2" or
"Corrected spelling: 'recieve' to 'receive'". If no changes were needed,
return an empty list for "changes".
"""


def correct_text(client: OpenAI, text: str) -> dict:
    """
    Correct grammar/spelling in `text` and return a dict:
        {"corrected_text": str, "changes": list[str]}

    Raises CorrectionError on empty input, API failure, or if the model's
    response can't be parsed as the expected JSON shape.
    """
    if not text or not text.strip():
        raise CorrectionError("Input text cannot be empty.")

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.2,  # low temperature: consistent corrections, not rewrites
        )
        raw = response.choices[0].message.content.strip()
    except Exception as e:
        raise CorrectionError(f"Correction request failed: {e}") from e

    return _parse_response(raw)


def _parse_response(raw: str) -> dict:
    """
    Parse the model's JSON response, tolerating common formatting quirks
    (e.g. accidental ```json fences) before giving up.
    """
    cleaned = raw.strip()
    # Strip markdown code fences if the model added them despite instructions.
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise CorrectionError(
            f"Could not parse model response as JSON: {e}\nRaw response: {raw}"
        ) from e

    if "corrected_text" not in data:
        raise CorrectionError(f"Model response missing 'corrected_text' field: {data}")

    corrected_text = data.get("corrected_text", "")
    changes = data.get("changes", [])
    if not isinstance(changes, list):
        changes = [str(changes)]

    return {"corrected_text": corrected_text, "changes": changes}
