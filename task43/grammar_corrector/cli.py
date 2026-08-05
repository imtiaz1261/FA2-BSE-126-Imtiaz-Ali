"""
Command-line interface for the grammar/spelling correction tool.

Usage:
    python cli.py

Paste a paragraph (can span multiple lines), then type END on its own
line to submit. The tool prints the corrected paragraph plus a short
list of the changes made. Type 'exit' instead of pasting text to quit.
"""

from corrector import get_client, correct_text, CorrectionError


def read_paragraph() -> str:
    """
    Reads multi-line input until the user types END on its own line.
    Returns the collected text (without the END marker).
    """
    print("Paste your paragraph below. Type END on its own line when done")
    print("(or type 'exit' instead of pasting to quit):\n")

    lines = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            return "\n".join(lines)

        if line.strip().lower() == "exit" and not lines:
            return "exit"
        if line.strip().upper() == "END":
            break
        lines.append(line)

    return "\n".join(lines)


def main():
    client = get_client()
    print("=" * 55)
    print("  Grammar & Spelling Correction Tool")
    print("=" * 55)

    while True:
        text = read_paragraph()

        if text.strip().lower() == "exit":
            print("Goodbye!")
            break
        if not text.strip():
            print("\nNo text entered. Try again.\n")
            continue

        try:
            result = correct_text(client, text)
        except CorrectionError as e:
            print(f"\n[Error] {e}\n")
            continue

        print("\n--- Corrected Text ---")
        print(result["corrected_text"])

        print("\n--- Changes Made ---")
        if result["changes"]:
            for i, change in enumerate(result["changes"], start=1):
                print(f"{i}. {change}")
        else:
            print("No changes were needed.")
        print()


if __name__ == "__main__":
    main()
