# Code Alpha — Autonomous Spec-Driven Coding Agent (Scaffold)

An in-progress implementation of Code Alpha's core loop:
**Understand → Plan → Generate → Verify → Refine → Human Review**

This repo is a working **skeleton**, not a finished product. Control-flow,
state machine, repo indexing, and spec generation are real and tested.
The parts that need an actual LLM (Coder/Fixer/Planner agent bodies) are
stubbed so the whole pipeline runs offline, with clear swap-in points.

---

## Requirements

- Python 3.10+ (uses `list[str]`-style type hints)
- No external packages required to run the demos. Optional (auto-detected,
  falls back gracefully if missing): `tree_sitter_languages`, `watchdog`

Check your version:
```bash
python --version   # or `python3 --version` on macOS/Linux
```

---

## Quick Start

```bash
# From the project root (the folder containing code_alpha/)
python -m code_alpha.main       # orchestrator: runs the full Plan→Generate→Test→Fix loop
python context_demo.py          # context engine: indexes this repo and queries it
python spec_demo.py             # spec generator: requirements → design → tasks + edit/regen cycle
```

On Windows use `python`, not `python3`, unless you've specifically installed
the `python3` alias. Run these from the folder **containing** `code_alpha/`,
not from inside it.

---

## What Each Demo Proves

| Command | What it demonstrates |
|---|---|
| `python -m code_alpha.main` | Task moves `Planning → Generating → Testing → Fixing → Testing → AwaitingReview`, with retry limits and failure routing enforced by the state machine. |
| `python context_demo.py` | Repo is scanned, Python files parsed via `ast`, chunked by function/class, embedded, and made searchable — `search_code`, `find_usages`, `get_dependency_graph` all return real results from this codebase. |
| `python spec_demo.py` | `requirements.md` → `design.md` → `tasks.md` generated in order; hand-editing `requirements.md` correctly marks `design.md` stale; `regenerate_from()` cascades the fix; every version is preserved under `versions/`. |

---

## Project Structure

```
code_alpha/
├── core/
│   ├── models.py          # Task, TaskState — the data that flows through the pipeline
│   ├── state_machine.py   # Legal state transitions only — enforced centrally
│   └── orchestrator.py    # Drives the loop: retry limits, fix-iteration cap, failure routing
├── agents/
│   └── base.py            # Agent interface + stub Planner/Coder/Fixer
│                           # (swap stub bodies for real Anthropic API calls)
├── context/                # Codebase Context Engine (repo indexing)
│   ├── scanner.py          # File walk + language detection
│   ├── parser.py           # AST parsing (Python via `ast`; regex fallback for others)
│   ├── chunker.py          # Chunk by function/class, not fixed length
│   ├── embeddings.py       # Embedder interface + offline hash-based fallback
│   ├── vector_store.py     # VectorStore interface + in-memory impl + pgvector schema
│   ├── dependency_graph.py # File-level import graph
│   ├── watcher.py          # Incremental re-indexing on file change
│   ├── engine.py           # ContextEngine — ties the above together
│   └── tools.py            # Agent-facing tool schemas (search_code, find_usages, ...)
├── spec/                   # Spec Generator (requirements → design → tasks)
│   ├── prompts.py          # The three generation prompts, as agent instructions
│   ├── store.py            # Versioned file storage under .codealpha/specs/, hash-chain sync
│   └── generator.py        # SpecGenerator — fills prompts, calls the model, regenerates chain
├── sandbox/
│   └── executor.py         # Ephemeral execution + test running (stub; timeout-aware)
├── diff/
│   └── layer.py            # Packages the final diff into a reviewable PR object
└── main.py                 # Entrypoint for the orchestrator demo

context_demo.py             # Self-indexes this repo and exercises every context tool
spec_demo.py                 # Runs the full spec generate/edit/regenerate cycle
```

---

## What's Real vs. What's Stubbed

**Real, tested, and runnable today:**
- Orchestrator control-flow, state machine, retry/fix-iteration limits, failure routing
- Repo scanning, Python AST parsing, function/class-level chunking
- In-memory vector search, symbol usage tracking, dependency graph
- Incremental file-watching (polling fallback if `watchdog` isn't installed)
- Spec doc generation, versioning, and hash-chain staleness detection/regeneration

**Stubbed — swap-in points for the next phase:**
- `agents/base.py` — `Planner`, `Coder`, `Fixer` return placeholder text instead of calling an LLM
- `spec/generator.py` — `_stub_completer()` returns placeholder Markdown instead of calling the Anthropic API
- `sandbox/executor.py` — simulates pass/fail instead of running real tests in a container
- `context/embeddings.py` — `HashEmbedder` is a dependency-free stand-in for a real code-embedding model
- `context/vector_store.py` — `InMemoryVectorStore` is a dev stand-in; `PGVECTOR_SCHEMA_SQL` is included for the production Postgres/pgvector backend

Each of these is behind a small interface (`Agent`, `Completer`, `Embedder`,
`VectorStore`) specifically so a real implementation can be dropped in
without touching the surrounding orchestration logic.

---

## Next Steps

1. Wire `agents/base.py` to real Anthropic API calls, using `context/tools.py`
   tool definitions so the Coder/Fixer can call `search_code`, `find_usages`, etc.
2. Replace `spec/generator.py`'s `_stub_completer` with a real Messages API call.
3. Replace `sandbox/executor.py` with real ephemeral-container execution.
4. Swap `HashEmbedder` for a code-tuned embedding model and `InMemoryVectorStore`
   for a pgvector-backed store using the included schema.