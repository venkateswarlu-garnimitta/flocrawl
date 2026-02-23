"""
Web search module for Flocrawl.

Uses DuckDuckGo for search. No API keys required.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def search_web(
    query: str,
    max_results: int = 10,
    region: str = "wt-wt",
) -> List[Dict[str, Any]]:
    """
    Execute web search and return structured results.

    Uses DuckDuckGo. No API key or tokens required.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (default 10).
        region: Region/locale for search (e.g. wt-wt, us-en).

    Returns:
        List of dicts with keys: title, url, snippet (or body).
    """
    return _search_duckduckgo(query, max_results, region)


def _search_duckduckgo(
    query: str,
    max_results: int,
    region: str,
) -> List[Dict[str, Any]]:
    """Search using DuckDuckGo (no API key required)."""
    try:
        from duckduckgo_search import DDGS
    except ImportError as e:
        raise ImportError(
            "duckduckgo-search is required for web search. "
            "Install with: pip install duckduckgo-search"
        ) from e

    results: List[Dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, region=region, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("url", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                })
    except Exception as e:
        logger.exception("DuckDuckGo search failed")
        raise RuntimeError(f"Search failed: {e}") from e

    return results
