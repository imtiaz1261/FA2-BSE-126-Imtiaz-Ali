"""
Simple command-line LLM Q&A tool.

Usage:
    python ask_llm.py

The script asks the user for a question on the command line, sends it to
an LLM (Groq's free, OpenAI-compatible API by default), and prints the
answer back in the terminal.
"""

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads variables from a local .env file

# ---------------------------------------------------------------
# Configuration — read from environment, never hardcoded here.
# ---------------------------------------------------------------
PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")


def get_client() -> OpenAI:
    """Build an OpenAI-compatible client pointed at the chosen provider."""
    if PROVIDER == "groq":
        if not GROQ_API_KEY:
            sys.exit(
                "ERROR: GROQ_API_KEY is missing.\n"
                "Get a free key at https://console.groq.com/keys and add it "
                "to your .env file."
            )
        return OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

    if PROVIDER == "openai":
        if not OPENAI_API_KEY:
            sys.exit(
                "ERROR: OPENAI_API_KEY is missing.\n"
                "Add it to your .env file, or set LLM_PROVIDER=groq to use "
                "the free Groq API instead."
            )
        return OpenAI(api_key=OPENAI_API_KEY)

    sys.exit(f"ERROR: Unknown LLM_PROVIDER '{PROVIDER}'. Use 'groq' or 'openai'.")


def ask(client: OpenAI, question: str) -> str:
    """Send the question to the LLM and return its answer text."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content


def main():
    client = get_client()

    print(f"Simple LLM CLI — provider: {PROVIDER}, model: {MODEL_NAME}")
    print("Type your question and press Enter. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        try:
            answer = ask(client, question)
            print(f"\nLLM: {answer}\n")
        except Exception as e:
            print(f"\n[Error] Request failed: {e}\n")


if __name__ == "__main__":
    main()
