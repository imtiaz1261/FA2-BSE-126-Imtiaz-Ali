# Multi-Document Question Answering System

A Retrieval-Augmented Generation (RAG) application that reads PDF, DOCX,
and TXT files, indexes them in a vector database, and answers questions
**using only the content of those documents**. Built with LangChain,
ChromaDB, and Sentence Transformers.

If the answer isn't in your documents, the system says so honestly:
> "I couldn't find the answer in the provided documents."

---

## 1. How it works (Complete RAG Workflow)

```
 data/*.pdf, *.docx, *.txt
          │
          ▼
   ┌─────────────┐   1. LOAD          loader.py
   │  Documents   │   extract text + metadata (file, page, paragraph)
   └─────────────┘
          │
          ▼
   ┌─────────────┐   2. SPLIT         splitter.py
   │   Chunks     │   RecursiveCharacterTextSplitter (1000 / 200 overlap)
   └─────────────┘
          │
          ▼
   ┌─────────────┐   3. EMBED         embeddings.py
   │  Embeddings  │   Sentence Transformers (default) or OpenAI
   └─────────────┘
          │
          ▼
   ┌─────────────┐   4. STORE         vector_store.py
   │  ChromaDB /  │   persisted locally, reused across runs
   │    FAISS     │
   └─────────────┘
          │
   user question
          │
          ▼
   ┌─────────────┐   5. RETRIEVE      retriever.py
   │  Top-K chunks│   similarity search on the query embedding
   └─────────────┘
          │
          ▼
   ┌─────────────┐   6. GENERATE      qa_chain.py
   │   LLM answer │   answer built ONLY from retrieved context
   └─────────────┘
          │
          ▼
     app.py displays: question, answer, and source(s)
```

---

## 2. Project structure

```
multi-document-qa/
│
├── app.py              # Main entry point / CLI loop (ties everything together)
├── loader.py            # Document Loading + Metadata Extraction
├── splitter.py          # Text Splitting (RecursiveCharacterTextSplitter)
├── embeddings.py         # Embedding Generation (Sentence Transformers / OpenAI)
├── vector_store.py       # Vector Database (Chroma / FAISS) build + persist + load
├── retriever.py          # Retriever + similarity search helper
├── qa_chain.py           # RetrievalQA chain with a strict "context-only" prompt
├── config.py             # All configuration, read from .env with sane defaults
├── utils.py              # Logging setup + small validation helpers
├── requirements.txt
├── README.md
├── .env.example          # Copy to .env and customize
├── data/                 # Put your PDF / DOCX / TXT files here
│   ├── sample.pdf
│   ├── sample.docx
│   └── sample.txt
├── chroma_db/             # Persisted vector database (auto-created)
└── logs/                  # app.log (auto-created)
```

---

## 3. Setup

### 3.1 Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3.2 Configure environment

```bash
cp .env.example .env
```

Embeddings and retrieval run fully offline (local Sentence Transformers +
local Chroma). Generating the final answer needs a chat LLM — the default
provider is **Groq**, which offers a generous free tier with no credit
card:

1. Get a free key at https://console.groq.com/keys
2. Put it in your own local `.env` file: `GROQ_API_KEY=gsk_...`
3. Never commit `.env` or paste a real key into source files — `.env` is
   already listed in `.gitignore` for this reason.

You only need to edit `.env` further if you want to:
- Use OpenAI instead (add `OPENAI_API_KEY`, set `LLM_PROVIDER=openai` and/or `EMBEDDING_PROVIDER=openai`)
- Use a fully local LLM via Ollama (set `LLM_PROVIDER=ollama`, run `ollama serve`)
- Switch the vector store to FAISS (`VECTOR_STORE_PROVIDER=faiss`)
- Change chunk size, top-k, model names, etc.

### 3.3 Add your documents

Drop your `.pdf`, `.docx`, and `.txt` files into `data/`. Three sample
files are already included so you can try the system immediately.

---

## 4. Usage

```bash
python app.py
```

First run: builds the vector store from everything in `data/` and
persists it to `chroma_db/`. Subsequent runs load the existing store
instantly — no re-embedding needed.

