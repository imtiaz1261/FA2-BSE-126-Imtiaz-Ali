# RAG Module Quick Start Guide

## Installation & Setup

### 1. Backend Dependencies

Add to `backend/requirements.txt`:
```
PyPDF2==3.0.1
python-docx==0.8.11
pgvector==0.2.4
openai==1.0.0
slowapi==0.1.8
```

Install:
```bash
cd backend
pip install -r requirements.txt
```

### 2. Database Migration

Run Alembic migration to create tables:
```bash
cd backend
alembic upgrade head
```

This creates:
- `uploaded_documents`
- `document_chunks`
- `document_embeddings`
- `upload_jobs`
- Enables pgvector extension

### 3. Environment Variables

Add to `.env`:
```bash
# OpenAI API
OPENAI_API_KEY=sk-...

# Database (PostgreSQL with pgvector)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/rag_db

# Frontend URL
FRONTEND_URL=http://localhost:3000
```

### 4. Start Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Available endpoints:
- `POST /documents/upload`
- `GET /documents/status/{job_id}`
- `GET /documents`
- `DELETE /documents/{document_id}`
- `POST /documents/retrieve`

### 5. Frontend Setup

Install dependencies:
```bash
cd frontend
npm install
```

Environment config in `.env`:
```bash
VITE_API_URL=http://localhost:8000
```

Start dev server:
```bash
npm run dev
```

---

## Basic Usage

### Upload a Document

```tsx
import { DocumentUpload } from "@/components/DocumentUpload";

export function ChatView() {
  return (
    <DocumentUpload
      conversationId={conversationId}
      onUploadComplete={(doc) => {
        console.log("Document ready:", doc.filename);
      }}
      onError={(error) => {
        console.error("Upload failed:", error);
      }}
    />
  );
}
```

### View Indexed Documents

```tsx
import { FileManager } from "@/components/FileManager";

export function DocumentsPanel() {
  return (
    <FileManager
      conversationId={conversationId}
      onDocumentDeleted={(docId) => {
        console.log("Deleted:", docId);
      }}
    />
  );
}
```

### Render Citations

```tsx
import { CitationRenderer, CitationList } from "@/components/CitationRenderer";

export function ChatMessage({ content, citations }) {
  return (
    <div>
      <CitationRenderer
        content={content}
        citations={citations}
        onCitationClick={(c) => console.log("Clicked:", c.filename)}
      />
      <CitationList citations={citations} />
    </div>
  );
}
```

### Retrieve Chunks for RAG

```tsx
import { retrieveChunks } from "@/lib/documentsApi";

async function queryDocuments() {
  const result = await retrieveChunks(
    "What are the main features?",
    conversationId,
    5  // top_k
  );

  console.log(`Found ${result.chunks.length} chunks:`);
  result.chunks.forEach((chunk, i) => {
    console.log(`[${i}] ${chunk.filename} - ${chunk.text.substring(0, 100)}`);
  });
}
```

---

## Testing

### Test Endpoint

```bash
# Upload a file
curl -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "conversation_id=550e8400-e29b-41d4-a716-446655440000"

# Expected response:
# {
#   "job_id": "...",
#   "document_id": "...",
#   "status": "pending",
#   "progress": 0
# }
```

### Poll Status

```bash
curl http://localhost:8000/documents/status/{job_id} \
  -H "Authorization: Bearer YOUR_TOKEN"

# Returns until status is "ready" or "failed"
```

### List Documents

```bash
curl http://localhost:8000/documents?conversation_id={id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Retrieve Chunks

```bash
curl -X POST \
  "http://localhost:8000/documents/retrieve?query=features&top_k=5" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

---

## Configuration

### Change Chunk Size

**Backend:** `app/services/document_processor.py`
```python
TARGET_CHUNK_SIZE_TOKENS = 500      # Change to desired size
TARGET_CHUNK_SIZE_CHARS = 2000      # Auto-calculated
CHUNK_OVERLAP_TOKENS = 100          # Overlap for context
```

### Change Embedding Model

**Backend:** `app/services/embeddings.py`
```python
# Use different OpenAI model
embedding_service = EmbeddingService(
    model="text-embedding-3-large"  # or other model
)
```

Or swap in custom embedding provider:
```python
class CustomEmbeddings(EmbeddingService):
    def embed_text(self, text: str) -> list[float]:
        # Your custom embedding logic
        return embedding_vector
```

### Change Retrieval Weights

**Backend:** `app/services/retrieval.py`
```python
BM25_WEIGHT = 0.3    # Increase for keyword-heavy queries
VECTOR_WEIGHT = 0.7  # Increase for semantic matching
```

### Change File Size Limit

**Backend:** `app/services/document_processor.py`
```python
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB
```

---

## Common Issues & Solutions

### "pgvector not found"
- Install: `pip install pgvector`
- Ensure PostgreSQL has vector extension
- Run migration: `alembic upgrade head`

### "Embedding generation failed"
- Check OpenAI API key is valid
- Verify network connectivity
- Check API rate limits
- Look in logs for error details

### "No chunks found for query"
- Verify document status is "ready"
- Try simpler query (common words)
- Check document had extractable text
- Query may be outside document scope

### "Upload stuck in processing"
- Check backend logs for errors
- Verify background task queue (Celery/RQ)
- Try different file format
- Check file size (<20MB)

### "Slow retrieval"
- Add database indexes
- Check query plan with `EXPLAIN`
- Reduce `top_k` parameter
- Profile with pgAdmin or similar

---

## Architecture Overview

```
Document Upload
      ↓
  Validate (type, size)
      ↓
  Extract Text (PDF/DOCX/TXT/CSV)
      ↓
  Chunk Text (~500 tokens)
      ↓
  Generate Embeddings (OpenAI 1536-dim)
      ↓
  Store in pgvector (PostgreSQL)
      ↓
                Ready for Retrieval
                      ↓
User Query → BM25 Search + Vector Search
                      ↓
            Merge & Rerank Results
                      ↓
          Return Top-5 with Citations
                      ↓
       Inject into LLM Prompt
                      ↓
            Generate Response
```

---

## Next Steps

1. **Deploy to Production**
   - Use managed PostgreSQL with pgvector
   - Set up Celery with Redis for background tasks
   - Configure CORS for production frontend URL
   - Use environment-based configuration

2. **Optimize Performance**
   - Add database query indexes
   - Implement vector search indexing (IVFFlat)
   - Cache retrieval results
   - Monitor API costs

3. **Enhance Features**
   - Add OCR for scanned PDFs
   - Support image extraction
   - Implement MMR deduplication
   - Add query expansion

4. **Monitor & Alert**
   - Track embedding quality
   - Monitor retrieval accuracy
   - Log all errors
   - Set up alerts for failures

---

## Support

For issues or questions:
1. Check `RAG_IMPLEMENTATION_COMPLETE.md` for detailed docs
2. Review component code comments
3. Check backend logs
4. Verify environment variables
5. Run tests from testing checklist

---

**Ready to index documents and start retrieving!** 🚀
