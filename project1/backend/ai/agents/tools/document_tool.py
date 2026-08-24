"""Document search tool — searches the user's uploaded documents via RAG."""
from __future__ import annotations
from backend.core.logging import get_logger

logger = get_logger(__name__)


async def search_documents(
    question: str,
    collection_name: str,
    top_k: int = 4,
) -> str:
    """
    Search the user's uploaded documents for relevant information.
    Returns formatted excerpts with source citations.
    """
    try:
        from backend.ai.rag.vector_store import get_vector_store
        store = get_vector_store(collection_name)
        results = store.similarity_search_with_relevance_scores(question, k=top_k)

        if not results:
            return "No relevant content found in your uploaded documents."

        formatted = []
        for i, (doc, score) in enumerate(results, 1):
            filename = doc.metadata.get("filename", "unknown")
            page = doc.metadata.get("page", "")
            page_str = f" (page {page})" if page else ""
            excerpt = doc.page_content[:500]
            formatted.append(
                f"[Excerpt {i}] From: {filename}{page_str}\n"
                f"Relevance: {score:.2f}\n{excerpt}"
            )

        logger.info("doc_search_used", question=question, results=len(results))
        return f"Document excerpts for '{question}':\n\n" + "\n\n---\n\n".join(formatted)
    except Exception as exc:
        logger.error("doc_search_failed", error=str(exc))
        return f"Document search failed: {exc}"


def search_documents_sync(question: str, collection_name: str, top_k: int = 4) -> str:
    """Synchronous wrapper for use in LangChain tool binding."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    search_documents(question, collection_name, top_k)
                )
                return future.result(timeout=30)
        return loop.run_until_complete(search_documents(question, collection_name, top_k))
    except Exception as exc:
        return f"Document search error: {exc}"
