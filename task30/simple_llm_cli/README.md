# Simple LLM CLI

A minimal command-line tool: type a question, get an LLM's answer printed
back in the terminal. Uses Groq's free, OpenAI-compatible API by default.

## Setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Add your API key

```bash
# Windows
copy .env.example .env
# macOS/Linux
cp .env.example .env
```

Open `.env` and fill in:

```
GROQ_API_KEY=gsk_your_real_key_here
```

Get a free key (no credit card required) at:
https://console.groq.com/keys

> **Never commit your real `.env` file or paste your API key into chats,
> docs, or screenshots.** Anyone who sees the key can use it on your
> account. `.env` is already excluded via `.gitignore` for this reason —
> only `.env.example` (with blanks) should ever be shared or committed.

## Run

```bash
python ask_llm.py
```

Example session:

```
Simple LLM CLI — provider: groq, model: llama-3.1-8b-instant
Type your question and press Enter. Type 'exit' or 'quit' to stop.

You: What does LLM mean?

LLM: LLM stands for Large Language Model...

You: exit
Goodbye!
```

## Switching to OpenAI instead of Groq

Edit `.env`:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-real-openai-key
MODEL_NAME=gpt-4o-mini
```

Note OpenAI is a paid API — Groq is free with generous rate limits, which
is why it's the default here.

## Troubleshooting

- **"GROQ_API_KEY is missing"** — you forgot to fill in `.env`, or you're
  running the script from a different folder than the one containing it.
- **401 / authentication error** — the key is wrong, expired, or was
  revoked (e.g. because it was accidentally shared somewhere public —
  rotate it at https://console.groq.com/keys if so).
- **Model not found** — check https://console.groq.com/docs/models for
  currently available free models and update `MODEL_NAME` in `.env`.
