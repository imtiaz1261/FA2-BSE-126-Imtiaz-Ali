# 🤖 Multi-Agent AI Research Assistant

A production-ready, ChatGPT-style web application built with **Streamlit** and **LangGraph**. Three specialised AI agents — Researcher, Writer, and Editor — collaborate to deliver polished, well-sourced answers to any research query.

---

## ✨ Features

| Feature | Details |
|---|---|
| 💬 ChatGPT-style chat | Native `st.chat_message` bubbles, user right / AI left |
| ⚡ Streaming responses | Token-by-token typing effect via `st.write_stream` |
| 🤖 Live agent progress | Real-time `st.status` cards for each agent while processing |
| 🔄 Regenerate | Re-run the last query with one click |
| 👍 👎 Feedback | Like / Dislike buttons on every assistant message |
| 📋 Copy response | Expandable code block for easy copy-paste |
| 🕘 Conversation history | Full multi-turn memory with search, rename, delete |
| 📥 Export | Download chats as Markdown, TXT, PDF, or DOCX |
| 🌙 Dark / Light mode | Toggle in sidebar or Settings page |
| ⚙️ Settings page | Model selector, temperature, max tokens, streaming toggle |
| ℹ️ Info panel | Execution time, token usage, cost estimate, sources |
| 📱 Responsive | Adapts cleanly to desktop and tablet |

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌──────────────────────────────────────────────────┐
│                Streamlit Frontend                 │
│  sidebar ── chat area ── agent panel ── input    │
└─────────────────────┬────────────────────────────┘
                      │  _call_backend(query)
                      ▼
┌──────────────────────────────────────────────────┐
│            LangGraph Supervisor Graph             │
└───────┬──────────────┬──────────────┬────────────┘
        ▼              ▼              ▼
  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │Researcher│──▶│  Writer  │──▶│  Editor  │
  │  Agent   │   │  Agent   │   │  Agent   │
  └──────────┘   └──────────┘   └──────────┘
  Tavily Search   GPT-4o Draft   GPT-4o Review
                                      │
                                      ▼
                               Final Response
```

---

## 📁 Project Structure

```
multi_agent_research_assistant/
│
├── app.py                      # Main entrypoint — run this
│
├── components/                 # Reusable UI components
│   ├── agent_panel.py          # Live st.status pipeline + idle summary
│   ├── chat_input.py           # Native st.chat_input, pending & regenerate
│   ├── chat_message.py         # st.chat_message bubbles + streaming
│   ├── info_panel.py           # Right-side workflow / token / sources panel
│   ├── sidebar.py              # Full sidebar: history, export, settings
│   └── welcome_screen.py       # Empty-state screen + suggestion cards
│
├── pages/                      # Full-page views
│   ├── settings_page.py        # Model, generation, appearance settings
│   └── about_page.py           # Architecture, agents, tech stack
│
├── styles/
│   └── theme.py                # LIGHT/DARK palettes + compiled CSS
│
├── utils/
│   ├── session.py              # Session state init + all CRUD helpers
│   ├── export.py               # MD / TXT / PDF / DOCX export (bytes)
│   └── formatters.py           # Timestamps, token counts, cost estimates
│
├── agents/                     # ← Wire your LangGraph agents here
├── graph/                      # ← Wire your LangGraph graph here
├── config/
│   ├── settings.py             # Pydantic settings (reads .env)
│   └── logging_config.py
│
├── .env                        # API keys (never commit)
├── .env.example                # Template
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & enter the project

```bash
git clone <your-repo-url>
cd multi_agent_research_assistant
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4o-mini
```

### 5. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🔌 Backend Integration

The frontend is fully decoupled from the AI backend. Connect your LangGraph pipeline in **one place** — `app.py`, function `_call_backend()`:

```python
# app.py  ──  find the  # ── BACKEND HOOK ──  comment

def _call_backend(query: str) -> str:
    # Replace this mock with your real pipeline:
    from graph.research_graph import run_research
    result = run_research(query)
    return result["final_response"]
```

### Streaming support

Return a **generator** from `_call_backend()` for true token-by-token streaming:

```python
def _call_backend(query: str):
    from graph.research_graph import stream_research
    return stream_research(query)   # yields str chunks
```

`stream_assistant_response()` in `components/chat_message.py` handles both `str` and `Generator[str]` transparently.

### Agent status updates

Call these helpers from inside your graph nodes to drive the live progress panel:

```python
from utils.session import set_agent_status, update_workflow_info

# Inside your Researcher node:
set_agent_status("researcher", "running")
# ... do work ...
set_agent_status("researcher", "done")
update_workflow_info(sources=["https://..."])

# Inside your Writer node:
set_agent_status("writer", "running")
# ... do work ...
set_agent_status("writer", "done")

# Inside your Editor node:
set_agent_status("editor", "running")
# ... do work ...
set_agent_status("editor", "done")
update_workflow_info(
    execution_time=2.4,
    token_usage={"prompt": 800, "completion": 600, "total": 1400},
)
```

---

## 🖥️ Interface Walkthrough

### Welcome Screen
Shown when no conversation exists. Displays feature cards and 6 clickable suggestion prompts that auto-populate the chat input.

