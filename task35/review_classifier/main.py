"""
Customer Review Sentiment Classifier
=====================================
Yeh script 5-10 sample customer reviews ko LLM (Groq - Llama 3.3 70B) prompt
ke through Positive, Negative, ya Neutral classify karta hai, aur result
ko table format mein print karta hai.

Requirements:
    pip install -r requirements.txt

Setup:
    1. Project root mein ek `.env` file banayein (`.env.example` ko copy
       karke) aur usmein apni Groq API key aur model daalein:
        GROQ_API_KEY=your-api-key-here
        GROQ_MODEL=llama-3.3-70b-versatile

Run:
    python main.py
"""

import os
import sys
from dotenv import load_dotenv
from groq import Groq
from tabulate import tabulate

load_dotenv()  # .env file se GROQ_API_KEY / GROQ_MODEL load karega

# ---------------------------------------------------------------------------
# 1. Sample customer reviews (aap inhe apne data se replace kar sakte hain)
# ---------------------------------------------------------------------------
SAMPLE_REVIEWS = [
    "The product quality is amazing, and it arrived earlier than expected!",
    "Worst purchase I've made this year. It broke within two days.",
    "It's okay, does the job but nothing special about it.",
    "Customer support was super helpful and resolved my issue quickly.",
    "I am extremely disappointed with the packaging, it was damaged.",
    "Average product, works fine for the price but not exceptional.",
    "Absolutely love this! Best purchase I've made in a long time.",
    "The item did not match the description at all, very misleading.",
    "It's decent, neither great nor terrible, just an average experience.",
    "Fast shipping and excellent build quality, highly recommend!",
]

# ---------------------------------------------------------------------------
# 2. LLM prompt template jo review ko classify karega
# ---------------------------------------------------------------------------
CLASSIFICATION_PROMPT = """You are a sentiment classification assistant.

Classify the following customer review into exactly ONE of these three
categories: Positive, Negative, or Neutral.

Rules:
- Respond with ONLY one word: Positive, Negative, or Neutral.
- Do not add any explanation, punctuation, or extra text.

Customer Review:
\"\"\"{review}\"\"\"

Sentiment:"""


def classify_review(client: Groq, model: str, review: str) -> str:
    """Send a single review to the Groq LLM and return its sentiment label."""
    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=10,
            messages=[
                {"role": "user", "content": CLASSIFICATION_PROMPT.format(review=review)}
            ],
        )
        label = response.choices[0].message.content.strip()

        # Normalize output in case the model adds punctuation/extra words
        for category in ("Positive", "Negative", "Neutral"):
            if category.lower() in label.lower():
                return category
        return label  # fallback: return raw model output
    except Exception as exc:
        return f"Error: {exc}"


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        print("Copy .env.example to .env and add your Groq API key, or:")
        print('  export GROQ_API_KEY="your-api-key-here"')
        sys.exit(1)

    client = Groq(api_key=api_key)

    results = []
    for idx, review in enumerate(SAMPLE_REVIEWS, start=1):
        sentiment = classify_review(client, model, review)
        results.append([idx, review, sentiment])
        print(f"Classified review {idx}/{len(SAMPLE_REVIEWS)}...")

    # -----------------------------------------------------------------
    # 3. Print results in a clean table format
    # -----------------------------------------------------------------
    headers = ["#", "Customer Review", "Sentiment"]
    print("\n" + tabulate(results, headers=headers, tablefmt="grid", maxcolwidths=[None, 60, None]))


if __name__ == "__main__":
    main()
