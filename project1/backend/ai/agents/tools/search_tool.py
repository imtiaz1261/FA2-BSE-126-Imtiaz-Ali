"""Web search tool — uses DuckDuckGo (free, no API key required)."""
from __future__ import annotations
from backend.core.logging import get_logger

logger = get_logger(__name__)


def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for current information using DuckDuckGo.
    Returns a formatted summary of the top results.
    """
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"**{r.get('title', 'No title')}**\n"
                    f"{r.get('body', '')}\n"
                    f"Source: {r.get('href', '')}"
                )
        if not results:
            return f"No results found for: {query}"
        logger.info("web_search_used", query=query, results=len(results))
        return f"Search results for '{query}':\n\n" + "\n\n---\n\n".join(results)
    except ImportError:
        return "Web search is not available (duckduckgo-search not installed)."
    except Exception as exc:
        logger.error("web_search_failed", error=str(exc))
        return f"Search failed: {exc}"
