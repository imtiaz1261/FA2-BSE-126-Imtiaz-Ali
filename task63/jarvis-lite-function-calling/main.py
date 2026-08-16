"""
main.py
-------
CLI for Jarvis-Lite. Type queries; the engine decides on its own
whether a tool is needed.

Usage:
    python main.py
"""

import sys

from engine import JarvisLite, EngineInitError


def main() -> int:
    try:
        jarvis = JarvisLite()
    except EngineInitError as exc:
        print(f"Error: {exc}")
        return 1

    print("Jarvis-Lite is ready. Type 'exit' or 'quit' to stop.\n")
    print("Try things like:")
    print('  - "What\'s the weather in Islamabad?"')
    print('  - "What is the stock price of AAPL?"')
    print('  - "Who wrote Romeo and Juliet?"  (no tool needed)\n')

    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not query:
            continue
        if query.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        try:
            answer = jarvis.ask(query)
        except Exception as exc:
            answer = f"Sorry, something went wrong: {exc}"

        print(f"\nJarvis: {answer}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
