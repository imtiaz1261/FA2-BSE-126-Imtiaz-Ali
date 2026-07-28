# Multi-Step Research Assistant Using LangGraph

A production-style research assistant that plans, searches, validates,
summarizes, and writes a structured report for any research question --
built as a stateful LangGraph workflow with conditional retry logic,
error recovery, and checkpointing. Groq powers the LLM steps; DuckDuckGo
powers web search (both free, and only Groq needs an API key). Ships
with both a FastAPI backend and a Streamlit frontend.

---

## 1. LangGraph workflow

```
        START
          |
          v
     +---------+
     | planner  |  decomposes query -> objective + task list
     +----+----+
          |
          v
   +-------------+
   |  web_search   |<--------------------+
   +------+------+                       |
          |                              | retry (insufficient,
          v                              | retries remain)
   +-------------+                       |
   |  validator    |-----------------------+
   +------+------+
          | done (all tasks validated
          | or retries exhausted)
          v
   +-------------+
   | summarizer    |  per-task summaries + combined summary
   +------+------+
          |
          v
   +----------------+
   | report_generator |  structured Markdown report
   +------+---------+
          |
          v
         END
```

- **Conditional edges**: `route_after_validation()` inspects
  `state["route_decision"]` (set by the validator) and routes back to
  `web_search` (retry same task, or move to the next task) or forward
  to `summarizer` (all tasks done).
- **Retry logic**: the validator tracks a per-task retry counter and
  loops back to `web_search` up to `MAX_RETRIES_PER_TASK` times when
  an LLM judge (with a heuristic fallback) decides the collected
  sources are insufficient.
- **Error handling/recovery**: every node is wrapped by `_safe_node()`
  (`graph/build.py`), which catches unexpected exceptions, logs them
  into `state["errors"]`, and returns a safe update -- so one bad node
  can't crash the whole run. The validator wrapper also guarantees a
  safe `route_decision` on failure, preventing infinite loops.
- **Checkpointing**: the compiled graph uses LangGraph's `MemorySaver`
  checkpointer, keyed by a `thread_id` per run, so a run's state is
  persisted in memory and could be inspected/resumed via the same id.
- **Node execution logging**: every node appends a timestamped entry
  to `state["node_log"]`, giving a full audit trail of the run.

---

## 2. Project structure

```
research-assistant/
|
├── main.py                 # CLI: run one query end-to-end
├── api.py                   # FastAPI backend
├── streamlit_app.py          # Streamlit frontend (calls the API)
├── state.py                  # ResearchState TypedDict (shared graph state)
├── llm.py                    # Shared Groq LLM accessor
├── config.py                  # Settings from .env
├── utils.py                   # Logging setup
|
├── graph/
│   ├── nodes.py                # planner, web_search, validator, summarizer,
│   │                            # report_generator + route_after_validation
│   └── build.py                 # StateGraph assembly, _safe_node wrapper,
│                                  # checkpointing, Mermaid diagram export
|
├── tools/
│   └── search_tool.py            # DuckDuckGo search + URL dedup
|
├── report/
│   └── report_builder.py          # Markdown report assembly + PDF/DOCX export
|
├── outputs/                    # Generated reports land here
├── logs/                       # research_assistant.log
|
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

Edit `.env` and set your key (the only required secret):
```
GROQ_API_KEY=gsk_...
```
Free, no credit card: https://console.groq.com/keys. Web search
(DuckDuckGo) needs no key.

---

## 4. Usage

### CLI (simplest way to try it)
```bash
python main.py "What are the latest advances in solid-state batteries?"
python main.py "..." --format pdf
python main.py "..." --format docx
python main.py --mermaid          # print the workflow diagram as Mermaid syntax
```

### FastAPI + Streamlit (both, per your setup)
Run each in its own terminal:
```bash
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
streamlit run streamlit_app.py
```
Then open the Streamlit URL it prints (usually http://localhost:8501),
type a research question, and click **Run Research**. Tabs show the
report, the full node-by-node execution log, and the generated task
list; buttons let you download the report as PDF or DOCX.

### API directly
```bash
curl -X POST http://127.0.0.1:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest advances in solid-state batteries?"}'

