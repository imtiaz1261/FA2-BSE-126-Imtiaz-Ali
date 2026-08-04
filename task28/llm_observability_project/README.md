# LLM Observability, Cost Tracking & Optimization Dashboard

A complete FastAPI + Streamlit application that chats with an LLM (via Groq's
OpenAI-compatible API) while tracking latency, tokens, and cost for every
request — and demonstrates, with real measured numbers, how much Redis
caching and prompt shortening reduce cost and latency.

## Features

- FastAPI backend with `/chat`, `/metrics`, `/metrics/summary`, `/benchmark`,
  `/benchmark/results`, `/health`
- Streamlit chat UI (`st.chat_message`, `st.chat_input`, session state) showing
  live token/latency/cost/cache-hit metrics per message
- Streamlit analytics dashboard with KPI cards and Plotly charts
- Redis response caching with graceful degradation if Redis is unavailable
- Prompt-shortening optimizer that strips filler text and duplicate lines
  without changing the user's intent
- Centralized, swappable model pricing config (no hardcoded prices in code)
- Optional Langfuse observability integration (no-ops if not configured)
- SQLite metrics storage (swappable for Postgres — see Architecture notes)
- A reproducible 20-query benchmark across 4 configurations: baseline,
  caching only, prompt optimization only, and both combined
- Automated tests using a mocked LLM (no paid API calls required to test)

## Architecture

```
Streamlit (chat + dashboard)
        │
        ▼
   FastAPI backend
        │
   ┌────┴────┐
   ▼         ▼
Redis     Prompt
Cache     Optimizer
   │         │
   └────┬────┘
        ▼
   LLM Service (Groq/OpenAI-compatible)
        │
        ▼
 Langfuse (optional observability)
        │
        ▼
   SQLite metrics store
        │
        ▼
 Streamlit Dashboard (reads back via /metrics)
```

`app/models/database.py` is intentionally a thin SQLite wrapper
(`init_db` / `insert_metric` / `fetch_metrics`) so it can be swapped for a
SQLAlchemy + PostgreSQL implementation later without touching any of the
calling code in `app/api/` or `benchmark/`.

## Folder structure

```
llm_observability_project/
├── app/
│   ├── main.py                  FastAPI app, CORS, global error handler
│   ├── api/                     chat.py, metrics.py, benchmark.py
│   ├── services/                llm_service, cache_service, prompt_optimizer,
│   │                            token_tracker, cost_tracker, observability
│   ├── models/                  schemas.py (Pydantic), database.py (SQLite)
│   ├── config/                  settings.py (env vars + pricing table)
│   └── utils/                   helpers.py
├── dashboard/                   streamlit_app.py, chat_ui.py, analytics.py, charts.py
├── benchmark/                   dataset.py (20 queries), runner.py, evaluator.py
├── tests/                       test_chat.py, test_cache.py, test_optimizer.py, test_cost.py
├── data/                        SQLite DB lives here at runtime
├── reports/                     exported benchmark reports land here
├── .env.example
├── requirements.txt
└── run.py
```

## Installation

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

> **Windows note:** if `pip install` tries to compile pandas from source
> (a `meson setup` error mentioning `vswhere.exe` or Visual Studio), it means
> pip couldn't find a prebuilt wheel for your Python version — usually
> because you're on a very new Python release (e.g. 3.13) that some
> scientific packages haven't published Windows wheels for yet. Fix by
> either using **Python 3.11 or 3.12** for the virtual environment, or by
> upgrading pip first (`pip install --upgrade pip`) so it can resolve a
> newer pandas release that does ship a wheel. `requirements.txt` uses
> `>=` floors rather than exact pins for this reason — let pip pick the
> newest compatible version rather than forcing an old one.

## Environment variables

```bash
# Windows
copy .env.example .env
# macOS/Linux
cp .env.example .env
```

Edit `.env` and fill in:

- `GROQ_API_KEY` — get a free key at https://console.groq.com/keys
  (no credit card required). **Never commit this file** — `.env` is
  gitignored, only `.env.example` (with blanks) is tracked.
- `MODEL_NAME` — defaults to `llama-3.1-8b-instant`.
- Leave `LANGFUSE_*` blank if you don't want observability — the app
  detects this and simply skips tracing.

If you'd rather use OpenAI instead of Groq, set `LLM_PROVIDER=openai` and
fill in `OPENAI_API_KEY`; note OpenAI is a paid API, so budget accordingly.

## Redis setup (optional but recommended)

The app works without Redis — caching just no-ops and every request hits the
LLM — but caching is the whole point of half this project, so it's worth
running:

```bash
docker run -d -p 6379:6379 redis:latest
```

Or install Redis natively and ensure it's listening on `REDIS_URL` from `.env`.

## Langfuse setup (optional)

