# Memory & Personalization Module

Complete implementation of long-term memory and personalization for cross-chat continuity, matching ChatGPT's approach.

## Overview

The Memory module enables the AI assistant to remember durable facts about users across conversations:

- **Personal Info**: Name, role, location, age
- **Preferences**: Communication style, work preferences, learning style
- **Goals & Values**: Career goals, values, stated objectives
- **Skills**: Technical skills, domain knowledge, languages
- **Constraints**: Time zone, availability, limitations
- **Recurring Tasks**: Patterns in work, repeated requests
- **Project Context**: Active projects, ongoing initiatives

All memories are:
- ✅ Extracted automatically from conversations (or manually added)
- ✅ Stored with audit trail (source, timestamp, extraction context)
- ✅ Retrieved semantically at conversation start
- ✅ Injected invisibly into system prompt
- ✅ User-editable with full control (manage, delete, opt-out)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Conversation Start                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
        ┌──────────────────────────────┐
        │  Memory Retrieval Service    │
        │  (retrieve_relevant_memories)│
        │  • Semantic similarity       │
        │  • Frequency-based ranking   │
        │  • Threshold filtering       │
        └──────────────────┬───────────┘
                           │
                           ↓
        ┌──────────────────────────────┐
        │   Vector Similarity Search    │
        │   (pgvector embeddings)       │
        │   or LRU frequency ranking    │
        └──────────────────┬───────────┘
                           │
                           ↓
     ┌─────────────────────────────────────┐
     │  Build Memory Context String        │
     │  "User has preferences:..."         │
     └─────────────────────┬───────────────┘
                           │
                           ↓
     ┌─────────────────────────────────────┐
     │  Inject into System Prompt          │
     │  (invisible to user)                │
     └─────────────────────┬───────────────┘
                           │
                           ↓
     ┌─────────────────────────────────────┐
     │  LLM Stream Response                │
     │  (personalized based on memories)   │
     └─────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│               Post-Conversation Extraction Job               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
        ┌──────────────────────────────┐
        │  Memory Extraction Service   │
        │  (extract_from_conversation) │
        │  • Format conversation       │
        │  • Call LLM with prompt      │
        │  • Parse JSON facts          │
        └──────────────────┬───────────┘
                           │
                           ↓
        ┌──────────────────────────────┐
        │  Fact Validation             │
        │  • Not sensitive             │
        │  • Not duplicate             │
        │  • Correct length            │
        └──────────────────┬───────────┘
                           │
                           ↓
        ┌──────────────────────────────┐
        │  Store UserMemoryItem        │
        │  • Generate embedding        │
        │  • Set relevance score       │
        │  • Track source              │
        └──────────────────┬───────────┘
                           │
                           ↓
        ┌──────────────────────────────┐
        │  Log MemoryExtractionLog     │
        │  • Facts extracted count     │
        │  • Rejection reasons         │
        │  • LLM token usage           │
        └──────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│         Frontend: Manage Memory Settings Screen              │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ↓             ↓             ↓
    ┌─────────┐  ┌─────────┐  ┌─────────┐
    │ Master  │  │Category │  │Settings │
    │ Toggle  │  │Filter   │  │ & Stats │
    │(enable/ │  │(view by │  │        │
    │disable) │  │ type)   │  │        │
    └─────────┘  └─────────┘  └─────────┘
         │             │             │
    ┌────┴─────────────┼─────────────┴────┐
    │                  ↓                   │
    │         ┌──────────────────┐         │
    │         │  Memory List     │         │
    │         │  • View facts    │         │
    │         │  • Edit content  │         │
    │         │  • Delete item   │         │
    │         │  • Category tags │         │
    │         │  • Relevance     │         │
    │         │    scores        │         │
    │         └──────────────────┘         │
    │                                      │
    └──────────────────────────────────────┘
         ↓
    ┌─────────────────────────────────┐
    │  Settings Controls              │
    │  • Max memory items             │
    │  • Context injection count      │
    │  • Retrieval threshold          │
    │  • Retention days               │
    │  • Auto-extract toggle          │
    └─────────────────────────────────┘
