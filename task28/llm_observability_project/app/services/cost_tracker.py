from app.config.settings import get_settings

settings = get_settings()


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> dict:
    pricing = settings.MODEL_PRICING.get(model)
    if pricing is None:
        # Unknown model — don't silently guess, flag it clearly.
        return {"cost_usd": 0.0, "cost_gbp": 0.0, "priced": False}

    input_cost = (input_tokens / 1_000_000) * pricing["input_per_1m"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]
    total_usd = round(input_cost + output_cost, 8)
    total_gbp = round(total_usd * settings.USD_TO_GBP, 8)

    return {
        "input_cost_usd": round(input_cost, 8),
        "output_cost_usd": round(output_cost, 8),
        "cost_usd": total_usd,
        "cost_gbp": total_gbp,
        "priced": True,
    }
