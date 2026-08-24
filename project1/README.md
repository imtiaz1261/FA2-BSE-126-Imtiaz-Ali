# 🤖 AIHub — Intelligent AI SaaS Platform

A production-grade, portfolio-level SaaS AI platform combining **RAG**, **AI Agents**, **Tool Calling**, **Guardrails**, **Streaming**, **Authentication**, **Subscription Management**, **Chat History**, **Analytics**, and **Docker Deployment**.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Environment Variables](#environment-variables)
- [Running Services](#running-services)
- [API Documentation](#api-documentation)
- [Development Roadmap](#development-roadmap)

---

## Overview

AIHub allows authenticated users to:

| Feature | Description |
|---|---|
| 💬 **AI Chat** | Conversational AI with streaming responses and persistent history |
| 📄 **Document Q&A** | Upload PDFs/DOCX and ask questions using RAG |
| 🤖 **AI Agents** | Autonomous agents with tool use (search, calculator, document lookup) |
| 🛡️ **Guardrails** | Input/output safety checks on every request |
| 💳 **Subscriptions** | Free / Pro / Enterprise plans with token and request limits |
| 📊 **Admin Dashboard** | Monitor users, usage, costs, and system health |

---

## Architecture

```
                         USER
                          │
                          ▼
              ┌─────────────────────┐
              │  Streamlit Web App  │  :8501
              └──────────┬──────────┘
                         │  HTTP / SSE
                          ▼
              ┌─────────────────────┐
              │    FastAPI API      │  :8000
              └──────────┬──────────┘
                         │
       ┌─────────────────┼──────────────────┐
       │                 │                  │
       ▼                 ▼                  ▼
 Authentication     Subscription       Guardrails
  (JWT / bcrypt)    & Usage Limits    (input/output)
       │             (Redis + PG)          │
       └─────────────────┼──────────────────┘
                         │
                         ▼
                  AI Orchestration
                  (LangChain / LangGraph)
                         │
                ┌────────┴────────┐
                │                 │
                ▼                 ▼
           RAG Pipeline       AI Agent
           (LangChain)       (LangGraph)
                │                 │
                │           ┌─────┼──────┐
                │           │     │      │
                │           ▼     ▼      ▼
                │        Search  Calc  DocSearch
                ▼
         Vector Database
         (ChromaDB / pgvector)
                │
                ▼
        Retrieved Context
                │
                └──────────┐
                           ▼
                      LLM Service
                      (OpenAI API)
                           │
                           ▼
                   Output Guardrail
                           │
                           ▼
                   Stream to User
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Database** | PostgreSQL 16 + pgvector |
| **ORM / Migrations** | SQLAlchemy 2.0 (async), Alembic |
| **Authentication** | JWT (python-jose), bcrypt (passlib) |
| **Cache / Rate Limiting** | Redis 7 |
| **AI / LLM** | OpenAI API, LangChain, LangGraph |
| **Vector Store** | ChromaDB (dev), pgvector (prod) |
| **Document Processing** | pypdf, python-docx, unstructured |
| **Frontend** | Streamlit 1.35 |
| **Payments** | Stripe (sandbox) |
| **Logging** | structlog (JSON) |
| **Containerisation** | Docker, Docker Compose |

---

## Project Structure

```
project1/
├── backend/
│   ├── api/v1/routes/       # FastAPI route handlers (thin layer)
│   ├── core/                # Config, security, logging, DI
│   ├── db/                  # SQLAlchemy models + session factory
│   ├── schemas/             # Pydantic request/response models
│   ├── services/            # Business logic layer
│   ├── ai/
│   │   ├── rag/             # Vector store, retriever, RAG chain
│   │   ├── agents/          # LangGraph agent + tools
│   │   └── guardrails/      # Input & output safety checks
│   ├── migrations/          # Alembic migration scripts
│   ├── tests/               # pytest test suite
│   └── main.py              # FastAPI app factory
├── frontend/
│   ├── pages/               # Streamlit multi-page app
│   ├── components/          # Reusable UI components
│   ├── utils/               # API client, session state
│   └── Home.py              # App entry point
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── postgres/init.sql    # pgvector + extensions setup
├── .env.example             # Environment variable reference
├── .env                     # Local secrets (never committed)
├── .gitignore
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Python 3.11+](https://www.python.org/downloads/) for local development
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1 — Clone and configure

```bash
# Copy the environment template
cp .env.example .env

# Open .env and fill in at minimum:
#   OPENAI_API_KEY=sk-...
#   SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
#   JWT_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
```

### 2 — Start infrastructure

```bash
# Start PostgreSQL + Redis (detached)
docker compose up postgres redis -d

# Verify both are healthy
docker compose ps
```

### 3 — Create a virtual environment and install dependencies

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 4 — Run the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Visit: http://localhost:8000/docs

### 5 — Run the frontend

```bash
streamlit run frontend/Home.py
```

Visit: http://localhost:8501

---

## Development Setup

### Generating secure secret keys

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Run this twice — once for `SECRET_KEY` and once for `JWT_SECRET_KEY`.

### Resetting the database

```bash
# Stop containers and wipe all volumes
docker compose down -v

# Restart fresh
docker compose up postgres redis -d
```

### Running tests

```bash
pytest backend/tests/ -v
```

---

## Environment Variables

See `.env.example` for the full reference with descriptions.

The minimum required variables to start the application:

| Variable | Description |
|---|---|
| `SECRET_KEY` | App secret (generate with `secrets.token_hex(32)`) |
| `JWT_SECRET_KEY` | JWT signing secret (generate separately) |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `POSTGRES_PASSWORD` | PostgreSQL password |

All others have safe defaults for local development.

---

## Running Services

| Service | Command | URL |
|---|---|---|
| Infrastructure | `docker compose up postgres redis -d` | — |
| Backend API | `uvicorn backend.main:app --reload` | http://localhost:8000 |
| API Docs | *(auto, when backend running)* | http://localhost:8000/docs |
| Frontend | `streamlit run frontend/Home.py` | http://localhost:8501 |
| Full stack (Docker) | `docker compose up --build -d` | — |

---

## API Documentation

When the backend is running in `DEBUG=true` mode, interactive API docs are available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Docs are automatically hidden in production (`DEBUG=false`).

---

## Development Roadmap

| Step | Feature | Status |
|---|---|---|
| **Step 1** | Project Foundation & Structure | ✅ Complete |
| **Step 2** | Authentication (Register, Login, JWT) | 🔜 Next |
| **Step 3** | Database Models & Migrations (Alembic) | 🔜 |
| **Step 4** | LLM Integration & Basic Chat | 🔜 |
| **Step 5** | Streaming + Chat History + Guardrails | 🔜 |
| **Step 6** | Document Upload & RAG Pipeline | 🔜 |
| **Step 7** | Subscriptions, Usage Limits & Billing | 🔜 |
| **Step 8** | AI Agents & Tool Calling (LangGraph) | 🔜 |
| **Step 9** | Admin Analytics Dashboard | 🔜 |
| **Step 10** | Docker + Cloud Deployment | 🔜 |

---

## License

MIT — built as a portfolio project.
