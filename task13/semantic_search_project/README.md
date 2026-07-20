# Semantic Search Engine — 100 Document Collection

A beginner-to-intermediate AI project that generates dense vector
embeddings for a collection of 100 documents and implements a full
semantic search engine on top of them — built with **Sentence-Transformers**,
**FAISS** / **ChromaDB**, and clean, modular Python.

```
Search> renewable energy and climate solutions

Semantic Search Results
------------------------
  #1  Doc ID: 61   Score: 0.8661  Category: environment
       Title:   Renewable Energy Adoption
       Preview: Scientists and policymakers are prioritizing renewable
                 energy adoption to address pressing environmental
                 challenges...
  #2  Doc ID: 87   Score: 0.7204  Category: science
       Title:   Climate Modeling
       ...
  Search latency: 4.32 ms
```

## Features

- ✅ Loads and preprocesses 100 text documents (also supports **PDF**)
- ✅ Cleans / normalizes text (whitespace, encoding, unicode)
- ✅ Generates dense embeddings with **Sentence-Transformers** (`all-MiniLM-L6-v2`)
- ✅ Stores embeddings in **FAISS** (default) or **ChromaDB**
- ✅ Interactive terminal loop: Top-K semantic search with similarity scores
- ✅ **Bonus:** metadata (category) filtering
- ✅ **Bonus:** embedding cache (skips regeneration on repeat runs)
- ✅ **Bonus:** search latency reporting
- ✅ **Bonus:** side-by-side comparison with traditional TF-IDF keyword search
- ✅ **Bonus:** Streamlit web UI (`streamlit_app.py`)
- ✅ Automatic offline fallback (TF-IDF + SVD) if you don't have internet
  access to download the Sentence-Transformers model weights
- ✅ Unit-tested (`pytest`), modular, exception-handled

## Project Structure

```
semantic_search_project/
├── data/
│   └── documents/          # 100 sample .txt documents (10 categories)
├── scripts/
│   └── generate_sample_documents.py   # regenerates the sample corpus
├── src/
│   ├── data_loader.py       # loads .txt / .pdf documents from disk
│   ├── preprocessing.py     # text cleaning & normalization
│   ├── embedding_generator.py  # Sentence-Transformers + offline fallback + caching
│   ├── vector_store.py      # FAISS / ChromaDB wrapper + metadata filtering
│   ├── keyword_search.py    # TF-IDF baseline (bonus: semantic vs keyword comparison)
│   ├── semantic_search.py   # orchestrates embedding + vector search + latency
│   └── main.py               # CLI application (entry point)
├── streamlit_app.py         # bonus web UI
├── tests/
│   └── test_pipeline.py     # pytest unit/integration tests
├── cache/                    # cached embeddings (auto-created)
├── requirements.txt
└── README.md
```

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
```

> **Note on the embedding model:** the first time you run the app,
> `sentence-transformers` downloads the `all-MiniLM-L6-v2` weights
> (~90 MB) from Hugging Face Hub, so you'll need internet access once.
> After that, the model is cached locally by the library itself. If you
> have no internet access at all, pass `--force-fallback` (see below) to
> use a fully local TF-IDF + SVD embedding instead — the rest of the
> pipeline (vector search, filtering, CLI, Streamlit UI) works identically.

## Usage

### CLI (interactive)

```bash
python -m src.main
```

Then type natural-language queries at the `Search>` prompt. In-app commands:

| Command                | Effect                                             |
|-------------------------|-----------------------------------------------------|
| `:k <N>`                | change Top-K result count                          |
| `:filter <category>`    | restrict results to a category (e.g. `technology`) |
| `:filter` (no value)    | clear the category filter                          |
| `:compare`               | toggle showing keyword-search results alongside    |
| `:exit` / `:quit`       | leave the app                                       |

### CLI (single query, non-interactive)

```bash
python -m src.main --query "how is AI used in healthcare" --top-k 5
```

### Useful flags

```bash
python -m src.main --backend chroma          # use ChromaDB instead of FAISS
python -m src.main --force-fallback          # force offline TF-IDF+SVD embeddings
python -m src.main --docs-dir path/to/docs   # point at a different document folder
```

### Streamlit web UI (bonus)

```bash
streamlit run streamlit_app.py
```

Gives you a Top-K slider, category filter dropdown, keyword-vs-semantic
comparison toggle, and latency display in the browser.

### Running tests

```bash
pytest tests/ -v
```

### Regenerating the sample document corpus

```bash
python scripts/generate_sample_documents.py
```

This produces 100 `.txt` files across 10 topic categories (technology,
health, finance, sports, travel, education, environment, food, science,
business), each with a small `Title:` / `Category:` metadata header used
to demonstrate metadata filtering. **To use your own documents**, simply
point `--docs-dir` at a folder of `.txt` or `.pdf` files — the header is
optional.

## How It Works

1. **Load** — `data_loader.py` reads every `.txt`/`.pdf` file in the
   documents folder, handling encoding issues gracefully and parsing an
   optional metadata header.
2. **Preprocess** — `preprocessing.py` normalizes unicode, strips stray
   control characters, and collapses whitespace. (Deliberately light —
   modern embedding models want natural language, not stemmed/stopword
   -stripped text; that heavier normalization is reserved for the
   keyword-search baseline.)
3. **Embed** — `embedding_generator.py` encodes every document into a
   384-dimensional (MiniLM) L2-normalized vector. Results are cached to
   disk keyed by a hash of the corpus + model, so re-running the app
   doesn't regenerate embeddings unless the documents change.
4. **Index** — `vector_store.py` adds all vectors to a FAISS
   `IndexFlatIP` (inner product = cosine similarity for normalized
   vectors) or a ChromaDB collection.
5. **Search** — `semantic_search.py` embeds the user's query the same
   way, retrieves the Top-K nearest documents, and times the whole
   operation.
6. **Compare (bonus)** — `keyword_search.py` runs the same query through
   a classic TF-IDF cosine-similarity search so you can see, side by
   side, how semantic search finds conceptually related documents that
   don't share exact keywords, while keyword search cannot.

## Learning Outcomes Covered

- What text embeddings are and how they represent meaning as vectors
- Why semantic search finds conceptually similar content that keyword
  search misses (and where keyword search still wins — exact terms,
  IDs, names)
- How to build and query a vector index (FAISS / ChromaDB)
- Cosine similarity as the retrieval metric
- Clean modular architecture, caching, and exception handling for a
  small production-style NLP application

## Extending This Project

- Swap in `text-embedding-3-small` (OpenAI) by adding a new backend
  branch in `embedding_generator.py`
- Add hybrid search (weighted blend of semantic + keyword scores)
- Swap FAISS's `IndexFlatIP` for `IndexIVFFlat` / `IndexHNSWFlat` to
  scale past a few hundred thousand documents
- Add reranking with a cross-encoder for higher precision on the
  final Top-K
