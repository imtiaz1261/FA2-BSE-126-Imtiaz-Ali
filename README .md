# Task 3 — Real-Time Streaming CLI Chatbot

A command-line chatbot built with the OpenAI SDK's async client that streams
the model's reply token-by-token as it's generated, instead of waiting for
the full response.
<img width="517" height="233" alt="Screenshot 2026-07-08 165408" src="https://github.com/user-attachments/assets/53fe2b7b-0860-47b8-a09d-7221ec3e3912" />
<img width="594" height="328" alt="Screenshot 2026-07-08 165705" src="https://github.com/user-attachments/assets/f221b667-5302-4ec0-ac32-5de1330d16d0" />

## What it demonstrates

- `AsyncOpenAI` client with `stream=True`
- `async for` loop consuming a streaming response
- Multi-turn conversation history
- Works with any OpenAI-compatible provider (Groq for free, or OpenAI)

## Files

| File               | Purpose                                         |
|--------------------|--------------------------------------------------|
| `chatbot.py`       | Main script — run this                          |
| `requirements.txt` | Python dependencies                             |
| `secret_key.py`    | Your API key (never commit this file)           |
| `.gitignore`       | Keeps `secret_key.py` out of version control     |

## Setup

1. **Create and activate a virtual environment**
   ```
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```
   (macOS/Linux: `source venv/bin/activate`)

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Add your API key**

   Get a free key at [console.groq.com/keys](https://console.groq.com/keys)
   (no credit card required), then open `secret_key.py` and set:
   ```python
   GROQ_API_KEY = "gsk_your_real_key_here"
   ```

## Usage

Run with the free Groq provider (default):
```
python chatbot.py
```

Use OpenAI instead (requires `OPENAI_API_KEY` in `secret_key.py`):
```
python chatbot.py --provider openai
```

Use a different model:
```
python chatbot.py --model llama-3.1-8b-instant
```

Type your message and press Enter. The reply streams in live. Type `exit`
or `quit` to end the session.

## Example

```
Streaming chatbot ready (model: llama-3.3-70b-versatile). Type 'exit' or 'quit' to leave.

You: what is recursion?
Assistant: Recursion is when a function calls itself to solve a smaller
version of the same problem, until it reaches a base case that stops it.
```

## Notes

- Conversation history resets each time you restart the script.
- If a request fails (e.g. rate limit), the failed turn is dropped from
  history so the conversation stays in a clean state.
