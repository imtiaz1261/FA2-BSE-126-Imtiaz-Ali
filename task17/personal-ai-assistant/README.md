# Personal AI Assistant Using Tools

A conversational AI assistant that understands natural language and
automatically decides which tool to use — calculator, weather, web
search, file reading (RAG), notes, or reminders — while keeping track
of conversation context. Built with LangChain's tool-calling agent
pattern and Groq for fast, free LLM inference.

---

## 1. Architecture

```
                     ┌─────────────────────┐
   User (text/voice) │                     │
   ─────────────────▶│   main.py (CLI)     │
                      │  loop: input→agent  │
                      │  →print/speak output│
                      └─────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │     memory.py         │  conversation buffer
                     │  (RAM + SQLite log)   │  (context-aware turns)
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │      agent.py         │  ChatGroq +
                     │ tool-calling agent    │  create_tool_calling_agent
                     └──────────┬───────────┘
                                │ decides which tool(s) to call
        ┌──────────┬──────────┼───────────┬────────────┬─────────────┐
        ▼          ▼          ▼           ▼            ▼             ▼
  calculator_  weather_   search_    file_tool.py   notes_tool.py  reminder_
  tool.py      tool.py    tool.py    (RAG via        (SQLite)      tool.py
  (safe AST     (Open-      (Duck-    rag/*.py)                     (SQLite)
   eval)        Meteo,      Duck                                    
                no key)     Go, no                                  
                            key)
```

**Full request flow example** — "What's the weather in Islamabad?":
1. `main.py` reads the input, adds it to `memory.py`.
2. `agent.py`'s Groq LLM sees the message + tool list, decides to call
   `weather(location="Islamabad")`.
3. `tools/weather_tool.py` geocodes "Islamabad" via Open-Meteo, fetches
   the current forecast, returns a formatted string.
4. The LLM turns that tool result into a natural sentence.
5. `main.py` prints it (and speaks it aloud if `--voice` is on) and logs
   it to memory.

---

## 2. Project structure

```
personal-ai-assistant/
│
├── main.py                    # CLI entry point / conversation loop
├── agent.py                    # Builds the Groq tool-calling agent
├── memory.py                   # Conversation memory (RAM + SQLite)
├── db.py                       # SQLite: notes, reminders, chat log
├── config.py                   # All settings, from .env
├── utils.py                    # Logging setup
│
├── tools/
│   ├── __init__.py              # ALL_TOOLS registry
│   ├── calculator_tool.py        # Safe AST-based arithmetic
│   ├── weather_tool.py           # Open-Meteo (free, no key)
│   ├── search_tool.py            # DuckDuckGo search (free, no key)
│   ├── file_tool.py              # Read/summarize/query PDF/DOCX/TXT
│   ├── notes_tool.py             # save/list/delete notes
│   └── reminder_tool.py          # create/list/delete reminders
│
├── rag/
│   ├── loader.py                 # PDF/DOCX/TXT extraction + metadata
│   ├── splitter.py               # RecursiveCharacterTextSplitter
│   └── vector_store.py           # Per-file in-memory Chroma index
│
├── voice/
│   ├── speech_to_text.py         # Microphone input (SpeechRecognition)
│   └── text_to_speech.py         # Offline TTS (pyttsx3)
│
├── data/                        # Put PDFs/DOCX/TXT files here
│   └── sample_notes.txt
├── db/                          # assistant.db (SQLite, auto-created)
├── vector_store/                 # (reserved; per-file indexes are in-memory)
├── logs/                        # assistant.log (auto-created)
│
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore
```

---

## 3. Setup