1. Sign up free at https://cloud.langfuse.com (or self-host).
2. Create a project, copy the public/secret keys into `.env`.
3. Traces will appear in the Langfuse dashboard as you chat or benchmark.

If you skip this, the app runs identically — `observability_enabled` is
`False` and `log_trace()` is a no-op.

## Running the API

```bash
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs for interactive Swagger docs.

Example request:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain Retrieval-Augmented Generation", "use_cache": true, "optimize_prompt": true}'
```

## Running the dashboard

In a second terminal (API must already be running):

```bash
streamlit run dashboard/streamlit_app.py
```

Open http://localhost:8501. Use the sidebar to switch between **Chat** and
**Dashboard**.

## Running the benchmark

Either click "Run full benchmark" on the Dashboard page, or from the API:

```bash
curl -X POST http://localhost:8000/benchmark \
  -H "Content-Type: application/json" \
  -d '{"configurations": ["baseline", "caching", "prompt_optimization", "full"], "repeat_queries": 2}'
```

Or directly in Python, which also lets you export a report file:

```python
from benchmark.runner import run_benchmark
from benchmark.evaluator import export_report

report = run_benchmark(
    ["baseline", "caching", "prompt_optimization", "full"],
    repeat_queries=2,
)
export_report(report, fmt="markdown")   # or "csv" / "json"
```

The benchmark clears the Redis cache before it starts and runs each of the
20 queries in `benchmark/dataset.py` `repeat_queries` times per
configuration, so cache hits on the second pass are real, measured hits —
not simulated numbers.

## How cost is calculated

`app/config/settings.py` holds a single `MODEL_PRICING` dict (USD per 1M
input/output tokens). `app/services/cost_tracker.py` is the only place that
reads it — update pricing there when a provider changes rates, and every
part of the app picks it up automatically. Costs are also converted to GBP
for generic display using a configurable `USD_TO_GBP` rate.

## How caching works

1. A cache key is the SHA-256 hash of `model:normalized_message`.
2. On a `/chat` request, if `use_cache=true`, Redis is checked first.
3. Hit → the stored response (with its original token/cost/latency metadata)
   is returned instantly, `cache_hit=true`, and no LLM call happens.
4. Miss → the LLM is called, the result is stored in Redis with a TTL
   (`CACHE_TTL_SECONDS`), and returned normally.
5. If Redis is down or errors, `cache_service` catches the exception and
   returns `None`/no-ops — the chat still works, just without caching.

## How prompt shortening works

`app/services/prompt_optimizer.py` strips known filler phrases ("could you
please", "in order to", etc.), collapses redundant whitespace, and removes
exact duplicate lines (common when a UI pastes repeated context). It does
**not** summarize or reinterpret the request — the semantic content and
intent are preserved, only free token waste is removed. Before/after token
counts and reduction percentage are tracked on every optimized request.

## Testing

```bash
pytest
```

Tests mock the LLM call (`app.api.chat.llm_service.call_llm`) so the suite
runs without hitting Groq/OpenAI and without needing a real API key.

## Troubleshooting

- **"Could not reach API" in Streamlit** — make sure `uvicorn` is running on
  port 8000 before starting Streamlit.
- **Every request is a cache miss** — check `docker ps` / that Redis is
  actually running and `REDIS_URL` matches; the app will run fine but silently
  skip caching if it can't connect.
- **`401` from Groq** — your `GROQ_API_KEY` in `.env` is missing, wrong, or
  was revoked (rotate keys at console.groq.com/keys if you ever paste one
  into a chat, doc, or public repo — treat it as compromised).
- **Costs show `0.0`** — the model name in `.env` doesn't match a key in
  `MODEL_PRICING` in `app/config/settings.py`; add it there.
- **Langfuse traces not appearing** — confirm both `LANGFUSE_PUBLIC_KEY` and
  `LANGFUSE_SECRET_KEY` are set; if either is blank, tracing is disabled
  by design.

## Future improvements

- Swap SQLite for PostgreSQL via SQLAlchemy for multi-instance deployments.
- Add PDF export to `benchmark/evaluator.py` (JSON/CSV/Markdown are done).
- Add streaming responses (`st.write_stream`) to the chat UI.
- Add per-user rate limiting middleware in FastAPI.
- Add a semantic-similarity cache (not just exact-match) for near-duplicate
  queries.

## Security notes

- Never commit `.env` — only `.env.example` (blank placeholders) is tracked.
- API keys are read only from environment variables, never hardcoded.
- The global FastAPI exception handler returns a generic 500 message —
  internal errors and stack traces are never sent to the client.
- Errors from LLM/Redis/observability failures are logged server-side only.
- Request bodies are validated and size-bounded via Pydantic (`ChatRequest`
  caps `message` at 8000 characters).