```

## Components

### Backend Models (`models_memory.py`)

**UserMemoryItem**
- `fact`: The actual memory (text)
- `category`: MemoryCategory enum (personal_info, preferences, skills, etc.)
- `embedding`: Vector embedding (1536-dim for OpenAI embeddings)
- `relevance_score`: Confidence score from extraction (0-1)
- `source_conversation_id`: Which conversation this came from
- `extraction_context`: Snippet that led to extraction
- `is_active`: Whether to include in retrievals
- `retrieval_count`, `last_retrieved_at`: Access statistics for LRU eviction

**UserMemorySettings**
- `memory_enabled`: Master toggle
- `auto_extract_enabled`: Enable/disable automatic extraction
- `max_memory_items`: Limit before LRU eviction
- `context_injection_count`: How many memories to inject per conversation
- `retrieval_threshold`: Minimum similarity to include (0-1)
- `retention_days`: Delete memories older than N days (0 = forever)

**MemoryExtractionLog**
- Audit trail of extraction events
- Facts extracted/rejected counts
- LLM token usage for cost tracking
- Trigger type (post_conversation, manual, periodic)
- Success status and error messages

**MemoryRetrievalLog**
- Track which memories were retrieved for which conversations
- User message that triggered retrieval
- Similarity scores for analytics

### Services

**MemoryExtractionService** (`memory_extraction.py`)
```python
# Extract facts after conversation ends
log = await extraction_service.extract_from_conversation(
    user_id=user_id,
    messages=conversation_messages,
    conversation_id=conv_id,
    db=db,
    trigger="post_conversation",
)

# Extract from recent conversations (periodic/manual)
logs = await extraction_service.extract_from_recent_conversations(
    user_id=user_id,
    db=db,
    limit=10,
)
```

**MemoryRetrievalService** (`memory_retrieval.py`)
```python
# Retrieve relevant memories at conversation start
memories = await retrieval_service.retrieve_relevant_memories(
    user_id=user_id,
    user_message=user_opening_message,
    db=db,
    conversation_id=conv_id,
)

# Build context string for system prompt
context = retrieval_service.build_memory_context(memories)
# Returns: "The user has the following preferences:\n• ...\n• ..."
```

**MemoryJobsService** (`memory_jobs.py`)
```python
# Post-conversation extraction
log = await jobs.extract_from_conversation(user_id, conv_id)

# Periodic reindexing of recent conversations
extracted_count = await jobs.periodic_reindex(user_id, limit=10)

# Cleanup old memories
cleaned = await jobs.cleanup_old_memories(user_id)
evicted = await jobs.enforce_memory_limits(user_id)
```

### API Endpoints (`routers/memory.py`)

**Memory Items CRUD**
```
GET    /memory/items?skip=0&limit=50&category=preferences
GET    /memory/items/{item_id}
POST   /memory/items?fact=...&category=...
PUT    /memory/items/{item_id}?fact=...&is_active=...
DELETE /memory/items/{item_id}
```

**Memory Settings**
```
GET  /memory/settings
PUT  /memory/settings?memory_enabled=true&auto_extract_enabled=...
```

**Extraction & Analytics**
```
POST /memory/extract                    # Trigger manual extraction
GET  /memory/stats                      # Get memory statistics
```

### Chat Integration (`routers/chat.py`)

The chat router automatically:
1. Retrieves relevant memories at conversation start
2. Injects them into the system prompt (invisible to user)
3. Logs retrieval for analytics

```python
# In POST /chat/stream:
memories = await retrieval_service.retrieve_relevant_memories(
    user_id=current_user.id,
    user_message=first_user_message,
    db=db,
    conversation_id=conversation_id,
)

memory_context = retrieval_service.build_memory_context(memories)

# Inject into system prompt
if memory_context:
    messages[0]["content"] += f"\n\n{memory_context}"
```

### Frontend Components (`components/settings/ManageMemory.tsx`)

**ManageMemory Screen**
- Master toggle to enable/disable memory
- Stats: total memories, by category, extraction history
- Category filter with item counts
- Memory list with:
  - Fact text
  - Category tag (color-coded)
  - Relevance score
  - Edit/Delete buttons
  - Created/Updated timestamps
- Add new memory form
- Settings controls:
  - Auto-extract toggle
  - Context injection count slider
  - Retrieval threshold slider
  - Max memory items
  - Retention days
- Manual extraction trigger button

## Extraction Prompt

The LLM extraction uses this prompt structure:

```
You are analyzing a conversation to identify durable facts about the user.

