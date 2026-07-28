"""
tools/search_tool.py
----------------------
Web search wrapper for the research assistant, using DuckDuckGo via the
`ddgs` package -- free, no API key needed.
"""

from typing import List

from config import SEARCH_RESULTS_PER_TASK
from state import SourceResult
from utils import get_logger

logger = get_logger(__name__)


class SearchError(Exception):
    """Raised when the search backend fails."""


def search_web(query: str, max_results: int = SEARCH_RESULTS_PER_TASK) -> List[SourceResult]:
    """Run a DuckDuckGo text search and return a list of SourceResult dicts."""
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise SearchError(
            "ddgs package not installed. Run: pip install ddgs"
        ) from exc

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:
        raise SearchError(f"Web search failed for query '{query}': {exc}") from exc

    results: List[SourceResult] = []
    for r in raw_results:
        results.append(SourceResult(
            title=r.get("title", "Untitled"),
            url=r.get("href", ""),
            snippet=(r.get("body") or "").strip(),
        ))
    logger.info("Search for %r returned %d result(s).", query, len(results))
    return results


def dedupe_by_url(existing: List[SourceResult], new: List[SourceResult]) -> List[SourceResult]:
    """Merge new results into existing, dropping duplicate URLs."""
    seen_urls = {r["url"] for r in existing if r["url"]}
    merged = list(existing)
    for r in new:
        if r["url"] and r["url"] in seen_urls:
            continue
        merged.append(r)
        if r["url"]:
            seen_urls.add(r["url"])
    return merged
