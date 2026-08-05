# Requirements Document — AI Research & Knowledge Workspace

## 1. Purpose
A production-grade, full-stack AI research and knowledge workspace: a
Streamlit UI backed by a FastAPI API, unified by an AI Orchestrator
that routes between RAG, LangGraph agents, and external tools.

## 2. Functional Requirements (by phase)
| # | Capability | Phase |
|---|---|---|
| 1 | Health-checked FastAPI + Streamlit connection | 2 |
| 2 | Persistent users, conversations, messages, documents, usage | 3 |
| 3 | Registration, login, JWT-protected routes | 4 |
| 4 | Multi-conversation chat UI | 5 |
| 5 | Centralized LLM chat service | 6 |
| 6 | Token-streamed responses | 7 |
| 7 | Document upload (PDF/DOCX/TXT/MD) | 8 |
| 8 | Retrieval-augmented generation over uploaded docs | 9 |
| 9 | Hybrid (BM25 + vector) retrieval with reranking & citations | 10 |
| 10 | LangGraph agent with planning + tool use | 11 |
| 11 | Calculator, web search, doc search, date/time tools | 12 |
| 12 | Multi-source web research reports | 13 |
| 13 | Input/output guardrails against prompt injection & jailbreaks | 14 |
| 14 | Plans, usage tracking, limits, upgrade flow | 15 |
| 15 | Redis caching + rate limiting | 16 |
| 16 | Langfuse tracing + cost dashboard | 17 |
| 17 | Admin analytics dashboard | 18 |
| 18 | RAGAS evaluation suite | 19 |
| 19 | Automated test suite | 20 |
| 20 | Dockerized dev/prod environment | 21 |
| 21 | Production deployment (AWS/Railway/Render) | 22 |
| 22 | CI/CD pipeline | 23 |
| 23 | Portfolio-ready docs & demos | 24 |

## 3. Non-Functional Requirements
- **Integration-first**: every feature is wired Streamlit → FastAPI →
  service layer → AI/DB → response → UI from Phase 2 onward — no
  feature is built UI-only or backend-only.
- **Config**: all settings centralized in `Settings` (backend) /
  `FrontendSettings` (frontend), loaded from `.env`, never hardcoded.
- **Security**: secrets only via environment variables; JWT auth on
  all protected routes; guardrails on both input and output.
- **Observability**: structured logging from day one; Langfuse
  tracing from Phase 17.
- **Testability**: modular service layer so business logic is
  unit-testable independent of FastAPI/Streamlit.

## 4. Tech Stack
See root `README.md` for the full stack table.

## 5. Out of Scope for Phase 1
No API routes, no database connection, no LLM calls yet — Phase 1 is
scaffold, config, and environment only. Verified by booting both
apps with no errors (see README "Run Commands").
