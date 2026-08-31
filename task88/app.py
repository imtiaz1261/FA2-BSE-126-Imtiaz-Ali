import os
import sys
from groq import Groq

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def generate(theme, style, output_type):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY environment variable is not set.")
        print("Set it first, then run the program again.")
        sys.exit(1)

    client = Groq(api_key=api_key)

    prompt = f"""Create a short {output_type} in English.
Theme/topic: {theme}
Style: {style}

Requirements:
- Keep it around 150-250 words for a story, or 12-24 lines for a poem.
- Make it original and engaging.
- Match the requested style clearly.
- Return only the {output_type}, with a suitable title.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": "You are a creative writing assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,
        max_tokens=700,
    )
    return response.choices[0].message.content.strip()

def main():
    print("=== Groq Story / Poem Generator ===\n")
    theme = input("Enter a theme/topic (e.g. friendship, monsoon): ").strip()
    if not theme:
        print("Theme/topic cannot be empty.")
        return

    print("\nChoose output:")
    print("1. Story")
    print("2. Poem")
    choice = input("Enter 1 or 2 [1]: ").strip() or "1"
    output_type = "story" if choice == "1" else "poem"

    print("\nChoose style:")
    print("1. Funny")
    print("2. Emotional")
    print("3. Adventure")
    style_choice = input("Enter 1, 2, or 3 [1]: ").strip() or "1"
    styles = {"1": "funny", "2": "emotional", "3": "adventure"}
    style = styles.get(style_choice, "funny")

    print("\nGenerating with Groq...\n")
    try:
        result = generate(theme, style, output_type)
        print("=" * 60)
        print(result)
        print("=" * 60)
    except Exception as e:
        print(f"\nGroq API error: {e}")

if __name__ == "__main__":
    main()
