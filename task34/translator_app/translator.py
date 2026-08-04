"""
Core translation logic — separated from the CLI so it can be reused,
tested, or wrapped in a different interface (web app, API, etc.) later.
"""

import sys
from openai import OpenAI
from config import LLM_PROVIDER, GROQ_API_KEY, OPENAI_API_KEY, MODEL_NAME

# A curated list of common target languages. Not exhaustive — the LLM can
# usually handle languages outside this list too, but offering a menu
# keeps the UX simple and avoids typos in language names.
SUPPORTED_LANGUAGES = [
    "Hindi",
    "French",
    "Spanish",
    "German",
    "Arabic",
    "Chinese",
    "Japanese",
    "Urdu",
    "Portuguese",
    "Russian",
]


class TranslationError(Exception):
    """Raised when a translation request fails."""


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


def translate(client: OpenAI, text: str, target_language: str) -> str:
    """
    Translate `text` into `target_language` using the LLM.

    Uses a system prompt that constrains the model to return only the
    translation — no explanations, no quotes, no extra commentary — so
    the output is clean and predictable for downstream use.
    """
    if not text or not text.strip():
        raise TranslationError("Input text cannot be empty.")
    if not target_language or not target_language.strip():
        raise TranslationError("Target language cannot be empty.")

    system_prompt = (
        "You are a professional translator. Translate the user's text into "
        f"{target_language.strip()}. "
        "Return ONLY the translated text, with no explanations, no quotation "
        "marks, and no additional commentary."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.3,  # lower temperature = more literal, consistent translations
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise TranslationError(f"Translation request failed: {e}") from e
