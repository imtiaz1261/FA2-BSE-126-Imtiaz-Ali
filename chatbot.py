"""
Real-time streaming CLI chatbot.

Uses the OpenAI SDK's async client with stream=True, and an `async for` loop
to print each token as it arrives from the model — instead of waiting for
the full response.

Works with any OpenAI-compatible endpoint (OpenAI itself, Groq, etc.) by
changing PROVIDER below or passing --provider on the command line.
"""

import argparse
import asyncio
import sys

from openai import AsyncOpenAI

try:
    from secret_key import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = None
try:
    from secret_key import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = None

PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "api_key": GROQ_API_KEY,
    },
    "openai": {
        "base_url": None,
        "default_model": "gpt-4o-mini",
        "api_key": OPENAI_API_KEY,
    },
}

SYSTEM_PROMPT = "You are a helpful, concise assistant."


async def stream_reply(client: AsyncOpenAI, model: str, messages: list[dict]) -> str:
    """Send the conversation to the model and print the reply token-by-token
    as it streams in. Returns the full assembled reply text."""

    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )

    full_reply = ""
    print("Assistant: ", end="", flush=True)

    async for chunk in stream:
        delta = chunk.choices[0].delta
        token = getattr(delta, "content", None)
        if token:
            print(token, end="", flush=True)
            full_reply += token

    print()  # newline after the reply finishes
    return full_reply


async def chat_loop(client: AsyncOpenAI, model: str) -> None:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print(f"Streaming chatbot ready (model: {model}). Type 'exit' or 'quit' to leave.\n")

    while True:
        try:
            user_input = (await asyncio.to_thread(input, "You: ")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            reply = await stream_reply(client, model, messages)
        except Exception as e:
            print(f"\n[Error] {e}")
            messages.pop()  # drop the failed user turn so the history stays clean
            continue

        messages.append({"role": "assistant", "content": reply})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Real-time streaming CLI chatbot")
    parser.add_argument(
        "--provider",
        choices=list(PROVIDERS.keys()),
        default="groq",
        help="Which API provider to use (default: groq, which is free)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the default model for the chosen provider",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    provider = PROVIDERS[args.provider]

    api_key = provider["api_key"]
    if not api_key:
        print(
            f"No API key found for provider '{args.provider}'. "
            f"Add it to secret_key.py first."
        )
        sys.exit(1)

    model = args.model or provider["default_model"]

    client_kwargs = {"api_key": api_key}
    if provider["base_url"]:
        client_kwargs["base_url"] = provider["base_url"]

    client = AsyncOpenAI(**client_kwargs)

    asyncio.run(chat_loop(client, model))


if __name__ == "__main__":
    main()
