# Architecture

## Data flow (every feature, end to end)
Streamlit UI → FastAPI API → Service layer → AI / Database → FastAPI response → Streamlit UI

## High-level diagram (conceptual)
- Streamlit UI and FastAPI API sit side by side, both driven by a shared AI Orchestrator.
- The Orchestrator routes requests to RAG, Agents, or Tools as needed.
- All roads lead to the LLM, then through an Output Guardrail, then streamed back to the user.
- Persistence: PostgreSQL + pgvector (vectors) + Redis (cache/rate-limit) + Langfuse (observability).

## Single env / single requirements file
Both apps read the SAME root-level `.env` and are installed from the
SAME root-level `requirements.txt`. Each `config.py` resolves the
`.env` path relative to its own file location (via `Path(__file__)`),
so it works no matter which directory you run the app from.

## Backend package layout
```
backend/
  app/
    core/       # config.py, logging_config.py — centralized settings & logging
    api/        # FastAPI routers — health.py (Phase 2)
    models/     # SQLAlchemy models — User, Conversation, Message, Document, UsageRecord (Phase 3)
    schemas/    # Pydantic request/response schemas
    services/   # business logic — LLM, RAG, auth, usage, etc. (Phase 6+)
    db/         # base_class.py, session.py (Phase 3)
    agents/     # LangGraph agent graph & nodes (Phase 11)
    tools/      # calculator, web search, doc search, date/time (Phase 12)
    guardrails/ # input/output guardrails (Phase 14)
    main.py     # FastAPI app entrypoint
  alembic/      # migrations, wired to Settings.DATABASE_URL (Phase 3)
  tests/
```

## Frontend package layout
```
frontend/
  streamlit_app/
    api_client/   # typed ApiClient with connection/timeout/HTTP error handling (Phase 2)
    components/   # reusable UI components (sidebar, chat bubble, etc.)
    pages/         # multi-page Streamlit views
    state/         # session_state helpers
    config.py      # centralized frontend settings, same root .env
    app.py          # entrypoint
```

## Data model (Phase 3)
- `User` (1) → (many) `Conversation` → (many) `Message`
- `User` (1) → (many) `Document`
- `User` (1) → (many) `UsageRecord`
All foreign keys cascade on delete. `User.plan` (free/pro/enterprise)
feeds Phase 15's usage limits; `UsageRecord` feeds Phase 18's admin
analytics.

## Chat flow (Phase 6/7)
`services/llm_service.py` wraps the OpenAI-compatible client (model/key
from `Settings`) with two entry points: `chat_completion` (Phase 6,
returns the full reply) and `stream_chat_completion` (Phase 7, an
async generator of text deltas). `services/prompts.py` turns stored
`Message` history + the new user message into the `messages` list,
selecting a system prompt per chat mode and trimming to
`LLM_MAX_HISTORY_MESSAGES`. `services/message_service.py` persists
both turns and auto-titles a fresh conversation from the first user
message. The streaming endpoint (`POST .../messages/stream`) persists
the assistant's full reply only after the generator completes, so a
client disconnect mid-stream doesn't save a truncated message.

## Document flow (Phase 8)
`services/storage_service.py` validates (content type, size) and
writes uploads to `backend/storage/documents/<user_id>/`.
`services/document_service.py` owns the DB row (`Document.status`
starts at `UPLOADED`; Phase 9 will move it through `PROCESSING` →
`READY` once chunking/embeddings land). Nothing about document
*content* is used yet — that's Phase 9 (RAG).

## Why the service layer exists
Routers and Streamlit pages stay thin. All business logic (LLM calls,
retrieval, guardrail checks, usage accounting) lives in
`backend/app/services/`, so it's independently unit-testable and
reusable from both the API and, later, background jobs.
