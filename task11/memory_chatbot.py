"""
CLI chatbot with bounded memory.

Remembers only the last 5 user messages (and their matching assistant
replies) so it can answer follow-up questions naturally ("what about
tomorrow?", "and the second one?"), without letting the conversation
history grow forever and eventually blow past the model's context limit
or slow every request down.

Uses collections.deque(maxlen=...) — a list-like structure that
automatically drops the oldest item once it's full, which is the
simplest way to implement a sliding window of memory.
"""

import argparse
from collections import deque

from openai import OpenAI

try:
    from secret_key import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = None

if not GROQ_API_KEY or "your-groq-key-here" in GROQ_API_KEY:
    raise SystemExit("Add your real Groq key to secret_key.py first.")

MODEL_NAME = "llama-3.3-70b-versatile"
MEMORY_SIZE = 5  # number of most recent user messages to remember

SYSTEM_PROMPT = "You are a helpful, concise assistant."


class MemoryChatbot:
    def __init__(self, memory_size: int = MEMORY_SIZE):
        self.client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

        # Each item in this deque is one (user_message, assistant_reply)
        # pair. maxlen=memory_size means once we add a 6th pair, the
        # oldest one is automatically dropped — that's the "remembers
        # only the last 5" behavior, with no manual trimming logic needed.
        self.history: deque = deque(maxlen=memory_size)

    def _build_messages(self, user_message: str) -> list[dict]:
        """Turns the remembered history + new message into the message
        list the API expects."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for past_user, past_reply in self.history:
            messages.append({"role": "user", "content": past_user})
            messages.append({"role": "assistant", "content": past_reply})

        messages.append({"role": "user", "content": user_message})
        return messages

    def ask(self, user_message: str) -> str:
        messages = self._build_messages(user_message)

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
        )
        reply = response.choices[0].message.content.strip()

        # Only store the pair AFTER a successful reply, and only here —
        # this is the one place memory gets updated, which is what makes
        # the deque's maxlen behavior enough to keep memory bounded.
        self.history.append((user_message, reply))

        return reply


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CLI chatbot with 5-message memory")
    parser.add_argument(
        "--memory-size", type=int, default=MEMORY_SIZE,
        help="How many recent user messages to remember (default: 5)"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bot = MemoryChatbot(memory_size=args.memory_size)

    print(f"Memory chatbot ready (remembers last {args.memory_size} messages). "
          f"Type 'exit' or 'quit' to leave.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        try:
            reply = bot.ask(user_input)
        except Exception as e:
            print(f"[Error] {e}")
            continue

        print(f"Assistant: {reply}")


if __name__ == "__main__":
    main()