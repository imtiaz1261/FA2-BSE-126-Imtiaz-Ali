# Jarvis-Lite — Phase 1: Core RAG Engine

A production-style Retrieval-Augmented Generation pipeline: ingest PDF/DOCX/TXT
documents, chunk and embed them, store them in a local vector database, and
answer questions against them with cited sources. This is the foundation
`Jarvis-Lite` — the later phases (memory, agents, tool calling, voice,
authentication, Docker deployment) build on top of the classes here without
having to change them.

## What's implemented in this phase

- Multi-format document loading (PDF, DOCX, TXT) with per-page metadata for PDFs
- Text cleaning (whitespace/control-character normalization)
- Chunking via LangChain's `RecursiveCharacterTextSplitter`, with per-chunk metadata
- Embeddings — configurable provider: local HuggingFace (`sentence-transformers`,
  no API key) or OpenAI
- Vector storage — configurable backend: ChromaDB (primary) or FAISS (optional),
  both persisted to disk under `data/vector_db/`
- Retrieval — top-k similarity search with scores
- RAG generation — retrieved context → prompt → OpenAI chat completion → answer
  with numbered citations
- A CLI (`main.py`) to ingest files and ask questions without a web server
- Unit tests for every stage of the pipeline

**Explicitly out of scope for this phase** (coming later): voice (STT/TTS),
authentication, conversation memory, tool calling, agents, and the FastAPI
HTTP layer itself. The service classes are written so wrapping them in FastAPI
routes later is a thin layer, not a rewrite.

## Project structure

```text
jarvis_lite/
├── app/
│   ├── core/            # logging setup, shared exception hierarchy
│   ├── config/           # centralized Settings (reads .env once)
│   ├── loaders/           # PDF/DOCX/TXT loaders + factory that picks one by extension
│   ├── preprocess/        # text cleaning before chunking
│   ├── chunking/          # RecursiveCharacterTextSplitter wrapper + DocumentChunk
│   ├── embeddings/        # OpenAI / HuggingFace providers + factory
│   ├── vectorstore/       # Chroma (primary) / FAISS (optional) + factory
│   ├── retriever/         # embeds a query, runs similarity search
│   ├── rag/               # prompt builder + RAGService (retrieve -> generate -> cite)
│   ├── models/            # Pydantic response schemas (FastAPI-ready)
│   ├── services/          # IngestionService — the load->clean->chunk->embed->store pipeline
│   ├── utils/             # filesystem helpers
│   └── tests/             # pytest suite, one file per pipeline stage
├── data/
│   ├── uploads/            # where ingested source files live
│   └── vector_db/          # Chroma/FAISS persistence (gitignored)
├── main.py                 # CLI: `ingest` and `query` commands
├── requirements.txt
├── .env.example
└── README.md
```

Each folder is a single-responsibility layer, and every layer only talks to the
one below it through its factory (`embedding_factory.get_embedding_provider()`,
`vectorstore_factory.get_vector_store()`), so swapping OpenAI ↔ HuggingFace or
Chroma ↔ FAISS is a `.env` change, not a code change.

## Setup

```bash
cd jarvis_lite
python3.11 -m venv venv

# macOS/Linux
source venv/bin/activate
# Windows (PowerShell)
venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- Leave `EMBEDDING_PROVIDER=huggingface` to run fully local with no API key
  (first run downloads the small `all-MiniLM-L6-v2` model, ~90MB).
- Set `EMBEDDING_PROVIDER=openai` and fill in `OPENAI_API_KEY` for
  OpenAI embeddings instead.
- **Either way**, set `OPENAI_API_KEY` — the final answer-generation step
  always calls the OpenAI chat model, even when embeddings are local.
- Leave `VECTOR_DB_PROVIDER=chroma`, or switch to `faiss` if you'd rather not
  install/run Chroma.

## Running it

```bash
# Put a file in data/uploads/, then:
python main.py ingest data/uploads/handbook.pdf

python main.py query "What is the refund policy?"
python main.py query "What is the refund policy?" --top-k 6
```

Example output:

```text
Answer:
Refunds are accepted within 30 days of purchase [1]. Shipping normally takes
3-5 business days [2].

Sources:
  - handbook.pdf, page 4
  - handbook.pdf, page 7
```

## Running the tests

```bash
pytest app/tests/ -v
```

Tests use a deterministic in-memory `DummyEmbeddingProvider` (no network, no
model download) and FAISS/Chroma with an isolated temp directory per test, so
they're safe to run repeatedly without polluting `data/vector_db/`. Tests for
whichever vector backend you haven't installed are skipped automatically.

## Roadmap (future phases)

- **Phase 2** — Conversation memory (short-term + persistent)
- **Phase 3** — Tool calling (calculator, web search, etc.)
- **Phase 4** — LangGraph agent orchestration
- **Phase 5** — Voice (speech-to-text / text-to-speech)
- **Phase 6** — Authentication
- **Phase 7** — FastAPI HTTP layer wrapping `IngestionService` / `RAGService`
- **Phase 8** — Docker deployment
