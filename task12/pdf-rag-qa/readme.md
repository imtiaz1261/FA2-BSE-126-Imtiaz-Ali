# PDF Question Answering System using RAG

A Retrieval-Augmented Generation (RAG) system that answers questions
using **only** the content of PDF documents you provide — it won't make
things up or use outside knowledge, and it says so explicitly when the
answer isn't in your document.

Built with LangChain, ChromaDB, free local HuggingFace embeddings, and
Groq's free hosted LLM API (Llama 3.3).

## Project Structure

```
pdf-rag-qa/
├── app.py              # Main CLI — run this to ask questions
├── ingest.py            # Run this first — processes PDFs into the vector DB
├── retriever.py          # Retrieval + QA chain logic
├── utils.py              # Shared validation & helper functions
├── requirements.txt
├── .env                  # Your real API key (never commit this)
├── .env.example           # Template showing what .env should contain
├── data/                  # Put your PDF(s) here
└── chroma_db/              # Generated automatically by ingest.py
```

## How Retrieval-Augmented Generation (RAG) works in this project

A plain LLM only knows what it learned during training — it has never
seen your PDF and can't answer questions about it. RAG solves this by
giving the LLM the *relevant part of your document* as context, right
inside the prompt, every time you ask a question:

```
Your PDF  --[ingest.py: split + embed]-->  ChromaDB (vector database)

Your question
      |
      v
[retriever.py: embed the question, search ChromaDB for the most similar chunks]
      |
      v
[stuff those chunks into a prompt: "Answer ONLY using this context: ..."]
      |
      v
[Groq LLM generates an answer grounded in that context]
      |
      v
Answer + which chunks/pages it came from
```

The key idea: instead of asking the LLM "what's the refund policy?" and
hoping it knows (it doesn't — it's never seen your document), we first
*retrieve* the 3-4 chunks of your PDF most likely to contain the answer,
then ask the LLM to *generate* an answer using only those chunks. That's
the "Retrieval" + "Augmented" + "Generation" in RAG.

## Installation

1. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

2. **Set up your API key**

   Get a free Groq API key at console.groq.com/keys (no credit card
   required), then create a `.env` file (copy `.env.example`) with:
   ```
   GROQ_API_KEY=your_actual_key_here
   ```

3. **Add your PDF(s)**

   Place one or more `.pdf` files in the `data/` folder.
<img width="451" height="354" alt="Screenshot 2026-07-18 151856" src="https://github.com/user-attachments/assets/0feb4ce2-a98e-4a85-be8c-5b245699a9b8" />
<img width="527" height="362" alt="Screenshot 2026-07-18 151822" src="https://github.com/user-attachments/assets/1a3c1c91-702c-4c3d-a7b2-8cce15335eb6" />
<img width="518" height="382" alt="Screenshot 2026-07-18 151732" src="https://github.com/user-attachments/assets/967e10f8-5f95-4f75-b55e-f119d7615caf" />
<img width="540" height="381" alt="Screenshot 2026-07-18 151613" src="https://github.com/user-attachments/assets/a7557d77-1a8f-498c-b244-c86dc1df9834" />

## Usage

**Step 1 — Ingest your PDF(s)** (run this once, or whenever you change
the PDFs in `data/`):
```
python ingest.py
```
This loads every PDF, splits it into chunks, embeds them, and saves
everything to `chroma_db/`.

**Step 2 — Ask questions:**
```
python app.py
```
```
Ask a question about your PDF: What is the refund policy?

======================================================================
Question: What is the refund policy?
======================================================================

Retrieved chunks:

  [1] data/sample.pdf (page 2)
      Customers may request a refund within 30 days of purchase...

  [2] data/sample.pdf (page 3)
      Refunds are processed within 5-7 business days after approval...

Answer:
  Customers can request a refund within 30 days of purchase, provided
  the item is unused. Refunds are processed within 5-7 business days.

Source page(s): 2, 3
======================================================================
```

Type `exit` or `quit` to leave.

## Error handling

This project handles these cases gracefully, with clear messages instead
of raw stack traces:

| Situation                          | What happens                                          |
|--------------------------------------|-----------------------------------------------------------|
| Missing/placeholder `GROQ_API_KEY`  | Clear error before any API call is attempted            |
| No PDFs in `data/`                  | `ingest.py` stops immediately with an actionable message |
| Empty question                      | Rejected before spending an API call on it               |
| `app.py` run before `ingest.py`      | Detected, tells you to run `ingest.py` first             |

