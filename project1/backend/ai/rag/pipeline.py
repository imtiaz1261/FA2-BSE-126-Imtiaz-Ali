"""
ai/rag/pipeline.py — Hybrid RAG Pipeline with Citations
=========================================================
Pipeline:
    Question
      ↓
    Vector Search  +  Keyword Search (hybrid)
      ↓
    Score-based Reranking
      ↓
    Top-K Context Chunks
      ↓
    LLM with citation instructions
      ↓
    Answer + CitationSource list
"""

from __future__ import annotations
import re
import time
from typing import Optional

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.ai.llm import count_tokens, get_llm
from backend.ai.guardrails.output_guard import check_output

logger = get_logger(__name__)

RAG_SYSTEM_PROMPT = """You are AIHub Assistant answering questions based ONLY on the provided document context.

Rules:
1. Answer using ONLY information from the provided context chunks.
2. If the answer is not in the context, say "I couldn't find information about this in the uploaded documents."
3. Always cite your sources using [Source N] notation inline.
4. Be precise and concise.
5. Never make up facts or citations.

Context:
{context}
"""


async def run_rag_query(
    question: str,
    collection_name: str,
    top_k: int = 5,
    mode: str = "hybrid",
    document_ids: Optional[list[str]] = None,
) -> dict:
    """
    Full RAG pipeline: retrieve → rerank → generate with citations.

    Args:
        question:        The user's question.
        collection_name: The user's vector store collection.
        top_k:           Number of chunks to retrieve.
        mode:            vector | keyword | hybrid
        document_ids:    If set, restrict search to these document IDs.

    Returns:
        dict with keys: answer, sources, prompt_tokens, completion_tokens, model
    """
    start = time.monotonic()

    # 1. Retrieve chunks
    chunks = await _retrieve_chunks(question, collection_name, top_k, mode, document_ids)

    if not chunks:
        return {
            "answer": "I couldn't find any relevant information in your uploaded documents for this question.",
            "sources": [],
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "model": settings.OPENAI_MODEL,
        }

    # 2. Build context string with source markers
    context_parts = []
    sources = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[Source {i}]\n{chunk['text']}")
        sources.append({
            "document_id": chunk.get("doc_id", ""),
            "filename": chunk.get("filename", "unknown"),
            "page": chunk.get("page"),
            "chunk_text": chunk["text"][:300],
            "score": round(chunk.get("score", 0.0), 4),
        })

    context = "\n\n".join(context_parts)

    # 3. Build prompt
    system_content = RAG_SYSTEM_PROMPT.format(context=context)
    prompt_tokens = count_tokens(system_content) + count_tokens(question)

    # 4. Call LLM
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        llm = get_llm(streaming=False)
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=question),
        ]
        response = await llm.ainvoke(messages)
        answer = response.content
        completion_tokens = count_tokens(answer)
    except Exception as exc:
        logger.error("rag_llm_error", error=str(exc))
        raise

    # 5. Output guardrail
    guard = check_output(answer)
    final_answer = guard.content

    # 6. Filter sources to only those cited
    cited_sources = _filter_cited_sources(final_answer, sources)

    latency = int((time.monotonic() - start) * 1000)
    logger.info(
        "rag_query_complete",
        chunks_retrieved=len(chunks),
        cited=len(cited_sources),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency,
    )

    return {
        "answer": final_answer,
        "sources": cited_sources,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "model": settings.OPENAI_MODEL,
    }


async def _retrieve_chunks(
    question: str,
    collection_name: str,
    top_k: int,
    mode: str,
    document_ids: Optional[list[str]],
) -> list[dict]:
    """Retrieve chunks using the selected strategy."""
    try:
        from backend.ai.rag.vector_store import get_vector_store
        store = get_vector_store(collection_name)

        # Build filter if document_ids specified
        filter_dict = None
        if document_ids:
            filter_dict = {"doc_id": {"$in": [str(d) for d in document_ids]}}

        results = []

        if mode in ("vector", "hybrid"):
            # Vector similarity search
            vector_results = store.similarity_search_with_relevance_scores(
                question,
                k=top_k,
                filter=filter_dict,
            )
            for doc, score in vector_results:
                results.append({
                    "text": doc.page_content,
                    "score": float(score),
                    "doc_id": doc.metadata.get("doc_id", ""),
                    "filename": doc.metadata.get("filename", ""),
                    "page": doc.metadata.get("page"),
                    "source": "vector",
                })

        if mode in ("keyword", "hybrid"):
            # Keyword search using MMR for diversity
            keyword_results = store.max_marginal_relevance_search(
                question,
                k=top_k // 2,
                filter=filter_dict,
            )
            existing_texts = {r["text"] for r in results}
            for doc in keyword_results:
                if doc.page_content not in existing_texts:
                    results.append({
                        "text": doc.page_content,
                        "score": 0.5,
                        "doc_id": doc.metadata.get("doc_id", ""),
                        "filename": doc.metadata.get("filename", ""),
                        "page": doc.metadata.get("page"),
                        "source": "keyword",
                    })

        # Sort by score descending, take top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    except Exception as exc:
        logger.error("rag_retrieval_failed", error=str(exc))
        return []


def _filter_cited_sources(answer: str, sources: list[dict]) -> list[dict]:
    """Return only sources that are actually cited in the answer."""
    cited_indices = set(re.findall(r'\[Source (\d+)\]', answer))
    if not cited_indices:
        return sources  # Return all if no explicit citations

    cited = []
    for idx_str in cited_indices:
        idx = int(idx_str) - 1
        if 0 <= idx < len(sources):
            cited.append(sources[idx])
    return cited
