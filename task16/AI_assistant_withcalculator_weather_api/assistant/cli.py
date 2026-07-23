"""
Command-line interface.

Run with:  python -m assistant.cli
"""

from .agent import Assistant, AssistantError


BANNER = """
==============================================
  AI Assistant (Calculator + Weather)
  Type your question, or 'exit' / 'quit' to stop.
  Type 'reset' to clear conversation memory.
==============================================
"""


def main():
    print(BANNER)
    try:
        assistant = Assistant()
    except AssistantError as exc:
        print(f"Startup error: {exc}")
        return

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
        if user_input.lower() == "reset":
            assistant.reset()
            print("(memory cleared)")
            continue

        reply = assistant.ask(user_input)
        print(f"Assistant: {reply}\n")


if __name__ == "__main__":
    main()
