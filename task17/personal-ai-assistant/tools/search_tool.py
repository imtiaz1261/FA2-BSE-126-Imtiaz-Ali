"""
tools/search_tool.py
----------------------
Web search for current events and factual queries, using DuckDuckGo
via the `duckduckgo-search` (ddgs) package -- free, no API key needed.
"""

from langchain_core.tools import tool

from config import SEARCH_MAX_RESULTS
from utils import get_logger

logger = get_logger(__name__)


class SearchError(Exception):
    """Raised when the search backend fails."""


def run_web_search(query: str, max_results: int = SEARCH_MAX_RESULTS) -> str:
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise SearchError(
            "duckduckgo search package not installed. Run: pip install ddgs"
        ) from exc

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:
        raise SearchError(f"Web search failed: {exc}") from exc

    if not results:
        return f"No web search results found for '{query}'."

    lines = [f"Web search results for '{query}':"]
    for i, result in enumerate(results, start=1):
        title = result.get("title", "Untitled")
        snippet = result.get("body", "").strip()
        url = result.get("href", "")
        lines.append(f"{i}. {title}\n   {snippet}\n   Source: {url}")

    return "\n".join(lines)


@tool
def web_search(query: str) -> str:
    """
    Search the web for current events, news, or factual information
    not likely to be known from memory alone (e.g. "latest AI news",
    "who is the CEO of Microsoft"). Returns a short list of results
    with titles, snippets, and source URLs.
    """
    logger.info("Web search tool invoked with query: %r", query)
    try:
        return run_web_search(query)
    except SearchError as exc:
        logger.warning("Search error: %s", exc)
        return f"Error: {exc}"
