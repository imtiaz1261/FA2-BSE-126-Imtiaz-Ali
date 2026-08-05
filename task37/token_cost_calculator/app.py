import os
from decimal import Decimal
from pathlib import Path

import tiktoken
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
API_KEY = os.getenv("GROQ_API_KEY")

# Approximate public pricing used by this project.
# Verify current Groq pricing before using results for billing decisions.
MODEL_PRICING = {
    "llama-3.3-70b-versatile": {
        "input_per_1m": Decimal("0.59"),
        "output_per_1m": Decimal("0.79"),
    }
}

def get_encoding(model: str):
    """Return the closest tiktoken encoding available for the selected model."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Groq-hosted Llama models do not necessarily have a native tiktoken
        # mapping. cl100k_base is a practical approximation for token counting.
        return tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str, model: str) -> int:
    encoding = get_encoding(model)
    return len(encoding.encode(text))

def calculate_cost(input_tokens: int, output_tokens: int, model: str):
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return None

    input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * pricing["input_per_1m"]
    output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * pricing["output_per_1m"]
    return input_cost, output_cost, input_cost + output_cost

def ask_groq(prompt: str, model: str):
    if not API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing from the .env file.")

    client = Groq(api_key=API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content

def main():
    print("=" * 65)
    print(" TIKTOKEN TOKEN COUNTER + GROQ APPROXIMATE COST CALCULATOR")
    print("=" * 65)
    print(f"Model: {MODEL}")

    if MODEL not in MODEL_PRICING:
        print("Warning: pricing for this model is not configured.")
        print("Update MODEL_PRICING in app.py with current provider pricing.")

    prompt = input("\nEnter your text/prompt:\n> ")

    input_tokens = count_tokens(prompt, MODEL)
    print(f"\nInput tokens (tiktoken approximation): {input_tokens:,}")

    run_api = input("\nSend prompt to Groq and calculate output cost? (y/n): ").strip().lower()

    if run_api == "y":
        try:
            answer = ask_groq(prompt, MODEL)
            output_tokens = count_tokens(answer, MODEL)

            print("\n--- Groq Response ---")
            print(answer)
            print("\n--- Token & Cost Report ---")
            print(f"Input tokens : {input_tokens:,}")
            print(f"Output tokens: {output_tokens:,}")
            print(f"Total tokens : {input_tokens + output_tokens:,}")

            costs = calculate_cost(input_tokens, output_tokens, MODEL)
            if costs:
                input_cost, output_cost, total_cost = costs
                print(f"Approx input cost : ${input_cost:.8f}")
                print(f"Approx output cost: ${output_cost:.8f}")
                print(f"Approx total cost : ${total_cost:.8f}")
                print("\nNote: Cost is an estimate based on configured per-1M-token pricing.")
            else:
                print("Cost unavailable because model pricing is not configured.")
        except Exception as exc:
            print(f"\nError: {exc}")
    else:
        costs = calculate_cost(input_tokens, 0, MODEL)
        if costs:
            print(f"Approx input-only cost: ${costs[0]:.8f}")
        print("\nDone.")

if __name__ == "__main__":
    main()
