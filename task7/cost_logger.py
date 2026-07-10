"""
Custom LangChain callback handler that logs the exact cost of every LLM
request to a .txt file, based on token counts.

How it works:
- LangChain fires callback events at each stage of a chain's execution.
- `on_llm_end` fires once the model finishes generating a response, and
  the response object includes token usage (prompt/completion/total)
  in `response.llm_output`.
- We look up a $/1K-token price for the model being used, calculate the
  cost from the token counts, and append a line to `cost_log.txt`.

Note on pricing: Groq's hosted open-weight models are currently free, so
requests through Groq will log $0.0000 cost — the token counts and the
calculation logic are still real, it's just the price table is $0 for
Groq's current free models. Swap to an OpenAI model (paid) to see non-zero
costs, or edit PRICING below with your own rates.
"""

import argparse
import datetime
import os

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

try:
    from secret_key import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = None

if not GROQ_API_KEY or "your-groq-key-here" in GROQ_API_KEY:
    raise SystemExit("Add your real Groq key to secret_key.py first.")

LOG_FILE = "cost_log.txt"

# Price per 1,000 tokens, (input_price, output_price), in USD.
# Groq's current models are free — priced at $0. Add/edit rows here for
# other providers/models as needed.
PRICING = {
    "llama-3.3-70b-versatile": (0.0, 0.0),   # Groq, free
    "llama-3.1-8b-instant": (0.0, 0.0),      # Groq, free
    "gpt-4o-mini": (0.00015, 0.0006),        # OpenAI, per 1K tokens
    "gpt-4o": (0.0025, 0.01),                # OpenAI, per 1K tokens
}
DEFAULT_PRICING = (0.0, 0.0)  # fallback for unknown models


class CustomCallbackHandler(BaseCallbackHandler):
    """Logs prompt/completion/total tokens and cost for every LLM call."""

    def __init__(self, log_file: str = LOG_FILE):
        self.log_file = log_file

    def on_llm_end(self, response, **kwargs) -> None:
        # response.llm_output typically looks like:
        # {"token_usage": {"prompt_tokens": .., "completion_tokens": .., "total_tokens": ..},
        #  "model_name": "..."}
        llm_output = response.llm_output or {}
        token_usage = llm_output.get("token_usage", {})
        model_name = llm_output.get("model_name", "unknown")

        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        total_tokens = token_usage.get("total_tokens", prompt_tokens + completion_tokens)

        input_price, output_price = PRICING.get(model_name, DEFAULT_PRICING)
        cost = (prompt_tokens / 1000) * input_price + (completion_tokens / 1000) * output_price

        self._write_log(model_name, prompt_tokens, completion_tokens, total_tokens, cost)

    def _write_log(self, model_name, prompt_tokens, completion_tokens, total_tokens, cost) -> None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = (
            f"[{timestamp}] model={model_name} "
            f"prompt_tokens={prompt_tokens} completion_tokens={completion_tokens} "
            f"total_tokens={total_tokens} cost=${cost:.6f}\n"
        )
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line)
        print(f"Logged: {line.strip()}")


def build_chain(handler: CustomCallbackHandler):
    prompt = ChatPromptTemplate.from_template("Answer briefly: {question}")
    model = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=GROQ_API_KEY,
        callbacks=[handler],  # attach the handler to the model itself
    )
    output_parser = StrOutputParser()
    return prompt | model | output_parser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask a question, log its cost")
    parser.add_argument("--question", help="Question to send to the model")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    question = args.question or input("Ask something: ").strip()

    handler = CustomCallbackHandler()
    chain = build_chain(handler)

    answer = chain.invoke({"question": question})

    print("\n=== Answer ===")
    print(answer)
    print(f"\nCost details appended to: {os.path.abspath(LOG_FILE)}")


if __name__ == "__main__":
    main()