### Chat Page
```
┌─────────────────────────────────┬──────────────────┐
│  🧑 User message (right-aligned) │  ℹ️ Workflow Info  │
│                                  │  Active Agent    │
│  🤖 AI response (left-aligned)   │  Status          │
│     📋 👍 👎 🔄  action row      │  Time Elapsed    │
│                                  │  Token Usage     │
│  ─────────────────────────────   │  Sources         │
│  🤖 Agent Pipeline               │                  │
│    🔍 Researcher  ✅ Complete     │                  │
│    ✍️ Writer      ✅ Complete     │                  │
│    📝 Editor      ✅ Complete     │                  │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 3/3           │                  │
│                                  │                  │
│  [ Ask anything…            ➤ ]  │                  │
└─────────────────────────────────┴──────────────────┘
```

### Live Agent Panel (during processing)
Each agent shows an expandable `st.status` card that updates in real-time:
```
⚙️ 🔍 Researcher Agent — Searching trusted sources…
   Querying search engine and retrieving sources…

✅ Researcher Agent — Research complete

⚙️ ✍️ Writer Agent — Generating first draft…
   Composing a well-structured response…

✅ Writer Agent — Draft complete

⚙️ 📝 Editor Agent — Reviewing and polishing…
   Checking accuracy, clarity, and completeness…

✅ Editor Agent — Final response ready
```

### Sidebar
- **➕ New Chat** — starts a fresh conversation
- **🔍 Search** — filter conversations by title
- **💬 History** — click to switch, ✏️ rename, 🗑️ delete
- **📥 Export** — Markdown / TXT / PDF / DOCX download buttons
- **⚙️ Settings** — dark mode, panel toggles, model picker
- **⚠️ Danger Zone** — clear all conversations

---

## ⚙️ Settings

| Setting | Default | Description |
|---|---|---|
| Provider | `openai` | `openai` / `gemini` / `ollama` |
| Model | `gpt-4o-mini` | Selected per provider |
| Temperature | `0.7` | 0.0 = deterministic, 2.0 = creative |
| Max Tokens | `4096` | Maximum response length |
| Streaming | `true` | Token-by-token display |
| Dark Mode | `false` | Light / dark theme |
| Font Size | `Medium` | Small / Medium / Large |
| Agent Panel | `true` | Show pipeline status below chat |
| Info Panel | `true` | Show right-side workflow panel |

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `streamlit` | ≥ 1.46 | Web framework |
| `langchain` | 0.3.25 | LLM application framework |
| `langgraph` | 0.4.8 | Multi-agent orchestration |
| `langchain-openai` | 0.3.19 | OpenAI integration |
| `langchain-google-genai` | 2.1.5 | Gemini integration |
| `tavily-python` | 0.5.4 | Web search |
| `openai` | 1.93.0 | OpenAI SDK |
| `pydantic` | 2.11.7 | Settings validation |
| `reportlab` | 4.4.1 | PDF export |
| `python-docx` | 1.1.2 | DOCX export |
| `python-dotenv` | 1.1.1 | .env loading |

Install all with:
```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes (if using OpenAI) | `sk-...` |
| `GOOGLE_API_KEY` | Yes (if using Gemini) | Google AI Studio key |
| `TAVILY_API_KEY` | Yes | Web search API key |
| `DEFAULT_LLM_PROVIDER` | No | `openai` / `gemini` / `ollama` |
| `DEFAULT_MODEL` | No | e.g. `gpt-4o-mini` |
| `TEMPERATURE` | No | Default `0.7` |
| `MAX_TOKENS` | No | Default `4096` |
| `LANGCHAIN_TRACING_V2` | No | `true` to enable LangSmith |
| `LANGCHAIN_API_KEY` | No | LangSmith key |

---

## 🧩 Extending the App

### Add a new suggestion prompt
Edit `components/welcome_screen.py` → `SUGGESTED_PROMPTS` list.

### Add a new export format
Edit `utils/export.py` → add a new function and entry to `EXPORT_OPTIONS`.

### Add a new settings section
Edit `pages/settings_page.py` → add a `_section_*()` function and call it in `render_settings_page()`.

### Add a fourth agent
1. Add it to `_AGENTS` in `components/agent_panel.py`.
2. Add a status call in `run_pipeline_with_status()`.
3. Call `set_agent_status("your_agent", "running/done")` in your graph node.

---

## 🐛 Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: streamlit` | Run `pip install streamlit` |
| `No space left on device` during install | Run `pip cache purge` then retry |
| App shows blank page | Check terminal for errors; ensure `.env` is configured |
| PDF export fails | Run `pip install reportlab` |
| DOCX export fails | Run `pip install python-docx` |
| Agents stuck on "running" | Backend raised an exception — check the activity log |

---

## 📄 License

MIT License — see `LICENSE` file for details.

---

## 🙏 Acknowledgements

- [Streamlit](https://streamlit.io) — the web framework
- [LangGraph](https://github.com/langchain-ai/langgraph) — multi-agent orchestration
- [LangChain](https://langchain.com) — LLM application toolkit
- [Tavily](https://tavily.com) — real-time web search API
- [OpenAI](https://openai.com) — language model provider
# from the project directory
streamlit run app.py
