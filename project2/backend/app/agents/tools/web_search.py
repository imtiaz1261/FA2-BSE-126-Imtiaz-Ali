"""
Web search tool — Phase 12.

Uses the Tavily Search API for real-time web queries.  Falls back to a
stub message when no API key is configured so the agent degrades
gracefully rather than erroring.

The tool returns a compact Markdown snippet (title + URL + summary for
each result) so the LLM can synthesise an answer without embedding raw
HTML in the context window.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_MAX_RESULTS = 5
_SNIPPET_LEN = 300  # chars per result summary


def web_search(query: str, max_results: int = _MAX_RESULTS) -> str:
    """
    Search the web for up-to-date information.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        A Markdown-formatted string with search results, or an error/stub.
    """
    from app.core.config import settings  # lazy import to avoid circular deps

    api_key = settings.TAVILY_API_KEY or settings.WEB_SEARCH_API_KEY
    if not api_key:
        return (
            "Web search is not configured. "
            "Set TAVILY_API_KEY in your .env to enable real web search."
        )

    try:
        from tavily import TavilyClient  # lazy import — optional dep

        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=min(max_results, 10),
            search_depth="basic",
        )
        results: List[dict] = response.get("results", [])
        if not results:
            return f"No results found for: {query}"

        lines = [f"**Web search results for:** {query}\n"]
        for i, r in enumerate(results[:max_results], start=1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            snippet = (r.get("content") or r.get("snippet") or "")[:_SNIPPET_LEN]
            lines.append(f"**[{i}] {title}**")
            lines.append(f"URL: {url}")
            lines.append(snippet)
            lines.append("")

        return "\n".join(lines).strip()

    except ImportError:
        return (
            "tavily-python is not installed. "
            "Run: pip install tavily-python"
        )
    except Exception as exc:
        logger.exception("Web search failed for query: %s", query)
        return f"Web search error: {exc}"
