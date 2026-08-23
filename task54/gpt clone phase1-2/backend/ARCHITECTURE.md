# Backend Architecture: AI Chat SaaS Platform

**Status:** Production-Ready Modular Monolith
**Last Updated:** 2024
**Version:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [System Architecture Diagram](#system-architecture-diagram)
4. [Technology Stack](#technology-stack)
5. [Module Structure](#module-structure)
6. [API Gateway](#api-gateway)
7. [Core Modules](#core-modules)
8. [Data Layer](#data-layer)
9. [Background Jobs](#background-jobs)
10. [Integration Patterns](#integration-patterns)
11. [Deployment](#deployment)
12. [Scalability Path](#scalability-path)

---

## Overview

The backend is a **modular monolith** built with FastAPI, designed to support an AI Chat SaaS platform with:

- **Authentication & Authorization** - Secure user management with OAuth + password auth
- **Chat & Conversations** - Message streaming with memory context injection
- **RAG** - Document Q&A via embeddings + hybrid search
- **Vision** - Image understanding (Q&A, extraction)
- **Agents** - Code generation with approval workflow
- **Memory** - Semantic fact extraction & retrieval
- **Billing** - Stripe integration with daily quotas
- **Observability** - Structured logging, health checks, metrics hooks

### Key Characteristics

✅ **Async-First** - FastAPI + asyncpg for high concurrency  
✅ **Type-Safe** - Pydantic v2 + SQLAlchemy 2.0 with typed models  
✅ **Modular** - Each domain has its own routes, services, models, schemas  
✅ **Extensible** - Abstract LLM providers, pluggable embeddings  
✅ **Production-Ready** - Error handling, rate limiting, audit trails  
✅ **Scalable** - Designed to decompose into microservices  

---

## Architecture Principles

### 1. Separation of Concerns

```
Route
 ├─ HTTP Handling
 ├─ Request Validation
 └─ Response Formatting
    ↓
Service
 ├─ Business Logic
 ├─ Orchestration
 └─ External API Calls
    ↓
Repository
 ├─ Database Access
 ├─ Query Building
 └─ Transactions
    ↓
Model
 ├─ Schema Definition
 ├─ Relationships
 └─ Constraints
```

**Routes** should NOT contain business logic.  
**Services** should NOT contain SQL queries.  
**Repositories** should NOT contain business decisions.

### 2. Modular Domains

Each domain (Auth, Chat, RAG, etc.) is self-contained:

```
Module: Chat
├── routers/
│   └── chat.py
├── schemas.py
├── services/
│   ├── chat_service.py
│   ├── ai_orchestrator.py
│   └── streaming.py
└── models.py
```

Modules communicate via well-defined service interfaces, not by importing models.

### 3. Async-First Design

- All I/O is async: database, HTTP, embeddings, LLM calls
- Blocking operations (hashing, encoding) are offloaded to thread pool
- Background tasks use async context, not threads

### 4. Dependency Injection

- FastAPI dependencies inject database, user context, Redis, etc.
- No global state, no singletons (except config)
- Testable: mock dependencies, no mocking libraries needed

### 5. Error Handling

- Structured error responses (see Error Format section)
- No internal stack traces exposed
- Proper HTTP status codes (400 bad request, 401 unauthorized, 429 rate limited, 500 server error)
- Audit trail for security-relevant errors

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│              (Conversations, Memory, Settings, etc.)            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI Application Gateway                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Middleware Layer                                         │  │
│  ├─ CORS                                                    │  │
│  ├─ Session (for OAuth state)                              │  │
│  ├─ Rate Limiting (SlowAPI)                                │  │
│  ├─ Usage Limiter (quota enforcement)                      │  │
│  ├─ Request ID tracking                                    │  │
│  └─ Error Handling                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────┬─────────┼──────────┬──────────┬────────────┐ │
│  ▼              ▼         ▼          ▼          ▼            ▼ │
│ Auth           Chat      RAG       Vision    Agent        Billing
│ Module         Module    Module    Module    Module       Module
│  │              │         │          │         │            │  │
│  ├─ Register    ├─ Stream ├─ Upload ├─ Upload├─ Start   ├─ Plans
│  ├─ Login       ├─ Memory ├─ Search ├─ Q&A   ├─ Approve ├─ Usage
│  ├─ Refresh     ├─ History├─ Ingest ├─ Extract├─ Reject  ├─ Subscribe
│  ├─ OAuth       └─ Folders└─ Delete └─ Track └─ Query    └─ Webhook
│  └─ Me                                                        
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Service Layer (Business Logic)                            │ │
│  ├─ UserService           ├─ ConversationService            │ │
│  ├─ AuthService           ├─ AIOrchestrator                 │ │
│  ├─ OAuthService          ├─ RAGService                     │ │
│  ├─ MemoryService         ├─ AgentService                   │ │
│  ├─ BillingService        ├─ VisionService                  │ │
│  ├─ UsageService          ├─ StreamingService               │ │
│  └─ SettingsService       └─ DocumentProcessor              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Repository Pattern (Data Access)                          │ │
│  ├─ UserRepository        ├─ ConversationRepository         │ │
│  ├─ MessageRepository     ├─ DocumentRepository             │ │
│  ├─ MemoryRepository      ├─ SubscriptionRepository         │ │
│  ├─ AgentRepository       ├─ UsageRepository                │ │
│  └─ SettingsRepository    └─ TokenRepository                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Data Access Layer                                         │ │
│  ├─ SQLAlchemy ORM                                          │ │
│  ├─ Async Database Session Management                      │ │
│  ├─ Query Building                                         │ │
│  └─ Transaction Management                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
            │                        │                 │
            ▼                        ▼                 ▼
    ┌──────────────┐        ┌──────────────┐  ┌──────────────┐
    │ PostgreSQL   │        │  Redis       │  │   S3/MinIO   │
    │              │        │              │  │              │
    │ - Users      │        │ - Cache      │  │ - Images     │
    │ - Conversations│      │ - Rate Limit │  │ - Signed URLs│
    │ - Messages   │        │ - Session    │  └──────────────┘
    │ - Documents  │        │ - Job State  │
    │ - Memory     │        └──────────────┘
    │ - Subscriptions│
    │ - pgvector   │
    └──────────────┘
            │
         Alembic
         Migrations

                    ┌─────────────────┐
                    │ External APIs   │
                    ├─────────────────┤
                    │ - OpenAI/Groq   │
                    │ - Stripe        │
                    │ - OAuth         │
                    │ - Gmail SMTP    │
                    └─────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│              Background Job System (Optional)                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Redis Streams / Celery                                    │ │
│  ├─ Document Ingestion Jobs                                  │ │
│  ├─ Memory Extraction Jobs                                   │ │
│  ├─ Data Export Jobs                                         │ │
│  └─ Periodic Tasks (LRU eviction, cleanup)                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Worker Processes                                          │ │
│  ├─ Document Ingestion Worker                                │ │
│  ├─ Memory Extraction Worker                                 │ │
│  └─ Cleanup Worker                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Framework

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Web Server | FastAPI | 0.115.0 | Async HTTP framework |
| ASGI | Uvicorn | 0.30.6 | ASGI server |
| ORM | SQLAlchemy | 2.0.35 | Async-first ORM |
| Database Driver | asyncpg | 0.29.0 | PostgreSQL async |
| Migrations | Alembic | 1.13.2 | Schema versioning |
| Validation | Pydantic | 2.9.2 | Data validation & serialization |
| Settings | pydantic-settings | 2.5.2 | Environment config |

### Authentication & Security

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Password Hashing | bcrypt | 4.2.0 | Argon2 alternative, widely used |
| Token Signing | python-jose | 3.3.0 | JWT creation/verification |
| OAuth 2.0 | authlib | 1.3.2 | OAuth client |
| Signature Validation | cryptography | Latest | Used by python-jose |

### Data & Persistence

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Vector Extension | pgvector | - | PostgreSQL vector search |
| HTTP Client | httpx | 0.27.2 | Async HTTP requests |
| Rate Limiting | slowapi | 0.1.9 | Request rate limiting |

### Development & Utilities

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Environment | python-dotenv | 1.0.1 | .env file loading |
| Email Validation | email-validator | 2.2.0 | Email format check |
| Form Data | python-multipart | 0.0.9 | Multipart form parsing |

### Optional (Recommended for Production)

| Component | Library | Purpose |
|-----------|---------|---------|
| Job Queue | Celery or RQ | Async background tasks |
| Cache | Redis | Session, cache, rate limit backing |
| Error Tracking | Sentry | Error monitoring |
| Observability | OpenTelemetry | Distributed tracing |
| AI Providers | openai, anthropic | LLM API clients |
| Document Processing | PyPDF2, python-docx | File extraction |

---

## Module Structure

### Folder Organization

```
backend/
│
├── app/
│   ├── main.py                        # FastAPI app factory
│   ├── config.py                      # Pydantic settings (env vars)
│   ├── dependencies.py                # FastAPI dependency injection
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py              # Main API router
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── conversations.py
│   │       ├── messages.py
│   │       ├── rag.py
│   │       ├── agents.py
│   │       ├── memory.py
│   │       ├── billing.py
│   │       ├── vision.py
│   │       ├── settings.py
│   │       └── share.py
│   │
│   ├── core/
│   │   ├── security.py                # Password hashing, JWT
│   │   ├── exceptions.py              # Custom exceptions
│   │   ├── logging.py                 # Structured logging
│   │   └── middleware.py              # Custom middleware
│   │
│   ├── db/
│   │   ├── session.py                 # Database connection
│   │   ├── base.py                    # SQLAlchemy base model
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── user.py
│   │       ├── conversation.py
│   │       ├── message.py
│   │       ├── document.py
│   │       ├── memory.py
│   │       ├── billing.py
│   │       ├── agent.py
│   │       └── settings.py
│   │
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── models.py              # Auth-specific models
│   │   │   ├── schemas.py             # Pydantic schemas
│   │   │   ├── repository.py
│   │   │   ├── service.py             # Business logic
│   │   │   └── oauth.py
│   │   │
│   │   ├── chat/
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   ├── orchestrator.py        # AI routing logic
│   │   │   └── streaming.py           # SSE formatting
│   │   │
│   │   ├── rag/
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   ├── ingestion.py           # Document processing
│   │   │   ├── embeddings.py          # Vector generation
│   │   │   ├── retrieval.py           # Hybrid search
│   │   │   └── document_processor.py
│   │   │
│   │   ├── agents/
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   ├── orchestrator.py
│   │   │   └── tools/
│   │   │       ├── file.py
│   │   │       ├── git.py
│   │   │       ├── test.py
│   │   │       └── build.py
│   │   │
│   │   ├── memory/
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   ├── extraction.py
│   │   │   └── retrieval.py
│   │   │
│   │   ├── billing/
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   ├── stripe_service.py
│   │   │   └── webhooks.py
│   │   │
│   │   ├── vision/
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   ├── s3_client.py
│   │   │   └── vision_api.py
│   │   │
│   │   ├── users/
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   └── service.py
│   │   │
│   │   └── settings/
│   │       ├── schemas.py
│   │       ├── repository.py
│   │       └── service.py
│   │
│   ├── ai/
│   │   ├── providers/
│   │   │   ├── base.py                # Abstract LLM provider
│   │   │   ├── openai.py
│   │   │   ├── anthropic.py
│   │   │   └── groq.py
│   │   ├── embeddings/
│   │   │   ├── base.py                # Abstract embedding provider
│   │   │   └── openai.py
│   │   └── orchestrator.py            # Routes to appropriate AI service
│   │
│   ├── workers/
│   │   ├── worker.py                  # Main worker process
│   │   ├── document_tasks.py
│   │   ├── memory_tasks.py
│   │   ├── export_tasks.py
│   │   └── cleanup_tasks.py
│   │
│   ├── redis/
│   │   ├── client.py                  # Redis connection
│   │   ├── cache.py                   # Cache wrapper
│   │   ├── rate_limit.py
│   │   └── job_queue.py
│   │
│   ├── schemas/
│   │   ├── common.py                  # Shared Pydantic schemas
│   │   ├── pagination.py
│   │   ├── errors.py
│   │   └── responses.py
│   │
│   └── __init__.py
│
├── tests/
│   ├── conftest.py                    # Pytest fixtures
│   ├── auth/
│   │   ├── test_signup.py
│   │   ├── test_login.py
│   │   └── test_oauth.py
│   ├── chat/
│   │   ├── test_stream.py
│   │   └── test_memory_injection.py
│   ├── rag/
│   │   ├── test_upload.py
│   │   └── test_search.py
│   ├── integration/
│   │   └── test_e2e_flow.py
│   └── fixtures/
│       ├── users.py
│       ├── conversations.py
│       └── documents.py
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_add_pgvector.py
│       ├── 0003_rag_schema.py
│       ├── 0004_billing.py
│       ├── 0005_memory.py
│       └── 0006_agent.py
│
├── .env.example
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── ARCHITECTURE.md                    # This file
```

---

## API Gateway

### Request Flow

```
HTTP Request
    │
    ├─ CORS Middleware (check origin)
    ├─ Session Middleware (OAuth state)
    ├─ Rate Limit Middleware (SlowAPI)
    ├─ Usage Limiter (chat endpoints only)
    ├─ Request ID Generation
    │
    ▼
Route Handler (HTTP Layer)
    ├─ Validate Request (Pydantic)
    ├─ Extract Dependencies (JWT user, DB session)
    ├─ Check Authorization (user owns resource?)
    │
    ▼
Service Layer (Business Logic)
    ├─ Orchestrate business operations
    ├─ Call repositories
    ├─ Call external APIs
    │
    ▼
Repository Layer (Data Access)
    ├─ Execute queries
    ├─ Handle transactions
    │
    ▼
Response Formatting
    ├─ Serialize to Pydantic schema
    ├─ Set HTTP status
    ├─ Return JSON
    │
    ▼
HTTP Response
```

### Error Handling

All errors return structured JSON:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid access token",
    "details": {
      "token_expired_at": "2024-01-15T12:00:00Z"
    }
  }
}
```

**Do NOT expose:**
- Internal stack traces
- Database query details
- Stripe secret keys
- API keys
- File system paths

### API Versioning

```
/api/v1/auth/...
/api/v1/conversations/...
/api/v1/billing/...
```

Future v2 can coexist without breaking v1 clients.

### OpenAPI / Swagger

FastAPI auto-generates:
- `GET /api/v1/openapi.json` - OpenAPI spec
- `GET /api/v1/docs` - Interactive Swagger UI
- `GET /api/v1/redoc` - ReDoc

Every endpoint must have tags, summaries, and documented parameters.

---

## Core Modules

### 1. Authentication Module

**Responsibilities:**
- User registration
- Email/password login
- Token refresh
- Email verification
- Password reset
- OAuth provider integration
- Session management

**Key Services:**
- `AuthService` - Register, login, verify, reset
- `OAuthService` - Google, GitHub, Microsoft
- `TokenService` - Generate, validate, revoke

**Endpoints:**
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
POST   /api/v1/auth/verify-email
POST   /api/v1/auth/forgot-password
POST   /api/v1/auth/reset-password
GET    /api/v1/auth/me
POST   /api/v1/auth/onboarding
```

**Dependency Injection:**
```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Validate JWT, fetch user, ensure active
    ...

async def get_optional_user(...) -> User | None:
    # Same, but returns None if no token
    ...
```

---

### 2. Chat Module

**Responsibilities:**
- Manage conversations
- Store messages
- Stream AI responses
- Inject memory context
- Track usage

**Key Services:**
- `ConversationService` - CRUD
- `AIOrchestrator` - Route to LLM/RAG/Agent
- `StreamingService` - SSE formatting
- `MemoryContextInjector` - Retrieve + format memories

**Endpoints:**
```
GET    /api/v1/conversations
POST   /api/v1/conversations
GET    /api/v1/conversations/{id}
PATCH  /api/v1/conversations/{id}
DELETE /api/v1/conversations/{id}

GET    /api/v1/conversations/{id}/messages
POST   /api/v1/conversations/{id}/stream
POST   /api/v1/conversations/{id}/stream/{message_id}/stop
```

**Stream Event Types:**
```
message_start       # Conversation started
retrieval_start     # RAG retrieval began
retrieval_complete  # Chunks retrieved
token               # LLM token received
tool_start          # Tool called
tool_result         # Tool result
agent_thought       # Agent reasoning
message_complete    # Conversation ended
error               # Error occurred
```

---

### 3. RAG Module

**Responsibilities:**
- Document upload
- Text extraction & chunking
- Embedding generation
- Vector storage
- Hybrid search
- Chunk retrieval with metadata

**Key Services:**
- `DocumentService` - Upload, delete, list
- `IngestionService` - Extract, chunk, embed (async)
- `RetrievalService` - Hybrid search
- `EmbeddingsService` - Vector generation

**Endpoints:**
```
POST   /api/v1/rag/documents
GET    /api/v1/rag/documents
GET    /api/v1/rag/documents/{id}
DELETE /api/v1/rag/documents/{id}
GET    /api/v1/rag/documents/{id}/status

POST   /api/v1/rag/search
```

**Search Request:**
```json
{
  "query": "What is the API authentication method?",
  "top_k": 5,
  "threshold": 0.5
}
```

**Search Response:**
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "content": "JWT tokens are...",
      "score": 0.92,
      "metadata": {
        "page_number": 5,
        "section": "Authentication"
      }
    }
  ]
}
```

---

### 4. Agents Module

**Responsibilities:**
- Code generation tasks
- Approval workflow
- Reasoning step tracking
- Test execution
- Docker sandbox

**Key Services:**
- `AgentService` - Start, approve, reject
- `AgentOrchestrator` - Reasoning + tool calling
- `ReactAgentEngine` - ReAct-style reasoning
- `SandboxManager` - Docker container lifecycle

**Endpoints:**
```
POST   /api/v1/agents/start
GET    /api/v1/agents/{session_id}
POST   /api/v1/agents/{session_id}/changes/{change_id}/approve
POST   /api/v1/agents/{session_id}/changes/{change_id}/reject
POST   /api/v1/agents/{session_id}/changes/{change_id}/edit
```

---

### 5. Memory Module

**Responsibilities:**
- Extract facts from conversations
- Store persistent memories
- Retrieve via semantic search
- User management (view, edit, delete)
- Extraction audit trail

**Key Services:**
- `MemoryService` - CRUD + settings
- `ExtractionService` - LLM-based fact extraction
- `RetrievalService` - Semantic search
- `ExtractionJob` - Async extraction

**Endpoints:**
```
GET    /api/v1/memory
POST   /api/v1/memory
PATCH  /api/v1/memory/{id}
DELETE /api/v1/memory/{id}

GET    /api/v1/memory/settings
PATCH  /api/v1/memory/settings

POST   /api/v1/memory/extract
```

---

### 6. Billing Module

**Responsibilities:**
- Subscription management
- Stripe integration
- Daily quota enforcement
- Webhook processing
- Usage tracking

**Key Services:**
- `SubscriptionService` - CRUD, status sync
- `StripeService` - API calls, webhook verification
- `BillingService` - Plans, pricing
- `UsageService` - Daily tracking

**Endpoints:**
```
GET    /api/v1/billing/plans
GET    /api/v1/billing/subscription
GET    /api/v1/billing/usage

POST   /api/v1/billing/checkout-session
POST   /api/v1/billing/customer-portal
POST   /api/v1/billing/webhook
```

---

## Data Layer

### Database Schema

**Core Tables:**

**users**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password TEXT,
    name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    oauth_provider VARCHAR(50),
    oauth_subject VARCHAR(255),
    use_case TEXT,
    theme_preference VARCHAR(20) DEFAULT 'light',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_subject);
```

**conversations**
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    model VARCHAR(100) DEFAULT 'default',
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    archived BOOLEAN NOT NULL DEFAULT FALSE,
    share_token VARCHAR(255) UNIQUE,
    search_vector tsvector,
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_share_token ON conversations(share_token);
CREATE INDEX idx_conversations_search ON conversations USING GIN(search_vector);
```

**messages**
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(30) NOT NULL,  -- user, assistant, system, tool
    content TEXT NOT NULL,
    model VARCHAR(100),
    token_count INTEGER,
    metadata JSONB DEFAULT '{}',
    search_vector tsvector,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_messages_search ON messages USING GIN(search_vector);
```

**documents**
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100),
    file_size_bytes BIGINT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, ready, failed
    chunk_count INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_status ON documents(status);
```

**document_chunks**
```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page_number INTEGER,
    token_count INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
```

**document_embeddings**
```sql
CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    embedding VECTOR(1536),  -- configurable dimension
    model VARCHAR(100) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_embeddings_chunk_id ON document_embeddings(chunk_id);
CREATE INDEX idx_embeddings_vector ON document_embeddings USING IVFFLAT(embedding vector_cosine_ops);
```

**memory_items**
```sql
CREATE TABLE memory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fact TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    embedding VECTOR(1536),
    relevance_score FLOAT DEFAULT 1.0,
    source_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    retrieval_count INTEGER DEFAULT 0,
    last_retrieved_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_memory_user_id ON memory_items(user_id);
CREATE INDEX idx_memory_embedding ON memory_items USING IVFFLAT(embedding vector_cosine_ops);
```

**subscriptions**
```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    stripe_customer_id VARCHAR(255) UNIQUE,
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_price_id VARCHAR(255),
    plan VARCHAR(50) NOT NULL DEFAULT 'free',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe_customer_id ON subscriptions(stripe_customer_id);
```

**usage_logs**
```sql
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    usage_type VARCHAR(50) NOT NULL,  -- chat, rag, agent, vision
    model VARCHAR(100),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    quantity INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id, created_at DESC);
CREATE INDEX idx_usage_logs_type ON usage_logs(usage_type);
CREATE INDEX idx_usage_logs_created_at ON usage_logs(created_at DESC);
```

### SQLAlchemy Models

**Typed Models with Relationships:**

```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str | None]
    name: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    memories: Mapped[list["MemoryItem"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

### Pydantic Schemas

**Request/Response Validation:**

```python
class CreateConversationRequest(BaseModel):
    title: str | None = None
    model: str = "default"

class ConversationResponse(BaseModel):
    id: UUID
    title: str | None
    model: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    has_next: bool
```

---

## Background Jobs

### Job Types

#### 1. Document Ingestion

```
User uploads file
    ↓
Create UploadJob (status=pending)
    ↓
Queue document.ingest task
    ↓
Worker processes:
  - Extract text
  - Split into chunks
  - Generate embeddings
  - Store in DB
  - Update UploadJob.progress
    ↓
UploadJob.status = ready
```

#### 2. Memory Extraction

```
Conversation completed
    ↓
User enabled auto-extract
    ↓
Queue memory.extract task
    ↓
Worker:
  - Fetch conversation
  - Call LLM extraction
  - Validate facts
  - Store in DB
  - Create MemoryExtractionLog
    ↓
Complete (no user notification needed)
```

#### 3. Data Export

```
User requests export
    ↓
Create DataExportJob (status=processing)
    ↓
Queue data.export task
    ↓
Worker:
  - Collect all user data (conversations, documents, memories)
  - Generate archive (ZIP)
  - Upload to S3 (or file storage)
  - Generate signed URL
  - Send email with link
  - Update DataExportJob.download_url
    ↓
Email sent with 7-day download link
```

### Implementation Options

**Option 1: Celery + Redis** (Recommended for production)
```python
# tasks.py
@celery.task(bind=True, max_retries=3)
async def ingest_document(self, document_id: str):
    try:
        ...
    except SoftTimeLimitExceeded:
        self.retry(countdown=60)
```

**Option 2: Redis Streams** (Lightweight)
```python
# Producer
await redis.xadd(
    "documents",
    {"document_id": document_id}
)

# Consumer
async for message in redis_stream("documents"):
    await process_document(message["document_id"])
```

**Option 3: APScheduler** (Periodic tasks)
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(cleanup_expired_tokens, "cron", hour=0)
```

---

## Integration Patterns

### Service-to-Service Communication

**Always via dependency injection:**

```python
@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    conversation_service: ConversationService = Depends(ConversationService)
):
    return await conversation_service.list_user_conversations(current_user.id, db)
```

**Not direct model access:**

```python
# ❌ DON'T do this:
conversations = db.query(Conversation).filter_by(user_id=user.id).all()

# ✅ DO this:
conversations = await conversation_service.list_user_conversations(user.id, db)
```

### External API Integration

**Abstract behind providers:**

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: list) -> str:
        ...

class OpenAIProvider(LLMProvider):
    async def generate(self, messages: list) -> str:
        client = OpenAI(api_key=self.api_key)
        return client.chat.completions.create(...)

class AnthropicProvider(LLMProvider):
    async def generate(self, messages: list) -> str:
        client = Anthropic(api_key=self.api_key)
        return client.messages.create(...)
```

### Error Handling

**Centralized error handling:**

```python
class AppException(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}

# Usage
raise AppException(
    code="USAGE_LIMIT_REACHED",
    message="Daily message limit exceeded",
    details={"reset_at": "2024-01-16T00:00:00Z"}
)

# Exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )
```

---

## Deployment

### Docker Compose (Development)

```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg15-latest
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: password
      POSTGRES_DB: chatline
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/code
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://app:password@postgres:5432/chatline
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  worker:
    build: .
    command: python -m celery -A app.workers.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+psycopg2://app:password@postgres:5432/chatline
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

**.env.example**

```bash
# App
APP_NAME="Chatline"
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/db
DATABASE_URL_SYNC=postgresql+psycopg2://user:password@localhost:5432/db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
FRONTEND_URL=http://localhost:3000

# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk-...

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PLUS_PRICE_ID=price_...
STRIPE_PRO_PRICE_ID=price_...

# AWS S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=...

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...

# OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

### Startup Commands

```bash
# Create database & run migrations
alembic upgrade head

# Start API server (development)
uvicorn app.main:app --reload

# Start API server (production)
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Start periodic tasks
celery -A app.workers.celery_app beat --loglevel=info

# Health check
curl http://localhost:8000/health
```

---

## Scalability Path

### Phase 1: Monolith (Current)

```
FastAPI + PostgreSQL + Redis
├─ All modules in one process
├─ Single database
└─ Shared Redis for cache/queues
```

### Phase 2: Separated Workers

```
API Process
├─ HTTP handlers
└─ Thin orchestration

Worker Processes
├─ Document ingestion
├─ Memory extraction
├─ Data export
└─ Periodic cleanup
```

### Phase 3: Microservices (Future)

```
API Gateway
├─ Auth Service (JWT validation)
├─ Chat Service (messages, streaming)
├─ RAG Service (documents, embeddings)
├─ Agent Service (code generation)
├─ Memory Service (fact extraction)
├─ Billing Service (subscriptions)
├─ Vision Service (image processing)
└─ File Service (S3, uploads)

Shared
├─ PostgreSQL (sharded by user_id)
├─ Redis (distributed cache)
├─ RabbitMQ / Kafka (event streaming)
└─ Observability (Prometheus, Jaeger, Sentry)
```

### Decoupling Strategy

1. **Define Service Boundaries** - Each module gets own database (optional)
2. **Event Streaming** - Services communicate via message queues
3. **API Gateway** - Central routing, auth, rate limiting
4. **Async Communication** - No synchronous inter-service calls
5. **Saga Pattern** - Distributed transactions for multi-service workflows

---

## Key Takeaways

✅ **Modular Design** - Each domain self-contained, can scale independently  
✅ **Async-First** - High concurrency, non-blocking I/O  
✅ **Type-Safe** - Pydantic + SQLAlchemy typed models  
✅ **Testable** - Dependency injection, no global state  
✅ **Secure** - No secrets exposed, proper auth/authn  
✅ **Observable** - Structured logging, health checks, metrics hooks  
✅ **Scalable** - Clear path from monolith → microservices  

---

**For implementation details on specific modules, see:**
- `API.md` - Complete endpoint reference
- `DATABASE.md` - Schema + migrations
- `TESTING.md` - Unit & integration tests
- `DEPLOYMENT.md` - Production setup