GUIDELINES:
1. Extract ONLY factual, non-sensitive information
2. NEVER extract: passwords, credentials, financial details
3. Each fact should be self-contained and understandable
4. Prefer specific, actionable facts over generic statements
5. Avoid speculation; only extract explicitly stated information
6. Categorize each fact appropriately

CATEGORIES:
- personal_info: Name, title, location
- preferences: Communication style, learning style
- goals_and_values: Career goals, values
- skills_and_expertise: Technical skills, domain knowledge
- constraints: Time zone, availability
- recurring_tasks: Repeated patterns
- project_context: Active projects
- other: Miscellaneous

CONVERSATION:
[formatted messages]

OUTPUT FORMAT:
{
  "facts": [
    {"fact": "...", "category": "...", "confidence": 0.95, "source_context": "..."}
  ],
  "rejected_facts": [
    {"draft_fact": "...", "reason": "sensitive|duplicate|unclear"}
  ],
  "summary": "..."
}
```

## Database Schema

```sql
-- Core memory storage
CREATE TABLE user_memory_items (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    fact TEXT NOT NULL,
    category memory_category ENUM,
    embedding vector(1536),  -- pgvector
    relevance_score FLOAT DEFAULT 1.0,
    source_conversation_id UUID,
    extraction_context TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    retrieval_count INTEGER DEFAULT 0,
    last_retrieved_at TIMESTAMP,
    user_edited_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- User memory settings
CREATE TABLE user_memory_settings (
    id UUID PRIMARY KEY,
    user_id UUID UNIQUE,
    memory_enabled BOOLEAN DEFAULT TRUE,
    auto_extract_enabled BOOLEAN DEFAULT TRUE,
    max_memory_items INTEGER DEFAULT 100,
    context_injection_count INTEGER DEFAULT 5,
    retrieval_threshold FLOAT DEFAULT 0.6,
    retention_days INTEGER DEFAULT 0,
    last_extraction_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Audit logs
CREATE TABLE memory_extraction_logs (
    id UUID PRIMARY KEY,
    user_id UUID,
    conversation_id UUID,
    facts_extracted_count INTEGER,
    facts_rejected_count INTEGER,
    rejection_reasons JSON,
    llm_prompt_tokens INTEGER,
    llm_completion_tokens INTEGER,
    trigger VARCHAR(50),  -- post_conversation|manual|periodic
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Retrieval analytics
CREATE TABLE memory_retrieval_logs (
    id UUID PRIMARY KEY,
    user_id UUID,
    conversation_id UUID,
    retrieved_memory_ids JSON,
    user_message TEXT,
    max_similarity_score FLOAT,
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Migration

Run the alembic migration to create all tables:

```bash
cd backend
alembic upgrade head  # Runs 0004_memory_tables.py
```

## Usage Examples

### Starting a Conversation with Memory

```python
# Frontend calls POST /chat/stream with user's opening message
# Backend automatically:
# 1. Retrieves relevant memories
# 2. Injects into system prompt
# 3. Streams personalized response

response = await fetch("/api/chat/stream", {
    method: "POST",
    body: JSON.stringify({
        conversation_id: "...",
        messages: [
            { role: "user", content: "Help me with my Python project" }
        ]
    })
})

# LLM receives injection like:
# System: "The user has the following preferences:
#  • Prefers concise, technical explanations
#  • Skilled in Python and Go
#  • Working on microservices with Docker/Kubernetes"
```

### Manual Memory Management

```python
# Create new memory
curl -X POST "http://localhost:8000/api/memory/items" \
  -H "Authorization: Bearer $TOKEN" \
  -d "fact=I work in UTC timezone&category=constraints"

# Update memory
curl -X PUT "http://localhost:8000/api/memory/items/{item_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -d "fact=I work in UTC+5 timezone"

# Delete memory
curl -X DELETE "http://localhost:8000/api/memory/items/{item_id}" \
  -H "Authorization: Bearer $TOKEN"

# Disable memory system
curl -X PUT "http://localhost:8000/api/memory/settings" \
  -H "Authorization: Bearer $TOKEN" \
  -d "memory_enabled=false"
```

### Scheduled Jobs

For production, run these via Celery or APScheduler:

```python
# Post-conversation extraction (call after chat ends)
from app.services.memory_jobs import run_post_conversation_extraction
await run_post_conversation_extraction(
    user_id="...",
    conversation_id="...",
    db_url=DATABASE_URL,
)

# Periodic reindexing (daily)
from app.services.memory_jobs import batch_periodic_reindex
await batch_periodic_reindex(db_url=DATABASE_URL)

# Memory cleanup (weekly)
from app.services.memory_jobs import batch_cleanup
await batch_cleanup(db_url=DATABASE_URL)
```

## Configuration

### Memory Settings (Per User)

Users can control:
- `memory_enabled`: Master on/off toggle
- `auto_extract_enabled`: Auto-extraction from conversations
- `max_memory_items`: Maximum facts to store (100 default, evicts LRU)
- `context_injection_count`: How many memories to include (5 default)
- `retrieval_threshold`: Min similarity to include (0.6 default)
- `retention_days`: Delete memories older than N days (0 = forever)

### System Configuration

In `backend/app/config.py`:

```python
# Memory module settings
MEMORY_MAX_ITEMS = 100
MEMORY_CONTEXT_INJECTION_COUNT = 5
MEMORY_RETRIEVAL_THRESHOLD = 0.6
MEMORY_EMBEDDING_DIM = 1536  # OpenAI embeddings

# Extraction settings
MEMORY_EXTRACTION_MODEL = "gpt-4"  # Use capable model
MEMORY_EXTRACTION_TEMPERATURE = 0.3  # Lower = more consistent

# Job settings
MEMORY_EXTRACTION_TRIGGER = "post_conversation"  # When to extract
MEMORY_REINDEX_INTERVAL = "daily"  # Periodic reindexing
MEMORY_CLEANUP_INTERVAL = "weekly"  # Cleanup old items
```

## Testing

Run comprehensive tests:

```bash
cd backend
pytest tests/test_memory.py -v

# 30+ tests covering:
# - Fact extraction and validation
# - Duplicate detection
# - Semantic similarity ranking
# - CRUD operations
# - Memory limits and eviction
# - Context injection
# - Settings management
# - Audit logging
```

## Performance Considerations

1. **Embedding Generation**: Expensive LLM call. Cache embeddings in pgvector for semantic search.
2. **Retrieval**: Use pgvector's `<->` operator for efficient similarity search (~5ms for 1000 items).
3. **Memory Limits**: Evict least-recently-used memories when max reached.
4. **Async Jobs**: Run extraction/cleanup asynchronously (post_conversation, periodic).
5. **Batching**: Batch multiple user extractions in scheduled jobs.

## Security

- 🔒 Sensitive patterns blocked (passwords, API keys, credit cards)
- 🔒 Path traversal prevented (facts scoped to user only)
- 🔒 Extraction context truncated (no full conversation stored)
- 🔒 Memory injection doesn't leak to user (injected into system prompt invisibly)
- 🔒 Audit trail (all extractions logged with metadata)
- 🔒 User control (delete/edit any memory, disable entirely)

## Future Enhancements

1. **Embedding Generation**: Integrate OpenAI embeddings API for semantic search
2. **Custom Embeddings**: Use Sentence Transformers for on-premise deployment
3. **Fact Relationships**: Track connections between memories (e.g., "uses Python" → "works in ML")
4. **Conflict Resolution**: Detect contradictions (e.g., "works in NYC" vs. "works in SF")
5. **Memory Versioning**: Keep history of memory edits
6. **Sharing**: Share memories across team/organization members
7. **Analytics Dashboard**: Visualize memory extraction trends
8. **Smart Reminders**: Proactively suggest updates to memories

## Troubleshooting

### Memory not being retrieved
- Check `memory_enabled` setting
- Verify `retrieval_threshold` not too high (0.6-0.8 recommended)
- Check context injection count > 0

### High LLM token usage
- Reduce `context_injection_count` (fewer memories per chat)
- Increase `retention_days` (clean up old facts)
- Disable `auto_extract_enabled` to extract manually only

### Out of memory
- Reduce `max_memory_items` (triggers LRU eviction)
- Decrease `embedding` vector dimension (trade-off semantic quality)
- Shorten `extraction_context` length

## References

- [pgvector: PostgreSQL vector extension](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [Sentence Transformers](https://www.sbert.net/)
