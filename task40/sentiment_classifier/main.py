"""
Runs sentiment classification over a set of customer reviews and prints
the results as a formatted table.

Usage:
    python main.py
"""

from tabulate import tabulate
from classifier import get_client, classify_reviews
from data.reviews import SAMPLE_REVIEWS
from config import MODEL_NAME, LLM_PROVIDER

MAX_REVIEW_DISPLAY_LENGTH = 60


def truncate(text: str, max_len: int = MAX_REVIEW_DISPLAY_LENGTH) -> str:
    """Shorten long review text for clean table display."""
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def print_summary(results: list[dict]):
    counts = {"Positive": 0, "Negative": 0, "Neutral": 0, "ERROR": 0}
    for r in results:
        counts[r["sentiment"]] = counts.get(r["sentiment"], 0) + 1

    print("\nSummary:")
    for label in ("Positive", "Negative", "Neutral"):
        print(f"  {label}: {counts[label]}")
    if counts["ERROR"]:
        print(f"  Errors: {counts['ERROR']}")


def main():
    client = get_client()

    print(f"Classifying {len(SAMPLE_REVIEWS)} reviews "
          f"(provider: {LLM_PROVIDER}, model: {MODEL_NAME})...\n")

    results = classify_reviews(client, SAMPLE_REVIEWS)

    table_rows = [
        [i + 1, truncate(r["review"]), r["sentiment"]]
        for i, r in enumerate(results)
    ]
    print(tabulate(
        table_rows,
        headers=["#", "Review", "Sentiment"],
        tablefmt="grid",
    ))

    print_summary(results)

    # surface any per-review errors separately so they don't get lost
    # in the truncated table column
    errors = [r for r in results if r["error"]]
    if errors:
        print("\nDetails on failed classifications:")
        for r in errors:
            print(f"  - {truncate(r['review'], 40)!r}: {r['error']}")


if __name__ == "__main__":
    main()
