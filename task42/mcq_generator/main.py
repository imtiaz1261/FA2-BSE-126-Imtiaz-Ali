"""
MCQ Generator
=============
User se ek paragraph ya topic leta hai, LLM (Groq - Llama 3.3 70B) se
us par 5 multiple-choice questions generate karwata hai (4 options +
correct answer ke saath), output ko Pydantic se validate karta hai,
aur clean, readable format mein print karta hai.

Setup:
    1. `.env.example` ko `.env` mein copy karein aur apni Groq API key
       aur model daalein:
        GROQ_API_KEY=your-api-key-here
        GROQ_MODEL=llama-3.3-70b-versatile

Run:
    python main.py
"""

import os
import sys
import json
from typing import List

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, ValidationError, field_validator

load_dotenv()


# ---------------------------------------------------------------------------
# 1. Pydantic schema — output validation ke liye
# ---------------------------------------------------------------------------
class MCQ(BaseModel):
    question: str
    options: List[str]
    correct_answer: str

    @field_validator("options")
    @classmethod
    def must_have_four_options(cls, v):
        if len(v) != 4:
            raise ValueError("Har question ke exactly 4 options hone chahiye")
        return v

    @field_validator("correct_answer")
    @classmethod
    def answer_must_match_option(cls, v, info):
        options = info.data.get("options", [])
        if options and v not in options:
            raise ValueError("correct_answer options list mein se hi ek hona chahiye")
        return v


class MCQSet(BaseModel):
    questions: List[MCQ]

    @field_validator("questions")
    @classmethod
    def must_have_five_questions(cls, v):
        if len(v) != 5:
            raise ValueError("Exactly 5 questions chahiye")
        return v


# ---------------------------------------------------------------------------
# 2. LLM prompt template
# ---------------------------------------------------------------------------
MCQ_PROMPT = """You are a quiz generator assistant.

Based on the following paragraph/topic, generate exactly 5 multiple-choice
questions (MCQs). Each question must have exactly 4 options, and one of
them must be the correct answer (copied exactly as it appears in the
options list).

Return ONLY a valid JSON object in this exact structure, with no
explanation, no markdown, no code fences — just raw JSON:

{{
  "questions": [
    {{
      "question": "<question text>",
      "options": ["<option A>", "<option B>", "<option C>", "<option D>"],
      "correct_answer": "<must exactly match one of the 4 options>"
    }},
    ... (5 questions total)
  ]
}}

Paragraph/Topic:
\"\"\"{content}\"\"\"

JSON:"""


# ---------------------------------------------------------------------------
# 3. Core logic
# ---------------------------------------------------------------------------
def clean_json_string(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    return raw.strip()


def generate_mcqs(client: Groq, model: str, content: str) -> dict:
    prompt = MCQ_PROMPT.format(content=content)
    response = client.chat.completions.create(
        model=model,
        max_tokens=1500,
        temperature=0.5,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    raw_output = response.choices[0].message.content
    cleaned = clean_json_string(raw_output)
    return json.loads(cleaned)


def print_mcqs(mcq_set: MCQSet) -> None:
    print("\n" + "=" * 65)
    print(" 📝  GENERATED QUIZ (5 Multiple Choice Questions)")
    print("=" * 65)

    labels = ["A", "B", "C", "D"]
    for idx, mcq in enumerate(mcq_set.questions, start=1):
        print(f"\nQ{idx}. {mcq.question}")
        for label, option in zip(labels, mcq.options):
            marker = "✔" if option == mcq.correct_answer else " "
            print(f"   {label}) {option}")
        correct_label = labels[mcq.options.index(mcq.correct_answer)]
        print(f"   ✅ Correct Answer: {correct_label}) {mcq.correct_answer}")

    print("\n" + "=" * 65)


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------
SAMPLE_TOPIC = """
Photosynthesis is the process by which green plants, algae, and some
bacteria convert light energy, usually from the sun, into chemical
energy stored in glucose. This process takes place mainly in the
chloroplasts of plant cells, using a green pigment called chlorophyll
to absorb sunlight. Photosynthesis uses carbon dioxide and water as raw
materials and releases oxygen as a byproduct. It is essential for life
on Earth, as it produces the oxygen we breathe and forms the base of
most food chains.
"""


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        print("Copy .env.example to .env and add your Groq API key, or:")
        print('  export GROQ_API_KEY="your-api-key-here"')
        sys.exit(1)

    client = Groq(api_key=api_key)

    print("=" * 65)
    print(" 📚  MCQ Generator")
    print("=" * 65)
    print("\nEnter karein ek paragraph ya topic (ya Enter dabayein sample")
    print("photosynthesis paragraph use karne ke liye):\n")

    user_input = input("Your paragraph/topic: ").strip()
    content = user_input if user_input else SAMPLE_TOPIC.strip()

    print("\n⏳ Generating 5 MCQs, please wait...")

    try:
        raw_json = generate_mcqs(client, model, content)
    except json.JSONDecodeError as exc:
        print(f"❌ LLM ne valid JSON return nahi kiya. Error: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"❌ Kuch masla hua LLM call mein: {exc}")
        sys.exit(1)

    try:
        mcq_set = MCQSet(**raw_json)
    except ValidationError as exc:
        print("❌ Output validation fail hui. Raw LLM output:\n")
        print(json.dumps(raw_json, indent=2, ensure_ascii=False))
        print("\nValidation errors:")
        print(exc)
        sys.exit(1)

    print_mcqs(mcq_set)


if __name__ == "__main__":
    main()
