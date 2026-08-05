# AI Research & Knowledge Workspace

Production-grade full-stack AI research and knowledge workspace:
Streamlit UI + FastAPI backend, unified by an AI Orchestrator routing
between RAG, LangGraph agents, and external tools.

**Status:** Phases 1-3 complete — scaffold, centralized config,
FastAPI↔Streamlit connection, and database models/migrations. See
`docs/requirements.md` for the full 24-phase roadmap.

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
│   │   ├── core/        # config.py (single .env loader), logging_config.py
│   │   ├── api/          # health.py (Phase 2)
│   │   ├── db/            # base_class.py, session.py (Phase 3)
│   │   ├── models/        # User, Conversation, Message, Document, UsageRecord (Phase 3)
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── services/      # business logic (Phase 6+)
│   │   ├── agents/        # LangGraph agent (Phase 11)
│   │   ├── tools/         # calculator/web/doc-search/date-time (Phase 12)
│   │   ├── guardrails/    # input/output guardrails (Phase 14)
│   │   └── main.py
│   ├── alembic/            # migrations, wired to Settings.DATABASE_URL
│   └── tests/
├── frontend/
│   └── streamlit_app/
│       ├── config.py             # loads the same root .env
│       ├── api_client/client.py  # typed client with error handling (Phase 2)
│       ├── components/ pages/ state/
│       └── app.py
├── docs/                # requirements.md, architecture.md
├── docker/               # (populated in Phase 21)
├── requirements.txt      # single file for backend + frontend
├── .env.example           # single file for backend + frontend
└── README.md
```

## Prerequisites
- Python 3.11+
- PostgreSQL 14+ running locally (or update `DATABASE_URL` to point elsewhere)
- git

## One-Time Setup (single venv, single .env, single requirements file)
From the **project root**:

```bash
python3.11 -m venv venv
source venv/bin/activate        # Windows PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```
Edit `.env` — at minimum confirm `DATABASE_URL` matches your local Postgres.

## Database Setup (Phase 3)
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
This creates `users`, `conversations`, `messages`, `documents`, and
`usage_records` with their relationships.

## Run Commands
Run each in its own terminal, from the **project root**, with the venv active.

**Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
Check:
- http://localhost:8000/docs — interactive API docs
- http://localhost:8000/api/health — `{"status":"ok",...}`
- http://localhost:8000/api/health/db — confirms Postgres is reachable

**Frontend:**
```bash
cd frontend
streamlit run streamlit_app/app.py
```
Open http://localhost:8501 — it calls `/api/health` and shows the
live result, or a clear error if the backend isn't running.

## Roadmap
See `docs/requirements.md` for the full phase-by-phase plan.
