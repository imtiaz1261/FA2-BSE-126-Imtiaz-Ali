# Groq API Retry Logic with Tenacity

Adds automatic retry handling to an LLM API call.

## Features
- 3 total attempts
- Rate-limit (HTTP 429) retry
- Server error (HTTP 5xx) retry
- Exponential backoff
- `.env` API-key protection

## Setup (Windows)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Run:

```powershell
python app.py
```

## Retry configuration

```python
@retry(
    retry=retry_if_exception(retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
```

The backoff increases between failed attempts. Tenacity handles the waiting
automatically.

For production, consider honoring the provider's `Retry-After` header and
adding structured logging.

Never commit `.env` to GitHub. If a real API key has been exposed, rotate it.
