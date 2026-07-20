"""
streamlit_app.py
-------------------
Bonus feature: a simple Streamlit web interface for the Semantic Search
Engine, offering the same functionality as the CLI (main.py) with a
friendlier UI: Top-K slider, category filter, semantic vs keyword
comparison, and latency display.

Run:
    streamlit run streamlit_app.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from src.data_loader import load_documents
from src.preprocessing import preprocess_documents, truncate_for_preview
from src.embedding_generator import EmbeddingGenerator
from src.vector_store import VectorStore
from src.semantic_search import SemanticSearchEngine
from src.keyword_search import KeywordSearchEngine

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "documents")

st.set_page_config(page_title="Semantic Search Engine", page_icon="🔎", layout="wide")


@st.cache_resource(show_spinner="Building search engines (documents, embeddings, index)...")
def build_engines(force_fallback: bool):
    documents = load_documents(DOCS_DIR)
    documents = preprocess_documents(documents)

    embedder = EmbeddingGenerator(force_fallback=force_fallback)
    clean_texts = [doc.metadata["clean_text"] for doc in documents]
    embeddings = embedder.get_or_create_embeddings(clean_texts, cache_name="doc_embeddings", show_progress=False)

    store = VectorStore(backend="faiss")
    metadatas = [
        {
            "doc_id": doc.doc_id,
            "filename": doc.filename,
            "title": doc.title,
            "category": doc.category or "uncategorized",
            "preview": truncate_for_preview(doc.metadata["clean_text"]),
        }
        for doc in documents
    ]
    store.add(embeddings, metadatas)

    keyword_engine = KeywordSearchEngine()
    keyword_engine.fit(clean_texts, metadatas)

    semantic_engine = SemanticSearchEngine(embedder, store)
    categories = sorted({m["category"] for m in metadatas})
    return semantic_engine, keyword_engine, categories, embedder.backend_name


def render_results(results, container):
    if not results:
        container.info("No results found.")
        return
    for rank, r in enumerate(results, start=1):
        meta = r["metadata"]
        with container.container(border=True):
            st.markdown(
                f"**#{rank}  {meta['title']}**  "
                f"&nbsp;·&nbsp; Doc ID `{meta['doc_id']}`  "
                f"&nbsp;·&nbsp; Score `{r['score']:.4f}`  "
                f"&nbsp;·&nbsp; Category `{meta['category']}`"
            )
            st.caption(meta["preview"])


def main():
    st.title("🔎 Semantic Search Engine")
    st.caption("100-document collection · Sentence embeddings · FAISS vector search")

    with st.sidebar:
        st.header("Settings")
        force_fallback = st.checkbox(
            "Use offline fallback embeddings (TF-IDF+SVD)",
            value=True,
            help=(
                "Enable if you don't have internet access to download the "
                "sentence-transformers model weights. Disable to use the "
                "real all-MiniLM-L6-v2 model for higher quality results."
            ),
        )
        top_k = st.slider("Top-K results", min_value=1, max_value=15, value=5)
        show_compare = st.checkbox("Compare with keyword (TF-IDF) search", value=False)

    semantic_engine, keyword_engine, categories, backend_name = build_engines(force_fallback)
    st.sidebar.success(f"Embedding backend: **{backend_name}**")

    with st.sidebar:
        category_filter = st.selectbox("Filter by category", options=["(all)"] + categories)
        category_filter = None if category_filter == "(all)" else category_filter

    query = st.text_input("Enter a natural-language search query", placeholder="e.g. renewable energy solutions")

    if query:
        outcome = semantic_engine.search(query, top_k=top_k, category_filter=category_filter)
        st.subheader("Semantic Search Results")
        st.metric("Search latency", f"{outcome['latency_ms']:.2f} ms")
        render_results(outcome["results"], st)

        if show_compare:
            st.subheader("Keyword (TF-IDF) Search Results")
            kw_results = keyword_engine.search(query, top_k=top_k)
            render_results(kw_results, st)
    else:
        st.info("Enter a query above to search the 100-document collection.")


if __name__ == "__main__":
    main()
