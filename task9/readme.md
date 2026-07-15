# Week 2 — Production Token/Cost Usage Logger

A production-style wrapper around any OpenAI-compatible LLM client that
transparently logs every request's input/output tokens, cost, and latency
for cost auditing — to a local rotating file, AWS CloudWatch Logs, or
both — without touching the code at each call site.

## Why this is "production-grade" vs. task 7's callback handler

| task7 (`CustomCallbackHandler`)         | task9 (`TrackedLLMClient`)                          |
|-------------------------------------------|-------------------------------------------------------|
| Tied to LangChain's callback system      | Works with any OpenAI-compatible client directly       |
| Logs only successful calls               | Logs successes **and** failures (failed-but-billed requests still get audited) |
| Simple append-only text file             | JSON-lines format, with automatic log rotation          |
| One backend (local file)                 | Pluggable backends: file, CloudWatch, or both           |
| No request tracing                       | Every request gets a unique `request_id` (UUID)         |
| No latency tracking                      | Measures and logs latency per request                   |
| Hardcoded destination                    | Backend chosen via environment variables — same code runs locally or in production |

## Architecture

```
your code
   |
   v
TrackedLLMClient.chat_completion(model, messages, ...)
   |
   |-- calls the real client.chat.completions.create(...)
   |-- measures latency
   |-- extracts prompt/completion/total tokens from the response
   |-- calculates cost from a per-model pricing table
   |-- builds a UsageRecord (request_id, timestamp, tokens, cost, latency, status)
   |
   v
dispatches the UsageRecord to every configured backend:
   |-- FileLogBackend       -> usage_log.jsonl (rotates automatically)
   `-- CloudWatchLogBackend -> AWS CloudWatch Logs (optional)
```

If the underlying API call raises an exception, `TrackedLLMClient` still
logs a record (with `status="error"` and the error message) before
re-raising — so a failed request that still consumed tokens/quota doesn't
silently disappear from your audit trail.

## Files

| File               | Purpose                                                     |
|---------------------|----------------------------------------------------------------|
| `usage_logger.py`  | Core module — `UsageRecord`, both backends, `TrackedLLMClient` |
| `demo.py`          | Example: wraps a real Groq client and asks a question         |
| `requirements.txt` | Python dependencies                                            |
| `secret_key.py`    | Your API key (never commit this file)                          |
| `.gitignore`       | Excludes `secret_key.py` and generated log files               |

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
   (`boto3` is only actually used if you enable the CloudWatch backend —
   it's safe to skip if you only plan to log to a local file.)

3. **Add your API key** in `secret_key.py`.

## Usage

### Local file logging (default)

```
python demo.py --question "What is the capital of France?"
```

Check the result:
```
type usage_log.jsonl
```

Each line is a JSON object like:
```json
{"request_id": "7b000d82-...", "timestamp": "2026-07-15T05:05:24+00:00", "model": "llama-3.3-70b-versatile", "prompt_tokens": 14, "completion_tokens": 22, "total_tokens": 36, "cost_usd": 0.0, "latency_ms": 412.7, "status": "success", "error": null}
```

### Switching to CloudWatch (or both)

Set environment variables before running (PowerShell):
```powershell
$env:LOG_BACKEND = "cloudwatch"
$env:CLOUDWATCH_LOG_GROUP = "/llm/usage"
$env:CLOUDWATCH_LOG_STREAM = "requests"
$env:AWS_REGION = "us-east-1"
python demo.py --question "What is the capital of France?"
```

This requires valid AWS credentials to be available (via `aws configure`,
environment variables, or an IAM role if running on AWS infrastructure
like EC2/Lambda). The wrapper auto-creates the log group and stream if
they don't already exist.

To log to **both** a local file and CloudWatch at once:
```powershell
$env:LOG_BACKEND = "both"
```

## Using it in your own code

```python
from openai import OpenAI
from usage_logger import TrackedLLMClient, FileLogBackend

raw_client = OpenAI(api_key="...", base_url="https://api.groq.com/openai/v1")
client = TrackedLLMClient(raw_client, backends=[FileLogBackend()])

response = client.chat_completion(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

Every call through `client.chat_completion(...)` is logged automatically —
there's nothing extra to remember at each call site, which is the point of
a wrapper like this in a real production codebase.

## Notes on extending this further

- **Async support**: mirror `TrackedLLMClient` with an `AsyncTrackedLLMClient`
  wrapping `AsyncOpenAI`, using `await client.chat.completions.create(...)`.
- **Streaming**: for `stream=True` calls, token usage typically only
  arrives in the final chunk — you'd accumulate content across the stream
  and log once the stream completes.
- **Alerting**: add a backend that checks `cost_usd` against a threshold
  and sends a Slack/email alert if a single request costs unexpectedly
  more than expected.
- **Batching CloudWatch writes**: for high-volume production use, batch
  multiple `UsageRecord`s into a single `put_log_events` call instead of
  one API call per request, to avoid CloudWatch rate limits.