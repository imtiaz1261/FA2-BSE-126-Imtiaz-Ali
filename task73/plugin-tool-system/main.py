"""
main.py
-------
CLI alternative to app.py, for quick testing without Streamlit.

Usage:
    python main.py
"""

import sys

from core.agent import PluginAgent, AgentInitError
from core.registry import PluginRegistry


def main() -> int:
    registry = PluginRegistry()
    try:
        agent = PluginAgent(registry=registry)
    except AgentInitError as exc:
        print(f"Error: {exc}")
        return 1

    enabled = list(registry.get_enabled_plugins().keys())
    print(f"Enabled plugins: {enabled}")
    print("Type 'exit' or 'quit' to stop. Type '/plugins' to re-list enabled plugins.\n")

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
        if query == "/plugins":
            print("Enabled plugins:", list(registry.get_enabled_plugins().keys()))
            continue

        try:
            answer = agent.ask(query)
        except Exception as exc:
            answer = f"Sorry, something went wrong: {exc}"

        print(f"\nAgent: {answer}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
