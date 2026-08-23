# API Reference: Complete Endpoint Documentation

**Version:** 1.0  
**Base URL:** `/api/v1`  
**Authentication:** Bearer Token (JWT)

---

## API Overview

### Response Format

All responses are JSON with consistent structure:

**Success (2xx):**
```json
{
  "data": {...} | [...]  or direct object,
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-15T12:00:00Z"
  }
}
```

**Error (4xx, 5xx):**
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {...}
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

### Common Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | GET successful |
| 201 | Created | POST successful |
| 204 | No Content | DELETE successful |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | No permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource exists |
| 429 | Too Many Requests | Rate limited |
| 500 | Server Error | Internal error |

---

## Authentication Endpoints

### Register

**Request:**
```
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123",
  "name": "John Doe"
}
```

**Validation:**
- Email: valid email format, unique
- Password: 8+ chars, uppercase, lowercase, digit
- Name: 1-255 chars

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-15T12:00:00Z"
}
```

**Errors:**
- `INVALID_EMAIL` - Invalid format
- `EMAIL_EXISTS` - Already registered
- `WEAK_PASSWORD` - Password doesn't meet requirements

---

### Login

**Request:**
```
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Rate Limiting:** 5 requests/minute per email

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900,
  "refresh_token": "rt_xxx..."  // httpOnly cookie also set
}
```

**Errors:**
- `INVALID_CREDENTIALS` - Email or password incorrect
- `USER_INACTIVE` - Account disabled
- `RATE_LIMITED` - Too many login attempts

---

### Refresh Token

**Request:**
```
POST /auth/refresh
Authorization: Bearer {refresh_token}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "expires_in": 900
}
```

**Errors:**
- `INVALID_TOKEN` - Token invalid/expired
- `TOKEN_REVOKED` - Token revoked

---

### Logout

**Request:**
```
POST /auth/logout
Authorization: Bearer {access_token}
```

**Response:**
```json
{ "message": "Logged out successfully" }
```

---

### Current User

**Request:**
```
GET /auth/me
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "plan": "plus",
  "is_verified": true,
  "created_at": "2024-01-15T12:00:00Z"
}
```

---

## Conversation Endpoints

### Create Conversation

**Request:**
```
POST /conversations
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Project Planning",
  "model": "default"
}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Project Planning",
  "model": "default",
  "pinned": false,
  "archived": false,
  "created_at": "2024-01-15T12:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

---

### List Conversations

**Request:**
```
GET /conversations?page=1&page_size=20&archived=false
Authorization: Bearer {token}
```

**Query Params:**
- `page` - Page number (default 1)
- `page_size` - Items per page (default 20, max 100)
- `archived` - Filter archived (optional)
- `pinned` - Filter pinned (optional)
- `search` - Full-text search (optional)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Project Planning",
      "model": "default",
      "pinned": false,
      "archived": false,
      "last_message_at": "2024-01-15T12:30:00Z",
      "created_at": "2024-01-15T12:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 45,
  "has_next": true
}
```

---

### Get Conversation

**Request:**
```
GET /conversations/{id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Project Planning",
  "model": "default",
  "pinned": false,
  "archived": false,
  "message_count": 12,
  "created_at": "2024-01-15T12:00:00Z",
  "updated_at": "2024-01-15T12:30:00Z"
}
```

**Errors:**
- `NOT_FOUND` - Conversation doesn't exist
- `FORBIDDEN` - Not owner

---

### Update Conversation

**Request:**
```
PATCH /conversations/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "New Title",
  "pinned": true,
  "archived": false
}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "New Title",
  "pinned": true,
  "archived": false,
  "updated_at": "2024-01-15T12:31:00Z"
}
```

---

### Delete Conversation

**Request:**
```
DELETE /conversations/{id}
Authorization: Bearer {token}
```

**Response:**
```json
{ "message": "Deleted successfully" }
```

---

## Chat Streaming Endpoints

### Stream Chat Response

**Request:**
```
POST /conversations/{id}/stream
Authorization: Bearer {token}
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "Explain quantum computing"
    }
  ]
}
```

**Response:** Server-Sent Events (streaming)

```
event: message_start
data: {"message_id": "uuid", "timestamp": "2024-01-15T12:00:00Z"}

