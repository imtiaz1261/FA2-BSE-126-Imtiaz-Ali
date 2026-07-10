# Task 7 — Custom Callback Handler: LLM Cost Logger

A `CustomCallbackHandler` that hooks into LangChain's callback system and
logs the exact token counts and cost of every LLM request to a `.txt`
file.

## What it demonstrates

- Subclassing `BaseCallbackHandler` and overriding `on_llm_end`, which
  fires automatically whenever a model finishes generating a response
- Extracting token usage (`prompt_tokens`, `completion_tokens`,
  `total_tokens`) from `response.llm_output`
- Calculating cost from a per-model $/1K-token pricing table
- Appending a structured log line to `cost_log.txt` for every request,
  with a timestamp

## Files

| File                 | Purpose                                       |
|-----------------------|------------------------------------------------|
| `cost_logger.py`     | Main script — run this                        |
| `requirements.txt`   | Python dependencies                           |
| `secret_key.py`      | Your API key (never commit this file)         |
| `.gitignore`         | Excludes `secret_key.py` and generated `cost_log.txt` |
| `cost_log.txt`       | Generated automatically — the running cost log |

## Setup

1. **Create and activate a virtual environment**
   ```
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Add your API key** in `secret_key.py` (get a free one at
   [console.groq.com/keys](https://console.groq.com/keys)).

## Usage

```
python cost_logger.py --question "What is the capital of France?"
```

or interactively:
```
python cost_logger.py
```

Each run appends one line to `cost_log.txt` in the same folder, e.g.:
```
[2026-07-10 14:32:07] model=llama-3.3-70b-versatile prompt_tokens=14 completion_tokens=8 total_tokens=22 cost=$0.000000
```

## Why the cost shows $0.0000 with Groq

Groq's hosted open-weight models are currently free to use, so their price
in the `PRICING` table is `(0.0, 0.0)`. The token counts and cost
calculation are real — only the price-per-token is zero. To see non-zero
costs, switch the model in `cost_logger.py` to an OpenAI model (e.g.
`gpt-4o-mini`, priced in the table) and use your `OPENAI_API_KEY` instead.

## Extending this

- Add more models to the `PRICING` dict as needed — check the provider's
  current pricing page since rates change over time.
- To log costs from a chain with multiple LLM calls, attach the same
  `handler` instance across all model instances in the chain — each call
  will append its own log line.
- To also see prompts/responses in the log (not just costs), you can
  override `on_llm_start` too, which receives the prompts being sent.