curl "http://127.0.0.1:8000/report/<run_id>/export?fmt=pdf" -o report.pdf
curl http://127.0.0.1:8000/graph/mermaid
```

---

## 5. Report structure

Every generated report contains:
`Title` - `Executive Summary` - `Research Objectives` - `Key Findings` -
`Detailed Analysis` - `Supporting Evidence` - `References & Sources` -
`Conclusion` - `Future Recommendations`

The five narrative sections (Executive Summary, Key Findings, Detailed
Analysis, Conclusion, Future Recommendations) are drafted by the LLM in
a single call, **grounded strictly in the collected, validated task
summaries** -- it's explicitly instructed not to add outside knowledge.
`References & Sources` is assembled **programmatically** from the
actual collected URLs (never LLM-generated), so citations can't be
hallucinated.

---

## 6. Error handling

- Missing `GROQ_API_KEY` -> clear error at startup, not mid-run
- Planner LLM call fails/returns bad JSON -> falls back to a single-task
  plan using the raw query, rather than crashing
- Web search failures -> logged into `state["errors"]`, task proceeds
  with whatever results (if any) were already collected
- Validator LLM judgment fails -> falls back to a simple heuristic
  (result count threshold) instead of blocking the workflow
- Any node's unexpected exception -> caught by `_safe_node`, logged,
  and the graph continues (or terminates gracefully) instead of crashing
- Report generation failure -> falls back to a minimal report containing
  the raw combined summary, with the error noted in a "Notes" section
- Empty research query -> rejected with a clear message (CLI and API)

---

## 7. Known limitations / scope notes

- **Bonus features not implemented** (to keep scope honest): streaming
  intermediate reasoning token-by-token to the frontend, human-in-the-loop
  approval before final report generation, automatic source credibility
  scoring, and cross-session conversation memory for follow-up research
  questions. See Future improvements below.
- **Validation quality** relies partly on LLM judgment of "sufficiency",
  which is inherently approximate -- it's paired with a cheap heuristic
  (minimum result count) so a failed/malformed LLM judgment call never
  blocks the workflow entirely.
- **Checkpointing is in-memory** (`MemorySaver`) -- state doesn't survive
  a process restart. Swap in `SqliteSaver` or `PostgresSaver` from
  `langgraph-checkpoint-sqlite` / `-postgres` for durable persistence.

---

## 8. Future improvements

- [ ] Streaming intermediate reasoning to the frontend (LangGraph's
      `.stream()` API + Streamlit's streaming UI primitives)
- [ ] Human-in-the-loop approval step before report generation
      (LangGraph supports interrupt-before-node natively)
- [ ] Automatic source credibility scoring (domain reputation heuristics
      or an LLM-based credibility judge)
- [ ] Conversation memory across research sessions for follow-up questions
- [ ] Persistent checkpointing (SQLite/Postgres) instead of in-memory
- [ ] Swap DuckDuckGo for Tavily/SerpAPI for higher-quality search results
- [ ] Multi-source citation clustering/dedup by claim, not just by URL
- [ ] Rendered (image) LangGraph diagram in the Streamlit sidebar, not
      just Mermaid text

---

## 9. Tech stack

Python - LangGraph - LangChain - Groq API - DuckDuckGo Search - FastAPI -
Streamlit - Pydantic - ReportLab (PDF) - python-docx (DOCX) -
python-dotenv
pip install -r requirements.txt
cp .env.example .env       # paste your GROQ_API_KEY in
python main.py "your research question"          # CLI
# or, in two terminals:
uvicorn api:app --port 8000
streamlit run streamlit_app.py