event: token
data: {"content": "Quantum"}

event: token
data: {"content": " computing"}

event: retrieval_complete
data: {
  "source": "RAG",
  "chunks": 5,
  "confidence": 0.92
}

event: token
data: {"content": " uses"}

event: message_complete
data: {
  "message_id": "uuid",
  "tokens": 150,
  "model": "default",
  "timestamp": "2024-01-15T12:00:05Z"
}
```

### Event Types

| Event | Data | Description |
|-------|------|-------------|
| `message_start` | `{message_id, timestamp}` | Generation started |
| `token` | `{content}` | Streamed token |
| `retrieval_start` | `{}` | RAG retrieval began |
| `retrieval_complete` | `{chunks, confidence}` | Retrieved chunks |
| `tool_start` | `{tool_name, input}` | Tool invoked |
| `tool_result` | `{result, status}` | Tool completed |
| `agent_thought` | `{thought, step}` | Agent reasoning |
| `message_complete` | `{tokens, model}` | Generation complete |
| `error` | `{code, message}` | Error occurred |

### Stop Generation

**Request:**
```
POST /conversations/{id}/stream/{message_id}/stop
Authorization: Bearer {token}
```

**Response:**
```json
{ "stopped": true }
```

---

## Messages Endpoints

### Get Messages

**Request:**
```
GET /conversations/{id}/messages?limit=50&before={message_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "role": "user",
      "content": "Hello",
      "created_at": "2024-01-15T12:00:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "Hi there!",
      "model": "default",
      "tokens": 10,
      "created_at": "2024-01-15T12:00:01Z"
    }
  ],
  "has_more": true
}
```

---

## RAG Endpoints

### Upload Document

**Request:**
```
POST /rag/documents
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: <binary>  (PDF, DOCX, TXT, CSV)
metadata: {"source": "project_docs"}  (optional JSON)
```

**Response:**
```json
{
  "id": "uuid",
  "filename": "api_guide.pdf",
  "status": "processing",
  "progress": 0,
  "created_at": "2024-01-15T12:00:00Z"
}
```

---

### Get Document Status

**Request:**
```
GET /rag/documents/{id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "uuid",
  "filename": "api_guide.pdf",
  "status": "ready",
  "progress": 100,
  "chunk_count": 42,
  "token_count": 15000,
  "created_at": "2024-01-15T12:00:00Z",
  "updated_at": "2024-01-15T12:05:00Z"
}
```

---

### Search Documents

**Request:**
```
POST /rag/search
Authorization: Bearer {token}
Content-Type: application/json

{
  "query": "How do I authenticate?",
  "top_k": 5,
  "threshold": 0.5
}
```

**Response:**
```json
{
  "query": "How do I authenticate?",
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "content": "Authentication uses JWT tokens...",
      "score": 0.94,
      "metadata": {
        "page_number": 5,
        "section": "Authentication"
      }
    }
  ],
  "total": 5
}
```

---

## Memory Endpoints

### List Memories

**Request:**
```
GET /memory?category=preferences&limit=50
Authorization: Bearer {token}
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "fact": "Prefers concise explanations",
      "category": "preferences",
      "relevance_score": 0.95,
      "created_at": "2024-01-15T12:00:00Z"
    }
  ],
  "total": 3
}
```

---

### Create Memory

**Request:**
```
POST /memory
Authorization: Bearer {token}
Content-Type: application/json

