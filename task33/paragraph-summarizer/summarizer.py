"""
summarizer.py
-------------
Core summarization logic: always exactly 3 lines, with a length
control (short / medium / long) that changes how much detail each
line carries -- not how many lines there are.
"""

from config import GROQ_API_KEY, GROQ_MODEL

LENGTH_PRESETS = {
    "short": "very brief -- around 6-10 words per line, key words only",
    "medium": "a full sentence per line -- around 12-18 words per line",
    "long": "a detailed sentence per line -- around 20-30 words per line",
}


class SummarizerError(Exception):
    """Raised for missing config or a failed API call."""


def summarize(paragraph: str, length: str = "medium") -> str:
    """
    Summarize `paragraph` into exactly 3 lines using Groq.

    Parameters
    ----------
    paragraph : the text to summarize
    length    : "short", "medium", or "long" -- controls detail per line

    Returns
    -------
    str -- the 3-line summary
    """
    if not paragraph or not paragraph.strip():
        raise SummarizerError("Please paste a paragraph to summarize.")

    length = (length or "medium").lower()
    if length not in LENGTH_PRESETS:
        raise SummarizerError(f"Invalid length '{length}'. Choose short, medium, or long.")

    if not GROQ_API_KEY:
        raise SummarizerError(
            "GROQ_API_KEY is missing from your .env file. Get a free key at "
            "https://console.groq.com/keys and add it as GROQ_API_KEY=... "
            "in your local .env file."
        )

    try:
        from groq import Groq
    except ImportError as exc:
        raise SummarizerError("The groq package is not installed. Run: pip install groq") from exc

    client = Groq(api_key=GROQ_API_KEY)

    prompt = (
        "Summarize the following paragraph in EXACTLY 3 lines -- one key "
        "idea per line, no numbering, no bullets, no headers. "
        f"Each line should be {LENGTH_PRESETS[length]}. "
        "Use only information present in the paragraph; do not add outside "
        "knowledge or invent facts.\n\n"
        f"Paragraph:\n{paragraph.strip()}\n\n"
        "3-line summary:"
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
    except Exception as exc:
        raise SummarizerError(f"Summarization request failed: {exc}") from exc

    summary = (response.choices[0].message.content or "").strip()
    if not summary:
        raise SummarizerError("The model returned an empty summary. Please try again.")
    return summary
