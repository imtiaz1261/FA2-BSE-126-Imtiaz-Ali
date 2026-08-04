"""
Command-line interface for the translator app.

Usage:
    python cli.py

Prompts the user for text and a target language, prints the translation,
and loops until the user types 'exit'.
"""

from translator import get_client, translate, TranslationError, SUPPORTED_LANGUAGES


def print_banner():
    print("=" * 50)
    print("  Simple Translator App")
    print("=" * 50)
    print("Suggested languages:", ", ".join(SUPPORTED_LANGUAGES))
    print("(You can also type any other language name.)")
    print("Type 'exit' at any prompt to quit.\n")


def main():
    client = get_client()
    print_banner()

    while True:
        text = input("Text to translate: ").strip()
        if text.lower() == "exit":
            print("Goodbye!")
            break
        if not text:
            print("Please enter some text.\n")
            continue

        target_language = input("Translate to (e.g. Hindi, French, Spanish): ").strip()
        if target_language.lower() == "exit":
            print("Goodbye!")
            break
        if not target_language:
            print("Please enter a target language.\n")
            continue

        try:
            translated = translate(client, text, target_language)
            print(f"\n{target_language} translation:\n{translated}\n")
        except TranslationError as e:
            print(f"\n[Error] {e}\n")


if __name__ == "__main__":
    main()