{
  "fact": "User is a Python developer",
  "category": "skills_and_expertise"
}
```

**Response:**
```json
{
  "id": "uuid",
  "fact": "User is a Python developer",
  "category": "skills_and_expertise",
  "relevance_score": 1.0,
  "created_at": "2024-01-15T12:00:00Z"
}
```

---

### Update Memory

**Request:**
```
PATCH /memory/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "fact": "User is an experienced Python developer with 5 years experience"
}
```

---

### Delete Memory

**Request:**
```
DELETE /memory/{id}
Authorization: Bearer {token}
```

---

## Billing Endpoints

### Get Plans

**Request:**
```
GET /billing/plans
```

**Response:**
```json
[
  {
    "id": "free",
    "name": "Free",
    "price_cents": 0,
    "daily_messages": 20,
    "features": ["20 messages/day", "Basic AI models"]
  },
  {
    "id": "plus",
    "name": "Plus",
    "price_cents": 1999,
    "daily_messages": 300,
    "features": ["300 messages/day", "Advanced models", "Priority support"],
    "stripe_price_id": "price_..."
  }
]
```

---

### Get Usage

**Request:**
```
GET /billing/usage
Authorization: Bearer {token}
```

**Response:**
```json
{
  "plan": "plus",
  "daily_limit": 300,
  "used_today": 84,
  "remaining_today": 216,
  "percentage_used": 28.0,
  "reset_at": "2024-01-16T00:00:00Z"
}
```

---

### Get Subscription

**Request:**
```
GET /billing/subscription
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "uuid",
  "plan": "plus",
  "status": "active",
  "stripe_customer_id": "cus_...",
  "current_period_start": "2024-01-01T00:00:00Z",
  "current_period_end": "2024-02-01T00:00:00Z",
  "cancel_at_period_end": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

### Create Checkout Session

**Request:**
```
POST /billing/checkout-session
Authorization: Bearer {token}
Content-Type: application/json

{
  "plan": "plus",
  "success_url": "https://app.example.com/billing?success=true",
  "cancel_url": "https://app.example.com/billing?cancelled=true"
}
```

**Response:**
```json
{
  "session_id": "cs_...",
  "checkout_url": "https://checkout.stripe.com/pay/cs_..."
}
```

---

### Customer Portal

**Request:**
```
POST /billing/customer-portal
Authorization: Bearer {token}
```

**Response:**
```json
{
  "portal_url": "https://billing.stripe.com/..."
}
```

---

### Webhook

**Request:**
```
POST /billing/webhook
Content-Type: application/json
Stripe-Signature: t=...,v1=...

{
  "id": "evt_...",
  "type": "customer.subscription.updated",
  "data": {...}
}
```

**Stripe Events Handled:**
- `customer.subscription.created` - New subscription
- `customer.subscription.updated` - Updated subscription
- `customer.subscription.deleted` - Subscription canceled
- `invoice.payment_succeeded` - Payment processed
- `invoice.payment_failed` - Payment failed

---

## Error Codes Reference

| Code | HTTP | Description |
|------|------|-------------|
| `UNAUTHORIZED` | 401 | Invalid/missing token |
| `FORBIDDEN` | 403 | No permission |
| `NOT_FOUND` | 404 | Resource not found |
| `INVALID_INPUT` | 400 | Validation error |
| `EMAIL_EXISTS` | 409 | Email already registered |
| `WEAK_PASSWORD` | 400 | Password too weak |
| `RATE_LIMITED` | 429 | Too many requests |
| `USAGE_LIMIT_REACHED` | 429 | Daily quota exceeded |
| `INVALID_CREDENTIALS` | 401 | Login failed |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limiting

### Limits by Endpoint Type

| Category | Limit | Window |
|----------|-------|--------|
| Authentication (login) | 5 | 1 minute |
| General API | 60 | 1 minute |
| Chat (streaming) | 20 | 1 minute |
| Upload (files) | 10 | 1 minute |

### Rate Limit Headers

All responses include:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1642255200
```

When rate limited (429):
```
Retry-After: 60
```

---

## Pagination

Standard pagination for list endpoints:

**Query Parameters:**
- `page` - Page number (default 1, min 1)
- `page_size` - Items per page (default 20, max 100)

**Response Structure:**
```json
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 245,
  "has_next": true,
  "has_previous": false
}
```

---

## OpenAPI / Swagger

Interactive API documentation available at:
- **Swagger UI:** `GET /api/v1/docs`
- **ReDoc:** `GET /api/v1/redoc`
- **OpenAPI JSON:** `GET /api/v1/openapi.json`
