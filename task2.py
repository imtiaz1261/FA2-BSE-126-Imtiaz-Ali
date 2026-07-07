import tiktoken

# Pricing table (example rates, per 1000 tokens, in USD)
# Ye real OpenAI pricing jaisi hai - tum apni zaroorat ke hisab se update kar sakte ho
PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},          # per 1K tokens
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},  # per 1K tokens
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}, # per 1K tokens
}


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Diye gaye text ke tokens count karta hai, model ke encoding ke hisab se."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Agar model tiktoken ko pata nahi, to default encoding use karo
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens = encoding.encode(text)
    return len(tokens)


def calculate_cost(input_tokens: int, output_tokens: int, model: str = "gpt-4o") -> dict:
    """Input aur output tokens ke hisab se total cost calculate karta hai."""
    if model not in PRICING:
        raise ValueError(f"Pricing not available for model: {model}")

    rates = PRICING[model]
    input_cost = (input_tokens / 1000) * rates["input"]
    output_cost = (output_tokens / 1000) * rates["output"]
    total_cost = input_cost + output_cost

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total_cost, 6),
    }


def simulate_response(prompt: str) -> str:
    """
    Real API call ki jagah ek dummy response simulate kar rahe hain
    (taake bina kisi paid API key ke pura flow test ho sake).
    Isko real API call se replace kiya ja sakta hai.
    """
    return f"This is a simulated response to the prompt: '{prompt[:50]}...'"


def main():
    model = "gpt-4o"
    prompt = "Explain the concept of asynchronous programming in Python with a real-world analogy."

    print(f"Prompt: {prompt}\n")

    # Step 1: Prompt ke tokens count karo (input tokens)
    input_tokens = count_tokens(prompt, model=model)
    print(f"Input tokens: {input_tokens}")

    # Step 2: "Response" generate karo (yahan simulate kar rahe hain)
    response = simulate_response(prompt)
    print(f"Response: {response}\n")

    # Step 3: Response ke bhi tokens count karo (output tokens)
    output_tokens = count_tokens(response, model=model)
    print(f"Output tokens: {output_tokens}")

    # Step 4: Total cost calculate karo
    cost_report = calculate_cost(input_tokens, output_tokens, model=model)

    print("\n--- Cost Report ---")
    print(f"Model: {model}")
    print(f"Input tokens:  {cost_report['input_tokens']} (${cost_report['input_cost']})")
    print(f"Output tokens: {cost_report['output_tokens']} (${cost_report['output_cost']})")
    print(f"Total cost for this run: ${cost_report['total_cost']}")


if __name__ == "__main__":
    main()