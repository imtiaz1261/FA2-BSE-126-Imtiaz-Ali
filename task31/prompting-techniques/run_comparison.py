"""
run_comparison.py
-------------------
Runs the same task through 5 different prompting techniques against a
Groq-hosted LLM, saving each output to outputs/groq/<technique>.txt so
you can read them side by side.

Setup:
    pip install -r requirements.txt
    cp .env.example .env        # paste your GROQ_API_KEY in

Usage:
    python run_comparison.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from prompts import PROMPTS, TASK_DESCRIPTION

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs" / "groq"


def main() -> int:
    if not GROQ_API_KEY:
        print(
            "Error: GROQ_API_KEY is missing from your .env file.\n"
            "Get a free key at https://console.groq.com/keys and add it as "
            "GROQ_API_KEY=... in your local .env file."
        )
        return 1

    try:
        from groq import Groq
    except ImportError:
        print("Error: the groq package is not installed. Run: pip install groq")
        return 1

    client = Groq(api_key=GROQ_API_KEY)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Task: {TASK_DESCRIPTION}\n")
    print(f"Model: {GROQ_MODEL}\n")

    for name, prompt in PROMPTS.items():
        print(f"Running: {name} ...")
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            output_text = response.choices[0].message.content.strip()
        except Exception as exc:
            output_text = f"[ERROR generating output: {exc}]"
            print(f"  ! Error: {exc}")

        out_path = OUTPUT_DIR / f"{name}.txt"
        out_path.write_text(
            f"PROMPT:\n{prompt}\n\n{'-' * 60}\n\nOUTPUT:\n{output_text}\n",
            encoding="utf-8",
        )
        print(f"  Saved to {out_path}")

    print(f"\nAll outputs saved in {OUTPUT_DIR}/")
    print("Open comparison_note.md for the technique-by-technique analysis template.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
