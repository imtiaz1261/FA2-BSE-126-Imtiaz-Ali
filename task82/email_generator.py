"""
Dynamic email draft generator.

Builds a PromptTemplate with two input variables — "topic" and "tone" —
and runs it through an LCEL chain (prompt | model | output_parser) to
generate an email draft that adapts its wording based on the chosen tone
(e.g. "professional" or "funny").
"""

import argparse

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

try:
    from secret_key import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = None

if not GROQ_API_KEY or "your-groq-key-here" in GROQ_API_KEY:
    raise SystemExit("Add your real Groq key to secret_key.py first.")

MODEL_NAME = "llama-3.3-70b-versatile"

# The template has two placeholders — {topic} and {tone} — that get filled
# in at invoke() time. Everything else is fixed instruction text that keeps
# the output shaped like a real email regardless of what values are passed.
EMAIL_PROMPT = ChatPromptTemplate.from_template(
    """You are an assistant that writes email drafts.

Write a complete email about the following topic, in the specified tone.

Topic: {topic}
Tone: {tone}

Rules:
- If the tone is "professional": use polite, businesslike language, a clear
  subject line, and a formal sign-off.
- If the tone is "funny": keep it lighthearted and witty, but still make
  sense as an actual email someone could send — include a subject line.
- Always include: a Subject line, a greeting, a body, and a sign-off.
- Do not include any explanation outside the email itself — output only
  the email draft.
"""
)


def build_chain():
    model = ChatGroq(model=MODEL_NAME, api_key=GROQ_API_KEY)
    output_parser = StrOutputParser()
    return EMAIL_PROMPT | model | output_parser


def generate_email(topic: str, tone: str) -> str:
    chain = build_chain()
    return chain.invoke({"topic": topic, "tone": tone})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a dynamic email draft")
    parser.add_argument("--topic", help="What the email is about")
    parser.add_argument(
        "--tone",
        choices=["professional", "funny"],
        help="Tone of the email",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    topic = args.topic or input("Topic: ").strip()
    tone = args.tone or input("Tone (professional/funny): ").strip().lower()

    if tone not in {"professional", "funny"}:
        print(f"Note: '{tone}' isn't one of the two example tones, but the "
              f"model will still try to match it.")

    print("\nGenerating email draft...\n")
    email = generate_email(topic, tone)
    print(email)


if __name__ == "__main__":
    main()