## Code walkthrough

### 1. Document Loading (`ingest.py` -> `load_pdfs`)
`PyPDFLoader` reads each PDF **page by page**, creating one LangChain
`Document` per page. Each Document automatically carries metadata like
`{"source": "data/sample.pdf", "page": 2}` — this is what makes it
possible to tell you exactly which page an answer came from later.

### 2. Text Splitting (`ingest.py` -> `split_documents`)
Pages are broken into ~1000-character chunks with 200-character overlap
using `RecursiveCharacterTextSplitter`. Splitting matters because whole
pages are often too large and unfocused for the embedding model to
represent well, and because the LLM's context window has limits. The
overlap prevents ideas that fall on a chunk boundary from being cut in
half — each chunk shares a bit of text with its neighbors.

### 3. Embeddings (`ingest.py` / `retriever.py`)
`HuggingFaceEmbeddings` (`all-MiniLM-L6-v2`) converts each chunk's text
into a 384-number vector that captures its *meaning*, not just its exact
words — so a question about "cost" can still match a chunk that says
"price" or "fee." This runs locally on your machine, free, no API key.

### 4. Vector Database (`ingest.py` -> `create_vector_store`)
ChromaDB stores every `(chunk text, vector, metadata)` triple on disk in
`chroma_db/`. Because it's persistent, you only pay the cost of
embedding your PDFs once — every future question just queries the
already-built database.

### 5. Similarity Search (`retriever.py` -> `vector_store.as_retriever`)
When you ask a question, it's embedded with the *same* model used during
ingestion, then ChromaDB finds the chunks whose vectors are closest to
the question's vector (by cosine/Euclidean distance) — this is
"similarity search."

### 6. Retriever (`retriever.py` -> `build_qa_chain`)
The retriever wraps that similarity search into a standard LangChain
interface (`search_kwargs={"k": 4}` — return the top 4 matches), so it
can be plugged directly into a chain.

### 7. RetrievalQA (`retriever.py` -> `RetrievalQA.from_chain_type`)
This chain automates the full loop: take a question -> retrieve chunks
-> insert them into the prompt -> call the LLM -> return the answer plus
the source documents used (`return_source_documents=True`).

### 8. Prompt Flow (`retriever.py` -> `QA_PROMPT_TEMPLATE`)
The prompt template is what actually enforces "answer only from the
document": it instructs the LLM to use *only* the provided context and
to respond with the exact fallback sentence if the answer isn't there.
This is the difference between a RAG system and just a chatbot with some
extra text pasted in — the prompt explicitly constrains the LLM's
behavior.

## Future improvements

- **Multiple PDFs simultaneously** — already partially supported
  (`ingest.py` loads every PDF in `data/`), but could add per-document
  filtering so users can ask "only search in report.pdf."
- **Chat history / memory** — let follow-up questions like "what about
  the second point?" work by feeding recent Q&A pairs into the prompt.
- **Streamlit interface** — a web UI for uploading PDFs and chatting,
  instead of the CLI.
- **FAISS support** — an alternative vector store, often faster for very
  large document collections.
- **Hybrid search** — combine vector similarity search with traditional
  keyword search (BM25) for better recall on exact terms/numbers.
- **Metadata filtering** — let users restrict retrieval to a specific
  page range, date, or document.
- **Citation generation** — have the LLM cite which retrieved chunk
  supports each specific claim in its answer.
- **PDF highlighting** — visually highlight the exact source passage in
  the original PDF.
- **Local LLM via Ollama** — swap Groq for a fully offline model, so the
  entire pipeline (embeddings + LLM) runs with zero internet dependency.
- **Different HuggingFace embedding models** — larger models (e.g.
  `all-mpnet-base-v2`) trade speed for better retrieval accuracy.

## Testing notes

Before delivering this project, the following was verified directly:
- All error-handling paths in `utils.py` (missing API key, placeholder
  key, missing PDF directory, empty PDF directory, empty question,
  missing/empty vector store) — tested with real inputs, all pass.
- `RecursiveCharacterTextSplitter` chunking behavior — tested with real
  LangChain splitter on a multi-chunk document, confirmed chunk sizes,
  overlap, and metadata preservation all work correctly.
- `answer_question()`'s result formatting (source page extraction,
  content previews, the "not found" fallback case) — tested with a
  mocked QA chain, since live Groq/embedding calls require network
  access this environment doesn't have; you should still do a real
  end-to-end run with your own PDF and API key before considering it
  fully verified in your environment.
