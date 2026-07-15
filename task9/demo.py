"""
Demo: using TrackedLLMClient against a real (free) Groq endpoint.

Every call to client.chat_completion(...) is transparently logged to
usage_log.jsonl — you don't have to add any logging code at each call site.
"""

import argparse

from openai import OpenAI
from usage_logger import TrackedLLMClient, backends_from_env

try:
    from secret_key import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = None

if not GROQ_API_KEY or "your-groq-key-here" in GROQ_API_KEY:
    raise SystemExit("Add your real Groq key to secret_key.py first.")

MODEL_NAME = "llama-3.3-70b-versatile"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question through the tracked client")
    parser.add_argument("--question", help="Question to send to the model")
    args = parser.parse_args()

    question = args.question or input("Ask something: ").strip()

    raw_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

    # backends_from_env() reads LOG_BACKEND from the environment ("file" by
    # default). Set LOG_BACKEND=cloudwatch or LOG_BACKEND=both to also (or
    # instead) stream to AWS CloudWatch Logs — see README.md.
    tracked_client = TrackedLLMClient(raw_client, backends=backends_from_env())

    response = tracked_client.chat_completion(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": question}],
    )

    print("\n=== Answer ===")
    print(response.choices[0].message.content)
    print("\nUsage details appended to usage_log.jsonl (or CloudWatch, if configured).")


if __name__ == "__main__":
    main()