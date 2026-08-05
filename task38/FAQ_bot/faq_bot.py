"""faq_bot.py — Answers user questions by finding the best matching FAQ
using difflib's similarity matching. If no FAQ is similar enough, falls
back to asking the LLM for a generic answer instead.

Run:
    python faq_bot.py
"""

from __future__ import annotations

import argparse
import difflib
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

try:
    from secret_key import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = None

FAQ_FILE = Path("faqs.txt")
MODEL_NAME = "llama-3.3-70b-versatile"

# Below this similarity score (0-1), we consider no FAQ a good enough
# match, and fall back to the LLM instead of returning a wrong answer.
SIMILARITY_THRESHOLD = 0.45


@dataclass
class FAQ:
    question: str
    answer: str


def load_faqs(path: Path) -> list[FAQ]:
    """Parses the FAQ text file into a list of FAQ objects.

    Expected format: alternating "Q: ..." / "A: ..." lines, one pair per
    block, blank lines between blocks (see faqs.txt).
    """
    if not path.exists():
        raise FileNotFoundError(f"FAQ file not found: {path}")

    text = path.read_text(encoding="utf-8")
    faqs: list[FAQ] = []

    current_question: str | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Q:"):
            current_question = line[2:].strip()
        elif line.startswith("A:") and current_question is not None:
            faqs.append(FAQ(question=current_question, answer=line[2:].strip()))
            current_question = None

    if not faqs:
        raise ValueError(f"No valid Q:/A: pairs found in {path}")

    return faqs


# Words with little discriminating value for matching — stripping these
# prevents unrelated questions from matching just because they share
# common phrasing like "how can I" or "what is".
STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "am", "be", "been", "being",
    "how", "what", "when", "where", "why", "who", "which",
    "can", "could", "would", "should", "do", "does", "did",
    "i", "you", "your", "my", "me", "we", "our",
    "to", "of", "in", "on", "at", "for", "with", "and", "or",
    "get", "have", "has", "will",
})


def _extract_keywords(text: str) -> str:
    """Removes stopwords, keeping only the words that actually carry
    meaning — this is what makes matching behave like keyword matching
    rather than being thrown off by shared filler phrases."""
    words = text.lower().replace("?", "").replace(",", "").split()
    keywords = [w for w in words if w not in STOPWORDS]
    return " ".join(keywords) if keywords else text.lower()


def find_best_match(user_question: str, faqs: list[FAQ]) -> tuple[FAQ | None, float]:
    """Finds the FAQ whose question is most similar to the user's
    question, using difflib.SequenceMatcher on KEYWORDS (stopwords
    stripped from both sides first) rather than raw text — this avoids
    two unrelated questions matching just because they share common
    words like "how can I" or "what is".

    Returns (best_faq, similarity_score). best_faq is None if the best
    score is still below SIMILARITY_THRESHOLD.
    """
    if not faqs:
        return None, 0.0

    best_faq: FAQ | None = None
    best_score = 0.0

    user_keywords = _extract_keywords(user_question.strip())

    for faq in faqs:
        faq_keywords = _extract_keywords(faq.question)
        score = difflib.SequenceMatcher(None, user_keywords, faq_keywords).ratio()
        if score > best_score:
            best_score = score
            best_faq = faq

    if best_score < SIMILARITY_THRESHOLD:
        return None, best_score

    return best_faq, best_score


def get_llm_fallback_answer(client: OpenAI, user_question: str) -> str:
    """Asks the LLM for a generic answer when no FAQ matches well
    enough."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful customer support assistant. "
                    "Answer the user's question concisely and politely. "
                    "If you don't have enough context to answer accurately, "
                    "say so honestly rather than guessing."
                ),
            },
            {"role": "user", "content": user_question},
        ],
    )
    return response.choices[0].message.content.strip()


def answer_question(
    user_question: str, faqs: list[FAQ], client: OpenAI | None
) -> tuple[str, str]:
    """Returns (answer, source) where source is 'faq' or 'llm_fallback'."""
    best_faq, score = find_best_match(user_question, faqs)

    if best_faq is not None:
        return best_faq.answer, f"faq (matched: \"{best_faq.question}\", similarity={score:.2f})"

    if client is None:
        return (
            "No matching FAQ found, and no LLM is configured for a fallback answer.",
            "none",
        )

    answer = get_llm_fallback_answer(client, user_question)
    return answer, f"llm_fallback (best FAQ similarity was only {score:.2f})"


def build_llm_client() -> OpenAI | None:
    if not GROQ_API_KEY or "your-groq-key-here" in GROQ_API_KEY:
        return None
    return OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FAQ bot with difflib matching + LLM fallback")
    parser.add_argument("--question", help="Ask a single question and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    faqs = load_faqs(FAQ_FILE)
    client = build_llm_client()

    if client is None:
        print("[Warning] No Groq API key configured — LLM fallback will be unavailable.\n")

    if args.question:
        answer, source = answer_question(args.question, faqs, client)
        print(f"Q: {args.question}")
        print(f"A: {answer}")
        print(f"(source: {source})")
        return

    print(f"FAQ bot ready — {len(faqs)} FAQs loaded. Type 'exit' or 'quit' to leave.\n")
    while True:
        try:
            user_question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_question:
            continue
        if user_question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        answer, source = answer_question(user_question, faqs, client)
        print(f"Bot: {answer}")
        print(f"     (source: {source})\n")


if __name__ == "__main__":
    main()