```bash
python app.py --rebuild          # force a fresh rebuild (e.g. after adding files)
python app.py --show-context     # also print the raw retrieved chunks
python app.py --data-dir ./other_folder
```

Example session:

```
Question: What is ChromaDB?

Answer: ChromaDB is an open-source embedded vector database that stores
embeddings locally and supports fast similarity search.

Sources:
  - sample.docx (paragraph 5)
```

Type `exit` or `quit` to leave the loop.

---

## 5. Component explanations

**Document Loading (`loader.py`)** — Reads each supported file type with
the right tool (`pypdf` for PDFs, `python-docx` for Word, plain read for
`.txt`) and wraps every extracted section in a LangChain `Document` with
metadata: `file_name`, `file_type`, `source` path, plus `page` (PDF) or
`paragraph` (DOCX) so every answer can be traced back to its origin.

**Metadata Extraction** — Happens inline with loading (see above). This
metadata rides along through splitting and embedding automatically,
which is what lets the final answer cite "sample.pdf, page 2".

**Text Splitting (`splitter.py`)** — Uses `RecursiveCharacterTextSplitter`
(chunk size 1000, overlap 200) so each chunk is small enough to embed
meaningfully while overlap prevents ideas from being cut in half at a
chunk boundary.

**Embedding Generation (`embeddings.py`)** — Turns each text chunk into a
dense numeric vector that captures its meaning. Default: local, free
`all-MiniLM-L6-v2` (384 dimensions) via Sentence Transformers. Optional:
OpenAI's `text-embedding-3-small`.

**Vector Database (`vector_store.py`)** — Stores every chunk's embedding
alongside its metadata for fast nearest-neighbor lookup. ChromaDB
persists to a local folder automatically; FAISS is supported as an
alternative backend. Once built, the store is reused across runs.

**Similarity Search / Retriever (`retriever.py`)** — Embeds the user's
question with the *same* embedding model used for the documents, then
finds the Top-K chunks whose vectors are closest (most semantically
similar) to the question's vector.

**RetrievalQA Chain (`qa_chain.py`)** — Combines the retriever with an
LLM behind a strict prompt: *"answer only from this context; if it's not
there, say you couldn't find it."* This is what makes the system
trustworthy — it can't hallucinate an answer from the model's general
training knowledge.

**Complete RAG Workflow** — `app.py` orchestrates all of the above:
load → split → embed → store → retrieve → generate → display, with
error handling and logging at every stage.

---

## 6. Error handling

The system handles, with clear messages rather than stack traces:
- Missing / empty `data/` directory
- Unsupported file formats (skipped with a warning, not a crash)
- Empty or unreadable files (e.g. scanned/image-only PDFs)
- Missing or misconfigured embedding model
- Missing or corrupted vector database (falls back to rebuilding)
- Empty user query (`clean_query` in `utils.py`)
- Missing API keys for optional cloud providers

---

## 7. Logging

Every stage logs to both the console and `logs/app.log`:
- Document loading (files found, sections extracted, warnings for skipped files)
- Chunk creation (counts, chunk size/overlap used)
- Embedding generation (model used, load success/failure)
- Retrieval operations (query, number of chunks retrieved)
- All errors, with enough context to debug without re-running

---

## 8. Future improvements

- [ ] Streamlit or Gradio web interface
- [ ] Drag-and-drop document upload
- [ ] Conversational memory (multi-turn chat with LangChain memory)
- [ ] Hybrid search (BM25 keyword search + vector search)
- [ ] Metadata filtering (e.g. "only search in report.pdf")
- [ ] Inline source citations within the generated answer text
- [ ] Multi-language document support
- [ ] OCR for scanned/image-based PDFs (e.g. via Tesseract)
- [ ] Local LLM support via Ollama (scaffolding already included)
- [ ] Pinecone / other managed vector DB integrations
- [ ] Streaming answers token-by-token

---

## 9. Tech stack

Python · LangChain · ChromaDB · FAISS (optional) · Sentence Transformers
· Groq API (default LLM) · OpenAI API (optional) · pypdf · python-docx
· python-dotenv · NumPy