import time
from openai import OpenAI
from app.config.settings import get_settings
from app.services.token_tracker import count_tokens

settings = get_settings()

if settings.llm_provider == "groq":
    _client = OpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )
else:
    _client = OpenAI(api_key=settings.openai_api_key)


def call_llm(prompt: str) -> dict:
    start = time.perf_counter()
    try:
        completion = _client.chat.completions.create(
            model=settings.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = (time.perf_counter() - start) * 1000
        choice = completion.choices[0].message.content

        usage = getattr(completion, "usage", None)
        if usage:
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
        else:
            # Documented fallback — provider didn't return usage metadata.
            input_tokens = count_tokens(prompt)
            output_tokens = count_tokens(choice)

        return {
            "response": choice,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "latency_ms": round(latency_ms, 2),
            "status": "success",
            "error": None,
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "response": "Sorry — the assistant is temporarily unavailable. Please try again.",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "latency_ms": round(latency_ms, 2),
            "status": "error",
            "error": str(e),  # logged internally only, never shown to end user
        }