```bash
python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set your key (the **only** required secret):
```
GROQ_API_KEY=gsk_...
```
Get a free key, no credit card, at https://console.groq.com/keys.
Everything else — embeddings, weather, web search, TTS — is free/local
and needs no key.

### Voice dependencies (optional but included by default)
`pyaudio` (needed by `SpeechRecognition` for microphone access) can be
finicky to install:
- **Windows:** `pip install pyaudio` usually just works from a wheel.
- **macOS:** `brew install portaudio` first, then `pip install pyaudio`.
- **Linux:** `sudo apt install portaudio19-dev python3-pyaudio` first.

If you don't need voice, just run without `--voice` — the assistant
works fully in text mode with zero extra setup.

---

## 4. Usage

```bash
python main.py                     # text chat
python main.py --voice              # speak to it, hear it reply
python main.py --session work       # named session (separate memory/history)
```

Example commands:
```
You: Calculate 125 * 48
You: What's the weather in Islamabad today?
You: Search the latest AI news
You: Summarize sample_notes.txt
You: Save this note: buy groceries on Friday
You: Create a reminder for tomorrow at 9 AM to call the bank
You: Who is the CEO of Microsoft?
```
Type `exit` or `quit` to leave the loop.

---

## 5. Component explanations

**agent.py (tool calling)** — Uses LangChain's `create_tool_calling_agent`,
which relies on the LLM's native function-calling ability: Groq's Llama
3.x models receive the full tool list + their JSON schemas (auto-derived
from each `@tool`-decorated function's docstring and type hints) and
decide which to call, with what arguments, purely from the user's
phrasing — no manual intent classification needed.

**memory.py (conversation memory)** — Keeps a sliding window of recent
messages in RAM for the current session (fed into the agent prompt as
`chat_history`) and durably logs every turn to SQLite via `db.py`, so a
session can optionally be resumed later with `--session <same-id>`.

**tools/calculator_tool.py** — Parses expressions into a Python AST and
walks it with a strict operator whitelist, rather than calling `eval()`
on user text — this avoids arbitrary code execution from a crafted prompt.

**tools/weather_tool.py** — Two free Open-Meteo calls: geocode the place
name to coordinates, then fetch current conditions. No API key required.

**tools/search_tool.py** — Wraps `ddgs` (DuckDuckGo search) for current
events / factual lookups the model shouldn't answer from memory alone.

**tools/file_tool.py + rag/** — Implements Retrieval-Augmented Generation
for local files: `loader.py` extracts text + metadata (page/paragraph),
`splitter.py` chunks it, `vector_store.py` embeds chunks with a local
Sentence Transformers model and builds an in-memory Chroma index per
file (cached for the session). A question routes to a similarity search;
a bare "summarize this" routes to the (truncated) full text.

**tools/notes_tool.py / reminder_tool.py** — Simple SQLite-backed CRUD.
Reminder times are parsed from natural language ("tomorrow at 9 AM")
using `dateparser`.

**voice/** — `speech_to_text.py` captures microphone audio and
transcribes it (Google's free public Web Speech endpoint via
`SpeechRecognition`, no key but needs internet); `text_to_speech.py`
speaks answers aloud fully offline via `pyttsx3`. Both fail gracefully
(falls back to typed input / silently skips speaking) if hardware or
drivers aren't available, rather than crashing the assistant.

---

## 6. Error handling

- Missing `GROQ_API_KEY` → clear startup message, doesn't crash mid-chat
- Unknown/misspelled file name → lists available files in `data/`
- Empty or scanned/image-only PDF → explicit "no extractable text" error
- Weather: unrecognized location → clear message, no stack trace
- Search: package missing / request failure → caught and reported as text
- Calculator: unsupported operators, division by zero, malformed input
  → caught, safe error message returned instead of crashing
- Reminder: unparseable time phrase → explicit suggestion of valid formats
- Microphone/audio unavailable → voice mode falls back to typed input;
  TTS failures are logged and silently skipped
- All tool errors are returned as text so the agent can explain the
  problem to the user in natural language instead of the app crashing

---

## 7. Known limitations / scope notes

- **Reminders are stored, not scheduled** — there's no background job
  that fires a notification at the reminder time; `list_reminders` shows
  what's upcoming. See future improvements below for adding a scheduler.
- **Voice STT uses a free public endpoint** (not a paid API), which is
  fine for personal use but is rate-limited and requires internet even
  though TTS is fully offline.
- **File RAG indexes are in-memory per process**, not persisted to disk
  between runs — re-asking about the same file in a new run re-embeds it
  (fast for typical documents with a local embedding model, but worth
  knowing).
- **Groq's tool-calling can intermittently emit a malformed tool call**
  (the tool name gets concatenated with its JSON arguments), surfacing
  as `Failed to call a function` or `... which was not in request.tools`.
  This is a known quirk of the provider/model combination, not a bug in
  the request. `main.py` automatically retries a couple of times on this
  specific error before giving up, which resolves it in almost all cases.
  If it persists, try lowering `LLM_TEMPERATURE` further (already
  defaults to `0.0`) or switching `GROQ_MODEL` to `llama-3.1-8b-instant`.

---

## 8. Future improvements

- [ ] Actual reminder notifications via APScheduler + OS notifications
- [ ] FastAPI backend + Streamlit or web front-end (currently CLI-only)
- [ ] Persist per-file vector indexes to disk so they survive restarts
- [ ] Multi-user support (separate SQLite rows / vector spaces per user)
- [ ] Streaming responses token-by-token
- [ ] Swap DuckDuckGo for Tavily/SerpAPI for higher-quality search results
- [ ] Local LLM support via Ollama as a fallback when offline
- [ ] Wake-word detection for hands-free voice activation

---

## 9. Tech stack

Python · LangChain (tool-calling agent) · Groq API (LLM) · ChromaDB +
Sentence Transformers (file RAG) · DuckDuckGo Search · Open-Meteo API ·
SQLite · SpeechRecognition · pyttsx3 · pypdf · python-docx · dateparser
· python-dotenv