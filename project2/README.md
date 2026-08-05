# AI Research & Knowledge Workspace

Production-grade full-stack AI research and knowledge workspace:
Streamlit UI + FastAPI backend, unified by an AI Orchestrator routing
between RAG, LangGraph agents, and external tools.
c
**Status:** Phases 1-8 complete — scaffold, config, FastAPI↔Streamlit
connection, database, JWT auth, SaaS chat shell, real LLM chat
(streaming + non-streaming, persisted), and document upload/management.
See `docs/requirements.md` for the full 24-phase roadmap.

## Tech Stack
| Area | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Database | PostgreSQL + SQLAlchemy + Alembic |
| Vector DB | pgvector |
| Cache | Redis |
| LLM | OpenAI-compatible API |
| RAG | LangChain |
| Hybrid Retrieval | BM25 + Vector |
| Reranking | Cross Encoder |
| Agents | LangGraph |
| Tools | Calculator + Web + RAG |
| Guardrails | Input + Output |
| Streaming | FastAPI + Async |
| Auth | JWT |
| Observability | Langfuse |
| Evaluation | RAGAS |
| Testing | Pytest |
| Containers | Docker |
| CI/CD | GitHub Actions |

## Project Structure
```
ai-research-workspace/
├── backend/
│   ├── app/
│   │   ├── core/        # config.py (single .env loader), logging_config.py, security.py
│   │   ├── api/          # health, auth, conversations, messages (Phase 6/7), documents (Phase 8)
│   │   ├── db/            # base_class.py, session.py
│   │   ├── models/        # User, Conversation, Message, Document, UsageRecord
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── services/      # auth, conversation, message, llm, prompts, storage, document
│   │   ├── agents/        # LangGraph agent (Phase 11)
│   │   ├── tools/         # calculator/web/doc-search/date-time (Phase 12)
│   │   ├── guardrails/    # input/output guardrails (Phase 14)
│   │   └── main.py
│   ├── alembic/            # migrations, wired to Settings.DATABASE_URL
│   ├── storage/documents/  # uploaded files land here (gitignored)
│   └── tests/
├── frontend/
│   └── streamlit_app/
│       ├── config.py             # loads the same root .env
│       ├── api_client/client.py  # typed client — auth, conversations, messages, streaming, documents
│       ├── components/            # auth_forms, sidebar, chat (Phase 6/7), documents (Phase 8)
│       ├── state/session.py       # session_state helpers
│       ├── pages/
│       └── app.py
├── docs/                # requirements.md, architecture.md
├── docker/               # (populated in Phase 21)
├── requirements.txt      # single file for backend + frontend
├── .env.example           # single file for backend + frontend
└── README.md
```

## Prerequisites
- Python 3.11 (not 3.13/3.14 yet — several deps don't have wheels for those)
- PostgreSQL 14+ running locally (or update `DATABASE_URL` to point elsewhere)
- An OpenAI-compatible API key (for Phase 6/7 chat)
- git

## One-Time Setup (single venv, single .env, single requirements file)
From the **project root**:

```bash
python3.11 -m venv venv
source venv/bin/activate        # Windows PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```
Edit `.env`:
- confirm `DATABASE_URL` matches your local Postgres
- set `OPENAI_API_KEY` (required for chat to work — without it you'll
  get a clean "No LLM API key configured" error instead of a crash)

## Database Setup
Create the database once (adjust name/user to match your `.env`):
```bash
createdb ai_workspace
```
Generate and apply the first migration (run from `backend/`, with the venv active):
```bash
cd backend
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

## Run Commands
Run each in its own terminal, from the **project root**, with the venv active.

**Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
Check:
- http://localhost:8000/docs — interactive API docs
- http://localhost:8000/api/health/db — confirms Postgres is reachable

**Frontend:**
```bash
cd frontend
streamlit run streamlit_app/app.py
```
Open http://localhost:8501.

## Try It
1. Register/log in.
2. Click **+ New conversation**.
3. Type a message — it streams back token-by-token from the LLM and
   both turns are persisted (refresh and it's still there).
4. Open the **📄 Documents** expander in the sidebar to upload a
   PDF/DOCX/TXT/MD file, see it listed, or delete it. (Documents are
   stored on disk and tracked in the DB — actually *using* them for
   retrieval is wired in Phase 9.)

You can also hit the API directly:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123"}'
```

## Roadmap
See `docs/requirements.md` for the full phase-by-phase plan.
