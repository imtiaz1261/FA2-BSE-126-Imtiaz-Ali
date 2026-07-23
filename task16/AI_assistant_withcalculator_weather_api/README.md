# AI Assistant with Calculator and Weather Tools

A conversational AI assistant that answers general questions, does math, and
checks the weather — via natural language. Built with Groq (fast, free-tier
Llama models with OpenAI-compatible function calling), a safe custom
calculator, and the OpenWeatherMap API. Includes both a CLI and a Streamlit
web UI.

## Features

- Natural language chat, powered by Llama 3.3 70B on Groq
- **Calculator tool**: safe expression evaluation (arithmetic, powers, roots,
  trig, logs, factorials) — no `eval()`, so it can't execute arbitrary code
- **Weather tool**: current conditions or a ~24h forecast for any city, via
  OpenWeatherMap
- Automatic tool selection: the model decides when a question needs a tool
  vs. a plain conversational answer
- Rolling conversation memory (last 10 exchanges by default)
- Error handling throughout: bad expressions, unknown cities, missing keys,
  network failures, and API errors all return friendly messages instead of
  crashing
- Both a terminal (CLI) interface and a Streamlit web interface

## Project structure

```
ai-assistant/
├── assistant/
│   ├── __init__.py
│   ├── tools.py     # calculate() and get_weather()
│   ├── agent.py      # Assistant class: LLM + tool calling + memory
│   └── cli.py         # terminal interface
├── app.py              # Streamlit web interface
├── requirements.txt
├── .env                # your real keys (already filled in, see note below)
├── .env.example       # template for sharing/version control
└── .gitignore
```

## Setup

1. **Install dependencies** (Python 3.10+ recommended):

   ```bash
   pip install -r requirements.txt
   ```

2. **API keys**: a `.env` file is already included with the keys you gave me:

   - `GROQ_API_KEY` — from https://console.groq.com/keys (free, no card needed)
   - `OPENWEATHER_API_KEY` — from https://home.openweathermap.org/api_keys

   ⚠️ **Security note**: these keys were pasted into our chat, so treat them
   as semi-exposed. Before using this project long-term or pushing it
   anywhere public, regenerate both keys and drop the new ones into `.env`.
   Never commit `.env` — it's already in `.gitignore`.

   Note: brand-new OpenWeatherMap keys can take up to ~2 hours to activate.
   If weather queries fail with an "invalid key" error at first, that's why —
   just retry later.

## Running it

**CLI:**

```bash
python -m assistant.cli
```

**Web UI:**

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

## Example queries to try

- "What is 245 × 78?"
- "Calculate the square root of 625."
- "What's the weather in Lahore today?"
- "Will it rain tomorrow in Karachi?"
- "Who invented Python?"
- "Summarize the benefits of machine learning."
- "reset" (CLI only — clears memory)

## How it works

1. Your message + recent conversation history is sent to the Llama model on
   Groq, along with two tool definitions (`calculate`, `get_weather`).
2. The model decides whether the question needs a tool. If yes, it returns a
   structured tool call (e.g. `get_weather(location="Lahore")`) instead of
   text.
3. The Python code runs the actual tool function and sends the result back
   to the model.
4. The model turns that raw result into a natural-language reply, which is
   shown to you and saved to memory for context in later turns.

This is the standard "function calling" pattern used by agentic AI systems —
no manual keyword matching or regex intent detection required; the LLM
handles intent recognition itself.

## Extending it

- **Add a tool**: write a function in `tools.py` that returns
  `{"success": bool, ...}`, add its JSON schema to `TOOLS` in `agent.py`, and
  register it in `_TOOL_IMPL`.
- **Swap the LLM provider**: `agent.py` isolates all Groq-specific code in
  `Assistant.ask()`. Swapping to OpenAI or Anthropic means changing the
  client init and the `chat.completions.create` call to match that
  provider's SDK — the tool schemas and dispatch logic stay the same.
- **Persist memory across restarts**: currently memory lives in-process
  (`self.history` / Streamlit's `session_state`). To persist it, serialize
  `assistant.history` to a file or database between runs.
