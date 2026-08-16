# Jarvis-Lite — Vector Database & Semantic Search Module

Production-ready semantic search module for the Jarvis-Lite AI
Knowledge Assistant: indexes your documents into a vector database
and answers natural-language queries with the top-K most relevant
passages, complete with relevance scores and metadata.

## Architecture

```
                ┌────────────────────┐
   query / docs │  SemanticSearchEngine │   <- single entry point (search_engine.py)
                └─────────┬──────────┘
                          │
         ┌────────────────┼─────────────────┐
         ▼                                   ▼
┌─────────────────┐                ┌──────────────────┐
│ Embedding        │                │ Vector Store       │
│ Provider          │                │ Provider            │
│ (embeddings/)      │                │ (vector_stores/)      │
├─────────────────┤                ├──────────────────┤
│ sentence_transformers│  (default)   │ chroma  (default)     │
│ openai               │              │ pinecone (optional)   │
│ local_tfidf (offline)│              │ memory  (dev/test)    │
└─────────────────┘                └──────────────────┘
```

Both embeddings and the vector store are swappable via environment
variables — nothing else in the code changes. `document_loader.py`
handles reading + chunking source files; `config.py` centralizes and
validates all settings; `logger.py` / `exceptions.py` provide
structured logging and precise error types throughout.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env         # edit if you want non-default settings
```

The default configuration (`sentence_transformers` + `chroma`) works
out of the box — the embedding model downloads automatically on first
run (~90MB, one-time, needs internet) and Chroma persists its index
locally under `./chroma_db`.

## Quick Start

```bash
# 1. Index the 54 sample documents in data/documents/ and run demo queries
python test_search.py

# 2. Then search interactively any time after that
python query_cli.py
```

```
ask> how do I reset my password
  1. [0.812] How to Reset Your Password  (IT & Security)
     To reset a forgotten password, go to the login page and select 'Forgot password'...
  2. [0.640] Common Login Issues and Fixes  (Customer Support)
     Most login problems are resolved by clearing browser cookies...
```

### Fully offline dev/test run (no model download, no chromadb needed)

```bash
EMBEDDING_PROVIDER=local_tfidf VECTOR_DB_PROVIDER=memory python test_search.py
```

This uses a zero-dependency TF-IDF + LSA embedding provider and an
in-memory vector store — useful for CI or environments without
internet access. Semantic quality is noticeably lower than the neural
default; use it for pipeline testing, not production quality bars.

## Using it in your own code

```python
from search_engine import SemanticSearchEngine

engine = SemanticSearchEngine()          # reads settings from .env / environment
engine.index_documents("data/documents") # loads, chunks, embeds, and upserts

results = engine.search("how do I get my password back", top_k=5)
for r in results:
    print(r.score, r.metadata["title"], r.metadata["filename"])
    print(r.document)
```

`search()` returns a list of `SearchResult(document, score, metadata)`:
- `score` — cosine similarity, 0 to 1, higher = more relevant
- `metadata` — `doc_id`, `filename`, `source`, `title`, `category`,
  `chunk_index`, `num_chunks`, `embedding_model`

Filter by metadata while still ranking by meaning:
```python
engine.search("VPN setup", top_k=5, filters={"category": "IT & Security"})
```

## Adding your own documents

Drop `.txt` or `.md` files into `data/documents/` (or point
`DOCUMENTS_DIR` elsewhere). Two supported formats:

**With title/category (recommended):**
```
Title: How to Reset Your Password
Category: IT & Security
---
To reset a forgotten password, go to the login page...
```

**Plain text (also works):** the filename becomes the title and
category defaults to "General".

Long documents are automatically split into overlapping chunks
(`CHUNK_SIZE` / `CHUNK_OVERLAP` env vars) so retrieval returns
focused passages instead of entire files.

Re-index after adding/changing documents:
```python
engine.reset_index()          # clears old vectors first (avoids stale duplicates)
engine.index_documents()
```

## Switching to Pinecone

```bash
pip install pinecone-client
```
```env
VECTOR_DB_PROVIDER=pinecone
PINECONE_API_KEY=your-key
PINECONE_INDEX_NAME=jarvis-knowledge-base
```
The serverless index is created automatically on first run if it
doesn't exist yet, with the correct dimension for your embedding model.

## Switching to OpenAI embeddings

```bash
pip install openai
```
```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=your-key
```

## Configuration reference

See `.env.example` for the full list — key ones:

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_PROVIDER` | `sentence_transformers` | `sentence_transformers` \| `openai` \| `local_tfidf` |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Model name for the chosen provider |
| `VECTOR_DB_PROVIDER` | `chroma` | `chroma` \| `pinecone` \| `memory` |
| `COLLECTION_NAME` | `jarvis_knowledge_base` | Collection/index name |
| `TOP_K` | `5` | Default number of results returned |
| `MIN_SCORE` | `0.0` | Drop results below this similarity score |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `100` | Document chunking (characters) |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |

## Error handling

All failures raise a typed exception from `exceptions.py`
(`ConfigurationError`, `ValidationError`, `EmbeddingError`,
`VectorStoreError`, `DocumentLoadError`), all subclasses of
`VectorSearchError` — catch that single base class if you just want
to handle "something in the search pipeline failed."

## Files

```
jarvis-vector-search/
├── config.py                 # env-var driven settings + validation
├── logger.py                 # centralized logging setup
├── exceptions.py              # typed exception hierarchy
├── document_loader.py         # reads + chunks .txt/.md files
├── search_engine.py           # SemanticSearchEngine — main entry point
├── embeddings/
│   ├── base.py                # BaseEmbeddingProvider interface
│   ├── sentence_transformer_provider.py   # default, local neural embeddings
│   ├── openai_provider.py     # OpenAI embeddings API
│   ├── local_tfidf_provider.py# offline TF-IDF/LSA fallback
│   └── factory.py
├── vector_stores/
│   ├── base.py                 # BaseVectorStore interface
│   ├── chroma_store.py         # default, persistent local vector DB
│   ├── pinecone_store.py       # optional managed cloud vector DB
│   ├── memory_store.py         # in-process, dev/test only
│   └── factory.py
├── data/
│   ├── documents/               # 54 sample knowledge-base .txt files
│   └── generate_documents.py    # regenerates the sample documents
├── test_search.py             # indexes 50+ docs, runs sample queries, asserts
├── query_cli.py                # interactive search CLI
├── requirements.txt
├── .env.example
└── README.md
```
