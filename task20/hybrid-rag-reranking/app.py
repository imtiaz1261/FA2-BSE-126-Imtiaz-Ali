"""app.py — Streamlit web interface for the Hybrid RAG system.

Lets you type a question, adjust hybrid retrieval weights live, and see
every pipeline stage (BM25 results, vector results, hybrid fusion,
reranking, and the final LLM answer) side by side. Also displays the
evaluation report/charts if you've already run scripts/evaluate.py.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

import config
from src.bm25_retriever import BM25Retriever
from src.vector_retriever import VectorRetriever
from src.hybrid_retriever import hybrid_fuse
from src.reranker import Reranker
from src.rag_chain import generate_answer

st.set_page_config(page_title="Hybrid RAG System", page_icon="🔎", layout="wide")


@st.cache_resource
def load_pipeline_components():
    """Loads all indexes/models once and caches them across reruns —
    without this, Streamlit would reload the embedding model and
    cross-encoder on every single interaction, which is far too slow.
    """
    bm25 = BM25Retriever.load(config.BM25_INDEX_PATH)

    vector = VectorRetriever(config.EMBEDDING_MODEL_NAME)
    vector.load(config.FAISS_INDEX_PATH)

    reranker = Reranker(config.CROSS_ENCODER_MODEL_NAME)

    return bm25, vector, reranker


def load_api_key() -> str | None:
    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or "your_api_key_here" in api_key:
        return None
    return api_key


def render_results_table(title: str, results, score_label: str = "Score") -> None:
    st.markdown(f"**{title}**")
    if not results:
        st.caption("No results.")
        return
    for r in results:
        st.write(f"`{r.doc_id}`  —  {score_label}: {r.score:.3f}")
        st.caption(r.text[:180] + ("..." if len(r.text) > 180 else ""))


def main() -> None:
    st.title("🔎 Hybrid RAG System")
    st.caption("BM25 + Vector Search + Cross-Encoder Reranking")

    # --- Sidebar: configurable hybrid weights (bonus feature) ---
    with st.sidebar:
        st.header("Settings")

        bm25_weight = st.slider("BM25 weight", 0.0, 1.0, config.BM25_WEIGHT, 0.05)
        vector_weight = round(1.0 - bm25_weight, 2)
        st.caption(f"Vector weight (auto): {vector_weight}")

        top_k_final = st.slider("Final results to show", 1, 5, config.TOP_K_RERANKED)

        st.divider()
        st.caption(
            f"Embedding model: `{config.EMBEDDING_MODEL_NAME}`\n\n"
            f"Cross-encoder: `{config.CROSS_ENCODER_MODEL_NAME}`\n\n"
            f"LLM: `{config.LLM_MODEL_NAME}` (via Groq)"
        )

    # --- Check prerequisites before doing anything else ---
    if not config.BM25_INDEX_PATH.exists() or not config.FAISS_INDEX_PATH.exists():
        st.error(
            "No index found. Run `python scripts/ingest.py` first, "
            "then restart this app."
        )
        return

    api_key = load_api_key()
    if not api_key:
        st.error(
            "GROQ_API_KEY missing. Add it to your `.env` file, then restart this app."
        )
        return

    bm25, vector, reranker = load_pipeline_components()
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    # --- Main query interface ---
    query = st.text_input("Ask a question about the document corpus:", "")
    run_search = st.button("Search", type="primary")

    if not (run_search and query.strip()):
        st.info("Enter a question above and click Search.")
        return

    with st.spinner("Retrieving and reranking..."):
        bm25_results = bm25.search(query, top_k=config.TOP_K_BM25)
        vector_results = vector.search(query, top_k=config.TOP_K_VECTOR)

        hybrid_results = hybrid_fuse(
            bm25_results, vector_results,
            bm25_weight=bm25_weight, vector_weight=vector_weight,
            top_k=config.TOP_K_HYBRID,
        )

        reranked_results = reranker.rerank(query, hybrid_results, top_k=top_k_final)

    with st.spinner("Generating answer..."):
        answer = generate_answer(client, config.LLM_MODEL_NAME, query, reranked_results)

    st.subheader("Answer")
    st.success(answer)

    st.divider()
    st.subheader("Pipeline stages")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_results_table("BM25 (sparse)", bm25_results)
    with col2:
        render_results_table("Vector (dense)", vector_results)
    with col3:
        render_results_table("Hybrid fused", hybrid_results)
    with col4:
        render_results_table("Reranked (final)", reranked_results)

    # --- Evaluation report viewer, if it's been generated ---
    report_path = config.REPORTS_DIR / "evaluation_report.md"
    chart_path = config.REPORTS_DIR / "metrics_comparison.png"
    latency_chart_path = config.REPORTS_DIR / "latency_comparison.png"

    if report_path.exists():
        st.divider()
        with st.expander("📊 View evaluation report (from scripts/evaluate.py)"):
            if chart_path.exists():
                st.image(str(chart_path), caption="Metric comparison across methods")
            if latency_chart_path.exists():
                st.image(str(latency_chart_path), caption="Latency by method")
            st.markdown(report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
