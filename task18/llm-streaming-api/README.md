# Real-Time LLM Streaming API (FastAPI)

A production-style FastAPI service that streams LLM responses token-by-token
over Server-Sent Events (SSE), with heartbeat keep-alives, graceful
disconnect/cancel handling, and a live HTML/JS frontend — the same pattern
ChatGPT-style apps use instead of waiting for the full response.

## Features

- `POST /chat/stream` — streams a chat completion as SSE
- Real token-by-token streaming via Groq's async streaming API (OpenAI-compatible)
- **Heartbeat**: a `heartbeat` event is sent whenever no token has arrived
  within `HEARTBEAT_INTERVAL_SECONDS`, so proxies/browsers don't time out
  the connection during slow generations
- **Cancellation**: `POST /chat/cancel/{request_id}` stops an in-flight
  stream immediately
- **Client disconnect handling**: if the browser closes the tab or drops
  the connection, the server detects it (`request.is_disconnected()`) and
  stops generating — no wasted tokens/cost
- **Request timeout**: a hard cap per stream (`REQUEST_TIMEOUT_SECONDS`)
- **Concurrency control**: `MAX_CONCURRENT_STREAMS` caps simultaneous
  streams via an `asyncio.Semaphore`; over the cap returns `503`
- **Token usage stats**: prompt/completion/total token counts are streamed
  back as a `usage` event when the provider reports them
- Structured logging of every stream's lifecycle (start, error, cancel, finish)
- A minimal but polished HTML/JS frontend with live markdown rendering,
  a blinking cursor, and a working Cancel button

## Project structure

```
llm-streaming-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, routes
│   ├── config.py             # env-driven settings (pydantic-settings)
│   ├── schemas.py            # request/response Pydantic models
│   ├── llm_service.py       # core async generator: tokens + heartbeat + errors
│   ├── streaming_utils.py   # SSE formatting + cancel/concurrency registry
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js            # fetch()-based SSE client (not EventSource)
├── requirements.txt
├── .env                       # your real Groq key (see note below)
├── .env.example
└── .gitignore
```

## Setup

```bash
pip install -r requirements.txt
```

A `.env` is already included with your Groq key:

```
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile
HEARTBEAT_INTERVAL_SECONDS=10
REQUEST_TIMEOUT_SECONDS=60
MAX_CONCURRENT_STREAMS=20
```

⚠️ That key was shared in chat, so treat it as semi-exposed — rotate it at
https://console.groq.com/keys before relying on this beyond local testing.
`.env` is already in `.gitignore`.

## Running it

```bash
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000** in a browser for the live demo UI, or
call the API directly:

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Explain SSE in 2 sentences"}]}'
```

`-N` disables curl's output buffering so you see tokens arrive live instead
of all at once.

## API reference

### `POST /chat/stream`

Request body:
```json
{
  "messages": [{"role": "user", "content": "Hello"}],
  "model": "llama-3.3-70b-versatile",   // optional
  "temperature": 0.7,                     // optional
  "max_tokens": 1024,                     // optional
  "request_id": "my-id-123"               // optional, needed to cancel later
}
```

Response: `text/event-stream`, events in order:

| event | when | data |
|---|---|---|
| `start` | immediately | `{request_id, model}` |
| `token` | per generated chunk | `{text}` |
| `heartbeat` | during quiet gaps > interval | `{t: unix_timestamp}` |
| `usage` | once, near the end | `{prompt_tokens, completion_tokens, total_tokens}` |
| `done` | normal completion | `{message, total_chars}` |
| `cancelled` | if cancelled via the cancel endpoint | `{message}` |
| `timeout` | if it exceeds `REQUEST_TIMEOUT_SECONDS` | `{message}` |
| `error` | on any provider/server failure | `{message}` |

Exactly one of `done` / `cancelled` / `timeout` / `error` terminates every stream.

### `POST /chat/cancel/{request_id}`

Stops the matching in-flight stream. Returns `404` if that `request_id`
isn't currently active.

### `GET /health`

Returns server status and current active-stream count — useful for
monitoring or load balancer health checks.

## How the streaming + heartbeat mechanism works

The hard part of this project is running two independent event sources —
"a new token arrived" and "no token has arrived in N seconds" — on the same
output stream. `app/llm_service.py` solves it like this:

1. A background `asyncio` task (`_produce_tokens`) opens the Groq streaming
   call and pushes each token onto an `asyncio.Queue` as it arrives.
2. The main generator (`stream_chat_response`, the thing FastAPI's
   `StreamingResponse` actually iterates) does:
   ```python
   kind, payload = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
   ```
   If a token shows up before the timeout, it's yielded immediately (real
   low-latency streaming). If the timeout fires first, a `heartbeat` event
   is yielded instead, and the loop continues waiting.
3. On every loop iteration it also checks: has the client disconnected
   (`request.is_disconnected()`), has this `request_id` been cancelled, and
   has the overall request exceeded its timeout. Any of these stop the
   loop and clean up the background task via `producer.cancel()`.

This is the same core pattern used by production LLM gateways — a queue
decouples "how fast the model produces tokens" from "how often we need to
prove to the client the connection is still alive."

## Notes on the frontend

Browsers' built-in `EventSource` API only supports `GET` requests with no
custom body, but this API takes a JSON body (message history, temperature,
etc.) via `POST`. So `app/static/app.js` doesn't use `EventSource` — it uses
`fetch()` with a `ReadableStream` reader and manually parses the
`event: ... \n data: ... \n\n` SSE framing. This is a standard, documented
way to consume SSE from a POST endpoint and is what most production
ChatGPT-style frontends do.

## Testing without hitting the real LLM API

If you want to verify the heartbeat/cancel/disconnect/timeout logic without
burning API calls, monkeypatch `app.llm_service._produce_tokens` with a
fake async generator that pushes `("token", text)` tuples onto the queue
with artificial delays — this is how the mechanics were verified during
development, since it isolates the SSE/concurrency machinery from the LLM
provider entirely.
