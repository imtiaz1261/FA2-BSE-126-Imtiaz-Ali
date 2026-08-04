"""
Continuous console chatbot with conversation memory.

Keeps the full conversation history and sends it with every request, so
the model has context from earlier turns. The loop continues until the
user types 'exit'.

Usage:
    python chatbot.py
"""

import sys
from openai import OpenAI
from config import LLM_PROVIDER, GROQ_API_KEY, OPENAI_API_KEY, MODEL_NAME


def get_client() -> OpenAI:
    """Build an OpenAI-compatible client pointed at the chosen provider."""
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


def main():
    client = get_client()

    # This list holds the full conversation and is sent with every request,
    # so the model can reference earlier turns.
    conversation = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

    print(f"Chatbot ready — provider: {LLM_PROVIDER}, model: {MODEL_NAME}")
    print("Type your message and press Enter. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        conversation.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=conversation,
            )
            reply = response.choices[0].message.content
            print(f"\nBot: {reply}\n")

            # Add the assistant's reply to history too, so future turns
            # have the full back-and-forth as context.
            conversation.append({"role": "assistant", "content": reply})

        except Exception as e:
            print(f"\n[Error] Request failed: {e}\n")
            # Remove the last user message so a failed turn doesn't
            # pollute the context sent on the next attempt.
            conversation.pop()


if __name__ == "__main__":
    main()
